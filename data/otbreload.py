import customtkinter as ctk

class OtbReloadTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        
        self.label = ctk.CTkLabel(
            self, 
            text="OTB Reload System\nIn Development...", 
            font=("Arial", 24),
            text_color="gray"
        )
        self.label.pack(expand=True)
