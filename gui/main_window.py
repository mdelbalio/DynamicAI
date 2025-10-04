"""
Main window for DynamicAI application with multi-row grid support and metadata management
"""

import os
import json
import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
from typing import List, Optional, Set, Dict

# Internal imports
from config import ConfigManager, DB_FILE
from database import CategoryDatabase
from loaders import create_document_loader
from export import ExportManager
from gui.dialogs import CategorySelectionDialog, SettingsDialog
from gui.dialogs.batch_manager import BatchManagerDialog
from gui.components import DocumentGroup, PageThumbnail
from utils import create_progress_dialog, show_help_dialog, show_about_dialog
from config.constants import RESAMPLEFILTER
from utils.branding import set_app_icon

class AIDOXAApp(tk.Tk):
    """Main application window for DynamicAI with multi-row grid support and metadata"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize core components
        self.config_manager = ConfigManager()
        self.category_db = CategoryDatabase(DB_FILE)
        self.export_manager = ExportManager(self.config_manager.config_data)
        
        # Initialize application
        self.init_variables()
        self.setup_window()
        self.setup_ui()
        self.bind_events()
        
        # Restore window layout
        self.after(200, self.restore_window_layout)

    def init_variables(self):
        """Initialize all instance variables"""
        # Document management
        self.documentgroups: List[DocumentGroup] = []
        self.documentloader = None
        self.original_data = None
        self.current_document_name = ""
        self.all_categories: Set[str] = set()
        
        # Metadata management - NUOVO
        self.header_metadata: Dict[str, str] = {
            'NumeroProgetto': '',
            'Intestatario': '',
            'IndirizzoImmobile': '',
            'LavoroEseguito': '',
            'EstremiCatastali': ''
        }
        self.input_folder_name = ""
        
        # Selection state
        self.selected_thumbnail: Optional[PageThumbnail] = None
        self.selected_group: Optional[DocumentGroup] = None
        
        # Drag and drop state
        self.dragging = False
        self.drag_preview: Optional[tk.Toplevel] = None
        self.drag_item: Optional[PageThumbnail] = None
        
        # Image display state
        self.current_image: Optional[Image.Image] = None
        self.zoom_factor = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.zoom_rect_start = None
        self.zoom_rect_end = None
        self.zoom_rect_id = None
        self.zoom_area_mode = False
        
        # UI state
        self.updating_ui = False
        
        # Pan mode state
        self.pan_mode = False
        self.pan_start = None

    def setup_window(self):
        """Setup main window properties"""
        set_app_icon(self)
        self.title("DynamicAI - Editor Lineare Avanzato v3.4")
        
        # Set window geometry from config
        window_settings = self.config_manager.get('window_settings', {})
        geometry = window_settings.get('geometry', '1400x800+100+50')
        self.geometry(geometry)
        
        # Restore window state
        state = window_settings.get('state', 'normal')
        if state == 'zoomed':
            self.state('zoomed')

    def setup_ui(self):
        """Setup the user interface"""
        self.create_menu()
        self.create_widgets()
        self.setup_left_panel()
        self.setup_center_panel()
        self.setup_right_panel()

    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Aggiorna Lista (Preview)", command=self.refresh_document_list, accelerator="Ctrl+R")
        file_menu.add_command(label="Completa Sequenza / Export", command=self.complete_sequence_export, accelerator="Ctrl+E")
        file_menu.add_separator()
        file_menu.add_command(label="Salva Configurazione", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Esci", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Impostazioni", menu=settings_menu)
        settings_menu.add_command(label="Preferenze...", command=self.open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Ripristina Layout Default", command=self.reset_layout)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Visualizza", menu=view_menu)
        view_menu.add_command(label="Aggiorna Miniature", command=self.refresh_thumbnails)

        # Batch menu
        if self.config_manager.get('batch_mode_enabled', True):
            batch_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Batch", menu=batch_menu)
            batch_menu.add_command(label="Esegui Batch...", 
                                  command=self.open_batch_manager,
                                  accelerator="Ctrl+B")
            batch_menu.add_separator()
            batch_menu.add_command(label="Info Batch", 
                                  command=self.show_batch_info)
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Aiuto", menu=help_menu)
        help_menu.add_command(label="Istruzioni", command=lambda: show_help_dialog(self))
        help_menu.add_command(label="Mostra Info Documento", command=self.show_document_info_dialog)  # NUOVO
        help_menu.add_separator()
        help_menu.add_command(label="Informazioni", command=lambda: show_about_dialog(self))
        
    def show_document_info_dialog(self):
        """Show document information in a dialog"""
        if not self.documentgroups:
            messagebox.showinfo("Informazioni Documento", 
                              "Nessun documento caricato.\n\n"
                              "Usa 'Aggiorna Lista (Preview)' per caricare un documento.")
            return
    
        # Crea finestra dialog
        info_dialog = tk.Toplevel(self)
        info_dialog.title("Informazioni Documento Corrente")
        info_dialog.geometry("600x500")
        info_dialog.transient(self)
    
        # Text widget scrollabile
        text_frame = tk.Frame(info_dialog)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
    
        text_widget = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set,
                             font=("Consolas", 9))
        text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text_widget.yview)
    
        # Genera info
        info = self.generate_document_info()
        text_widget.insert("1.0", info)
        text_widget.config(state="disabled")
    
        # Bottone chiudi
        tk.Button(info_dialog, text="Chiudi", command=info_dialog.destroy,
                 bg="lightgray", font=("Arial", 10)).pack(pady=10)

    def generate_document_info(self):
        """Generate document information text"""
        if not self.documentgroups:
            return "Nessun documento caricato"
    
        export_format = self.config_manager.get('export_format', 'JPEG')
        format_display = {
            'JPEG': 'JPEG',
            'PDF_SINGLE': 'PDF (pagina singola)',
            'PDF_MULTI': 'PDF (multipagina per documento)',
            'TIFF_SINGLE': 'TIFF (pagina singola)',
            'TIFF_MULTI': 'TIFF (multipagina per documento)'
        }.get(export_format, export_format)
    
        file_handling_mode = self.config_manager.get('file_handling_mode', 'auto_rename')
        file_handling_display = {
            'auto_rename': 'Rinomina automaticamente',
            'ask_overwrite': 'Chiedi conferma',
            'always_overwrite': 'Sovrascrivi sempre'
        }.get(file_handling_mode, file_handling_mode)
    
        db_categories_count = len(self.category_db.get_all_categories())
    
        grid_info = ""
        for i, group in enumerate(self.documentgroups):
            page_count = group.get_page_count()
            group_info = group.get_info()
            grid_rows = group_info.get('grid_rows', 0)
            per_row = group_info.get('thumbnails_per_row', 4)
            if page_count > 0:
                grid_info += f"  Doc {i+1}: {page_count} pagine ({grid_rows} righe, {per_row}/riga)\n"
    
        metadata_info = "\n".join([f"  {k}: {v}" for k, v in self.header_metadata.items() if v])
    
        info = f"""DOCUMENTO CARICATO:

    Documento: {self.current_document_name}
    Nome CSV Export: {self.input_folder_name}.csv

    METADATI HEADER:
    {metadata_info if metadata_info else "  Nessun metadato"}

    Categorie JSON: {len(self.all_categories)}
    Categorie Database: {db_categories_count}
    Documenti: {len(self.documentgroups)}
    Pagine totali: {self.documentloader.totalpages if self.documentloader else 0}

    LAYOUT A GRIGLIA MULTI-RIGA:
    {grid_info}

    EXPORT:
    Formato: {format_display}
    Qualità JPEG: {self.config_manager.get('jpeg_quality', 95)}%
    File esistenti: {file_handling_display}
    CSV: Generato automaticamente con metadati

    Usa Menu → Aiuto → Istruzioni per dettagli completi.
    """
    
        return info

    def create_widgets(self):
        """Create main application widgets"""
        # Single horizontal PanedWindow with three independent panels
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, 
                                        sashrelief=tk.RAISED, sashwidth=4, sashpad=2,
                                        bg="gray")
        self.main_paned.pack(fill="both", expand=True, padx=2, pady=2)

        # Left panel for documents and thumbnails
        self.left_panel = tk.Frame(self.main_paned, bg="lightgray", bd=1, relief="solid")
        self.main_paned.add(self.left_panel, width=400, minsize=200, sticky="nsew")  # Ridotto minsize

        # Center panel for image display
        self.center_panel = tk.Frame(self.main_paned, bg="black", bd=1, relief="solid")
        self.main_paned.add(self.center_panel, width=700, minsize=300, sticky="nsew")

        # Right panel for controls
        self.right_panel = tk.Frame(self.main_paned, bg="lightgray", bd=1, relief="solid")
        self.main_paned.add(self.right_panel, width=300, minsize=150, sticky="nsew")  # Ridotto minsize

    def setup_left_panel(self):
        """Setup left panel with document list and thumbnails"""
        # Header for left panel
        header_left = tk.Label(self.left_panel, text="Documenti e Miniature", 
                              font=("Arial", 12, "bold"), bg="lightgray")
        header_left.pack(pady=10)

        # Action buttons - vertically stacked
        button_frame = tk.Frame(self.left_panel, bg="lightgray")
        button_frame.pack(pady=5)
        
        btn_refresh = tk.Button(button_frame, text="Aggiorna Lista (Preview)", 
                               command=self.refresh_document_list, 
                               bg="lightblue", font=("Arial", 10, "bold"), width=25)
        btn_refresh.pack(pady=2)

        btn_export = tk.Button(button_frame, text="Completa Sequenza / Export", 
                              command=self.complete_sequence_export, 
                              bg="lightgreen", font=("Arial", 10, "bold"), width=25)
        btn_export.pack(pady=2)

        # Scroll frame for documents
        self.setup_document_scroll_area()

    def setup_document_scroll_area(self):
        """Setup scrollable area for document groups"""
        self.scrollframe = tk.Frame(self.left_panel, bg="lightgray")
        self.scrollframe.pack(fill="both", expand=True, padx=5, pady=5)

        self.vscrollbar = tk.Scrollbar(self.scrollframe, orient=tk.VERTICAL)
        self.vscrollbar.pack(side="right", fill="y")

        self.canvas = tk.Canvas(self.scrollframe, yscrollcommand=self.vscrollbar.set, bg="white")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.vscrollbar.config(command=self.canvas.yview)

        self.content_frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        # Bind scroll events
        self.content_frame.bind("<Configure>", 
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        self.canvas.bind("<MouseWheel>", on_mousewheel)
        self.content_frame.bind("<MouseWheel>", on_mousewheel)
        
        # For Linux
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def setup_center_panel(self):
        """Setup center panel for image display"""
        # Frame contenitore con scrollbar
        self.image_frame = tk.Frame(self.center_panel, bg="black")
        self.image_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Scrollbars
        self.xscrollbar = tk.Scrollbar(self.image_frame, orient=tk.HORIZONTAL)
        self.xscrollbar.pack(side="bottom", fill="x")
        self.yscrollbar = tk.Scrollbar(self.image_frame, orient=tk.VERTICAL)
        self.yscrollbar.pack(side="right", fill="y")

        # Canvas con scroll
        self.image_canvas = tk.Canvas(
            self.image_frame, bg="black", cursor="cross",
            xscrollcommand=self.xscrollbar.set, yscrollcommand=self.yscrollbar.set
        )
        self.image_canvas.pack(side="left", fill="both", expand=True)

        self.xscrollbar.config(command=self.image_canvas.xview)
        self.yscrollbar.config(command=self.image_canvas.yview)

        # Zoom controls at bottom
        self.setup_zoom_controls()

        # Bind image canvas events
        self.bind_image_events()
    def setup_zoom_controls(self):
        """Setup zoom control buttons"""
        zoom_frame = tk.Frame(self.center_panel, bg="darkgray", height=50)
        zoom_frame.pack(side="bottom", fill="x", padx=2, pady=2)
        zoom_frame.pack_propagate(False)

        tk.Button(zoom_frame, text="Zoom +", command=self.zoom_in, 
                 bg="orange", font=("Arial", 9)).pack(side="left", padx=2)
        tk.Button(zoom_frame, text="Zoom -", command=self.zoom_out, 
                 bg="orange", font=("Arial", 9)).pack(side="left", padx=2)
        tk.Button(zoom_frame, text="Fit", command=self.zoom_fit, 
                 bg="yellow", font=("Arial", 9)).pack(side="left", padx=2)
        tk.Button(zoom_frame, text="Zoom Area", command=self.toggle_zoom_area, 
                 bg="lightgreen", font=("Arial", 9)).pack(side="left", padx=2)
        tk.Button(zoom_frame, text="Pan", command=self.toggle_pan_mode, 
                 bg="lightblue", font=("Arial", 9)).pack(side="left", padx=2)

        # Status label
        self.zoom_status = tk.Label(zoom_frame, text="", bg="darkgray", fg="white", font=("Arial", 8))
        self.zoom_status.pack(side="right", padx=10)

    def bind_image_events(self):
        """Bind events for image canvas"""
        # Click-to-fit (solo se non in pan/zoom-area)
        self.image_canvas.bind("<Button-1>", self.on_image_click)
        # Zoom area
        self.image_canvas.bind("<ButtonPress-1>", self.on_zoom_rect_start, add='+')
        self.image_canvas.bind("<B1-Motion>", self.on_zoom_rect_drag, add='+')
        self.image_canvas.bind("<ButtonRelease-1>", self.on_zoom_rect_end, add='+')
        # Pan (usa scan_mark/dragto)
        self.image_canvas.bind("<ButtonPress-1>", self.on_pan_start, add='+')
        self.image_canvas.bind("<B1-Motion>", self.on_pan_move, add='+')
        self.image_canvas.bind("<Configure>", self.on_canvas_resize)

        # Hover effects
        self.image_canvas.bind("<Enter>", self.on_canvas_enter)
        self.image_canvas.bind("<Leave>", self.on_canvas_leave)
    def setup_right_panel(self):
        """Setup right panel with controls and metadata"""
        # Header
        header_right = tk.Label(self.right_panel, text="Controlli e Dettagli", 
                               font=("Arial", 12, "bold"), bg="lightgray")
        header_right.pack(pady=10)

        # Selection info
        self.selection_info = tk.Label(self.right_panel, text="Nessuna selezione", 
                                      font=("Arial", 10, "bold"), bg="lightgray", fg="darkblue")
        self.selection_info.pack(pady=5)

        # Category selection frame
        self.setup_category_controls()

        # Page info
        self.page_info_label = tk.Label(self.right_panel, text="", 
                                       font=("Arial", 10), bg="lightgray")
        self.page_info_label.pack(pady=10)

        # NUOVO: Metadata frame
        self.setup_metadata_controls()

        # Instructions text area
        # self.setup_instructions_area()

    def setup_category_controls(self):
        """Setup category selection controls"""
        cat_frame = tk.Frame(self.right_panel, bg="lightgray", relief="ridge", bd=2)
        cat_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(cat_frame, text="Categoria Documento:", 
                font=("Arial", 10, "bold"), bg="lightgray").pack(anchor="w", padx=5, pady=2)
        
        # Frame for combobox + button
        combo_frame = tk.Frame(cat_frame, bg="lightgray")
        combo_frame.pack(fill="x", padx=5, pady=5)
        
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(combo_frame, textvariable=self.category_var, 
                                          font=("Arial", 9))
        self.category_combo.pack(side="left", fill="x", expand=True)
        
        # Button to save new category
        save_cat_btn = tk.Button(combo_frame, text="Salva", command=self.save_new_category, 
                                bg="lightgreen", font=("Arial", 8), width=6)
        save_cat_btn.pack(side="right", padx=(5, 0))
        
        # Bind events
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_changed)
        self.category_combo.bind("<Return>", self.on_category_enter)
    
    def setup_metadata_controls(self):
        """Setup metadata editing controls - completely dynamic based on JSON"""
        # Rimuovi frame esistente se presente
        if hasattr(self, 'metadata_frame'):
            self.metadata_frame.destroy()

        self.metadata_frame = tk.LabelFrame(
            self.right_panel, text="Metadati Documento",
            font=("Arial", 10, "bold"), bg="lightgray",
            relief="ridge", bd=2
        )
        self.metadata_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Container per canvas + scrollbar
        container = tk.Frame(self.metadata_frame, bg="lightgray")
        container.pack(fill="both", expand=True)

        # Canvas con larghezza minima più grande
        canvas = tk.Canvas(container, bg="lightgray", highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    
        # Frame scrollabile che si espande
        scrollable_frame = tk.Frame(canvas, bg="lightgray")

        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Forza il canvas a essere largo almeno quanto il frame
            canvas_width = max(scrollable_frame.winfo_reqwidth(), 240)
            canvas.itemconfig(canvas_window, width=canvas_width)

        scrollable_frame.bind("<Configure>", on_frame_configure)

        # Crea window con anchor="nw" e width iniziale
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        self.metadata_vars = {}
        self.metadata_entries = {}
        self.scrollable_metadata_frame = scrollable_frame

        # Popola con metadati correnti
        self.populate_metadata_fields(scrollable_frame)

        # Pack canvas e scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind per adattare larghezza quando il canvas cambia
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
    
        canvas.bind("<Configure>", on_canvas_configure)

        # Scroll con rotellina
        def on_metadata_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind("<MouseWheel>", on_metadata_mousewheel)
        scrollable_frame.bind("<MouseWheel>", on_metadata_mousewheel)

    def populate_metadata_fields(self, parent_frame):
        """Populate metadata fields dynamically from current header_metadata - RESPONSIVE"""
        # Clear existing widgets
        for widget in parent_frame.winfo_children():
            widget.destroy()

        self.metadata_vars.clear()
        self.metadata_entries.clear()

        row = 0
        for field, value in self.header_metadata.items():
            # Label con nome campo
            lbl = tk.Label(
                parent_frame, text=f"{field}:",
                font=("Arial", 9, "bold"), bg="lightgray", anchor="w"
            )
            lbl.grid(row=row, column=0, sticky="w", padx=5, pady=(5, 0))

            # Entry per valore - RESPONSIVE
            self.metadata_vars[field] = tk.StringVar(value=value)
            entry = tk.Entry(
                parent_frame, textvariable=self.metadata_vars[field],
                font=("Arial", 9), bg="white"
            )
            # CAMBIATO: sticky="ew" fa espandere l'entry in orizzontale
            entry.grid(row=row+1, column=0, sticky="ew", padx=5, pady=(0, 5), ipady=3)
            self.metadata_entries[field] = entry

            # Bind per auto-save
            self.metadata_vars[field].trace('w', lambda *args, f=field: self.on_metadata_changed(f))

            row += 2

        # IMPORTANTE: Configura colonna per espandersi
        parent_frame.grid_columnconfigure(0, weight=1)
    
        # AGGIUNTO: Forza update del layout
        parent_frame.update_idletasks()

    def setup_instructions_area(self):
        """Setup instructions text area"""
        instructions_label = tk.Label(self.right_panel, text="Pannello Informazioni:", 
                                     font=("Arial", 10, "bold"), bg="lightgray")
        instructions_label.pack(pady=(20, 5))

        self.instructions_text = ScrolledText(self.right_panel, height=10, width=35)
        self.instructions_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Default instructions
        self.update_instructions("Configura le cartelle input/output nelle Preferenze e usa 'Aggiorna Lista (Preview)' per iniziare.\n\nNuovo in v3.4: Gestione metadati e export CSV!")

    def bind_events(self):
        """Bind keyboard shortcuts and window events"""
        # Keyboard shortcuts
        self.bind_all('<Control-r>', lambda e: self.refresh_document_list())
        self.bind_all('<Control-e>', lambda e: self.complete_sequence_export())
        self.bind_all('<Control-q>', lambda e: self.on_closing())
        
        # Batch shortcut
        if self.config_manager.get('batch_mode_enabled', True):
            self.bind_all('<Control-b>', lambda e: self.open_batch_manager())
        
        # Window events
        # if self.config_manager.get('save_window_layout', True):
        #    self.bind('<Configure>', self.on_window_configure)
        #    self.bind_all('<B1-Motion>', self.on_paned_motion)
        #    self.bind_all('<ButtonRelease-1>', self.on_paned_release)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    # Event handlers
    def on_canvas_enter(self, event):
        """Handle mouse enter on image canvas"""
        if self.current_image:
            self.image_canvas.configure(bg="#1a1a1a")

    def on_canvas_leave(self, event):
        """Handle mouse leave on image canvas"""
        if self.current_image:
            self.image_canvas.configure(bg="black")

    def on_window_configure(self, event):
        """Handle window resize/move events"""
        # IMPORTANTE: ignora eventi che non sono della finestra principale
        if event.widget != self:
            return
    
        if self.config_manager.get('save_window_layout', True):
            if hasattr(self, '_save_config_after_id'):
                self.after_cancel(self._save_config_after_id)
            self._save_config_after_id = self.after(2000, self.save_config)

    def on_paned_motion(self, event):
        """Handle paned window motion during drag"""
        if hasattr(self, '_is_paned_dragging'):
            self._is_paned_dragging = True

    def on_paned_release(self, event):
        """Handle paned window sash release"""
        if self.config_manager.get('save_window_layout', True):
            self.after(100, self.save_config)

    def on_category_changed(self, event=None):
        """Handle category selection change"""
        new_category = self.category_var.get()
        
        if self.selected_group:
            if new_category != self.selected_group.categoryname:
                old_category = self.selected_group.categoryname
                self.selected_group.update_category_name(new_category)
                self.page_info_label.config(text=f"Documento: {new_category} ({len(self.selected_group.pages)} pagine)")
                
                self.category_db.add_category(new_category)
                
                if self.selected_thumbnail:
                    self.selection_info.config(text=f"Selezionata: Pagina {self.selected_thumbnail.pagenum}")
                
                self.debug_print(f"Category changed from {old_category} to {new_category}")

    def on_category_enter(self, event):
        """Handle Enter key in category combo"""
        self.save_new_category()

    def on_metadata_changed(self, field_name):
        """Handle metadata field change - NUOVO"""
        new_value = self.metadata_vars[field_name].get()
        self.header_metadata[field_name] = new_value
        self.debug_print(f"Metadata {field_name} changed to: {new_value}")

    def on_canvas_resize(self, event):
        """Handle canvas resize to update image display"""
        if self.current_image and hasattr(self, 'auto_fit_on_resize') and self.config_manager.get('auto_fit_images', True):
            self.after_idle(self.update_image_display)

    def on_closing(self):
        """Handle application closing"""
        self.debug_print("Application closing, saving configuration...")
        if self.config_manager.get('auto_save_changes', True):
            self.save_config()
        self.destroy()

    # Configuration and layout management
    def save_config(self):
        """Save current configuration"""
        try:
            if self.config_manager.get('save_window_layout', True):
                self.config_manager.config_data['window_settings'] = {
                    'geometry': self.geometry(),
                    'state': self.state()
                }
                
                try:
                    if hasattr(self, 'main_paned'):
                        left_center_pos = self.main_paned.sash_coord(0)[0]
                        center_right_pos = self.main_paned.sash_coord(1)[0]
                        
                        self.config_manager.config_data['panel_settings'] = {
                            'left_center_position': left_center_pos,
                            'center_right_position': center_right_pos
                        }
                        
                        self.debug_print(f"Saving panel positions: {left_center_pos}, {center_right_pos}")
                except Exception as e:
                    print(f"Error getting paned positions: {e}")
            
            self.config_manager.save_config()
            
        except Exception as e:
            print(f"Error saving config: {e}")

    def restore_window_layout(self):
        """Restore window layout from configuration"""
        try:
            panel_settings = self.config_manager.get('panel_settings', {})
            
            left_center_pos = panel_settings.get('left_center_position', 400)
            if hasattr(self, 'main_paned') and left_center_pos > 50:
                self.main_paned.sash_place(0, left_center_pos, 0)
                self.debug_print(f"Restored left-center position: {left_center_pos}")
            
            center_right_pos = panel_settings.get('center_right_position', 1100)
            if hasattr(self, 'main_paned') and center_right_pos > left_center_pos + 100:
                self.main_paned.sash_place(1, center_right_pos, 0)
                self.debug_print(f"Restored center-right position: {center_right_pos}")
                
        except Exception as e:
            print(f"Error restoring window layout: {e}")

    # Utility methods
    def debug_print(self, message: str):
        """Print debug messages only if enabled in config"""
        if self.config_manager.get('show_debug_info', False):
            print(f"[DEBUG] {message}")

    def update_instructions(self, text: str):
        """Update instructions text area"""
        if hasattr(self, 'instructions_text'):
            self.instructions_text.delete("1.0", tk.END)
            self.instructions_text.insert(tk.END, text)

    # Menu handlers
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.config_manager)
        if dialog.result:
            old_thumb_size = (self.config_manager.get('thumbnail_width', 80), 
                            self.config_manager.get('thumbnail_height', 100))
            old_font_settings = (
                self.config_manager.get('document_font_name', 'Arial'),
                self.config_manager.get('document_font_size', 10),
                self.config_manager.get('document_font_bold', True),
                self.config_manager.get('document_counter_digits', 4)
            )
            
            self.config_manager.update(dialog.result)
            self.config_manager.save_config()
            
            new_thumb_size = (self.config_manager.get('thumbnail_width', 80), 
                            self.config_manager.get('thumbnail_height', 100))
            new_font_settings = (
                self.config_manager.get('document_font_name', 'Arial'),
                self.config_manager.get('document_font_size', 10),
                self.config_manager.get('document_font_bold', True),
                self.config_manager.get('document_counter_digits', 4)
            )
            
            if old_thumb_size != new_thumb_size:
                self.refresh_thumbnails()
            
            if old_font_settings != new_font_settings:
                self.refresh_document_headers()
                
            messagebox.showinfo("Impostazioni", "Impostazioni salvate con successo!")

    def reset_layout(self):
        """Reset window layout to default"""
        if messagebox.askyesno("Conferma", "Ripristinare il layout predefinito della finestra?"):
            self.geometry("1400x800+100+50")
            if hasattr(self, 'main_paned'):
                self.main_paned.sash_place(0, 400, 0)
                self.main_paned.sash_place(1, 1100, 0)
            self.save_config()

    def refresh_thumbnails(self):
        """Refresh all thumbnails with new size settings"""
        if not self.documentgroups:
            return
        
        for group in self.documentgroups:
            group.refresh_thumbnail_sizes()
            self.after_idle(lambda g=group: g.repack_thumbnails_grid())

    def refresh_document_headers(self):
        """Refresh all document headers with new font settings"""
        if not self.documentgroups:
            return
        
        for group in self.documentgroups:
            group.refresh_font_settings()

    # Category management
    def save_new_category(self):
        """Save new category from combobox"""
        new_category = self.category_var.get().strip()
        if new_category and new_category not in [self.category_combo['values']]:
            if self.category_db.add_category(new_category):
                self.update_category_combo()
                if self.selected_group and new_category != self.selected_group.categoryname:
                    old_category = self.selected_group.categoryname
                    self.selected_group.update_category_name(new_category)
                    self.page_info_label.config(text=f"Documento: {new_category} ({len(self.selected_group.pages)} pagine)")
                    
                    if self.selected_thumbnail:
                        self.selection_info.config(text=f"Selezionata: Pagina {self.selected_thumbnail.pagenum}")
                    
                    messagebox.showinfo("Categoria Salvata", f"Categoria '{new_category}' salvata nel database!")
                    self.debug_print(f"New category saved: {new_category}")
                else:
                    messagebox.showinfo("Categoria Salvata", f"Categoria '{new_category}' salvata nel database!")
            else:
                messagebox.showerror("Errore", "Errore nel salvataggio della categoria")
        else:
            messagebox.showwarning("Attenzione", "Inserisci una categoria valida o nuova")

    def update_category_combo(self):
        """Update category combo with all available categories"""
        json_categories = list(self.all_categories)
        db_categories = self.category_db.get_all_categories()
        all_cats = sorted(set(json_categories + db_categories))
        self.category_combo['values'] = all_cats

    def load_metadata_from_json(self, data):
        """Load metadata from JSON header - completely dynamic"""
        header = data.get('header', data)  # Supporta sia {header: {...}} che JSON flat
    
        # Reset metadati
        self.header_metadata.clear()
    
        # Carica tutti i campi dal JSON dinamicamente
        for key, value in header.items():
            # Converti None in stringa vuota
            self.header_metadata[key] = str(value) if value is not None else ''
    
        # Rebuild UI metadati
        if hasattr(self, 'scrollable_metadata_frame'):
            self.populate_metadata_fields(self.scrollable_metadata_frame)
    
        self.debug_print(f"Loaded {len(self.header_metadata)} metadata fields: {list(self.header_metadata.keys())}")

    # Document loading and management
    def refresh_document_list(self):
        """Load document from configured input folder - supports both modes"""
        input_folder = self.config_manager.get('default_input_folder', '')
    
        if not input_folder or not os.path.exists(input_folder):
            messagebox.showerror("Errore", 
                            "Cartella input non configurata o non esistente.\n"
                            "Configura la cartella nelle Preferenze.")
            return

        self.input_folder_name = os.path.basename(os.path.normpath(input_folder))

        json_file = None
        doc_file = None
    
        for file in os.listdir(input_folder):
            if file.lower().endswith('.json'):
                json_file = os.path.join(input_folder, file)
            elif file.lower().endswith(('.pdf', '.tiff', '.tif')):
                doc_file = os.path.join(input_folder, file)

        if not json_file or not doc_file:
            messagebox.showerror("Errore", 
                           "Cartella input deve contenere un file JSON e un documento PDF/TIFF")
            return

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.original_data = data
        
            # Carica metadati (dinamici)
            self.load_metadata_from_json(data)
        
            # Determina modalità
            has_categories = 'categories' in data and isinstance(data['categories'], list)
            split_enabled = self.config_manager.get('split_documents_by_category', True)
        
            self.current_document_name = os.path.splitext(os.path.basename(doc_file))[0]
        
            # Carica documento
            self.load_document(doc_file)
        
            if has_categories and split_enabled:
                # MODALITÀ 1: Dividi in documenti multipli
                categories = data['categories']
                self.all_categories = set(cat['categoria'] for cat in categories if cat['categoria'] != "Pagina vuota")
                self.update_category_combo()
                self.build_document_groups(categories)
                self.debug_print(f"Mode: SPLIT - {len(categories)} categories, {len(self.documentgroups)} documents")
            else:
                # MODALITÀ 2: Documento unico con tutte le pagine
                self.all_categories = set()
                self.update_category_combo()
                self.build_single_document()
                self.debug_print(f"Mode: SINGLE DOCUMENT - {self.documentloader.totalpages} pages")
        
            self.debug_print(f"Document loaded with {len(self.header_metadata)} metadata fields")
        
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {str(e)}")
            import traceback
            traceback.print_exc()

    def load_document(self, doc_path: str):
        """Load PDF or TIFF document"""
        try:
            self.documentloader = create_document_loader(doc_path)
            self.documentloader.load()
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento del documento: {str(e)}")
            self.documentloader = None
    def build_document_groups(self, categories: List[dict]):
        """Build document groups from category data with improved grid layout"""
        if self.updating_ui:
            return
        self.updating_ui = True

        for group in self.documentgroups:
            group.destroy()
        self.documentgroups.clear()

        current_group = None
        current_pages = []
        documents = []

        for cat in categories:
            cat_name = cat['categoria']
            start = cat['inizio']
            end = cat['fine']
            
            if cat_name == "Pagina vuota" and current_group is not None:
                for p in range(start, end+1):
                    current_pages.append(p)
            else:
                if current_group is not None:
                    documents.append({
                        "categoria": current_group,
                        "pagine": current_pages.copy()
                    })
                current_group = cat_name
                current_pages = list(range(start, end+1))
        
        if current_group is not None:
            documents.append({
                "categoria": current_group,
                "pagine": current_pages.copy()
            })

        document_counter = 1
        for doc in documents:
            group = DocumentGroup(self.content_frame, doc["categoria"], self, document_counter)
            for pagenum in doc["pagine"]:
                img = self.documentloader.get_page(pagenum)
                if img:
                    group.add_page(pagenum, img)
            group.pack(pady=5, fill="x", padx=5)
            self.documentgroups.append(group)
            document_counter += 1

        self.after_idle(self.update_scroll_region)
        
        self.updating_ui = False
        self.debug_print(f"Created {len(documents)} document groups with grid layout")

    def build_single_document(self):
        """Build single document group with all pages (no category splitting)"""
        if self.updating_ui:
            return
        self.updating_ui = True

        # Clear existing groups
        for group in self.documentgroups:
            group.destroy()
        self.documentgroups.clear()

        # Crea documento unico
        document_name = self.input_folder_name or "Documento"
        group = DocumentGroup(self.content_frame, document_name, self, 1)
    
        # Aggiungi tutte le pagine
        for pagenum in range(1, self.documentloader.totalpages + 1):
            img = self.documentloader.get_page(pagenum)
            if img:
                group.add_page(pagenum, img)
    
        group.pack(pady=5, fill="x", padx=5)
        self.documentgroups.append(group)

        self.after_idle(self.update_scroll_region)
        self.updating_ui = False
        self.debug_print(f"Created single document with {self.documentloader.totalpages} pages")

    def update_scroll_region(self):
        """Update scroll region for document groups"""
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def update_document_instructions(self, json_file: str, doc_file: str, input_folder: str, categories: List):
        """Update instructions panel with document information including metadata"""
        export_format = self.config_manager.get('export_format', 'JPEG')
        format_display = {
            'JPEG': 'JPEG',
            'PDF_SINGLE': 'PDF (pagina singola)',
            'PDF_MULTI': 'PDF (multipagina per documento)',
            'TIFF_SINGLE': 'TIFF (pagina singola)',
            'TIFF_MULTI': 'TIFF (multipagina per documento)'
        }.get(export_format, export_format)
        
        file_handling_mode = self.config_manager.get('file_handling_mode', 'auto_rename')
        file_handling_display = {
            'auto_rename': 'Rinomina automaticamente',
            'ask_overwrite': 'Chiedi conferma',
            'always_overwrite': 'Sovrascrivi sempre'
        }.get(file_handling_mode, file_handling_mode)
        
        db_categories_count = len(self.category_db.get_all_categories())
        
        grid_info = ""
        for i, group in enumerate(self.documentgroups):
            page_count = group.get_page_count()
            group_info = group.get_info()
            grid_rows = group_info.get('grid_rows', 0)
            per_row = group_info.get('thumbnails_per_row', 4)
            if page_count > 0:
                grid_info += f"  Doc {i+1}: {page_count} pagine ({grid_rows} righe, {per_row}/riga)\n"
        
        metadata_info = "\n".join([f"  {k}: {v}" for k, v in self.header_metadata.items() if v])
        
        instructions = f"""DOCUMENTO CARICATO:

File JSON: {os.path.basename(json_file)}
Documento: {os.path.basename(doc_file)}
Cartella Input: {input_folder}
Nome CSV Export: {self.input_folder_name}.csv

METADATI HEADER:
{metadata_info if metadata_info else "  Nessun metadato"}

Categorie JSON: {len(self.all_categories)}
Categorie Database: {db_categories_count}
Documenti: {len(self.documentgroups)}
Pagine totali: {self.documentloader.totalpages if self.documentloader else 0}

LAYOUT A GRIGLIA MULTI-RIGA:
{grid_info}

EXPORT:
Formato: {format_display}
Qualità JPEG: {self.config_manager.get('jpeg_quality', 95)}%
File esistenti: {file_handling_display}
CSV: Generato automaticamente con metadati

Usa il menu 'Aiuto > Istruzioni' per dettagli completi.
        """
        
        self.update_instructions(instructions)
    
    # inserire qui def complete_sequence
    def complete_sequence_export(self):
        """Export images and CSV to configured output folder"""
        if not self.documentgroups:
            messagebox.showwarning("Attenzione", "Nessun documento caricato")
            return

        output_folder = self.config_manager.get('default_output_folder', '')
        
        if not output_folder:
            messagebox.showerror("Errore", 
                               "Cartella output non configurata.\n"
                               "Configura la cartella nelle Preferenze.")
            return
            
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile creare cartella output: {str(e)}")
                return

        try:
            export_format = self.config_manager.get('export_format', 'JPEG')
            progress_window, progress_var, _ = create_progress_dialog(self, f"Export in formato {export_format}...")
            
            def progress_callback(message):
                progress_var.set(message)
                progress_window.update()
            
            exported_files = self.export_manager.export_documents(
                output_folder, self.documentgroups, self.current_document_name, progress_callback
            )
            
            progress_var.set("Generazione CSV...")
            progress_window.update()
            csv_filename = self.export_csv_metadata(output_folder, exported_files)
            progress_window.destroy()
            
            summary_message = f"Export completato!\n\n"
            summary_message += f"Formato: {export_format}\n"
            summary_message += f"Cartella: {output_folder}\n"
            summary_message += f"File immagini: {len(exported_files)}\n"
            summary_message += f"File CSV: {csv_filename}\n"
            if export_format in ['PDF_MULTI', 'TIFF_MULTI']:
                summary_message += f"Documenti processati: {len(self.documentgroups)}"
            
            messagebox.showinfo("Export Completato", summary_message)
            
            if messagebox.askyesno("Reset Workspace", "Export completato!\n\nVuoi resettare il workspace per un nuovo documento?"):
                self.reset_workspace()
                
            self.config_manager.set('last_folder', output_folder)
            if self.config_manager.get('auto_save_changes', True):
                self.save_config()
            self.debug_print(f"Exported {len(exported_files)} files and CSV to {output_folder}")
            
        except Exception as e:
            if 'progress_window' in locals():
                progress_window.destroy()
            messagebox.showerror("Errore", f"Errore durante l'export: {str(e)}")
    
    def reset_workspace(self):
        """Reset workspace after export"""
        for group in self.documentgroups:
            group.destroy()
        self.documentgroups.clear()
        self.documentloader = None
        self.original_data = None
        self.current_document_name = ""
        self.all_categories = set()
        self.input_folder_name = ""
        for field in self.header_metadata:
            self.header_metadata[field] = ''
            if field in self.metadata_vars:
                self.metadata_vars[field].set('')
        self.selected_thumbnail = None
        self.selected_group = None
        self.selection_info.config(text="Nessuna selezione")
        self.page_info_label.config(text="")
        self.category_var.set("")
        self.image_canvas.delete("all")
        self.current_image = None
        self.after_idle(self.update_scroll_region)
        self.debug_print("Workspace reset completed")
        
    def export_csv_metadata(self, output_folder: str, exported_files: List[str]) -> str:
        """Export CSV file with dynamic metadata - respects file handling settings"""
        csv_filename = f"{self.input_folder_name}.csv"
        csv_path = os.path.join(output_folder, csv_filename)
    
        # Check file esistente
        if os.path.exists(csv_path):
            file_handling_mode = self.config_manager.get('file_handling_mode', 'auto_rename')
        
            if file_handling_mode == 'ask_overwrite':
                response = messagebox.askyesnocancel(
                    "File CSV Esistente",
                    f"Il file CSV '{csv_filename}' esiste già.\n\n"
                    "Sì = Sovrascrivi\n"
                    "No = Rinomina automaticamente\n"
                    "Annulla = Salta creazione CSV"
                )
            
                if response is None:
                    self.debug_print("CSV export cancelled by user")
                    return ""
                elif response is False:
                    csv_path = self._get_unique_csv_filename(output_folder, csv_filename)
                    csv_filename = os.path.basename(csv_path)
                
            elif file_handling_mode == 'auto_rename':
                csv_path = self._get_unique_csv_filename(output_folder, csv_filename)
                csv_filename = os.path.basename(csv_path)
                self.debug_print(f"CSV renamed to: {csv_filename}")
    
        delimiter = self.config_manager.get('csv_delimiter', ';')
    
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=delimiter)
            
                # Header dinamico: Nome File + Categoria + tutti i metadati
                header_row = ['Nome File', 'Categoria'] + list(self.header_metadata.keys())
                writer.writerow(header_row)
            
                export_format = self.config_manager.get('export_format', 'JPEG')
            
                if export_format in ['PDF_MULTI', 'TIFF_MULTI']:
                    # Export multipagina
                    for doc_index, group in enumerate(self.documentgroups, 1):
                        if not group.thumbnails:
                            continue
                    
                        safe_category = self.export_manager.sanitize_filename(group.categoryname)
                        matching_files = [f for f in exported_files if f'_doc{doc_index:03d}_{safe_category}' in f]
                    
                        if matching_files:
                            filename = matching_files[0]
                        else:
                            ext = '.pdf' if 'PDF' in export_format else '.tiff'
                            filename = f"{self.current_document_name}_doc{doc_index:03d}_{safe_category}{ext}"
                    
                        # Riga dinamica
                        row = [filename, group.categoryname] + [self.header_metadata.get(k, '') for k in self.header_metadata.keys()]
                        writer.writerow(row)
                else:
                    # Export pagina singola
                    file_index = 0
                    for group in self.documentgroups:
                        for thumbnail in group.thumbnails:
                            if file_index < len(exported_files):
                                filename = exported_files[file_index]
                                row = [filename, group.categoryname] + [self.header_metadata.get(k, '') for k in self.header_metadata.keys()]
                                writer.writerow(row)
                                file_index += 1
        
            self.debug_print(f"CSV exported with {len(self.header_metadata)} metadata columns: {csv_path}")
            return csv_filename
        
        except Exception as e:
            self.debug_print(f"Error exporting CSV: {e}")
            raise

    def _get_unique_csv_filename(self, folder: str, original_filename: str) -> str:
        """Generate unique CSV filename by adding counter"""
        base_name = os.path.splitext(original_filename)[0]
        extension = os.path.splitext(original_filename)[1]
        
        counter = 1
        new_path = os.path.join(folder, original_filename)
        
        while os.path.exists(new_path):
            new_filename = f"{base_name}({counter}){extension}"
            new_path = os.path.join(folder, new_filename)
            counter += 1
            
            # Safety check to avoid infinite loop
            if counter > 9999:
                raise Exception("Troppi file CSV con lo stesso nome base")
        
        return new_path

    def select_thumbnail(self, thumbnail: PageThumbnail):
        """Select a thumbnail and display its image"""
        self.debug_print(f"select_thumbnail called for page {thumbnail.pagenum}")
        
        if self.selected_thumbnail:
            try:
                self.selected_thumbnail.deselect()
            except tk.TclError:
                pass
        if self.selected_group:
            try:
                self.selected_group.deselect_group()
            except tk.TclError:
                pass
            
        self.selected_thumbnail = thumbnail
        self.selected_group = thumbnail.document_group
        
        thumbnail.select()
        self.selected_group.select_group()
        
        self.debug_print(f"About to display image for page {thumbnail.pagenum}")
        
        try:
            if thumbnail.image:
                self.display_image(thumbnail.image)
                self.debug_print(f"Image displayed successfully for page {thumbnail.pagenum}")
            else:
                self.debug_print(f"No image found for page {thumbnail.pagenum}")
        except Exception as e:
            print(f"[ERROR] Failed to display image: {e}")
            self.debug_print(f"Error displaying image: {e}")
        
        self.category_var.set(thumbnail.categoryname)
        self.selection_info.config(text=f"Selezionata: Pagina {thumbnail.pagenum}")
        self.page_info_label.config(text=f"Documento: {thumbnail.categoryname}")
        
        thumbnail.select()
        self.selected_group.select_group()
        
        self.debug_print(f"About to display image for page {thumbnail.pagenum}")
        
        try:
            if thumbnail.image:
                self.display_image(thumbnail.image)
                self.debug_print(f"Image displayed successfully for page {thumbnail.pagenum}")
            else:
                self.debug_print(f"No image found for page {thumbnail.pagenum}")
        except Exception as e:
            print(f"[ERROR] Failed to display image: {e}")
            self.debug_print(f"Error displaying image: {e}")
        
        self.category_var.set(thumbnail.categoryname)
        self.selection_info.config(text=f"Selezionata: Pagina {thumbnail.pagenum}")
        self.page_info_label.config(text=f"Documento: {thumbnail.categoryname}")

    def select_document_group(self, group: DocumentGroup):
        """Select an entire document group"""
        if self.selected_thumbnail:
            self.selected_thumbnail.deselect()
            self.selected_thumbnail = None
        if self.selected_group:
            self.selected_group.deselect_group()
            
        self.selected_group = group
        group.select_group()
        
        self.category_var.set(group.categoryname)
        self.selection_info.config(text=f"Selezionato: Documento")
        self.page_info_label.config(text=f"Documento: {group.categoryname} ({len(group.pages)} pagine)")

    def display_image(self, image: Image.Image):
        """Display image in center panel"""
        self.debug_print(f"display_image called with image: {image is not None}")
        
        if not image:
            self.debug_print("Warning: No image provided to display_image")
            self.image_canvas.delete("all")
            self.current_image = None
            return
        
        self.current_image = image
        self.zoom_factor = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.auto_fit_on_resize = True
        
        self.debug_print(f"Image size: {image.size if image else 'None'}")
        
        if self.config_manager.get('auto_fit_images', True):
            self.after_idle(self.zoom_fit)
        else:
            self.after_idle(self.update_image_display)
        
        self.debug_print("display_image completed")

    def zoom_fit(self):
        """Fit image to canvas"""
        if not self.current_image:
            return
        
        canvas_w = self.image_canvas.winfo_width()
        canvas_h = self.image_canvas.winfo_height()
        
        if canvas_w < 50 or canvas_h < 50:
            self.after(100, self.zoom_fit)
            return
        
        img_w, img_h = self.current_image.size
        scale_w = canvas_w / img_w
        scale_h = canvas_h / img_h
        self.zoom_factor = min(scale_w, scale_h) * 0.9
        
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.update_image_display()
        self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def zoom_in(self):
        """Zoom in the image"""
        if self.current_image:
            self.auto_fit_on_resize = False
            self.zoom_factor *= 1.25
            self.update_image_display()
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def zoom_out(self):
        """Zoom out the image"""
        if self.current_image:
            self.auto_fit_on_resize = False
            self.zoom_factor = max(0.1, self.zoom_factor / 1.25)
            self.update_image_display()
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def toggle_zoom_area(self):
        """Toggle zoom area selection mode"""
        self.zoom_area_mode = not self.zoom_area_mode
        if self.zoom_area_mode:
            self.image_canvas.config(cursor="crosshair")
            self.zoom_status.config(text="Seleziona area per zoom")
        else:
            self.image_canvas.config(cursor="cross")
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def on_image_click(self, event):
        """Handle image click - click-to-fit"""
        if self.current_image and not self.zoom_area_mode and not self.pan_mode:
            self.auto_fit_on_resize = True
            if self.config_manager.get('auto_fit_images', True):
                self.zoom_fit()

    def on_zoom_rect_start(self, event):
        """Start zoom rectangle selection"""
        if self.pan_mode:
            return
        if self.zoom_area_mode and self.current_image:
            self.zoom_rect_start = (event.x, event.y)
            if self.zoom_rect_id:
                self.image_canvas.delete(self.zoom_rect_id)

    def on_zoom_rect_drag(self, event):
        """Drag zoom rectangle"""
        if self.pan_mode:
            return
        if self.pan_mode:
            return
        if self.zoom_area_mode and self.zoom_rect_start and self.current_image:
            if self.zoom_rect_id:
                self.image_canvas.delete(self.zoom_rect_id)
            self.zoom_rect_id = self.image_canvas.create_rectangle(
                self.zoom_rect_start[0], self.zoom_rect_start[1], 
                event.x, event.y, outline="red", width=2)

    def on_zoom_rect_end(self, event):
        """End zoom rectangle selection"""
        if self.zoom_area_mode and self.zoom_rect_start and self.current_image:
            self.zoom_rect_end = (event.x, event.y)
            if self.zoom_rect_id:
                self.image_canvas.delete(self.zoom_rect_id)
                self.zoom_rect_id = None
            
            x1, y1 = self.zoom_rect_start
            x2, y2 = self.zoom_rect_end
            if abs(x2-x1) > 10 and abs(y2-y1) > 10:
                self.auto_fit_on_resize = False
                self.zoom_to_area(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
            
            self.zoom_area_mode = False
            self.image_canvas.config(cursor="cross")
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def toggle_pan_mode(self):
        """Toggle pan mode"""
        self.pan_mode = not self.pan_mode
        if self.pan_mode:
            self.image_canvas.config(cursor="fleur")
            self.zoom_status.config(text="Modalità Pan attiva")
        else:
            self.image_canvas.config(cursor="cross")
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def on_pan_start(self, event):
        """Start canvas panning"""
        if self.pan_mode and self.current_image:
            self.image_canvas.scan_mark(event.x, event.y)

    def on_pan_move(self, event):
        """Canvas panning drag"""
        if self.pan_mode and self.current_image:
            self.image_canvas.scan_dragto(event.x, event.y, gain=1)
    def zoom_to_area(self, x: int, y: int, w: int, h: int):
        """Zoom to specific area"""
        if not self.current_image:
            return
        
        canvas_w = self.image_canvas.winfo_width()
        canvas_h = self.image_canvas.winfo_height()
        
        zoom_w = canvas_w / w
        zoom_h = canvas_h / h
        new_zoom = min(zoom_w, zoom_h) * self.zoom_factor
        
        center_x = x + w/2
        center_y = y + h/2
        
        self.zoom_factor = new_zoom
        self.image_offset_x = canvas_w/2 - center_x * (new_zoom / self.zoom_factor)
        self.image_offset_y = canvas_h/2 - center_y * (new_zoom / self.zoom_factor)
        
        self.update_image_display()
        self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def update_image_display(self):
        """Update the image display on canvas with scroll support"""
        if not self.current_image:
            return

        self.image_canvas.delete("all")

        img_w, img_h = self.current_image.size
        new_w = int(img_w * self.zoom_factor)
        new_h = int(img_h * self.zoom_factor)

        if new_w <= 0 or new_h <= 0:
            return

        try:
            resized_img = self.current_image.resize((new_w, new_h), RESAMPLEFILTER)
            self.photo = ImageTk.PhotoImage(resized_img)

            canvas_w = self.image_canvas.winfo_width()
            canvas_h = self.image_canvas.winfo_height()

            pad_x = max(0, (canvas_w - new_w) // 2)
            pad_y = max(0, (canvas_h - new_h) // 2)

            # Disegna immagine ancorata a NW (con eventuale padding per centrare se più piccola)
            self.image_canvas.create_image(pad_x, pad_y, image=self.photo, anchor="nw")

            # Scrollregion: area massima tra canvas e immagine
            sr_w = max(new_w, canvas_w)
            sr_h = max(new_h, canvas_h)
            self.image_canvas.config(scrollregion=(0, 0, sr_w, sr_h))

        except Exception as e:
            self.debug_print(f"Error updating image display: {e}")
    def create_drag_preview(self, thumbnail: PageThumbnail):
        """Create drag preview window"""
        self.drag_item = thumbnail
        self.drag_preview = tk.Toplevel(self)
        self.drag_preview.overrideredirect(True)
        self.drag_preview.attributes('-topmost', True)
        lbl = tk.Label(self.drag_preview, image=thumbnail.thumbnail_imgtk, bd=2, relief="solid", bg="yellow")
        lbl.pack()
        self.drag_preview.geometry(f"+{self.winfo_pointerx()+20}+{self.winfo_pointery()+20}")

    def move_drag_preview(self, x: int, y: int):
        """Move drag preview to coordinates"""
        if self.drag_preview:
            self.drag_preview.geometry(f"+{x}+{y}")

    def stop_drag(self, x_root: int, y_root: int):
        """Stop drag operation - Enhanced for grid layout"""
        if not self.dragging:
            return
        
        self.dragging = False
        
        if self.drag_preview:
            self.drag_preview.destroy()
            self.drag_preview = None
            
        target_group = self.get_group_at_position(x_root, y_root)
        
        if target_group and self.drag_item:
            original_group = None
            for group in self.documentgroups:
                if self.drag_item in group.thumbnails:
                    original_group = group
                    break
            
            if original_group == target_group:
                self.reorder_within_group(self.drag_item, target_group, x_root, y_root)
            else:
                self.move_page_to_group(self.drag_item, target_group)
            
        self.drag_item = None

    def get_group_at_position(self, x_root: int, y_root: int) -> Optional[DocumentGroup]:
        """Get document group at screen coordinates"""
        for group in self.documentgroups:
            try:
                gx = group.frame.winfo_rootx()
                gy = group.frame.winfo_rooty()
                gw = group.frame.winfo_width()
                gh = group.frame.winfo_height()
                if gx <= x_root <= gx + gw and gy <= y_root <= gy + gh:
                    return group
            except tk.TclError:
                continue
        return None

    def reorder_within_group(self, thumbnail: PageThumbnail, group: DocumentGroup, x_root: int, y_root: int):
        """Reorder thumbnail within the same group - Enhanced for grid layout"""
        old_index = group.thumbnails.index(thumbnail)
        
        new_index = self.calculate_grid_drop_position(group, x_root, y_root)
        
        if new_index > old_index:
            new_index -= 1
            
        if old_index == new_index:
            return
        
        group.thumbnails.pop(old_index)
        group.pages.pop(old_index)
        
        group.thumbnails.insert(new_index, thumbnail)
        group.pages.insert(new_index, thumbnail.pagenum)
        
        group.repack_thumbnails_grid()
        
        self.debug_print(f"Reordered page {thumbnail.pagenum} in {group.categoryname} from {old_index} to {new_index}")

    def calculate_grid_drop_position(self, group: DocumentGroup, x_root: int, y_root: int) -> int:
        """Calculate drop position in grid layout based on mouse coordinates"""
        if not group.thumbnails:
            return 0
        
        frame_x = group.pages_frame.winfo_rootx()
        frame_y = group.pages_frame.winfo_rooty()
        relative_x = x_root - frame_x
        relative_y = y_root - frame_y
        
        thumb_width = self.config_manager.get('thumbnail_width', 80)
        thumb_height = self.config_manager.get('thumbnail_height', 100)
        padding = 6
        
        col = max(0, relative_x // (thumb_width + padding))
        row = max(0, relative_y // (thumb_height + 20 + padding))
        
        thumbnails_per_row = group.thumbnails_per_row
        estimated_position = row * thumbnails_per_row + col
        
        return min(estimated_position, len(group.thumbnails))

    def move_page_to_group(self, thumbnail: PageThumbnail, target_group: DocumentGroup):
        """Move page to different group"""
        original_group = None
        for group in self.documentgroups:
            if thumbnail in group.thumbnails:
                original_group = group
                break
                
        if not original_group or original_group == target_group:
            return

        original_group.remove_thumbnail(thumbnail)
        
        thumbnail.frame.destroy()
        
        new_thumbnail = target_group.add_page(thumbnail.pagenum, thumbnail.image)
        
        if self.selected_thumbnail == thumbnail:
            self.selected_thumbnail = new_thumbnail
            self.selected_group = target_group
            new_thumbnail.select()
            target_group.select_group()
            self.category_var.set(target_group.categoryname)
            self.selection_info.config(text=f"Selezionata: Pagina {thumbnail.pagenum}")
            self.page_info_label.config(text=f"Documento: {target_group.categoryname}")

        self.debug_print(f"Moved page {thumbnail.pagenum} from {original_group.categoryname} to {target_group.categoryname}")

    def show_document_context_menu(self, document_group: DocumentGroup, event):
        """Show context menu for document group"""
        context_menu = tk.Menu(self, tearoff=0)
        
        context_menu.add_command(label="Nuovo documento prima", 
                               command=lambda: self.create_new_document(document_group, "before"))
        context_menu.add_command(label="Nuovo documento dopo", 
                               command=lambda: self.create_new_document(document_group, "after"))
        context_menu.add_separator()
        
        if document_group.is_empty():
            context_menu.add_command(label="Elimina documento vuoto", 
                                   command=lambda: self.delete_empty_document(document_group))
        else:
            context_menu.add_command(label="Elimina documento vuoto", state="disabled")
        
        try:
            context_menu.post(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def create_new_document(self, reference_document: DocumentGroup, position: str):
        """Create new document before or after reference document"""
        json_categories = list(self.all_categories)
        db_categories = self.category_db.get_all_categories()
        
        dialog = CategorySelectionDialog(self, json_categories, db_categories, 
                                       "Seleziona Categoria per Nuovo Documento")
        
        if dialog.result:
            selected_category = dialog.result
            
            self.category_db.add_category(selected_category)
            
            ref_index = self.documentgroups.index(reference_document)
            
            if position == "after":
                new_index = ref_index + 1
            else:
                new_index = ref_index
            
            new_counter = self.get_next_counter_for_position(new_index)
            new_group = DocumentGroup(self.content_frame, selected_category, self, new_counter)
            
            self.documentgroups.insert(new_index, new_group)
            
            self.renumber_documents()
            
            self.repack_all_documents()
            
            if selected_category not in self.all_categories:
                self.all_categories.add(selected_category)
                self.update_category_combo()
            
            self.debug_print(f"Created new document: {selected_category} at position {new_index}")

    def delete_empty_document(self, document_group: DocumentGroup):
        """Delete empty document group"""
        if not document_group.is_empty():
            messagebox.showwarning("Attenzione", "Il documento contiene pagine e non può essere eliminato")
            return
        
        doc_name = f"{document_group.document_counter:04d} {document_group.categoryname}"
        if messagebox.askyesno("Conferma Eliminazione", 
                             f"Eliminare il documento vuoto:\n{doc_name}?"):
            
            if document_group in self.documentgroups:
                self.documentgroups.remove(document_group)
            
            document_group.destroy()
            
            self.renumber_documents()
            
            self.after_idle(self.update_scroll_region)
            
            if self.selected_group == document_group:
                self.selected_group = None
                self.selected_thumbnail = None
                self.selection_info.config(text="Nessuna selezione")
                self.page_info_label.config(text="")
            
            self.debug_print(f"Deleted empty document: {doc_name}")

    def get_next_counter_for_position(self, position: int) -> int:
        """Get appropriate counter for new document at position"""
        if position == 0:
            return 1
        elif position >= len(self.documentgroups):
            return len(self.documentgroups) + 1
        else:
            return position + 1

    def renumber_documents(self):
        """Renumber all document counters sequentially"""
        for i, group in enumerate(self.documentgroups, 1):
            group.update_document_counter(i)

    def repack_all_documents(self):
        """Repack all document groups in UI"""
        for group in self.documentgroups:
            group.pack_forget()
    # ==========================================
    # BATCH MANAGER METHODS
    # ==========================================
    
    def open_batch_manager(self):
        """Open batch manager dialog"""
        if not self.config_manager.get('batch_mode_enabled', True):
            messagebox.showinfo("Batch Disabilitato", 
                              "Il Batch Manager è disabilitato nelle impostazioni.")
            return
        
        try:
            dialog = BatchManagerDialog(self, self.config_manager, self)
            self.wait_window(dialog.dialog)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore apertura Batch Manager: {str(e)}")
    
    def show_batch_info(self):
        """Show batch manager information"""
        info_text = """BATCH MANAGER - Elaborazione Multipla Documenti

Il Batch Manager permette di processare multipli documenti in sequenza automatica.

FUNZIONALITÀ:
- Scansione automatica cartella con PDF/TIFF + JSON
- Rilevamento coppie documento-metadati
- Elaborazione sequenziale con validazione
- Export finale CSV con tutti i metadati

WORKFLOW SUPPORTATI:
1. JSON con "categories" → split documento in categorie
2. JSON flat metadati → documento unico con metadati tabellari

MODALITÀ CSV:
- Incrementale: unico metadata.csv con tutti i documenti
- Per File: CSV separato per ogni documento

Per utilizzare: Menu Batch → Esegui Batch (Ctrl+B)"""
        
        messagebox.showinfo("Informazioni Batch Manager", info_text)
        
        for group in self.documentgroups:
            group.pack(pady=5, fill="x", padx=5)
        
        self.after_idle(self.update_scroll_region)