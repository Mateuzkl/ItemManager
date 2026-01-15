import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFrame, QGridLayout, 
                             QLabel, QPushButton, QSizePolicy)
from PyQt6.QtGui import QIcon, QCursor
from PyQt6.QtCore import Qt, QSize

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Assumes assets are in ../assets/window relative to data/
ICON_PATH = os.path.join(BASE_DIR, "..", "assets", "window")

class ToolsTab(QWidget):
    def __init__(self, datspr_tab):
        super().__init__()
        self.datspr_tab = datspr_tab
        self.init_ui()

    def init_ui(self):
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Title/Header
        title_frame = QFrame()
        title_layout = QVBoxLayout(title_frame)
        title_layout.setContentsMargins(0, 0, 0, 10)
        
        lbl_title = QLabel("Utility Tools")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #5b9bd5;")
        title_layout.addWidget(lbl_title)
        
        lbl_desc = QLabel("Access various generators and editors for Item Manager.")
        lbl_desc.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        title_layout.addWidget(lbl_desc)
        
        layout.addWidget(title_frame)

        # Tools Grid Container
        grid_frame = QFrame()
        grid_frame.setStyleSheet("background: rgba(30, 30, 46, 0.5); border-radius: 8px;")
        grid_layout = QGridLayout(grid_frame)
        grid_layout.setContentsMargins(20, 20, 20, 20)
        grid_layout.setSpacing(15)

        # Tool Definitions: (Name, Icon, Tooltip, Callback)
        tools = [
            ("Sprite Editor", "spriteEditor.png", "Extract and edit sprites", self.datspr_tab.open_sprite_editor),
            ("Sprite Optimizer", "hash.png", "Optimize sprite storage", self.datspr_tab.open_sprite_optimizer),
            ("LookType Generator", "looktype.png", "Generate XML for LookTypes", self.datspr_tab.open_looktype_generator),
            ("Monster Generator", "monster.png", "Create custom monsters", self.datspr_tab.open_monster_generator),
            ("Spell Maker", "viewer_icon.png", "Design and test spells", self.datspr_tab.open_spell_maker),
            ("Shader Editor", "viewer_icon.png", "Edit client shaders", self.datspr_tab.open_shader),
            ("Particle Editor", "viewer_icon.png", "Edit particle effects", self.datspr_tab.open_particle),
        ]

        row = 0
        col = 0
        max_cols = 3 # 3 columns

        for name, icon, tooltip, callback in tools:
            btn = self.create_tool_button(name, icon, tooltip, callback)
            grid_layout.addWidget(btn, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        layout.addWidget(grid_frame)
        layout.addStretch()

    def create_tool_button(self, text, icon_name, tooltip, callback):
        btn = QPushButton(f"  {text}")
        if icon_name:
            icon_file = os.path.join(ICON_PATH, icon_name)
            if os.path.exists(icon_file):
                btn.setIcon(QIcon(icon_file))
            else:
                # Fallback or keep empty
                pass
                
        btn.setIconSize(QSize(32, 32))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedHeight(60)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3e3e50; 
                border: 1px solid #4a4a5a; 
                border-radius: 6px;
                color: white;
                font-weight: bold;
                font-size: 13px;
                text-align: left;
                padding-left: 15px;
            }
            QPushButton:hover {
                background-color: #4a90e2;
                border: 1px solid #5b9bd5;
            }
            QPushButton:pressed {
                background-color: #357abd;
            }
        """)
        
        # Connect safely
        if callback:
             btn.clicked.connect(callback)
             
        return btn
