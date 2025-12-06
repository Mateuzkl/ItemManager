import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageEnhance
import numpy as np
import os
import subprocess
import threading

class ImageUpscaleTab(ctk.CTkFrame):
    def __init__(self, parent, base_path):
        super().__init__(parent)
        self.base_path = base_path
        
        # Configurar caminho do executável Waifu
        self.waifu_exe = os.path.join(base_path, "waifu2x-caffe", "waifu2x-caffe-cui.exe")
        
        self.input_photos = []
        self.output_photos = []
        
        self.build_ui()
        
        self.build_loading_overlay()        

    def build_ui(self):
        # Frame principal do Sprite Manager
        self.frame = ctk.CTkFrame(self, corner_radius=10)
        self.frame.pack(padx=10, pady=0, fill="x")

        # Pasta
        ctk.CTkLabel(self.frame, text="Path:").pack(pady=0)
        self.path_entry = ctk.CTkEntry(self.frame, placeholder_text="Choose a folder...")
        self.path_entry.pack(padx=10, pady=0, fill="x")
        ctk.CTkButton(self.frame, text="Search Folder", command=self.select_folder).pack(pady=5)

        # Ajustes avançados
        self.create_advanced_adjustments(self.frame)

        # Controles Denoise / Upscale
        self.create_denoise_upscale_controls(self.frame)

        ctk.CTkButton(
            self,
            text="Apply",
            height=25,
            font=("Arial", 16),
            fg_color="#ff9326",
            hover_color="#ffa64c",
            command=self.convert_images_thread
        ).pack(pady=5)

        # Frames para log e imagens
        self.create_display_frames(self)

        self.status = ctk.CTkLabel(self, text="Finish!", text_color="lightgreen")
        self.status.pack(pady=5)
        
        

    def build_loading_overlay(self):
        self.loading_overlay = ctk.CTkFrame(self, fg_color="gray10", corner_radius=0)
        
        # Cria o label centralizado
        self.loading_label = ctk.CTkLabel(
            self.loading_overlay, 
            text="Loading...", 
            font=("Arial", 24, "bold"),
            text_color="white"
        )
        self.loading_label.place(relx=0.5, rely=0.5, anchor="center")

    def show_loading(self, message="Loading..."):
        self.loading_label.configure(text=message)
        # Place cobrindo tudo (relwidth=1, relheight=1)
        self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # CRUCIAL: Força o desenho da tela antes de travar no processamento
        self.update() 

    def hide_loading(self):
        self.loading_overlay.place_forget()
        
        

    # ------------------- GUI Helpers -------------------
    def create_advanced_adjustments(self, parent):
        adv_frame = ctk.CTkFrame(parent, corner_radius=10)
        adv_frame.pack(padx=10, pady=2, fill="x")
        ctk.CTkLabel(adv_frame, text="Advanced").pack(pady=5)

        # Brilho, Contraste, Cor
        self.brightness_slider = ctk.CTkSlider(adv_frame, from_=0, to=2, number_of_steps=20)
        self.brightness_slider.set(1.0)
        ctk.CTkLabel(adv_frame, text="Bright").pack()
        self.brightness_slider.pack(padx=10, pady=2, fill="x")

        self.contrast_slider = ctk.CTkSlider(adv_frame, from_=0, to=2, number_of_steps=20)
        self.contrast_slider.set(1.0)
        ctk.CTkLabel(adv_frame, text="Contrast").pack()
        self.contrast_slider.pack(padx=10, pady=2, fill="x")

        self.color_slider = ctk.CTkSlider(adv_frame, from_=0, to=2, number_of_steps=20)
        self.color_slider.set(1.0)
        ctk.CTkLabel(adv_frame, text="Saturation").pack()
        self.color_slider.pack(padx=10, pady=2, fill="x")

        # Rotação
        self.rotate_slider = ctk.CTkSlider(adv_frame, from_=0, to=360, number_of_steps=36)
        self.rotate_slider.set(0)
        ctk.CTkLabel(adv_frame, text="Rotation:").pack()
        self.rotate_slider.pack(padx=10, pady=2, fill="x")

        # Ajustes RGB
        self.red_slider = ctk.CTkSlider(adv_frame, from_=0, to=2, number_of_steps=20)
        self.red_slider.set(1.0)
        ctk.CTkLabel(adv_frame, text="Red").pack()
        self.red_slider.pack(padx=10, pady=2, fill="x")

        self.green_slider = ctk.CTkSlider(adv_frame, from_=0, to=2, number_of_steps=20)
        self.green_slider.set(1.0)
        ctk.CTkLabel(adv_frame, text="Green").pack()
        self.green_slider.pack(padx=10, pady=2, fill="x")

        self.blue_slider = ctk.CTkSlider(adv_frame, from_=0, to=2, number_of_steps=20)
        self.blue_slider.set(1.0)
        ctk.CTkLabel(adv_frame, text="Blue").pack()
        self.blue_slider.pack(padx=10, pady=2, fill="x")

        # Flips
        self.flip_horizontal = ctk.CTkSwitch(adv_frame, text="Mirror Horizontal")
        self.flip_horizontal.pack(padx=10, pady=2)
        self.flip_vertical = ctk.CTkSwitch(adv_frame, text="Mirror Vertical")
        self.flip_vertical.pack(padx=10, pady=2)

    def create_denoise_upscale_controls(self, parent):
        controls_frame = ctk.CTkFrame(parent, corner_radius=10)
        controls_frame.pack(padx=10, pady=5, fill="x")

        # Denoise
        denoise_frame = ctk.CTkFrame(controls_frame)
        denoise_frame.pack(side="left", padx=10, pady=5)
        ctk.CTkLabel(denoise_frame, text="Denoise").pack(side="left")
        self.use_denoise = ctk.CTkSwitch(denoise_frame, text="", width=30)
        self.use_denoise.pack(side="left", padx=5)
        self.denoise_level = ctk.CTkComboBox(denoise_frame, values=["0", "1", "2", "3"], width=50)
        self.denoise_level.set("1")
        self.denoise_level.pack(side="left", padx=5)

        # Upscale
        upscale_frame = ctk.CTkFrame(controls_frame)
        upscale_frame.pack(side="left", padx=10, pady=5)
        ctk.CTkLabel(upscale_frame, text="Upscale").pack(side="left")
        self.use_upscale = ctk.CTkSwitch(upscale_frame, text="", width=30)
        self.use_upscale.pack(side="left", padx=5)
        self.upscale_factor = ctk.CTkComboBox(upscale_frame, values=["2", "4", "8"], width=50)
        self.upscale_factor.set("2")
        self.upscale_factor.pack(side="left", padx=5)

        # Resize
        resize_frame = ctk.CTkFrame(controls_frame)
        resize_frame.pack(side="left", padx=10, pady=5)
        ctk.CTkLabel(resize_frame, text="Resize").pack(side="left")
        self.use_resize = ctk.CTkSwitch(resize_frame, text="", width=30)
        self.use_resize.pack(side="left", padx=5)
        self.resize_output = ctk.CTkComboBox(resize_frame, values=["32", "64", "128", "240", "256", "512"], width=60)
        self.resize_output.set("32")
        self.resize_output.pack(side="left", padx=5)

        # Custom Resize
        custom_resize_frame = ctk.CTkFrame(controls_frame)
        custom_resize_frame.pack(side="left", padx=10, pady=5)

        ctk.CTkLabel(custom_resize_frame, text="Custom Size").pack(side="left")

        self.use_custom_resize = ctk.CTkSwitch(custom_resize_frame, text="", width=30)
        self.use_custom_resize.pack(side="left", padx=5)

        self.custom_width = ctk.CTkEntry(custom_resize_frame, placeholder_text="W", width=55)
        self.custom_width.pack(side="left", padx=2)

        self.custom_height = ctk.CTkEntry(custom_resize_frame, placeholder_text="H", width=55)
        self.custom_height.pack(side="left", padx=2)

    def create_display_frames(self, parent):
        main_display_frame = ctk.CTkFrame(parent, corner_radius=2)
        main_display_frame.pack(padx=10, pady=0, fill="both", expand=True)
        main_display_frame.grid_columnconfigure(0, weight=1)
        main_display_frame.grid_columnconfigure(1, weight=1)
        main_display_frame.grid_columnconfigure(2, weight=1)

        # Log
        log_frame = ctk.CTkFrame(main_display_frame, corner_radius=2)
        log_frame.grid(row=0, column=0, padx=5, pady=0, sticky="nsew")
        ctk.CTkLabel(log_frame, text="Log:").pack()
        self.log_box = ctk.CTkTextbox(log_frame, height=10)
        self.log_box.pack(padx=5, pady=5, fill="both", expand=True)

        # Input
        input_frame = ctk.CTkFrame(main_display_frame, corner_radius=2)
        input_frame.grid(row=0, column=1, padx=5, pady=0, sticky="nsew")
        ctk.CTkLabel(input_frame, text="Main Folder:").pack()
        self.input_scroll = ctk.CTkScrollableFrame(input_frame, height=0)
        self.input_scroll.pack(padx=5, pady=5, fill="both", expand=True)

        # Output
        output_frame = ctk.CTkFrame(main_display_frame, corner_radius=2)
        output_frame.grid(row=0, column=2, padx=5, pady=0, sticky="nsew")
        ctk.CTkLabel(output_frame, text="Output:").pack()
        self.output_scroll = ctk.CTkScrollableFrame(output_frame, height=0)
        self.output_scroll.pack(padx=5, pady=5, fill="both", expand=True)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            self.show_images(folder)

    def show_images(self, folder):
        # Limpa os widgets antigos
        for widget in self.input_scroll.winfo_children():
            widget.destroy()
        for widget in self.output_scroll.winfo_children():
            widget.destroy()

        self.input_photos = []
        self.output_photos = []

        for file in os.listdir(folder):
            if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                path = os.path.join(folder, file)
                img = Image.open(path)

                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 100))
                self.input_photos.append(ctk_img)

                label = ctk.CTkLabel(self.input_scroll, image=ctk_img, text="")
                label.pack(pady=5)

        out_folder = os.path.join(folder, "output_processed")
        if os.path.isdir(out_folder):
            for file in os.listdir(out_folder):
                if file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
                    path = os.path.join(out_folder, file)
                    img = Image.open(path)

                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(50, 50))
                    self.output_photos.append(ctk_img)

                    label = ctk.CTkLabel(self.output_scroll, image=ctk_img, text="")
                    label.pack(pady=5)

    def log(self, msg):
        self.log_box.insert("end", msg + "\n")
        self.log_box.see("end")

    def process_pillow_image(self, img):
        
        
        self.show_loading("Loading...\nPlease wait.") 
        
        img = ImageEnhance.Brightness(img).enhance(self.brightness_slider.get())
        img = ImageEnhance.Contrast(img).enhance(self.contrast_slider.get())
        img = ImageEnhance.Color(img).enhance(self.color_slider.get())

        img_np = np.array(img).astype(np.float32)

        # Ajustes RGB
        img_np[..., 0] = np.clip(img_np[..., 0] * self.red_slider.get(), 0, 255)
        img_np[..., 1] = np.clip(img_np[..., 1] * self.green_slider.get(), 0, 255)
        img_np[..., 2] = np.clip(img_np[..., 2] * self.blue_slider.get(), 0, 255)

        img = Image.fromarray(img_np.astype(np.uint8))

        angle = self.rotate_slider.get()
        if angle != 0:
            img = img.rotate(angle, expand=True)
        if self.flip_horizontal.get():
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        if self.flip_vertical.get():
            img = img.transpose(Image.FLIP_TOP_BOTTOM)

        return img
        
        self.hide_loading()          

    def convert_images_thread(self):
        threading.Thread(target=self.convert_images, daemon=True).start()

    def convert_images(self):
        folder = self.path_entry.get().strip()
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Select a valid folder!")
            return
        self.show_loading("Loading...\nPlease wait.") 
        
        denoise_enabled = self.use_denoise.get()
        upscale_enabled = self.use_upscale.get()
        resize_enabled = self.use_resize.get()
        denoise_level = self.denoise_level.get()
        upscale_factor = self.upscale_factor.get()
        resize_final = int(self.resize_output.get())

        custom_resize_enabled = self.use_custom_resize.get()
        custom_w = self.custom_width.get()
        custom_h = self.custom_height.get()

        if custom_resize_enabled:
            try:
                custom_w = int(custom_w)
                custom_h = int(custom_h)
            except:
                messagebox.showerror("Error", "Invalid Custom Resize values! Use only numbers.")
                return

        if not denoise_enabled and not upscale_enabled and not resize_enabled:
            messagebox.showerror("Error", "Select at least one option!")
            return

        if (denoise_enabled or upscale_enabled) and not os.path.isfile(self.waifu_exe):
            messagebox.showerror("Erro", f"File not found:\n{self.waifu_exe}")
            return

        out_folder = os.path.join(folder, "output_processed")
        os.makedirs(out_folder, exist_ok=True)
        count = 0

        files_to_process = [f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp"))]

        for file in files_to_process:
            input_path = os.path.join(folder, file)
            temp_output = os.path.join(out_folder, "temp_" + file)
            final_output = os.path.join(out_folder, file)
            src = input_path

            self.log(f"Processing: {file}")

            if denoise_enabled:
                cmd = [
                    self.waifu_exe, "-i", src, "-o", temp_output,
                    "-s", "1", "-m", "noise", "-n", denoise_level, "-p", "cpu"
                ]
                subprocess.run(cmd)
                src = temp_output

            if upscale_enabled:
                cmd = [
                    self.waifu_exe, "-i", src, "-o", temp_output,
                    "-s", upscale_factor, "-m", "noise_scale", "-n", denoise_level, "-p", "cpu"
                ]
                subprocess.run(cmd)
                src = temp_output

            img = Image.open(src)

            if custom_resize_enabled:
                img = img.resize((custom_w, custom_h), Image.NEAREST)
            elif resize_enabled:
                img = img.resize((resize_final, resize_final), Image.NEAREST)

            img = self.process_pillow_image(img)
            img.save(final_output)

            if os.path.exists(temp_output):
                os.remove(temp_output)

            count += 1

        self.show_images(folder)
        self.status.configure(text=f"Completed! {count} processed images.")
        messagebox.showinfo("Ready", f"{count} Images were successfully generated!")

        self.hide_loading()       
