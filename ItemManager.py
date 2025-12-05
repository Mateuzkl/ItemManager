import customtkinter as ctk
import os
import sys
import time
import tkinter as tk
from PIL import Image, ImageTk

def show_splash(image_path, duration=2000):
    splash = tk.Tk()
    splash.overrideredirect(True)     
    splash.attributes("-topmost", True)

    pil_img = Image.open(image_path)
    width, height = pil_img.size
    tk_img = ImageTk.PhotoImage(pil_img)

    screen_w = splash.winfo_screenwidth()
    screen_h = splash.winfo_screenheight()
    x = (screen_w // 2) - (width // 2)
    y = (screen_h // 2) - (height // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")

    label = tk.Label(splash, image=tk_img, border=0)
    label.image = tk_img  
    label.pack()

    splash.after(duration, splash.destroy)
    splash.mainloop()

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
        
        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        icon_path = os.path.join(base_path, "ItemManagerIco.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.after(1, self.state, 'zoomed')

        self.tab_view = ctk.CTkTabview(self)
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_manager = self.tab_view.add("Sprite Editor")
        self.tab_sprdat = self.tab_view.add("Spr/Dat Editor")
        self.tab_otbreload = self.tab_view.add("Otb Reload")


        self.upscale_module = ImageUpscaleTab(self.tab_manager, base_path)
        self.upscale_module.pack(fill="both", expand=True)

        self.datspr_module = DatSprTab(self.tab_sprdat)
        self.datspr_module.pack(fill="both", expand=True)

        self.otb_module = OtbReloadTab(self.tab_otbreload)
        self.otb_module.pack(fill="both", expand=True)
        
if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    splash_path = os.path.join(base_path, "ItemManagersplash.png")

    show_splash(splash_path, duration=3000)  

    app = App()
    app.mainloop()
