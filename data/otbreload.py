import customtkinter as ctk
from tkinter import filedialog, messagebox
import os

from otbparser import OtbFile

OTB_FLAG_BLOCK_SOLID        = 1 << 0  # Unpassable
OTB_FLAG_BLOCK_PROJECTILE   = 1 << 1  # BlockMissile
OTB_FLAG_BLOCK_PATHFIND     = 1 << 2  # BlockPathfind
OTB_FLAG_HAS_HEIGHT         = 1 << 3  # HasElevation
OTB_FLAG_USEABLE            = 1 << 4  # Usable
OTB_FLAG_PICKUPABLE         = 1 << 5  # Pickupable
OTB_FLAG_MOVEABLE           = 1 << 6  # !Unmoveable
OTB_FLAG_STACKABLE          = 1 << 7  # Stackable
OTB_FLAG_FLOORCHANGEDOWN    = 1 << 8  # (Lógica complexa, as vezes 'Ground' ajuda)
OTB_FLAG_FLOORCHANGENORTH   = 1 << 9
OTB_FLAG_FLOORCHANGEEAST    = 1 << 10
OTB_FLAG_FLOORCHANGESOUTH   = 1 << 11
OTB_FLAG_FLOORCHANGEWEST    = 1 << 12
OTB_FLAG_ALWAYSONTOP        = 1 << 13 # OnTop
OTB_FLAG_READABLE           = 1 << 14 # Writable / WritableOnce
OTB_FLAG_ROTATABLE          = 1 << 15 # Rotatable
OTB_FLAG_HANGABLE           = 1 << 16 # Hangable
OTB_FLAG_VERTICAL           = 1 << 17 # HookVertical
OTB_FLAG_HORIZONTAL         = 1 << 18 # HookHorizontal
OTB_FLAG_CANNOTDECAY        = 1 << 19 # (Sem flag direta no dat comum)
OTB_FLAG_ALLOWDISTREAD      = 1 << 20
OTB_FLAG_CORPSE             = 1 << 21 # (Geralmente ID fixo ou lógica de item)
OTB_FLAG_CLIENTCHARGES      = 1 << 22
OTB_FLAG_LOOKTHROUGH        = 1 << 23 # IgnoreLook? Translucent?
OTB_FLAG_ANIMATION          = 1 << 24 # AnimateAlways
OTB_FLAG_FULLGROUND         = 1 << 25 # FullGround
OTB_FLAG_FORCEUSE           = 1 << 26 # ForceUse

class OtbReloadTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)

        ctk.CTkLabel(
            self,
            text="OTB Reload Attributes",
            font=("Arial", 20, "bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            self,
            text="Esta ferramenta atualizará o items.otb usando os atributos\n do Tibia.dat carregado na outra aba.",
            text_color="gray"
        ).pack(pady=5)

        # --- CONTROLES ---
        self.btn_search = ctk.CTkButton(
            self, text="1. Load items.otb", command=self.load_otb, width=200
        )
        self.btn_search.pack(pady=15)

        self.path_label = ctk.CTkLabel(self, text="Nenhum OTB carregado", text_color="gray")
        self.path_label.pack(pady=5)

        self.btn_apply = ctk.CTkButton(
            self, text="2. Update OTB from DAT", command=self.apply_reload, 
            fg_color="green", width=200, state="disabled"
        )
        self.btn_apply.pack(pady=20)
        
        self.log_box = ctk.CTkTextbox(self, width=600, height=300)
        self.log_box.pack(pady=10)

        self.otb = None
        self.otb_path = None
        self.parent_app = None # Será setado pelo Main para acessar a aba DAT

    def load_otb(self):
        path = filedialog.askopenfilename(
            title="Select items.otb", 
            filetypes=[("OTB Files", "*.otb")]
        )
        if not path:
            return

        try:
            self.otb = OtbFile()
            self.otb.load(path)
            self.otb_path = path
            self.path_label.configure(text=os.path.basename(path))
            self.btn_apply.configure(state="normal")
            self.log_box.insert("end", f"OTB carregado: {path}\n")
            self.log_box.insert("end", f"Total de itens lidos: {len(self.otb.get_all_items())}\n")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler OTB: {e}")

    def get_dat_editor(self):
        # Tenta acessar a instância do DatEditor da aba vizinha
        # main.py define: self.datspr_module = DatSprTab(...)
        # Precisamos navegar: self (Tab) -> TabView -> App -> datspr_module
        
        # Uma forma mais segura é passar a referencia no main.py, 
        # mas vamos tentar acessar via 'master' se a estrutura for Tkinter padrão.
        # Porém, o ideal é que o App injete essa dependencia.
        
        # Assumindo que o App (root) tem 'datspr_module'
        app = self.winfo_toplevel()
        if hasattr(app, 'datspr_module') and app.datspr_module.editor:
            return app.datspr_module.editor
        return None

    def apply_reload(self):
        dat_editor = self.get_dat_editor()
        
        if not dat_editor:
            messagebox.showerror("Erro", "O arquivo Tibia.dat não está carregado na aba 'Spr/Dat Editor'.\nPor favor, carregue o .dat primeiro.")
            return
            
        if not self.otb:
            return

        updated_count = 0
        items_list = self.otb.get_all_items()
        
        self.log_box.insert("end", "Iniciando atualização...\n")
        self.update_idletasks()

        for item in items_list:
            # OTB usa ServerID, mas contém ClientID (CID) para mapear o sprite.
            # Precisamos do CID para buscar no DAT.
            cid = item.client_id
            
            if cid == 0: # Itens sem sprite (ex: grupos ou especiais)
                continue
                
            # Busca no DAT
            dat_thing = dat_editor.things['items'].get(cid)
            
            if not dat_thing:
                # Item existe no OTB mas não no DAT (Sprite deletada?)
                continue
                
            props = dat_thing['props']
            
            # --- 1. ATUALIZAR FLAGS ---
            new_flags = 0
            
            if 'Unpassable' in props:      new_flags |= OTB_FLAG_BLOCK_SOLID
            if 'BlockMissile' in props:    new_flags |= OTB_FLAG_BLOCK_PROJECTILE
            if 'BlockPathfind' in props:   new_flags |= OTB_FLAG_BLOCK_PATHFIND
            if 'HasElevation' in props:    new_flags |= OTB_FLAG_HAS_HEIGHT
            if 'Usable' in props:          new_flags |= OTB_FLAG_USEABLE
            if 'Pickupable' in props:      new_flags |= OTB_FLAG_PICKUPABLE
            if 'Stackable' in props:       new_flags |= OTB_FLAG_STACKABLE
            if 'OnTop' in props:           new_flags |= OTB_FLAG_ALWAYSONTOP
            if 'Rotatable' in props:       new_flags |= OTB_FLAG_ROTATABLE
            if 'Hangable' in props:        new_flags |= OTB_FLAG_HANGABLE
            if 'HookVertical' in props:    new_flags |= OTB_FLAG_VERTICAL
            if 'HookHorizontal' in props:  new_flags |= OTB_FLAG_HORIZONTAL
            if 'AnimateAlways' in props:   new_flags |= OTB_FLAG_ANIMATION
            if 'FullGround' in props:      new_flags |= OTB_FLAG_FULLGROUND
            if 'ForceUse' in props:        new_flags |= OTB_FLAG_FORCEUSE
            if 'ShowOnMinimap' in props:   new_flags |= OTB_FLAG_IGNORELOOK # Exemplo: Minimap as vezes é atrelado a ignore look ou custom

            # Lógica especial para Moveable
            if 'Unmoveable' not in props:
                new_flags |= OTB_FLAG_MOVEABLE
                
            # Lógica especial para Readable
            if 'Writable' in props or 'WritableOnce' in props:
                new_flags |= OTB_FLAG_READABLE

            # Atualiza flags
            if item.flags != new_flags:
                item.flags = new_flags
                # updated_count += 1 (Opcional contar só flags)

            # --- 2. ATUALIZAR SPEED (Ground Speed) ---
            if 'Ground' in props and 'Ground_data' in props:
                speed_val = props['Ground_data'][0]
                item.speed = speed_val
            else:
                item.speed = 0

            # --- 3. ATUALIZAR LIGHT ---
            if 'HasLight' in props and 'HasLight_data' in props:
                # HasLight_data = (level, color)
                l_level, l_color = props['HasLight_data']
                item.light_level = l_level
                item.light_color = l_color
            else:
                item.light_level = 0
                item.light_color = 0

            updated_count += 1

        # Salvar
        try:
            # Salva como _updated.otb para segurança
            base_dir = os.path.dirname(self.otb_path)
            filename = os.path.basename(self.otb_path)
            new_path = os.path.join(base_dir, filename.replace(".otb", "_updated.otb"))
            
            self.otb.save(new_path)
            
            self.log_box.insert("end", f"--------------------------------\n")
            self.log_box.insert("end", f"SUCESSO! Arquivo salvo em:\n{new_path}\n")
            self.log_box.insert("end", f"Itens processados: {updated_count}\n")
            messagebox.showinfo("Concluído", f"OTB Atualizado!\nArquivo salvo como: {os.path.basename(new_path)}")
            
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", str(e))

