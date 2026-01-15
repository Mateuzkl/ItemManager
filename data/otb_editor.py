from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
                             QTreeWidget, QTreeWidgetItem, QGroupBox, QFormLayout, QSpinBox, 
                             QLineEdit, QSplitter, QMessageBox, QLabel, QCheckBox, QScrollArea, 
                             QGridLayout, QFrame, QComboBox, QPlainTextEdit, QMenuBar, QMenu,
                             QInputDialog, QTreeWidgetItemIterator)
from PyQt6.QtGui import QIcon, QPixmap, QImage, QColor, QAction
from otb_handler import * 
import sys
from PIL import Image

def pil_to_qpixmap(pil_image):
    if pil_image is None:
        return QPixmap()
    
    if pil_image.mode == "RGB":
        r, g, b = pil_image.split()
        pil_image = Image.merge("RGB", (b, g, r))
    elif pil_image.mode == "RGBA":
        r, g, b, a = pil_image.split()
        pil_image = Image.merge("RGBA", (b, g, r, a))
    elif pil_image.mode == "L":
        pil_image = pil_image.convert("RGBA")
        
    im2 = pil_image.convert("RGBA")
    data = im2.tobytes("raw", "BGRA")
    qim = QImage(data, im2.width, im2.height, QImage.Format.Format_ARGB32)
    return QPixmap.fromImage(qim)


class OtbEditorTab(QWidget):
    def __init__(self, datspr_module=None):
        super().__init__()
        self.datspr_module = datspr_module
        self.otb_root = None
        self.current_node = None
        self.item_nodes = [] 
        self.init_ui()
        self.create_menu_bar()

    def create_menu_bar(self):
        # Create Menu Bar
        self.menu_bar = QMenuBar(self)
        self.layout().setMenuBar(self.menu_bar)

        # File Menu
        file_menu = self.menu_bar.addMenu("File")
        
        load_action = QAction("Open...", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_otb)
        file_menu.addAction(load_action)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_otb)
        file_menu.addAction(save_action)
        
        # Edit Menu
        edit_menu = self.menu_bar.addMenu("Edit")
        
        create_action = QAction("Create Item", self)
        create_action.setShortcut("Ctrl+I")
        create_action.triggered.connect(self.create_item)
        edit_menu.addAction(create_action)
        
        dup_action = QAction("Duplicate Item", self)
        dup_action.setShortcut("Ctrl+D")
        dup_action.triggered.connect(self.duplicate_item)
        edit_menu.addAction(dup_action)
        
        reload_action = QAction("Reload Item", self)
        reload_action.setShortcut("Ctrl+R")
        reload_action.triggered.connect(self.reload_current_item)
        edit_menu.addAction(reload_action)
        
        edit_menu.addSeparator()
        
        missing_action = QAction("Create Missing Items", self)
        missing_action.triggered.connect(self.create_missing_items)
        edit_menu.addAction(missing_action)
        
        find_action = QAction("Find Item", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.open_find_dialog)
        edit_menu.addAction(find_action)

        # View Menu
        view_menu = self.menu_bar.addMenu("View")
        # Placeholders for now
        view_menu.addAction("Show Mismatched Items (TODO)")
        view_menu.addAction("Show Deprecated Items (TODO)")
        
        # Tools Menu
        tools_menu = self.menu_bar.addMenu("Tools")
        
        reload_attrs = QAction("Reload Item Attributes", self)
        reload_attrs.triggered.connect(self.reload_all_attributes)
        tools_menu.addAction(reload_attrs)

        # Help Menu
        help_menu = self.menu_bar.addMenu("Help")
        about_action = QAction("About ItemEditor", self)
        about_action.triggered.connect(lambda: QMessageBox.information(self, "About", "ItemManager OTB Editor\nBased on ItemEditor 0.5"))
        help_menu.addAction(about_action)

    def init_ui(self):
        # Existing UI setup...
        pass 

    # --- Feature Implementations ---

    def create_item(self):
        if not self.otb_root: return
        
        # Find max Server ID
        max_sid = 0
        for node in self.item_nodes:
            sid = node.attribs.get('serverId', 0)
            if sid > max_sid: max_sid = sid
            
        new_sid = max_sid + 1
        
        # Create new node
        new_node = OTBNode()
        new_node.type = 0 # ItemGroup None? Or normal item type? 
        # Usually type denotes group (Container, etc). Default to None (0) or Item
        
        new_node.attribs['serverId'] = new_sid
        new_node.attribs['clientId'] = 0 # Default
        
        self.otb_root.add_child(new_node)
        self.item_nodes.append(new_node)
        
        # Add to Tree
        root = self.tree.invisibleRootItem()
        self.add_tree_item(new_node, root)
        
        self.log(f"Created Item {new_sid}")

    def duplicate_item(self):
        if not self.current_node: return
        
        # Find max Server ID
        max_sid = 0
        for node in self.item_nodes:
            sid = node.attribs.get('serverId', 0)
            if sid > max_sid: max_sid = sid
            
        new_sid = max_sid + 1
        
        # Deep copy node logic (manual copy of attributes)
        import copy
        new_node = OTBNode()
        new_node.type = self.current_node.type
        new_node.attribs = copy.deepcopy(self.current_node.attribs)
        new_node.attribs['serverId'] = new_sid
        
        # Copy raw props? 
        # Ideally we re-serialize attribs, so raw_props might be stale.
        # But let's copy them just in case
        new_node.raw_props = copy.deepcopy(self.current_node.raw_props)
        if 16 in new_node.raw_props: del new_node.raw_props[16] # Remove old ID from raw
        
        self.otb_root.add_child(new_node)
        self.item_nodes.append(new_node)
        
        root = self.tree.invisibleRootItem()
        self.add_tree_item(new_node, root)
        
        self.log(f"Duplicated Item {self.current_node.attribs.get('serverId')} to {new_sid}")

    def create_missing_items(self):
        if not self.datspr_module or not self.datspr_module.editor:
            QMessageBox.warning(self, "Error", "Load Tibia.dat first!")
            return
            
        items_map = self.datspr_module.editor.things.get("items", {})
        if not items_map: return
        
        max_cid_dat = max(items_map.keys()) if items_map else 0
        
        # Find existing Client IDs in OTB
        existing_cids = set()
        max_sid = 0
        for node in self.item_nodes:
            cid = node.attribs.get('clientId', 0)
            sid = node.attribs.get('serverId', 0)
            existing_cids.add(cid)
            if sid > max_sid: max_sid = sid
            
        created_count = 0
        # Start from 100 usually
        for cid in range(100, max_cid_dat + 1):
            if cid not in existing_cids:
                # Create it
                new_node = OTBNode()
                new_node.type = 0 # Default type
                
                max_sid += 1
                new_node.attribs['serverId'] = max_sid
                new_node.attribs['clientId'] = cid
                
                # Try to sync basic attributes from DAT?
                # For now just create blank link
                
                self.otb_root.add_child(new_node)
                self.item_nodes.append(new_node)
                
                root = self.tree.invisibleRootItem()
                self.add_tree_item(new_node, root)
                created_count += 1
                
        self.log(f"Created {created_count} missing items.")

    def open_find_dialog(self):
        text, ok = QInputDialog.getText(self, "Find Item", "Enter Item ID (Server) or Name:")
        if ok and text:
            # Search
            search_term = text.lower()
            found_items = []
            
            # Simple linear search
            iterator = QTreeWidgetItemIterator(self.tree)
            while iterator.value():
                item = iterator.value()
                node = item.data(0, Qt.ItemDataRole.UserRole)
                if node:
                    sid = str(node.attribs.get('serverId', 0))
                    name = node.attribs.get('name', '').lower()
                    
                    if search_term == sid or search_term in name:
                        self.tree.setCurrentItem(item)
                        self.tree.scrollToItem(item)
                        self.on_item_clicked(item, 0)
                        return # Stop at first match or implementation next button?
                iterator += 1
            
            QMessageBox.information(self, "Find", "Item not found.")

    def reload_current_item(self):
        pass # Placeholder for "Sync with DAT" logic
    
    def reload_all_attributes(self):
        pass # Placeholder
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        self.btn_load = QPushButton("Load items.otb")
        self.btn_load.setIcon(QIcon.fromTheme("document-open"))
        self.btn_load.clicked.connect(self.load_otb)
        self.btn_save = QPushButton("Save items.otb")
        self.btn_save.setIcon(QIcon.fromTheme("document-save"))
        self.btn_save.clicked.connect(self.save_otb)
        
        btn_style = """
            QPushButton {
                background-color: #3b3b3b;
                color: #e0e0e0;
                border: 1px solid #555;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover { background-color: #4a4a4a; }
        """
        self.btn_load.setStyleSheet(btn_style)
        self.btn_save.setStyleSheet(btn_style)
        
        toolbar_layout.addWidget(self.btn_load)
        toolbar_layout.addWidget(self.btn_save)
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #444; width: 2px; }")
        main_layout.addWidget(splitter)
        
        # --- LEFT PANEL: Item List ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Item"])
        self.tree.setIconSize(QSize(32, 32))
        self.tree.setIndentation(0)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #2b2b2b;
                color: #ccc;
                border: 1px solid #444;
                font-size: 13px;
            }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected {
                background-color: #445566;
                color: white;
            }
        """)
        self.tree.itemClicked.connect(self.on_item_clicked)
        left_layout.addWidget(self.tree)
        left_widget.setMinimumWidth(280)
        
        splitter.addWidget(left_widget)
        
        # --- MIDDLE PANEL: Appearance ---
        middle_widget = QWidget()
        middle_layout = QVBoxLayout(middle_widget)
        middle_layout.setContentsMargins(10, 0, 10, 0)
        
        # Appearance Box
        grp_appearance = QGroupBox("Appearance")
        app_layout = QVBoxLayout()
        grp_appearance.setLayout(app_layout)
        
        # Preview Labels matching reference "Previous" and "Current"
        prev_layout = QHBoxLayout()
        self.lbl_prev_preview = QLabel()
        self.lbl_prev_preview.setFixedSize(64, 64)
        self.lbl_prev_preview.setStyleSheet("background-color: #222; border: 1px solid #444;")
        
        self.lbl_preview = QLabel()
        self.lbl_preview.setFixedSize(64, 64)
        self.lbl_preview.setStyleSheet("background-color: #222; border: 1px solid #444;")
        self.lbl_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        app_layout.addWidget(QLabel("Previous:"))
        app_layout.addWidget(self.lbl_prev_preview)
        app_layout.addWidget(QLabel("Current:"))
        app_layout.addWidget(self.lbl_preview)
        
        middle_layout.addWidget(grp_appearance)
        
        # ID Box
        grp_ids = QGroupBox()
        ids_layout = QFormLayout()
        grp_ids.setLayout(ids_layout)
        
        self.inp_server_id = QSpinBox()
        self.inp_server_id.setRange(0, 65535)
        self.inp_client_id = QSpinBox()
        self.inp_client_id.setRange(0, 65535)
        self.inp_client_id.valueChanged.connect(self.update_preview_from_input)

        ids_layout.addRow("Server ID:", self.inp_server_id)
        ids_layout.addRow("Client ID:", self.inp_client_id)
        
        middle_layout.addWidget(grp_ids)
        middle_layout.addStretch()
        
        splitter.addWidget(middle_widget)

        # --- RIGHT PANEL: Attributes & Console ---
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_scroll.setWidget(right_content)

        # Main Grid for Attributes and Props
        # Reference shows: Checkboxes on left, Props on right
        
        top_grid_layout = QHBoxLayout()
        
        # 1. Attributes (Flags)
        grp_flags = QGroupBox("Attributes")
        grp_flags.setStyleSheet("QGroupBox { font-weight: bold; color: #bbb; }")
        flags_layout = QVBoxLayout()
        grp_flags.setLayout(flags_layout)
        
        # Use Red color for critical flags to match reference
        chk_style = """
            QCheckBox { spacing: 5px; color: #aaa; }
            QCheckBox:checked { color: #ff5555; font-weight: bold; }
        """
        
        self.flags_mapping = [
            (QCheckBox("Unpassable"), FLAG_BLOCK_SOLID),
            (QCheckBox("Movable"), FLAG_MOVEABLE),
            (QCheckBox("Block Missiles"), FLAG_BLOCK_PROJECTILE),
            (QCheckBox("Block Pathfinder"), FLAG_BLOCK_PATHFIND),
            (QCheckBox("Pickupable"), FLAG_PICKUPABLE),
            (QCheckBox("Stackable"), FLAG_STACKABLE),
            (QCheckBox("Force Use"), FLAG_FORCE_USE),
            (QCheckBox("Multi Use"), FLAG_USEABLE), # Correct mapping?
            (QCheckBox("Rotatable"), FLAG_ROTATABLE),
            (QCheckBox("Hangable"), FLAG_HANGABLE),
            (QCheckBox("Hook South"), FLAG_VERTICAL),
            (QCheckBox("Hook East"), FLAG_HORIZONTAL),
            
            # Second col in reference? No, reference has 2 cols mixed? 
            # Reference image shows single col of checkboxes mostly
            # But let's add the rest
            (QCheckBox("Has Elevation"), FLAG_HAS_HEIGHT),
            (QCheckBox("Ignore Look"), FLAG_IGNORE_LOOK),
            (QCheckBox("Readable"), FLAG_READABLE),
            (QCheckBox("Full Ground"), FLAG_FULL_GROUND),
            (QCheckBox("Info (Client Charges)"), FLAG_CLIENT_CHARGES),
            (QCheckBox("Dist Read"), FLAG_ALLOW_DISTREAD),
            (QCheckBox("Decay"), FLAG_CANNOT_DECAY), # Inverted? Check definition. 
            # FLAG_CANNOT_DECAY = 524288. If name is "Decay", logic might be inverted.
            # Reference doesn't show "Decay" checkbox explicitly, maybe under other name.
            # I'll stick to standard names but styled
        ]
        
        for chk, _ in self.flags_mapping:
            chk.setStyleSheet(chk_style)
            flags_layout.addWidget(chk)
            
        top_grid_layout.addWidget(grp_flags, 1) # Stretch 1
        
        # 2. Properties (Right side of attributes)
        props_container = QWidget()
        props_layout = QFormLayout(props_container)
        
        self.inp_speed = QSpinBox(); self.inp_speed.setRange(0, 9999)
        self.inp_minimap_color = QSpinBox(); self.inp_minimap_color.setRange(0, 65535)
        self.inp_light_level = QSpinBox(); self.inp_light_level.setRange(0, 255)
        self.inp_light_color = QSpinBox(); self.inp_light_color.setRange(0, 255)
        self.inp_ware_id = QSpinBox(); self.inp_ware_id.setRange(0, 65535)
        self.inp_stack_order = QComboBox(); self.inp_stack_order.addItems(["None", "Border", "Bottom", "Top"]) 
        self.inp_name = QLineEdit()
        self.inp_type = QComboBox() 
        self.inp_type.addItems(["None", "Ground", "Container", "Weapon", "Ammunition", "Armor", "Charges", "Teleport", "MagicField", "Writeable", "Key", "Splash", "Fluid", "Door", "Deprecated", "Depot"])
        
        props_layout.addRow("Ground Speed:", self.inp_speed)
        props_layout.addRow("Minimap Color:", self.inp_minimap_color)
        props_layout.addRow("Light Level:", self.inp_light_level)
        props_layout.addRow("Light Color:", self.inp_light_color)
        props_layout.addRow("Ware ID:", self.inp_ware_id)
        props_layout.addRow("Stack Order:", self.inp_stack_order)
        props_layout.addRow("Name:", self.inp_name)
        props_layout.addRow("Type:", self.inp_type)
        
        # Extra props not in reference main view but needed
        self.inp_weight = QSpinBox(); self.inp_weight.setRange(0, 999999); self.inp_weight.setSuffix(" oz")
        props_layout.addRow("Weight:", self.inp_weight)
        self.inp_armor = QSpinBox(); self.inp_armor.setRange(0, 9999)
        props_layout.addRow("Armor:", self.inp_armor)
        self.inp_attack = QSpinBox(); self.inp_attack.setRange(0, 9999)
        props_layout.addRow("Attack:", self.inp_attack)
        
        top_grid_layout.addWidget(props_container, 2) # Stretch 2
        
        right_layout.addLayout(top_grid_layout)
        
        # Console Log at Bottom
        self.console_log = QPlainTextEdit()
        self.console_log.setReadOnly(True)
        self.console_log.setStyleSheet("background-color: #222; color: #aaa; font-family: Consolas; font-size: 11px; border: 1px solid #444;")
        self.console_log.setMinimumHeight(150)
        right_layout.addWidget(self.console_log)
        
        # Actions
        actions_layout = QHBoxLayout()
        self.btn_update = QPushButton("Update Node")
        self.btn_update.setStyleSheet("background-color: #444; color: white;")
        self.btn_update.clicked.connect(self.update_node)
        
        self.btn_debug = QPushButton("Debug (Log)")
        self.btn_debug.setStyleSheet("background-color: #554422; color: white;")
        self.btn_debug.clicked.connect(self.debug_current_node)
        
        self.btn_scan = QPushButton("Scan All (Log)")
        self.btn_scan.setStyleSheet("background-color: #224455; color: white;")
        self.btn_scan.clicked.connect(self.scan_otb)
        
        actions_layout.addWidget(self.btn_update)
        actions_layout.addWidget(self.btn_debug)
        actions_layout.addWidget(self.btn_scan)
        right_layout.addLayout(actions_layout)

        splitter.addWidget(right_scroll)
        splitter.setSizes([300, 200, 500])

    def log(self, message):
        self.console_log.appendPlainText(f">> {message}")

    def load_otb(self):
        if not self.datspr_module or not self.datspr_module.editor or not self.datspr_module.spr:
            QMessageBox.warning(self, "Requirement", "Please load Tibia.dat and Tibia.spr first!")
            return

        path, _ = QFileDialog.getOpenFileName(self, "Load OTB", "", "OTB Files (*.otb);;All Files (*)")
        if not path: return
        
        self.log(f"Loading {path}...")
        try:
            self.otb_root = OTBHandler.load(path)
            if self.otb_root:
                self.populate_tree()
                self.log("OTB Loaded successfully.")
            else:
                 self.log("Failed to parse OTB.")
        except Exception as e:
            self.log(f"Error: {e}")

    def populate_tree(self):
        self.tree.clear()
        if not self.otb_root: return
        
        self.item_nodes = []
        
        def traverse(node):
            if 'serverId' in node.attribs or 'clientId' in node.attribs:
                self.item_nodes.append(node)
            for child in node.children:
                traverse(child)
                
        traverse(self.otb_root)
        
        root = self.tree.invisibleRootItem()
        unnamed_count = 0
        
        for node in self.item_nodes:
            # FILTER: Skip items with Client ID 0 (empty sprites) as requested
            cid = node.attribs.get('clientId', 0)
            if cid == 0: continue
            
            self.add_tree_item(node, root)
            if 'name' not in node.attribs or not node.attribs['name']:
                unnamed_count += 1
                
        self.log(f"Loaded {len(self.item_nodes)} items.")
        if unnamed_count > 0:
            self.log(f"{unnamed_count} items are unnamed (Displayed as Item ID).")
            
    def add_tree_item(self, node, parent):
        sid = node.attribs.get('serverId', 0)
        cid = node.attribs.get('clientId', 0)
        name = node.attribs.get('name', '')
        
        # Format similar to reference: [Icon] 100 - Name
        display_text = f"{sid} - {name}" if name else f"{sid} - Item {cid}"
        if sid == 0: display_text = f"{cid} (Client ID) - {name}" if name else f"{cid} (Client ID)"
        
        item = QTreeWidgetItem(parent)
        item.setText(0, display_text)
        
        if cid > 0:
            pil_img = self.get_node_sprite(cid)
            if pil_img:
                icon_pm = pil_to_qpixmap(pil_img.resize((32, 32), Image.NEAREST))
                item.setIcon(0, QIcon(icon_pm))

        item.setData(0, Qt.ItemDataRole.UserRole, node)

    # ... get_node_sprite, on_item_clicked, update_node similar but mapping new fields ...
    def get_node_sprite(self, client_id):
        if not self.datspr_module: return None
        if not self.datspr_module.editor: return None
        try:
            if "items" in self.datspr_module.editor.things and client_id in self.datspr_module.editor.things["items"]:
                item = self.datspr_module.editor.things["items"][client_id]
                from datspr import DatEditor
                sprite_ids = DatEditor.extract_sprite_ids_from_texture_bytes(item["texture_bytes"])
                if sprite_ids and sprite_ids[0] > 0:
                    img = self.datspr_module.spr.get_sprite(sprite_ids[0])
                    return img
        except: pass
        return None

    def on_item_clicked(self, item, col):
        node = item.data(0, Qt.ItemDataRole.UserRole)
        if node:
            self.current_node = node
            self.inp_server_id.setValue(node.attribs.get('serverId', 0))
            self.inp_client_id.setValue(node.attribs.get('clientId', 0))
            
            # Map flags
            flags = node.attribs.get('flags', 0)
            for chk, flag_val in self.flags_mapping:
                chk.setChecked(bool(flags & flag_val))
                
            # Props
            self.inp_name.setText(node.attribs.get('name', ''))
            self.inp_weight.setValue(node.attribs.get('weight', 0))
            self.inp_speed.setValue(node.attribs.get('speed', 0))
            self.inp_armor.setValue(node.attribs.get('armor', 0))
            self.inp_attack.setValue(node.attribs.get('attack', 0))
            self.inp_light_level.setValue(node.attribs.get('lightLevel', 0))
            self.inp_light_color.setValue(node.attribs.get('lightColor', 0))
            self.inp_minimap_color.setValue(node.attribs.get('minimapColor', 0))
            self.inp_ware_id.setValue(node.attribs.get('wareId', 0))
            
            # Update Preview
            self.update_preview_from_input()
            
    def update_preview_from_input(self):
        cid = self.inp_client_id.value()
        if cid > 0:
            pil_img = self.get_node_sprite(cid)
            if pil_img:
                pm = pil_to_qpixmap(pil_img.resize((64, 64), Image.NEAREST))
                self.lbl_preview.setPixmap(pm)
            else:
                self.lbl_preview.clear()
        else:
            self.lbl_preview.clear()

    def save_otb(self):
        if not self.otb_root: return
        path, _ = QFileDialog.getSaveFileName(self, "Save OTB", "", "OTB Files (*.otb)")
        if not path: return
        OTBHandler.save(self.otb_root, path)
        self.log("Saved OTB file.")
            
    def debug_current_node(self):
        if not self.current_node: 
            self.log("No node selected to debug.")
            return

        node = self.current_node
        self.console_log.clear()
        self.log("=== ITEM DEBUG ===")
        self.log(f"Node Type: {node.type}")
        self.log(f"Current Parsed SID: {node.attribs.get('serverId', 'Not Found')}")
        self.log(f"Current Parsed CID: {node.attribs.get('clientId', 'Not Found')}")
        self.log(f"Parsed Attributes: {list(node.attribs.keys())}")
        
        # Analyze Raw Props
        self.log("--- Raw Property Analysis ---")
        p = io.BytesIO(node.props)
        raw_attrs_found = []
        while True:
            attr_byte = p.read(1)
            if not attr_byte: break
            attr = attr_byte[0]
            size_b = p.read(2)
            if len(size_b) < 2: break
            size = struct.unpack('<H', size_b)[0]
            data = p.read(size)
            
            raw_attrs_found.append(f"ID {attr} (len {len(data)})")
            
            # Specific check for ServerID (16)
            if attr == 16:
                val = struct.unpack('<H', data[:2])[0] if len(data) >= 2 else "ERR"
                self.log(f"-> FOUND SERVER_ID (16): Value = {val}")
        
        self.log(f"All Raw Attribute IDs in blob: {raw_attrs_found}")
        self.log("==================")

    def scan_otb(self):
        if not self.otb_root: return
        self.console_log.clear()
        self.log("Starting Full Diagnostic Scan...")
        
        total = 0
        zero_sid = 0
        no_cid = 0
        no_name = 0
        
        def traverse(node):
            nonlocal total, zero_sid, no_cid, no_name
            # Check only Item nodes (usually those with any attributes)
            if node.props: 
                total += 1
                sid = node.attribs.get('serverId', 0)
                cid = node.attribs.get('clientId', 0)
                name = node.attribs.get('name', '')
                
                if sid == 0: zero_sid += 1
                if cid == 0: no_cid += 1
                if not name: no_name += 1
            
            for child in node.children:
                traverse(child)
        
        traverse(self.otb_root)
        
        self.log(f"Scan Complete.")
        self.log(f"Total Nodes with Props: {total}")
        self.log(f"Nodes with ServerID 0: {zero_sid}")
        self.log(f"Nodes with ClientID 0: {no_cid}")
        self.log(f"Nodes Unnamed: {no_name}")
        
        if zero_sid == total:
             self.log("CRITICAL: All items have ServerID 0. This suggests the Parser is missing Attribute 16, or the file does not contain Server IDs (using ClientID mapping?).")
        elif zero_sid > 0:
             self.log("Warning: Some items have ServerID 0. This is common if they are not used or purely client-side.")

    def update_node(self):
        if self.current_node:
            node = self.current_node
            node.attribs['serverId'] = self.inp_server_id.value()
            node.attribs['clientId'] = self.inp_client_id.value()
            node.attribs['name'] = self.inp_name.text()
            node.attribs['weight'] = self.inp_weight.value()
            node.attribs['speed'] = self.inp_speed.value()
            node.attribs['armor'] = self.inp_armor.value()
            node.attribs['attack'] = self.inp_attack.value()
            node.attribs['lightLevel'] = self.inp_light_level.value()
            node.attribs['lightColor'] = self.inp_light_color.value()
            node.attribs['minimapColor'] = self.inp_minimap_color.value()
            node.attribs['wareId'] = self.inp_ware_id.value()
            
            flags = 0
            for chk, flag_val in self.flags_mapping:
                if chk.isChecked(): flags |= flag_val
            node.attribs['flags'] = flags
            
            self.log(f"Updated Node SID:{node.attribs['serverId']}")

