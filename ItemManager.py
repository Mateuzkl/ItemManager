import customtkinter as ctk
import os
import sys

if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

data_path = os.path.join(base_path, "data")
if data_path not in sys.path:
    sys.path.append(data_path)


from ImageUpscale import ImageUpscaleTab
from datspr import DatSprTab
from otbreload import OtbReloadTab


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Item Manager")
        self.geometry("900x1000")
        
        # Caminho base para ícones
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        icon_path = os.path.join(base_path, "ItemManagerIco.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        # Maximizar janela (Windows)
        self.after(1, self.state, 'zoomed')

        # --- TabView Principal ---
        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        # Criando as abas
        self.tab_manager = self.tab_view.add("Sprite Editor")
        self.tab_sprdat = self.tab_view.add("Spr/Dat Editor")
        self.tab_otbreload = self.tab_view.add("Otb Reload")

        # 1. Aba de Imagens (Passamos a aba como 'parent')
        self.upscale_module = ImageUpscaleTab(self.tab_manager, base_path)
        self.upscale_module.pack(fill="both", expand=True)

        # 2. Aba DAT/SPR
        self.datspr_module = DatSprTab(self.tab_sprdat)
        self.datspr_module.pack(fill="both", expand=True)

        # 3. Aba OTB 
        self.otb_module = OtbReloadTab(self.tab_otbreload)
        self.otb_module.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = App()
    app.mainloop()
