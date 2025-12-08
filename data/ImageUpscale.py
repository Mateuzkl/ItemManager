import os
import subprocess
import numpy as np
from PIL import Image, ImageEnhance, ImageQt
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFrame, QSlider, 
                             QCheckBox, QComboBox, QTextEdit, QScrollArea, 
                             QFileDialog, QMessageBox, QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QImage

# --- CLASSE WORKER PARA PROCESSAMENTO EM BACKGROUND ---
# Isso é necessário para não travar a janela durante o processamento e
# para atualizar a UI de forma segura (sem crashar).
class ProcessingWorker(QThread):
    log_signal = pyqtSignal(str)      # Sinal para enviar texto ao log
    finished_signal = pyqtSignal()    # Sinal quando terminar tudo
    error_signal = pyqtSignal(str)    # Sinal em caso de erro

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.stop_requested = False

    def run(self):
        folder = self.params['folder']
        out_folder = os.path.join(folder, "output_processed")
        os.makedirs(out_folder, exist_ok=True)
        
        files_to_process = [f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))]
        count = 0

        waifu_exe = self.params['waifu_exe']
        
        for file in files_to_process:
            if self.stop_requested: break

            input_path = os.path.join(folder, file)
            temp_output = os.path.join(out_folder, "temp_" + file)
            final_output = os.path.join(out_folder, file)
            src = input_path

            self.log_signal.emit(f"Processing: {file}")

            # 1. Waifu2x Denoise
            if self.params['denoise_enabled']:
                cmd = [
                    waifu_exe, "-i", src, "-o", temp_output,
                    "-s", "1", "-m", "noise", "-n", self.params['denoise_level'], "-p", "cpu"
                ]
                subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                src = temp_output

            # 2. Waifu2x Upscale
            if self.params['upscale_enabled']:
                cmd = [
                    waifu_exe, "-i", src, "-o", temp_output,
                    "-s", self.params['upscale_factor'], "-m", "noise_scale", 
                    "-n", self.params['denoise_level'], "-p", "cpu"
                ]
                subprocess.run(cmd, creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                src = temp_output

            # 3. Pillow Processing (Resize, Color, Rotate)
            try:
                img = Image.open(src)
                
                # Resize logic
                if self.params['custom_resize_enabled']:
                    img = img.resize((self.params['custom_w'], self.params['custom_h']), Image.NEAREST)
                elif self.params['resize_enabled']:
                    size = self.params['resize_final']
                    img = img.resize((size, size), Image.NEAREST)

                # Visual adjustments
                img = self.apply_pillow_adjustments(img)
                img.save(final_output)
                
                count += 1

            except Exception as e:
                self.log_signal.emit(f"Error processing {file}: {str(e)}")

            # Cleanup temp
            if os.path.exists(temp_output):
                os.remove(temp_output)

        self.log_signal.emit(f"Completed! {count} images processed.")
        self.finished_signal.emit()

    def apply_pillow_adjustments(self, img):
        p = self.params
        img = ImageEnhance.Brightness(img).enhance(p['brightness'])
        img = ImageEnhance.Contrast(img).enhance(p['contrast'])
        img = ImageEnhance.Color(img).enhance(p['saturation'])

        img_np = np.array(img).astype(np.float32)

        # RGB Adjustments
        img_np[..., 0] = np.clip(img_np[..., 0] * p['red'], 0, 255)
        img_np[..., 1] = np.clip(img_np[..., 1] * p['green'], 0, 255)
        img_np[..., 2] = np.clip(img_np[..., 2] * p['blue'], 0, 255)

        img = Image.fromarray(img_np.astype(np.uint8))

        if p['rotation'] != 0:
            img = img.rotate(p['rotation'], expand=True)
        if p['flip_h']:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if p['flip_v']:
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            
        return img


# --- CLASSE PRINCIPAL DA ABA ---
class ImageUpscaleTab(QWidget):
    def __init__(self, parent_widget_ignored, base_path): 
        # Nota: em PyQt, geralmente não passamos o parent no __init__ se vamos adicionar em layout depois, 
        # mas mantive a assinatura similar para facilitar sua integração.
        super().__init__()
        self.base_path = base_path
        
        # Configurar caminho do executável Waifu
        self.waifu_exe = os.path.join(base_path, "waifu2x-caffe", "waifu2x-caffe-cui.exe")
        
        self.layout_main = QVBoxLayout(self)
        self.build_ui()
        self.build_loading_overlay()

    def build_ui(self):
        # --- PATH SELECTION ---
        path_frame = QFrame()
        path_layout = QHBoxLayout(path_frame)
        path_layout.setContentsMargins(0,0,0,0)
        
        self.path_entry = QLineEdit()
        self.path_entry.setPlaceholderText("Choose a folder...")
        btn_search = QPushButton("Search Folder")
        btn_search.clicked.connect(self.select_folder)
        
        path_layout.addWidget(QLabel("Path:"))
        path_layout.addWidget(self.path_entry)
        path_layout.addWidget(btn_search)
        
        self.layout_main.addWidget(path_frame)

        # --- ADVANCED ADJUSTMENTS (Group Box para organização) ---
        self.create_advanced_adjustments()

        # --- CONTROLS DENOISE / UPSCALE ---
        self.create_denoise_upscale_controls()

        # --- APPLY BUTTON ---
        self.btn_apply = QPushButton("Apply Processing")
        self.btn_apply.setFixedHeight(40)
        # Estilizando o botão para parecer com o do CustomTkinter (Laranja)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #ff9326;
                color: black;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ffa64c;
            }
            QPushButton:pressed {
                background-color: #e5821e;
            }
        """)
        self.btn_apply.clicked.connect(self.start_processing)
        self.layout_main.addWidget(self.btn_apply)

        # --- DISPLAY FRAMES (Log, Input, Output) ---
        self.create_display_frames()

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: lightgreen; font-weight: bold;")
        self.layout_main.addWidget(self.status_label)

    def create_advanced_adjustments(self):
        group = QGroupBox("Advanced Adjustments")
        layout = QGridLayout(group)
        
        # Helper para criar sliders (Qt usa int, precisamos converter para float logicamente)
        def create_slider(label_text, min_v, max_v, default_v, scale_factor=100):
            lbl = QLabel(label_text)
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(min_v * scale_factor), int(max_v * scale_factor))
            slider.setValue(int(default_v * scale_factor))
            return lbl, slider

        # Brilho, Contraste, Saturação
        l_br, self.slider_brightness = create_slider("Brightness", 0, 2, 1)
        l_ct, self.slider_contrast = create_slider("Contrast", 0, 2, 1)
        l_sat, self.slider_saturation = create_slider("Saturation", 0, 2, 1)

        layout.addWidget(l_br, 0, 0); layout.addWidget(self.slider_brightness, 0, 1)
        layout.addWidget(l_ct, 1, 0); layout.addWidget(self.slider_contrast, 1, 1)
        layout.addWidget(l_sat, 2, 0); layout.addWidget(self.slider_saturation, 2, 1)

        # RGB
        l_r, self.slider_red = create_slider("Red", 0, 2, 1)
        l_g, self.slider_green = create_slider("Green", 0, 2, 1)
        l_b, self.slider_blue = create_slider("Blue", 0, 2, 1)

        layout.addWidget(l_r, 0, 2); layout.addWidget(self.slider_red, 0, 3)
        layout.addWidget(l_g, 1, 2); layout.addWidget(self.slider_green, 1, 3)
        layout.addWidget(l_b, 2, 2); layout.addWidget(self.slider_blue, 2, 3)

        # Rotação e Flips
        l_rot, self.slider_rotate = create_slider("Rotation", 0, 360, 0, scale_factor=1) # Fator 1 pois é grau inteiro
        self.chk_flip_h = QCheckBox("Mirror Horizontal")
        self.chk_flip_v = QCheckBox("Mirror Vertical")

        layout.addWidget(l_rot, 3, 0); layout.addWidget(self.slider_rotate, 3, 1)
        layout.addWidget(self.chk_flip_h, 3, 2)
        layout.addWidget(self.chk_flip_v, 3, 3)

        self.layout_main.addWidget(group)

    def create_denoise_upscale_controls(self):
        frame = QFrame()
        layout = QHBoxLayout(frame)
        
        # Denoise
        self.chk_denoise = QCheckBox("Denoise")
        self.combo_denoise = QComboBox()
        self.combo_denoise.addItems(["0", "1", "2", "3"])
        self.combo_denoise.setCurrentText("1")
        layout.addWidget(self.chk_denoise)
        layout.addWidget(self.combo_denoise)
        
        # Separator
        line1 = QFrame(); line1.setFrameShape(QFrame.Shape.VLine); layout.addWidget(line1)

        # Upscale
        self.chk_upscale = QCheckBox("Upscale")
        self.combo_upscale = QComboBox()
        self.combo_upscale.addItems(["2", "4", "8"])
        layout.addWidget(self.chk_upscale)
        layout.addWidget(self.combo_upscale)

        # Separator
        line2 = QFrame(); line2.setFrameShape(QFrame.Shape.VLine); layout.addWidget(line2)

        # Resize Standard
        self.chk_resize = QCheckBox("Resize")
        self.combo_resize = QComboBox()
        self.combo_resize.addItems(["32", "64", "128", "240", "256", "512"])
        self.combo_resize.setEditable(True) # Permite digitar
        layout.addWidget(self.chk_resize)
        layout.addWidget(self.combo_resize)

        # Custom Resize
        line3 = QFrame(); line3.setFrameShape(QFrame.Shape.VLine); layout.addWidget(line3)
        
        self.chk_custom_resize = QCheckBox("Custom Size")
        self.entry_w = QLineEdit(); self.entry_w.setPlaceholderText("W"); self.entry_w.setFixedWidth(50)
        self.entry_h = QLineEdit(); self.entry_h.setPlaceholderText("H"); self.entry_h.setFixedWidth(50)
        
        layout.addWidget(self.chk_custom_resize)
        layout.addWidget(self.entry_w)
        layout.addWidget(self.entry_h)

        self.layout_main.addWidget(frame)

    def create_display_frames(self):
        display_container = QWidget()
        layout = QHBoxLayout(display_container)
        
        # --- LOG ---
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        log_layout.addWidget(self.log_box)
        
        # --- INPUT SCROLL ---
        input_group = QGroupBox("Main Folder")
        input_layout = QVBoxLayout(input_group)
        self.scroll_input = QScrollArea()
        self.scroll_input.setWidgetResizable(True)
        self.input_content = QWidget()
        self.input_content_layout = QVBoxLayout(self.input_content)
        self.scroll_input.setWidget(self.input_content)
        input_layout.addWidget(self.scroll_input)

        # --- OUTPUT SCROLL ---
        output_group = QGroupBox("Output")
        output_layout = QVBoxLayout(output_group)
        self.scroll_output = QScrollArea()
        self.scroll_output.setWidgetResizable(True)
        self.output_content = QWidget()
        self.output_content_layout = QVBoxLayout(self.output_content)
        self.scroll_output.setWidget(self.output_content)
        output_layout.addWidget(self.scroll_output)

        layout.addWidget(log_group, 1)
        layout.addWidget(input_group, 1)
        layout.addWidget(output_group, 1)

        self.layout_main.addWidget(display_container)

    def build_loading_overlay(self):
        # Overlay widget semi-transparente
        self.overlay = QFrame(self)
        self.overlay.setStyleSheet("background-color: rgba(0, 0, 0, 180);")
        self.overlay.hide()
        
        # Label de loading
        self.lbl_loading = QLabel("Processing...\nPlease Wait", self.overlay)
        self.lbl_loading.setStyleSheet("color: white; font-size: 24px; font-weight: bold;")
        self.lbl_loading.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def resizeEvent(self, event):
        # Garante que o overlay cubra tudo ao redimensionar
        self.overlay.resize(self.size())
        self.lbl_loading.resize(self.size())
        super().resizeEvent(event)

    def show_loading(self, show=True):
        if show:
            self.overlay.raise_()
            self.overlay.show()
            self.btn_apply.setEnabled(False)
        else:
            self.overlay.hide()
            self.btn_apply.setEnabled(True)

    # --- LOGIC ---

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.path_entry.setText(folder)
            self.load_images_to_scroll(folder, self.input_content_layout, is_input=True)

    def load_images_to_scroll(self, folder, layout, is_input=True):
        # Limpar layout
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()
        
        size = (100, 100) if is_input else (50, 50)
        
        if not os.path.exists(folder): return

        files = sorted([f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".bmp"))])
        
        # Limitando visualização para não travar se tiver 1000 imagens
        # O PyQt carrega tudo na RAM, então cuidado com pastas gigantes
        limit = 50 
        for i, file in enumerate(files):
            if i >= limit:
                layout.addWidget(QLabel(f"... and {len(files)-limit} more"))
                break
                
            path = os.path.join(folder, file)
            try:
                # Usando QPixmap para performance
                pix = QPixmap(path)
                if not pix.isNull():
                    pix = pix.scaled(size[0], size[1], Qt.AspectRatioMode.KeepAspectRatio)
                    lbl_img = QLabel()
                    lbl_img.setPixmap(pix)
                    lbl_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.addWidget(lbl_img)
            except:
                pass
        
        layout.addStretch() # Empurra itens para cima

    def log(self, message):
        self.log_box.append(message)

    def start_processing(self):
        folder = self.path_entry.text().strip()
        if not os.path.isdir(folder):
            QMessageBox.critical(self, "Error", "Invalid Folder!")
            return
            
        # Coletar parâmetros
        params = {
            'folder': folder,
            'waifu_exe': self.waifu_exe,
            
            'denoise_enabled': self.chk_denoise.isChecked(),
            'denoise_level': self.combo_denoise.currentText(),
            
            'upscale_enabled': self.chk_upscale.isChecked(),
            'upscale_factor': self.combo_upscale.currentText(),
            
            'resize_enabled': self.chk_resize.isChecked(),
            'resize_final': int(self.combo_resize.currentText()) if self.combo_resize.currentText().isdigit() else 32,
            
            'custom_resize_enabled': self.chk_custom_resize.isChecked(),
            'custom_w': 0,
            'custom_h': 0,
            
            # Ajustes Pillow (Sliders divididos por 100 ou 1)
            'brightness': self.slider_brightness.value() / 100.0,
            'contrast': self.slider_contrast.value() / 100.0,
            'saturation': self.slider_saturation.value() / 100.0,
            'red': self.slider_red.value() / 100.0,
            'green': self.slider_green.value() / 100.0,
            'blue': self.slider_blue.value() / 100.0,
            'rotation': self.slider_rotate.value(),
            'flip_h': self.chk_flip_h.isChecked(),
            'flip_v': self.chk_flip_v.isChecked()
        }

        # Validação Custom Resize
        if params['custom_resize_enabled']:
            try:
                params['custom_w'] = int(self.entry_w.text())
                params['custom_h'] = int(self.entry_h.text())
            except ValueError:
                QMessageBox.critical(self, "Error", "Invalid Custom Size (must be numbers)")
                return

        if not (params['denoise_enabled'] or params['upscale_enabled'] or params['resize_enabled'] or params['custom_resize_enabled']):
             QMessageBox.warning(self, "Warning", "Select at least one action (Denoise, Upscale or Resize)")
             return
             
        if (params['denoise_enabled'] or params['upscale_enabled']) and not os.path.isfile(self.waifu_exe):
             QMessageBox.critical(self, "Error", f"Waifu2x exe not found at:\n{self.waifu_exe}")
             return

        # Iniciar Worker
        self.show_loading(True)
        self.log_box.clear()
        
        self.worker = ProcessingWorker(params)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_processing_finished)
        self.worker.start()

    def on_processing_finished(self):
        self.show_loading(False)
        self.status_label.setText("Processing Finished!")
        folder = self.path_entry.text()
        out_folder = os.path.join(folder, "output_processed")
        self.load_images_to_scroll(out_folder, self.output_content_layout, is_input=False)
        QMessageBox.information(self, "Success", "All images processed successfully.")
