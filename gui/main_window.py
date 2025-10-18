"""
Main window for DynamicAI application with multi-row grid support and metadata management
"""

import os
import json
import csv
import tkinter as tk
import sqlite3
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
from typing import List, Optional, Set, Dict
from .workflow_manager import WorkflowManager, WorkflowMode, InterfaceState


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
        
        # 🆕 Initialize category database for dynamic management
        self.initialize_category_database_if_needed()
        self.export_manager = ExportManager(self.config_manager)
        
        # Initialize Workflow Manager  
        from .workflow_manager import WorkflowManager, WorkflowMode, InterfaceState
        self.workflow_manager = WorkflowManager(self)        
        
        # Initialize application
        self.init_variables()
        self.setup_window()
        self.setup_ui()
        self.bind_events()
        
        # Restore window layout
        self.after(200, self.restore_window_layout)

        # ✅ NUOVO: Avvia polling per reflow automatico
        self.after(500, self.check_groups_reflow_needed)
        
        def initialize_category_database_if_needed(self):
            """Initialize category database for dynamic management if not already done"""
            try:
                if not hasattr(self, 'category_db') or not self.category_db:
                    from config import DB_FILE
                    from database import CategoryDatabase
                    self.category_db = CategoryDatabase(DB_FILE)
                    print("[DEBUG] Category database initialized")
            except Exception as e:
                print(f"Error initializing category database: {e}")

    def initialize_category_database_if_needed(self):
        """Initialize category database for dynamic management if not already done"""
        try:
            if not hasattr(self, 'category_db') or not self.category_db:
                from config import DB_FILE
                from database import CategoryDatabase
                self.category_db = CategoryDatabase(DB_FILE)
                print("[DEBUG] Category database initialized")
        except Exception as e:
            print(f"Error initializing category database: {e}")
        
    def init_variables(self):
        """Initialize all instance variables"""
        # Document management
        self.documentgroups: List[DocumentGroup] = []
        self.documentloader = None
        self.original_data = None
        self.current_document_name = ""
        self.all_categories: Set[str] = set()
        self.document_groups = []  # ✅ AGGIUNGI QUESTA RIGA
        self.pdf_files = []        # ✅ AGGIUNGI ANCHE QUESTA
        
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
        self.create_progress_toolbar()
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
        file_menu.add_command(label="Apri Documento Singolo", command=self.open_document_dialog, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Aggiorna Lista Preview", command=self.refresh_document_list, accelerator="Ctrl+R")
        file_menu.add_command(label="Completa Sequenza Export", command=self.complete_sequence_export, accelerator="Ctrl+E")
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

        # 🆕 Categories menu
        categories_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Categorie", menu=categories_menu)
        categories_menu.add_command(label="Statistiche Categorie", command=self.get_category_statistics)
        categories_menu.add_command(label="Pulizia Categorie", command=self.cleanup_old_categories)
        categories_menu.add_separator()
        categories_menu.add_command(label="🔧 Fix Database Schema", command=self.fix_database_schema)

    def create_progress_toolbar(self):
        """Create progress toolbar for background loading"""
        self.progress_toolbar = tk.Frame(self, bg="#2C3E50", height=35)
        self.progress_toolbar.pack(side="top", fill="x", after=self.menubar if hasattr(self, 'menubar') else None)
        
        # Container centrato
        container = tk.Frame(self.progress_toolbar, bg="#2C3E50")
        container.pack(side="left", fill="x", expand=True, padx=10, pady=5)
        
        # Icona + Label status
        self.progress_status_label = tk.Label(
            container, text="", bg="#2C3E50", fg="white",
            font=("Arial", 9)
        )
        self.progress_status_label.pack(side="left", padx=(0, 10))
        
        # Progress bar
        self.background_progress_bar = ttk.Progressbar(
            container, mode='determinate', length=300
        )
        self.background_progress_bar.pack(side="left", padx=5)
        
        # Percentage label
        self.progress_percent_label = tk.Label(
            container, text="", bg="#2C3E50", fg="white",
            font=("Arial", 9, "bold")
        )
        self.progress_percent_label.pack(side="left", padx=(5, 0))
        
        # Nascondi toolbar inizialmente
        self.progress_toolbar.pack_forget()
                
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

        # Action buttons - modern style with padding
        # Action buttons - horizontal layout with icons
        button_frame = tk.Frame(self.left_panel, bg="lightgray")
        button_frame.pack(pady=10, padx=5, fill="x")
        
        # Configure grid columns to expand equally
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        
        # Refresh button with folder icon
        btn_refresh = tk.Button(
            button_frame, 
            text="📂\nCarica", 
            command=self.refresh_document_list, 
            bg="#4A90E2", 
            fg="white",
            font=("Arial", 9, "bold"), 
            relief="flat",
            cursor="hand2",
            activebackground="#357ABD",
            activeforeground="white",
            bd=0,
            padx=8,
            pady=8
        )
        btn_refresh.grid(row=0, column=0, padx=2, sticky="ew")

        # Export button with save icon
        btn_export = tk.Button(
            button_frame, 
            text="💾\nEsporta", 
            command=self.complete_sequence_export, 
            bg="#50C878",
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#3EA65E",
            activeforeground="white",
            bd=0,
            padx=8,
            pady=8
        )
        btn_export.grid(row=0, column=1, padx=2, sticky="ew")

        # Reset button with trash icon
        btn_reset = tk.Button(
            button_frame, 
            text="🗑\nRimuovi", 
            command=self.reset_workspace, 
            bg="#E74C3C",
            fg="white",
            font=("Arial", 9, "bold"),
            relief="flat",
            cursor="hand2",
            activebackground="#C0392B",
            activeforeground="white",
            bd=0,
            padx=8,
            pady=8
        )
        btn_reset.grid(row=0, column=2, padx=2, sticky="ew")
        
        # Hover effects
        def on_enter_refresh(e):
            btn_refresh.config(bg="#357ABD")
        def on_leave_refresh(e):
            btn_refresh.config(bg="#4A90E2")
            
        def on_enter_export(e):
            btn_export.config(bg="#3EA65E")
        def on_leave_export(e):
            btn_export.config(bg="#50C878")
            
        def on_enter_reset(e):
            btn_reset.config(bg="#C0392B")
        def on_leave_reset(e):
            btn_reset.config(bg="#E74C3C")
        
        btn_refresh.bind("<Enter>", on_enter_refresh)
        btn_refresh.bind("<Leave>", on_leave_refresh)
        btn_export.bind("<Enter>", on_enter_export)
        btn_export.bind("<Leave>", on_leave_export)
        btn_reset.bind("<Enter>", on_enter_reset)
        btn_reset.bind("<Leave>", on_leave_reset)

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
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        
        # ✅ CRITICO: Ridimensiona content_frame con canvas
        def on_canvas_configure(event):
            canvas_width = event.width
            print(f"[CANVAS] Canvas resized to: {canvas_width}px")  # ✅ DEBUG
            self.canvas.itemconfig(self.canvas_window, width=canvas_width)
            # Trigger reflow dopo resize
            if hasattr(self, 'trigger_all_groups_reflow'):
                if hasattr(self, '_canvas_resize_timer'):
                    self.after_cancel(self._canvas_resize_timer)
                self._canvas_resize_timer = self.after(300, self.trigger_all_groups_reflow)
        
        self.canvas.bind('<Configure>', on_canvas_configure)
        
        # ✅ CRITICO: Ridimensiona content_frame con canvas
        def resize_content_frame(event):
            # Imposta larghezza content_frame = larghezza canvas
            canvas_width = event.width
            self.canvas.itemconfig(canvas_window, width=canvas_width)
        
        self.canvas.bind('<Configure>', resize_content_frame, add='+')

        # ✅ NUOVO: Bind canvas resize per trigger reflow
        self.canvas.bind('<Configure>', self.on_canvas_resize_trigger_reflow)
    
    def on_canvas_resize_trigger_reflow(self, event):
        """Trigger reflow quando canvas cambia dimensione"""
        if event.widget == self.canvas:
            # Cancella timer precedente
            if hasattr(self, '_canvas_resize_timer'):
                self.after_cancel(self._canvas_resize_timer)
            # Schedule reflow dopo 200ms
            self._canvas_resize_timer = self.after(200, self.trigger_all_groups_reflow)
        
        # Mouse wheel scrolling - MIGLIORATO con caricamento thumbnail
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            # Trigger immediato caricamento thumbnail
            if hasattr(self, 'load_visible_thumbnails_progressive'):
                # Cancella timer precedente se esiste
                if hasattr(self, '_scroll_timer'):
                    self.after_cancel(self._scroll_timer)
                # Avvia nuovo timer (carica dopo 200ms di stop scroll)
                self._scroll_timer = self.after(200, self.load_visible_thumbnails_progressive)
            return "break" 
        
        def bind_mousewheel(widget):
            """Bind ricorsivo su tutti i widget figli"""
            widget.bind("<MouseWheel>", on_mousewheel)
            widget.bind("<Button-4>", lambda e: (self.canvas.yview_scroll(-1, "units"), "break"))
            widget.bind("<Button-5>", lambda e: (self.canvas.yview_scroll(1, "units"), "break"))
            for child in widget.winfo_children():
                bind_mousewheel(child)
        
        # Bind iniziale
        self.canvas.bind("<MouseWheel>", on_mousewheel)
        self.canvas.bind("<Button-4>", lambda e: (self.canvas.yview_scroll(-1, "units"), "break"))
        self.canvas.bind("<Button-5>", lambda e: (self.canvas.yview_scroll(1, "units"), "break"))
        bind_mousewheel(self.content_frame)
        
        # Bind automatico per nuovi widget aggiunti
        def on_content_configure(event):
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            # Re-bind mousewheel su nuovi widget
            bind_mousewheel(self.content_frame)
        
        self.content_frame.bind("<Configure>", on_content_configure)
        
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
        """Setup zoom control buttons - CENTRATI"""
        zoom_frame = tk.Frame(self.center_panel, bg="#2C3E50", height=50)
        zoom_frame.pack(side="bottom", fill="x", padx=2, pady=2)
        zoom_frame.pack_propagate(False)
        
        # Container CENTRATO per i pulsanti
        btn_container = tk.Frame(zoom_frame, bg="#2C3E50")
        btn_container.place(relx=0.5, rely=0.5, anchor="center")  # CENTRATO!
        
        # State tracking per pulsanti toggle
        self.zoom_area_active = False
        self.pan_active = False
        
        # Zoom In button
        self.btn_zoom_in = tk.Button(
            btn_container, text="🔍+", command=self.zoom_in,
            bg="#3498DB", fg="white", font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2", bd=0, padx=10, pady=5
        )
        self.btn_zoom_in.pack(side="left", padx=2)
        
        # Zoom Out button
        self.btn_zoom_out = tk.Button(
            btn_container, text="🔍-", command=self.zoom_out,
            bg="#3498DB", fg="white", font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2", bd=0, padx=10, pady=5
        )
        self.btn_zoom_out.pack(side="left", padx=2)
        
        # Fit button
        self.btn_fit = tk.Button(
            btn_container, text="⊡ Fit", command=self.zoom_fit,
            bg="#16A085", fg="white", font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2", bd=0, padx=10, pady=5
        )
        self.btn_fit.pack(side="left", padx=2)
        
        # Zoom Area button (toggle)
        self.btn_zoom_area = tk.Button(
            btn_container, text="⊞ Area", command=self.toggle_zoom_area,
            bg="#7F8C8D", fg="white", font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2", bd=0, padx=10, pady=5
        )
        self.btn_zoom_area.pack(side="left", padx=2)
        
        # Pan button (toggle)
        self.btn_pan = tk.Button(
            btn_container, text="✋ Pan", command=self.toggle_pan_mode,
            bg="#7F8C8D", fg="white", font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2", bd=0, padx=10, pady=5
        )
        self.btn_pan.pack(side="left", padx=2)
        
        # ⭐ NUOVO: Full Width button
        self.btn_full_width = tk.Button(
            btn_container, text="↔️ Full Width", command=self.fit_width,
            bg="#FF9800", fg="white", font=("Arial", 10, "bold"),
            relief="flat", cursor="hand2", bd=0, padx=10, pady=5
        )
        self.btn_full_width.pack(side="left", padx=2)
        
        # Status label - SEMPRE A DESTRA
        self.zoom_status = tk.Label(
            zoom_frame, text="", bg="#2C3E50", fg="white", 
            font=("Arial", 9)
        )
        self.zoom_status.pack(side="right", padx=15)
        
        # Hover effects
        def create_hover(btn, color_normal, color_hover):
            btn.bind("<Enter>", lambda e: btn.config(bg=color_hover))
            btn.bind("<Leave>", lambda e: btn.config(bg=color_normal))
        
        create_hover(self.btn_zoom_in, "#3498DB", "#2980B9")
        create_hover(self.btn_zoom_out, "#3498DB", "#2980B9")
        create_hover(self.btn_fit, "#16A085", "#138D75")

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

        # ✅ NUOVO: Mouse wheel scroll verticale per immagini zoommatte
        self.image_canvas.bind("<MouseWheel>", self.on_image_mouse_wheel)
        self.image_canvas.bind("<Button-4>", self.on_image_mouse_wheel)  # Linux scroll up
        self.image_canvas.bind("<Button-5>", self.on_image_mouse_wheel)  # Linux scroll down

    def on_image_mouse_wheel(self, event):
        """Handle mouse wheel scroll for vertical image panning when zoomed"""
        if not self.current_image:
            return
            
        # Solo se l'immagine è zoomata (factor > 1.0) o in modalità full width
        if self.zoom_factor > 1.0:
            # Determina direzione scroll
            if hasattr(event, 'delta'):  # Windows
                if event.delta > 0:  # Scroll up
                    direction = -1
                else:  # Scroll down
                    direction = 1
            elif hasattr(event, 'num'):  # Linux
                if event.num == 4:  # Scroll up
                    direction = -1
                else:  # Scroll down (event.num == 5)
                    direction = 1
            else:
                return
            
            # Esegui scroll verticale
            try:
                self.image_canvas.yview_scroll(direction, "units")
            except:
                pass  # Ignora errori se scrolling non possibile
                
            return "break"  # Prevent event propagation
            
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
        self.page_info_label.pack(pady=2)

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
        self.metadata_frame.pack(fill="both", expand=True, padx=10, pady=(2, 10))

        # Canvas + scrollbar con frame container
        container = tk.Frame(self.metadata_frame, bg="lightgray")
        container.pack(fill="both", expand=True)

        # IMPORTANTE: Crea PRIMA il canvas
        canvas = tk.Canvas(container, bg="lightgray", highlightthickness=0)
        # POI crea la scrollbar che riferisce a canvas.yview
        scrollable_frame = tk.Frame(canvas, bg="lightgray")        
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)

        # Configura scrollregion
        def configure_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", configure_scrollregion)

        # Crea window nel canvas
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Ridimensiona frame interno quando canvas cambia
        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        canvas.bind("<Configure>", on_canvas_configure)

        self.metadata_vars = {}
        self.metadata_entries = {}
        self.scrollable_metadata_frame = scrollable_frame

        # Popola metadati
        self.populate_metadata_fields(scrollable_frame)

        # Pack: scrollbar a destra, canvas a sinistra
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        # Scroll con rotella - bind migliorato
        def on_metadata_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            return "break"

        # Bind su canvas
        canvas.bind("<MouseWheel>", on_metadata_mousewheel)
        canvas.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break"))
        canvas.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break"))
    
        # Bind su scrollable_frame
        scrollable_frame.bind("<MouseWheel>", on_metadata_mousewheel)
        scrollable_frame.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break"))
        scrollable_frame.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break"))
    
        # Bind ricorsivo su widget figli (labels, entries)
        def bind_to_mousewheel(widget):
            widget.bind("<MouseWheel>", on_metadata_mousewheel)
            widget.bind("<Button-4>", lambda e: (canvas.yview_scroll(-1, "units"), "break"))
            widget.bind("<Button-5>", lambda e: (canvas.yview_scroll(1, "units"), "break"))
            for child in widget.winfo_children():
                bind_to_mousewheel(child)
    
        # Applica binding dopo creazione widgets
        self.after(100, lambda: bind_to_mousewheel(scrollable_frame))

    def scroll_to_widget(self, widget):
        """Scroll canvas to make widget visible when it gets focus"""
        try:
            # Trova il canvas dei metadati
            canvas = None
            parent = widget.master
            while parent:
                if isinstance(parent, tk.Canvas):
                    canvas = parent
                    break
                parent = parent.master
        
            if not canvas:
                return
        
            # Calcola posizione del widget
            widget.update_idletasks()
            widget_y = widget.winfo_rooty()
            canvas_y = canvas.winfo_rooty()
            canvas_height = canvas.winfo_height()
        
            relative_y = widget_y - canvas_y
        
            # Se il widget è fuori dalla vista, scrolla
            if relative_y < 0 or relative_y > canvas_height - 50:
                # Calcola frazione di scroll necessaria
                scrollregion = canvas.cget('scrollregion').split()
                if len(scrollregion) == 4:
                    total_height = float(scrollregion[3])
                    if total_height > 0:
                        # Centra il widget nella vista
                        target_y = widget.winfo_y() - (canvas_height / 2) + (widget.winfo_height() / 2)
                        fraction = max(0, min(1, target_y / total_height))
                        canvas.yview_moveto(fraction)
        except Exception as e:
            self.debug_print(f"Error scrolling to widget: {e}")

    def populate_metadata_fields(self, parent_frame):
        """Populate metadata fields dynamically from current header_metadata - RESPONSIVE with auto-scroll"""
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
            entry.grid(row=row+1, column=0, sticky="ew", padx=5, pady=(0, 5), ipady=3)
            self.metadata_entries[field] = entry

            # Bind per auto-save
            self.metadata_vars[field].trace('w', lambda *args, f=field: self.on_metadata_changed(f))

            # Auto-scroll quando si entra nel campo con Tab/Click
            def on_entry_focus(event, entry_widget=entry):
                self.scroll_to_widget(entry_widget)
        
            entry.bind("<FocusIn>", on_entry_focus)

            row += 2

        # Configura colonna per espandersi
        parent_frame.grid_columnconfigure(0, weight=1)
    
        # Forza update del layout
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
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # ✅ NUOVO: Bind sash motion del PanedWindow per reflow thumbnail
        if hasattr(self, 'main_paned'):
            # Bind al rilascio del sash (quando finisci di trascinare)
            self.main_paned.bind('<ButtonRelease-1>', self.on_paned_sash_release)
            # Bind anche durante il drag per feedback live (opzionale)
            self.main_paned.bind('<B1-Motion>', self.on_paned_sash_drag)
    
    def on_paned_sash_release(self, event):
        """Handle PanedWindow sash release - trigger thumbnail reflow"""
        self.after(50, self.trigger_all_groups_reflow)
    
    def on_paned_sash_drag(self, event):
        """Handle PanedWindow sash drag - live reflow (opzionale)"""
        # Cancella timer precedente per evitare troppi reflow
        if hasattr(self, '_reflow_timer'):
            self.after_cancel(self._reflow_timer)
        # Schedule reflow dopo 100ms
        self._reflow_timer = self.after(100, self.trigger_all_groups_reflow)
    
    def trigger_all_groups_reflow(self):
        """Trigger reflow su tutti i document groups"""
        if not hasattr(self, 'documentgroups'):
            return
        
        for group in self.documentgroups:
            try:
                # Forza ricalcolo layout
                frame_width = group.pages_frame.winfo_width()
                if frame_width > 10:
                    new_per_row = group.calculate_optimal_thumbnails_per_row()
                    if new_per_row != group.thumbnails_per_row:
                        group.thumbnails_per_row = new_per_row
                        group.repack_thumbnails_grid()
                        self.debug_print(f"Reflow triggered: {new_per_row} per row (width: {frame_width}px)")
            except Exception as e:
                self.debug_print(f"Error in group reflow: {e}")

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
        """Handle category selection change with enhanced tracking"""
        new_category = self.category_var.get()
        if self.selected_group:
            if new_category != self.selected_group.categoryname:
                old_category = self.selected_group.categoryname
                self.selected_group.update_categoryname(new_category)
                self.page_info_label.config(text=f"Documento: {new_category} ({len(self.selected_group.pages)} pagine)")
                
                # 🆕 Track category usage with proper source
                self.category_db.add_category(new_category, source='manual')
                print(f"[DEBUG] Category usage tracked: {new_category}")
                
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

    def update_ui_non_blocking(self):
        """Forza update UI senza bloccare"""
        try:
            self.update_idletasks()
            self.content_frame.update_idletasks()
        except Exception as e:
            self.debug_print(f"Error updating UI: {e}")

    # ✅ AGGIUNGI QUESTO METODO QUI
    def check_groups_reflow_needed(self):
        """Check periodicamente se serve reflow (ogni 500ms)"""
        if hasattr(self, 'documentgroups') and self.documentgroups:
            for idx, group in enumerate(self.documentgroups):
                try:
                    frame_width = group.pages_frame.winfo_width()
                    
                    # ✅ DEBUG: Stampa larghezza frame
                    if idx == 0:  # Solo primo gruppo per non spammare
                        if self.config_manager.get('debug_reflow', False):
                            print(f"[REFLOW] Group 0: width={frame_width}px, per_row={group.thumbnails_per_row}")
                    
                    # ✅ Inizializza last_calculated_width se non esiste
                    if not hasattr(group, 'last_calculated_width'):
                        group.last_calculated_width = frame_width
                        if self.config_manager.get('debug_reflow', False):
                            print(f"[REFLOW] Initialized last_width for group {idx}: {frame_width}px")
                        continue
                    
                    # Se larghezza cambiata significativamente
                    width_change = abs(frame_width - group.last_calculated_width)
                    
                    # ✅ DEBUG: Stampa cambio larghezza
                    if width_change > 20 and idx == 0:
                        if self.config_manager.get('debug_reflow', False):
                            print(f"[REFLOW] Width changed: {group.last_calculated_width}px -> {frame_width}px (change: {width_change}px)")
                    
                    if width_change > 20 and frame_width > 10:
                        new_per_row = group.calculate_optimal_thumbnails_per_row()
                        
                        # ✅ DEBUG: Stampa nuovo per_row
                        if self.config_manager.get('debug_reflow', False):
                            print(f"[REFLOW] Group {idx}: {group.thumbnails_per_row} -> {new_per_row} per row")
                        
                        if new_per_row != group.thumbnails_per_row:
                            group.thumbnails_per_row = new_per_row
                            group.last_calculated_width = frame_width
                            group.repack_thumbnails_grid()
                            self.debug_print(f"✅ Auto-reflow: {new_per_row} per row (width: {frame_width}px)")
                
                except Exception as e:
                    print(f"[REFLOW ERROR] {e}")
                    import traceback
                    traceback.print_exc()
        
        # Re-schedule check
        self.after(500, self.check_groups_reflow_needed)
    
    def trigger_all_groups_reflow(self):
        """Trigger reflow su tutti i document groups"""
        if not hasattr(self, 'documentgroups'):
            return
        
        for group in self.documentgroups:
            try:
                # Forza ricalcolo layout
                frame_width = group.pages_frame.winfo_width()
                if frame_width > 10:
                    new_per_row = group.calculate_optimal_thumbnails_per_row()
                    if new_per_row != group.thumbnails_per_row:
                        group.thumbnails_per_row = new_per_row
                        group.last_calculated_width = frame_width
                        group.repack_thumbnails_grid()
                        self.debug_print(f"Reflow triggered: {new_per_row} per row (width: {frame_width}px)")
            except Exception as e:
                self.debug_print(f"Error in group reflow: {e}")
        
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
                    self.selected_group.update_categoryname(new_category)
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
        """Update category combobox with current categories (JSON first, then manual)"""
        try:
            # Get all categories from database (JSON first, then manual)
            all_categories = self.category_db.get_all_categories()
            
            # Update combobox values
            if hasattr(self, 'category_combo') and self.category_combo:
                current_value = self.category_combo.get()
                self.category_combo['values'] = all_categories
                
                # Restore previous value if still valid
                if current_value in all_categories:
                    self.category_combo.set(current_value)
                elif all_categories:
                    self.category_combo.set(all_categories[0])  # Set to first (likely JSON category)
                
                print(f"[DEBUG] Updated category combobox with {len(all_categories)} categories")
            
        except Exception as e:
            print(f"Error updating category combobox: {e}")
    
    # Alias per compatibilità
    def update_category_combobox(self):
        """Alias for update_category_combo for compatibility"""
        return self.update_category_combo()

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
        """Load documents from configured input folder - intelligent workflow detection"""
        input_folder = self.config_manager.get('default_input_folder', '')

        if not input_folder or not os.path.exists(input_folder):
            messagebox.showerror("Errore", 
                            "Cartella input non configurata o non esistente.\n"
                            "Configura la cartella nelle Preferenze.")
            return

        self.input_folder_name = os.path.basename(os.path.normpath(input_folder))

        # JSON folder configuration
        use_same_folder_flag = self.config_manager.get('use_same_folder_for_json', True)
        json_folder_config = self.config_manager.get('json_folder', '').strip()

        self.debug_print("=== JSON Configuration Debug ===")
        self.debug_print(f"input_folder: {input_folder}")
        self.debug_print(f"use_same_folder_for_json FLAG: {use_same_folder_flag}")
        self.debug_print(f"json_folder CONFIG: '{json_folder_config}'")

        if use_same_folder_flag:
            json_folder = input_folder
            self.debug_print(f"MODE: SAME FOLDER -> {json_folder}")
        else:
            if not json_folder_config:
                messagebox.showwarning("Attenzione",
                            "Checkbox 'Usa stessa cartella' disabilitato ma nessuna "
                            "cartella JSON separata configurata.\n\n"
                            "Verrà usata la stessa cartella del documento.")
                json_folder = input_folder
                self.debug_print(f"MODE: SEPARATE FOLDER (fallback to same) -> {json_folder}")
            else:
                json_folder = json_folder_config
                
                if not os.path.exists(json_folder):
                    messagebox.showerror("Errore", 
                                f"La cartella JSON separata non esiste:\n{json_folder}\n\n"
                                "Verifica il percorso nelle Preferenze -> Percorsi.")
                    return
                
                self.debug_print(f"MODE: SEPARATE FOLDER -> {json_folder}")

        self.debug_print(f"JSON FOLDER: {json_folder}")
        self.debug_print("================================")
        
        # Trova tutti i PDF+JSON
        self.pdf_files = []
        
        for file in os.listdir(input_folder):
            if file.lower().endswith(('.pdf', '.tiff', '.tif')):
                pdf_path = os.path.join(input_folder, file)
                json_name = os.path.splitext(file)[0] + '.json'
                json_path = os.path.join(json_folder, json_name)
                
                if os.path.exists(json_path):
                    self.pdf_files.append({
                        'pdf': pdf_path,
                        'json': json_path,
                        'name': os.path.splitext(file)[0]
                    })
                    self.debug_print(f"Found document: {pdf_path}")
                    self.debug_print(f"Found JSON: {json_path}")
        
        if not self.pdf_files:
            messagebox.showerror("Errore",
                f"Nessuna coppia PDF+JSON trovata.\n\n"
                f"Cartella PDF: {input_folder}\n"
                f"Cartella JSON: {json_folder}")
            return
        
        self.debug_print(f"Found {len(self.pdf_files)} PDF+JSON pairs")
        
        # Analizza primo JSON per determinare workflow
        try:
            with open(self.pdf_files[0]['json'], 'r', encoding='utf-8') as f:
                sample_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Errore", f"Errore lettura JSON: {str(e)}")
            return
        
        # Determina workflow type
        has_categories = 'categories' in sample_data and isinstance(sample_data['categories'], list) and len(sample_data['categories']) > 0
        split_enabled = self.config_manager.get('split_documents_by_category', True)
        
        if has_categories and split_enabled:
            # WORKFLOW 1: JSON CON CATEGORIE - Dialog selezione (UNO alla volta)
            self.debug_print("WORKFLOW: SPLIT MODE (categories detected)")
            self.load_single_document_with_split()
        else:
            # WORKFLOW 2: JSON FLAT - Carica TUTTI i documenti (PaperStream style)
            self.debug_print("WORKFLOW: MULTI-DOCUMENT MODE (no categories)")
            self.load_all_documents_flat()

    def load_single_document_with_split(self):
        """WORKFLOW 1: Carica UN documento con split categorie (dialog di selezione)"""
        from tkinter import Toplevel, Listbox, Scrollbar, SINGLE, END
        
        # Mostra dialog di selezione
        dialog = Toplevel(self)
        dialog.title("Seleziona Documento")
        dialog.geometry("500x400")
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"Trovati {len(self.pdf_files)} documenti. Selezionane uno:",
                font=("Arial", 10, "bold")).pack(pady=10)
        
        # Listbox con documenti
        list_frame = tk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        listbox = Listbox(list_frame, selectmode=SINGLE, font=("Arial", 9),
                        yscrollcommand=scrollbar.set)
        listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=listbox.yview)
        
        for doc in self.pdf_files:
            listbox.insert(END, doc['name'])
        
        listbox.select_set(0)
        
        selected_doc = [None]
        
        def on_select():
            selection = listbox.curselection()
            if selection:
                selected_doc[0] = self.pdf_files[selection[0]]
                dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Bottoni
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Carica", command=on_select,
                bg="#50C878", fg="white", font=("Arial", 10, "bold"),
                width=12).pack(side="left", padx=5)
        
        tk.Button(btn_frame, text="Annulla", command=on_cancel,
                bg="#E74C3C", fg="white", font=("Arial", 10, "bold"),
                width=12).pack(side="left", padx=5)
        
        listbox.bind("<Double-Button-1>", lambda e: on_select())
        
        self.wait_window(dialog)
        
        if not selected_doc[0]:
            return
        
        selected = selected_doc[0]
        doc_file = selected['pdf']
        json_file = selected['json']
        self.current_document_name = selected['name']
        
        try:
            # Carica JSON e documento
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.original_data = data
            
            self.load_metadata_from_json(data)
            
            # Sincronizza categorie
            if 'categories' in data and data['categories']:
                all_json_categories = [cat.get('categoria', '') for cat in data['categories'] if cat.get('categoria')]
                excluded_categories = ['Pagina vuota', 'pagina vuota', 'PAGINA VUOTA']
                json_categories = list(set(cat for cat in all_json_categories if cat not in excluded_categories))
                
                if json_categories:
                    self.category_db.sync_json_categories(json_categories, json_file)
                    self.update_category_combobox()
                    self.debug_print(f"Synced {len(json_categories)} categories from JSON")
            
            # Carica documento
            self.load_document(doc_file)
            
            if not self.documentloader:
                raise Exception("Errore nell'inizializzazione del document loader")
            
            # SPLIT MODE
            categories = data['categories']
            self.all_categories = set(cat['categoria'] for cat in categories if cat['categoria'] != "Pagina vuota")
            self.update_category_combo()
            self.build_document_groups(categories)
            self.debug_print(f"Mode: SPLIT - {len(categories)} categories, {len(self.documentgroups)} documents")
            
            self.after(100, self.auto_load_first_image)
        
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {str(e)}")
            import traceback
            traceback.print_exc()

    def load_all_documents_flat(self):
        """WORKFLOW 2: Carica TUTTI i documenti velocemente + thumbnail on-demand"""
        # Reset workspace
        for group in self.documentgroups:
            group.destroy()
        self.documentgroups.clear()
        
        # Dizionario per salvare metadati
        if not hasattr(self, 'document_metadata_cache'):
            self.document_metadata_cache = {}
        self.document_metadata_cache.clear()
        
        # Mostra toolbar progress
        if hasattr(self, 'progress_toolbar'):
            self.progress_toolbar.pack(side="top", fill="x", before=self.main_paned)
            self.progress_status_label.config(text="⏳ Caricamento...")
            self.background_progress_bar['value'] = 0
            self.progress_percent_label.config(text="0%")
        
        total_docs = len(self.pdf_files)
        
        # STEP 1: Pre-carica TUTTI i JSON (velocissimo)
        self.debug_print("Pre-loading JSON metadata...")
        for doc_index, doc_info in enumerate(self.pdf_files, 1):
            try:
                with open(doc_info['json'], 'r', encoding='utf-8') as f:
                    doc_metadata = json.load(f)
                self.document_metadata_cache[doc_index] = doc_metadata
            except Exception as e:
                self.debug_print(f"Error caching metadata: {e}")
                self.document_metadata_cache[doc_index] = {}
        
        # Carica metadati primo documento
        if self.pdf_files and 1 in self.document_metadata_cache:
            self.load_metadata_from_json(self.document_metadata_cache[1])
            self.current_document_name = self.pdf_files[0]['name']
            self.debug_print("✅ First metadata loaded")
        
        # STEP 2: Carica TUTTI i documenti UNO alla volta (solo struttura)
        def load_document_progressive(index):
            """Carica UN documento alla volta con placeholder"""
            if index >= total_docs:
                # Finito!
                self.after_idle(self.update_scroll_region)
                
                if hasattr(self, 'progress_toolbar'):
                    self.progress_status_label.config(text="✅ Caricamento completato!")
                    self.after(2000, lambda: self.progress_toolbar.pack_forget())
                
                self.debug_print(f"✅ All {total_docs} documents loaded")
                
                # Auto-seleziona primo
                if self.documentgroups:
                    self.after(100, lambda: self.select_document_group(self.documentgroups[0]))
                
                # Avvia caricamento thumbnail visibili
                self.after(300, self.load_visible_thumbnails_progressive)
                return
            
            doc_info = self.pdf_files[index]
            doc_index = index + 1
            
            # Update progress
            progress = (doc_index / total_docs) * 100
            if hasattr(self, 'progress_toolbar'):
                self.background_progress_bar['value'] = progress
                self.progress_percent_label.config(text=f"{progress:.0f}%")
                self.progress_status_label.config(text=f"⏳ {doc_info['name']} ({doc_index}/{total_docs})")
            
            try:
                # Carica PDF
                documentloader = create_document_loader(doc_info['pdf'])
                documentloader.load()
                
                # Crea gruppo UI
                group = DocumentGroup(self.content_frame, doc_info['name'], self, doc_index)
                group.document_loader = documentloader
                group.json_path = doc_info['json']
                group.doc_metadata = self.document_metadata_cache.get(doc_index, {})
                
                # Aggiungi pagine SOLO come placeholder (NO caricamento immagini)
                for page_num in range(1, min(documentloader.totalpages + 1, 51)):
                    group.add_page_lazy(page_num, documentloader)
                
                group.pack(pady=5, fill='both', expand=False, padx=5)
                self.documentgroups.append(group)
                
                self.debug_print(f"✅ Document {doc_index}/{total_docs} structure loaded")
                
                # Update UI ogni 2 documenti
                if doc_index % 2 == 0:
                    self.update_idletasks()
                
            except Exception as e:
                self.debug_print(f"Error loading document: {e}")
            
            # Carica prossimo dopo 10ms (velocissimo)
            self.after(10, lambda: load_document_progressive(index + 1))
        
        # Avvia caricamento progressivo
        self.after(300, lambda: load_document_progressive(0))

    def load_document_from_batch(self, doc_dict: dict):
        """
        Load document from batch processing - accepts dictionary from batch database
        
        Args:
            doc_dict: Dictionary containing document info from batch database
        """
    def load_document_from_batch(self, doc_dict: dict):
        """Load document from batch processing with workflow management"""
        try:
            # ✅ SET BATCH MODE
            self.workflow_manager.set_mode(WorkflowMode.BATCH_PROCESSING)
            
            # Extract parameters from dictionary
            if isinstance(doc_dict, dict):
                doc_path = doc_dict.get('doc_path', '')
                json_path = doc_dict.get('json_path', '')
                json_data = doc_dict.get('json_data', {})
            else:
                doc_path = str(doc_dict)
                json_path = ""
                json_data = {}
                
            self.debug_print(f"[BATCH] Loading document: {doc_path}")
            
            if not doc_path or not os.path.exists(doc_path):
                raise ValueError(f"Document path not found: {doc_path}")
            
            self.reset_workspace()
            
            # Create document loader
            from loaders import create_document_loader
            self.document_loader = create_document_loader(doc_path)
            self.document_loader.load()
            
            self.debug_print(f"[BATCH] Document loader created, total pages: {len(self.document_loader.pages) if hasattr(self.document_loader, 'pages') else 'Unknown'}")
            
            # Test loading first page
            try:
                test_image = self.document_loader.get_page(0)
                if test_image:
                    self.debug_print(f"[BATCH] Test: Successfully loaded page 1, size: {test_image.size}")
                else:
                    self.debug_print(f"[BATCH] Test: Page 1 returned None")
            except Exception as e:
                self.debug_print(f"[BATCH] Test: Error loading page 1: {e}")
            
            # Process JSON data
            if json_data and isinstance(json_data, dict):
                categories = json_data.get('categories', [])
                header = json_data.get('header', {})
                
                # ✅ DETERMINE INTERFACE MODE
                has_categories = bool(categories)
                has_metadata = bool(header)
                interface_mode = self.workflow_manager.determine_interface_mode(has_categories, has_metadata)
                
                # ✅ SET INTERFACE MODE
                self.workflow_manager.set_mode(WorkflowMode.BATCH_PROCESSING, interface_mode)
                
                if categories:
                    self.debug_print(f"[BATCH] Loading split mode with {len(categories)} categories")
                    
                    # Save JSON data temporarily
                    self.current_json_data = json_data
                    
                    # Load in split mode
                    self.load_split_mode_from_data(categories, header)
                    
                    # Load metadata
                    if header:
                        self.load_header_metadata(header)
                    
                    self.debug_print("[BATCH] Split mode loaded successfully")
                    return True
            
            # Fallback to single document mode
            self.debug_print("[BATCH] Loading single document mode")
            self.build_single_document()
            
            self.debug_print("[BATCH] Document loaded successfully")
            return True
            
        except Exception as e:
            self.debug_print(f"[BATCH] Error loading document: {e}")
            messagebox.showerror("Errore", f"Impossibile aprire il documento: {str(e)}")
            return False

    def load_split_mode_from_data(self, categories: list, header: dict = None):
        """Load document in split mode using provided categories data"""
        try:
            # Sync categories with database
            category_names = list(set([cat.get('categoria', '') for cat in categories if cat.get('categoria')]))
            if category_names:
                self.category_db.sync_json_categories(category_names, "batch_document")  # ✅ CORRETTO
                self.debug_print(f"Synced {len(category_names)} categories from batch")
            
            # Build document groups
            self.build_document_groups_from_categories(categories)
            
            # Update UI
            self.update_category_combobox()
            
        except Exception as e:
            self.debug_print(f"Error loading split mode from data: {e}")
            raise

    def build_document_groups_from_categories(self, json_categories):
        """Build document groups - ONLY if workflow allows it"""
        # ✅ CHECK WORKFLOW PERMISSIONS
        if not self.workflow_manager.can_load_thumbnails():
            self.debug_print(f"[CATEGORIES] Skipped building groups - Current mode: {self.workflow_manager.current_interface.value}")
            return
            
        if not json_categories:
            self.debug_print("[CATEGORIES] No categories data to process")
            return
            
        try:
            self.debug_print(f"[CATEGORIES] Building groups for {len(json_categories)} categories in {self.workflow_manager.current_interface.value} mode")
            
            # Get categories and sync with database
            category_names = self.sync_categories_from_batch(json_categories)
            self.debug_print(f"Synced {len(category_names)} categories from batch")
            
            # Update workflow manager
            self.workflow_manager.loaded_categories = json_categories
            self.workflow_manager.categories_present = True
            
            # Update category combobox
            self.update_category_combobox(category_names)
            
            # Clear existing groups
            self.clear_document_groups()
            
            # Create document groups with multi-row grid layout
            self.document_groups = []
            for i, category_name in enumerate(category_names):
                group = DocumentGroup(
                    self.document_scroll_frame,
                    category_name,
                    self,
                    i + 1
                )
                group.set_document_loader(self.document_loader)
                self.document_groups.append(group)
            
            # Grid layout for document groups
            self.update_document_groups_layout()
            
            self.debug_print(f"Created {len(self.document_groups)} document groups with grid layout")
            
            # ✅ SAFE thumbnail loading per workflow
            self._safe_build_thumbnail_groups(json_categories)
            
            # Ensure category combobox is populated
            if hasattr(self, 'category_combobox'):
                self.update_category_combobox(category_names)
            
        except Exception as e:
            self.debug_print(f"[CATEGORIES] Error building document groups: {e}")
            import traceback
            self.debug_print(f"[CATEGORIES] Full traceback: {traceback.format_exc()}")

    def _safe_build_thumbnail_groups(self, json_categories):
        """Safely build thumbnail groups based on workflow state"""
        try:
            groups_built = 0
            for category_data in json_categories:
                category_name = category_data.get('name', '')
                pages = category_data.get('pages', [])
                
                if category_name and pages:
                    group = self.get_document_group_by_name(category_name)
                    if group:
                        for page_num in pages:
                            try:
                                self.debug_print(f"[THUMBNAIL] Attempting to load page {page_num} (PDF index {page_num - 1}) for category {category_name}")
                                
                                # Load page image - PDF pages start at 0, JSON at 1
                                image = self.document_loader.get_page(page_num - 1)
                                
                                if image:
                                    self.debug_print(f"[THUMBNAIL] Successfully loaded page {page_num}, image size: {image.size}")
                                    group.add_page(page_num, image, category_name)  # ✅ Fixed: use category_name not cat_name
                                    self.debug_print(f"[THUMBNAIL] Added page {page_num} to group {category_name}")
                                else:
                                    self.debug_print(f"[THUMBNAIL] Page {page_num} returned None image")
                                    
                            except Exception as e:
                                self.debug_print(f"[THUMBNAIL] Error loading page {page_num}: {e}")
                                import traceback
                                self.debug_print(f"[THUMBNAIL] Full traceback: {traceback.format_exc()}")
                        
                        groups_built += 1
            
            self.debug_print(f"Built {groups_built} document groups")
            
        except Exception as e:
            self.debug_print(f"[CATEGORIES] Error in safe thumbnail building: {e}")

    def load_header_metadata(self, header: dict):
        """Load header metadata - ONLY if workflow allows it"""
        # ✅ CHECK WORKFLOW PERMISSIONS
        if not self.workflow_manager.can_load_metadata():
            self.debug_print(f"[METADATA] Skipped loading - Current mode: {self.workflow_manager.current_interface.value}")
            return
        
        if not header:
            self.debug_print("[METADATA] No header data to load")
            return
            
        try:
            if not hasattr(self, 'header_metadata'):
                self.header_metadata = {}
            
            # Update header metadata
            self.header_metadata.update(header)
            self.workflow_manager.loaded_metadata = header
            
            self.debug_print(f"[METADATA] Loading {len(header)} metadata fields in {self.workflow_manager.current_interface.value} mode")
            
            # ✅ SAFE metadata loading per modalità
            self._safe_load_metadata_fields(header)
            
            self.debug_print("[METADATA] Successfully loaded metadata fields")
            
        except Exception as e:
            self.debug_print(f"[METADATA] Error loading header metadata: {e}")
            import traceback
            self.debug_print(f"[METADATA] Full traceback: {traceback.format_exc()}")

    def _safe_load_metadata_fields(self, header: dict):
        """Safely load metadata into interface fields"""
        try:
            # Try to find and populate metadata fields
            metadata_mapping = {
                'NumeroProgetto': ['numero_progetto_entry', 'project_number_entry', 'number_entry'],
                'Intestatario': ['intestatario_entry', 'owner_entry', 'titolare_entry'], 
                'IndirizzoImmobile': ['indirizzo_immobile_entry', 'address_entry', 'indirizzo_entry'],
                'LavoroEseguito': ['lavoro_eseguito_text', 'work_done_text', 'lavori_text', 'work_text'],
                'EstremiCatastali': ['estremi_catastali_entry', 'cadastral_entry', 'catasto_entry']
            }
            
            fields_updated = 0
            for key, possible_names in metadata_mapping.items():
                if key in header:
                    value = str(header[key])
                    if self._try_update_field(possible_names, value):
                        fields_updated += 1
                        self.debug_print(f"[METADATA] ✅ Updated {key}: {value[:50]}...")
                    else:
                        self.debug_print(f"[METADATA] ⚠️ Field not found for {key}")
            
            self.debug_print(f"[METADATA] Successfully updated {fields_updated}/{len(header)} fields")
            
        except Exception as e:
            self.debug_print(f"[METADATA] Error in safe loading: {e}")

    def _try_update_field(self, field_names: list, value: str) -> bool:
        """Try to update a field with given possible names"""
        for field_name in field_names:
            if hasattr(self, field_name):
                try:
                    field = getattr(self, field_name)
                    if hasattr(field, 'delete') and hasattr(field, 'insert'):
                        if hasattr(field, 'get'):  # Entry widget
                            field.delete(0, tk.END)
                            field.insert(0, value)
                        else:  # Text widget
                            field.delete('1.0', tk.END)
                            field.insert('1.0', value)
                        return True
                except Exception:
                    continue
        return False

    def create_placeholder_for_remaining(self, start_index, total_docs):
        """Crea PLACEHOLDER per documenti rimanenti (caricamento on-demand)"""
        self.debug_print(f"Creating placeholders for documents {start_index+1}-{total_docs}")
        
        for doc_index in range(start_index, total_docs):
            doc_info = self.pdf_files[doc_index]
            doc_num = doc_index + 1
            
            try:
                # Update progress
                progress = 50 + ((doc_index - start_index + 1) / (total_docs - start_index)) * 50
                if hasattr(self, 'progress_toolbar'):
                    self.background_progress_bar['value'] = progress
                    self.progress_percent_label.config(text=f"{progress:.0f}%")
                    self.progress_status_label.config(text=f"⏳ Preparazione {doc_info['name']}")
                
                # Crea gruppo SENZA caricare PDF (placeholder)
                group = DocumentGroup(self.content_frame, doc_info['name'], self, doc_num)
                group.document_loader = None  # Verrà caricato on-demand
                group.json_path = doc_info['json']
                group.doc_metadata = self.document_metadata_cache.get(doc_num, {})
                group.pdf_path = doc_info['pdf']  # Salva path per caricamento lazy
                
                # NON aggiungere pagine ancora (solo header)
                group.pack(pady=5, fill='both', expand=False, padx=5)
                self.documentgroups.append(group)
                
                # Update UI ogni 2 documenti
                if doc_index % 2 == 0:
                    self.update_idletasks()
                
            except Exception as e:
                self.debug_print(f"Error creating placeholder: {e}")
        
        # Finito!
        self.after_idle(self.update_scroll_region)
        
        if hasattr(self, 'progress_toolbar'):
            self.progress_status_label.config(text="✅ Caricamento completato!")
            self.after(2000, lambda: self.progress_toolbar.pack_forget())
        
        self.debug_print(f"✅ Created {total_docs - start_index} placeholders")
        
        # Avvia caricamento thumbnail visibili
        self.after(500, self.load_visible_thumbnails_progressive)

    def update_loading_progress(self, progress, doc_name, doc_index, total_docs):
        """Update progress bar (chiamato da thread via after())"""
        if hasattr(self, 'progress_toolbar'):
            self.background_progress_bar['value'] = progress
            self.progress_percent_label.config(text=f"{progress:.0f}%")
            self.progress_status_label.config(text=f"⏳ {doc_name} ({doc_index}/{total_docs})")

    def create_document_groups_from_loaded(self, loaded_docs, total_docs):
        """Crea gruppi UI da documenti caricati (main thread)"""
        self.debug_print(f"Creating UI for {len(loaded_docs)} documents...")
        
        for doc_data in loaded_docs:
            try:
                # Crea gruppo documento
                group = DocumentGroup(self.content_frame, doc_data['name'], self, doc_data['index'])
                group.document_loader = doc_data['loader']
                group.json_path = doc_data['json_path']
                group.doc_metadata = doc_data['metadata']
                
                # Aggiungi pagine con placeholder
                for page_num in range(1, min(doc_data['loader'].totalpages + 1, 51)):
                    group.add_page_lazy(page_num, doc_data['loader'])
                
                group.pack(pady=5, fill='both', expand=False, padx=5)
                self.documentgroups.append(group)
                
                # Update UI ogni 2 documenti
                if doc_data['index'] % 2 == 0:
                    self.update_idletasks()
                
            except Exception as e:
                self.debug_print(f"Error creating group for {doc_data['name']}: {e}")
        
        # Finito!
        self.after_idle(self.update_scroll_region)
        
        if hasattr(self, 'progress_toolbar'):
            self.progress_status_label.config(text="✅ Caricamento completato!")
            self.after(2000, lambda: self.progress_toolbar.pack_forget())
        
        self.debug_print(f"✅ All {len(loaded_docs)} documents loaded")
        
        # Auto-seleziona primo documento
        if self.documentgroups:
            self.after(200, lambda: self.select_document_group(self.documentgroups[0]))
        
        # Avvia caricamento thumbnail visibili
        self.after(500, self.load_visible_thumbnails_progressive)

    def select_document_group(self, group: DocumentGroup):
        """Select document group - carica on-demand se necessario"""
        if self.selected_thumbnail:
            self.selected_thumbnail.deselect()
            self.selected_thumbnail = None
        if self.selected_group:
            self.selected_group.deselect_group()
            
        self.selected_group = group
        group.select_group()
        
        self.category_var.set(group.categoryname)
        self.selection_info.config(text=f"Selezionato: Documento")
        
        # ✅ CARICA METADATI IMMEDIATAMENTE
        if hasattr(self, 'document_metadata_cache') and group.document_counter in self.document_metadata_cache:
            doc_metadata = self.document_metadata_cache[group.document_counter]
            self.load_metadata_from_json(doc_metadata)
            self.current_document_name = group.categoryname
            self.update_idletasks()  # Forza update
            self.debug_print(f"✅ Loaded metadata for: {group.categoryname}")
        
        # ✅ CARICA DOCUMENTO ON-DEMAND se non ancora caricato
        if group.document_loader is None and hasattr(group, 'pdf_path'):
            self.debug_print(f"Loading document on-demand: {group.categoryname}")
            
            try:
                # Mostra messaggio
                self.selection_info.config(text=f"Caricamento: {group.categoryname}...")
                self.update_idletasks()
                
                # Carica PDF
                documentloader = create_document_loader(group.pdf_path)
                documentloader.load()
                group.document_loader = documentloader
                
                # Aggiungi pagine
                for page_num in range(1, min(documentloader.totalpages + 1, 51)):
                    group.add_page_lazy(page_num, documentloader)
                
                self.update_idletasks()
                self.debug_print(f"✅ Document loaded on-demand: {documentloader.totalpages} pages")
                
            except Exception as e:
                self.debug_print(f"Error loading document on-demand: {e}")
                messagebox.showerror("Errore", f"Impossibile caricare documento:\n{str(e)}")
                return
        
        # Aggiorna info
        page_count = len(group.pages) if group.pages else "caricamento..."
        self.page_info_label.config(text=f"Documento: {group.categoryname} ({page_count} pagine)")
        
        # Carica thumbnail se già caricato
        if group.document_loader:
            def load_selected_thumbnails():
                loaded = 0
                for thumb in group.thumbnails[:10]:  # Prime 10 pagine
                    if not thumb.image_loaded and thumb.document_loader:
                        try:
                            img = thumb.document_loader.get_page(thumb.pagenum)
                            if img:
                                thumb.set_image(img)
                                loaded += 1
                                # Update UI ogni 2 thumbnail
                                if loaded % 2 == 0:
                                    self.update_idletasks()
                        except Exception as e:
                            self.debug_print(f"Error loading thumbnail: {e}")
                
                if loaded > 0:
                    self.debug_print(f"✅ Loaded {loaded} thumbnails for selected document")
            
            # Carica in background
            self.after(50, load_selected_thumbnails)
        
    def auto_load_first_image(self):
        """Auto-carica la prima immagine disponibile"""
        try:
            if self.documentgroups:
                first_group = self.documentgroups[0]
                if first_group.thumbnails:
                    first_thumbnail = first_group.thumbnails[0]
                    first_thumbnail.select()
                    self.select_thumbnail(first_thumbnail)
                    self.debug_print("Prima immagine caricata automaticamente")
        except Exception as e:
            self.debug_print(f"Errore auto-load prima immagine: {e}")
            
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
                # ⭐ NUOVO: Carica solo numeri pagina, non immagini (VELOCE!)
                group.add_page_lazy(pagenum, self.documentloader)  # Passa il loader, non l'immagine
            group.pack(pady=5, fill="x", padx=5)
            self.documentgroups.append(group)
            document_counter += 1

        # ⭐ NUOVO: Carica solo le prime 3 thumbnail reali per preview
        self.after(10, lambda: self.preload_thumbnails_progressive())

        self.after_idle(self.update_scroll_region)
        
        self.updating_ui = False
        self.debug_print(f"Created {len(documents)} document groups with grid layout")
        
        # ⭐ NUOVO: Auto-carica prima immagine del primo documento
        self.after(100, self.auto_load_first_image)

    def build_single_document(self):
        """Build single document group with all pages (no category splitting)"""
        if self.updating_ui:
            return
        self.updating_ui = True
        
        # ✅ FIX: Usa self.documentgroups invece di self.document_groups
        for group in self.documentgroups:
            group.destroy()
        self.documentgroups.clear()
        
        # ✅ CONTROLLO SICUREZZA: Verifica che documentloader esista
        if not hasattr(self, 'documentloader') or not self.documentloader:
            self.debug_print("WARNING: documentloader not available, skipping build_single_document")
            self.updating_ui = False
            return
        
        # Crea documento unico
        document_name = self.input_folder_name or "Documento"
        group = DocumentGroup(self.content_frame, document_name, self, 1)
        
        # VELOCE! Lazy loading
        for page_num in range(1, self.documentloader.totalpages + 1):
            group.add_page_lazy(page_num, self.documentloader)
            
        group.pack(pady=5, fill='both', expand=False, padx=5)
        self.documentgroups.append(group)
        
        self.after_idle(self.update_scroll_region)
        self.updating_ui = False
        self.debug_print(f"Created single document with {self.documentloader.totalpages} pages")
        
        # Auto-carica prime thumbnail
        self.after(10, lambda: self.preload_thumbnails_progressive())

    def update_scroll_region(self):
        """Update scroll region for document groups"""
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def preload_first_thumbnails(self, count: int = 5):
        """Pre-carica prime N thumbnail per preview veloce"""
        loaded = 0
        for group in self.documentgroups:
            for thumbnail in group.thumbnails:
                if loaded >= count:
                    return
                # Carica thumbnail reale se non già caricata
                if hasattr(thumbnail, 'image_loaded') and not thumbnail.image_loaded:
                    try:
                        img = thumbnail.document_loader.get_page(thumbnail.pagenum)
                        if img:
                            thumbnail.set_image(img)
                            loaded += 1
                            self.debug_print(f"Preloaded thumbnail for page {thumbnail.pagenum}")
                    except Exception as e:
                        self.debug_print(f"Error preloading thumbnail {thumbnail.pagenum}: {e}")

    def preload_thumbnails_progressive(self):
        """Smart lazy loading - carica solo thumbnail visibili + buffer"""
        if not hasattr(self, 'documentgroups') or not self.documentgroups:
            return
        
        # Raccogli tutte le thumbnail che necessitano caricamento
        thumbnails_to_load = []
        for group in self.documentgroups:
            for thumb in group.thumbnails:
                if not thumb.image_loaded and thumb.document_loader:
                    thumbnails_to_load.append(thumb)
        
        if not thumbnails_to_load:
            self.debug_print("✅ Tutti le thumbnail sono caricate")
            return
        
        # Ordina per priorità di viewport
        # Ordina per priorità di viewport
        try:
            # ✅ FIX: Usa self.canvas invece di left_scrollable_frame
            scroll_top = self.canvas.canvasy(0)
            thumbnails_to_load.sort(key=lambda t: t.get_load_priority(scroll_top))
        except Exception as e:
            # Se errore, mantieni ordine originale
            self.debug_print(f"Cannot determine scroll position: {e}")
            pass
        
        # Carica batch di 3 thumbnail ad alta priorità
        loaded_count = 0
        for thumb in thumbnails_to_load[:3]:
            try:
                # ✅ FIX: Rimuovi controllo viewport (non necessario, thumbnails_to_load è già ordinato)
                if thumb.load_image_if_needed():
                    loaded_count += 1
                    # Piccola pausa per non bloccare UI
                    if loaded_count >= 1:
                        break
            except Exception as e:
                self.debug_print(f"Error in progressive loading: {e}")
        
        # Continua caricamento se ci sono altre thumbnail
        if len(thumbnails_to_load) > 3:
            # Schedule prossimo batch tra 100ms
            self.after(100, self.preload_thumbnails_progressive)
        else:
            self.debug_print("🎯 Lazy loading completato per viewport corrente")
    
    def load_visible_thumbnails_progressive(self):
        """Carica progressivamente le thumbnail visibili nel viewport"""
        if not hasattr(self, 'documentgroups') or not self.documentgroups:
            return
        
        try:
            # Ottieni area visibile del canvas
            canvas_top = self.canvas.canvasy(0)
            canvas_bottom = self.canvas.canvasy(self.canvas.winfo_height())
            
            # Raccogli thumbnail visibili non caricate
            visible_thumbnails = []
            for group in self.documentgroups:
                # Controlla se il gruppo è visibile
                try:
                    group_y = group.frame.winfo_y()
                    group_height = group.frame.winfo_height()
                    
                    # Se gruppo è nel viewport
                    if group_y < canvas_bottom and (group_y + group_height) > canvas_top:
                        # Aggiungi thumbnail del gruppo
                        for thumb in group.thumbnails:
                            if not thumb.image_loaded and thumb.document_loader:
                                visible_thumbnails.append(thumb)
                except:
                    pass
            
            if not visible_thumbnails:
                self.debug_print("No visible thumbnails to load")
                return
            
            # Carica prime 5 thumbnail visibili
            loaded = 0
            for thumb in visible_thumbnails[:5]:
                try:
                    img = thumb.document_loader.get_page(thumb.pagenum)
                    if img:
                        thumb.set_image(img)
                        loaded += 1
                        self.debug_print(f"Loaded visible thumbnail: page {thumb.pagenum}")
                        
                        # Update UI ogni 2 thumbnail
                        if loaded % 2 == 0:
                            self.update_idletasks()
                except Exception as e:
                    self.debug_print(f"Error loading visible thumbnail: {e}")
            
            # Se ci sono altre thumbnail da caricare, continua
            if len(visible_thumbnails) > 5:
                self.after(300, self.load_visible_thumbnails_progressive)
            else:
                self.debug_print("✅ All visible thumbnails loaded")
                
        except Exception as e:
            self.debug_print(f"Error in progressive thumbnail loading: {e}")
    
    def setup_viewport_loading(self):
        """Setup caricamento intelligente basato su scroll"""
        # Bind scroll events per triggering lazy loading
        def on_scroll(*args):
            # Trigger lazy loading quando l'utente scrolla
            self.after_idle(self.preload_thumbnails_progressive)
        
        # Bind alle scrollbar se esistono
        try:
            if hasattr(self.left_scrollable_frame, 'yview_moveto'):
                # Canvas scrolling
                self.left_scrollable_frame.bind('<Configure>', lambda e: on_scroll())
        except:
            pass
        
        # Bind anche a mouse wheel
        def on_mousewheel(event):
            self.after(50, on_scroll)  # Lazy trigger dopo scroll
        
        self.left_scrollable_frame.bind('<MouseWheel>', on_mousewheel)
        self.left_scrollable_frame.bind('<Button-4>', on_mousewheel)  # Linux
        self.left_scrollable_frame.bind('<Button-5>', on_mousewheel)  # Linux
    
    def _preload_next_thumbnail(self):
        """Carica prossima thumbnail in background (non bloccante)"""
        if not hasattr(self, '_preload_queue') or self._preload_index >= len(self._preload_queue):
            self.debug_print("✅ All thumbnails preloaded!")
            return
        
        # ⭐ CARICA 5 THUMBNAIL ALLA VOLTA
        batch_size = 5
        end_index = min(self._preload_index + batch_size, len(self._preload_queue))
        
        for i in range(self._preload_index, end_index):
            thumbnail = self._preload_queue[i]
            
            # Carica thumbnail
            if hasattr(thumbnail, 'image_loaded') and not thumbnail.image_loaded:
                try:
                    img = thumbnail.document_loader.get_page(thumbnail.pagenum)
                    if img:
                        thumbnail.set_image(img)
                        self.debug_print(f"⚡ Background loaded thumbnail page {thumbnail.pagenum}")
                except Exception as e:
                    self.debug_print(f"❌ Error loading thumbnail {thumbnail.pagenum}: {e}")
        
        self._preload_index = end_index
        
        # Continua con prossimo batch (delay 20ms per non bloccare UI)
        if self._preload_index < len(self._preload_queue):
            self.after(20, self._preload_next_batch)  # ⭐ Delay ridotto da 50ms a 20ms

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
    
    def validate_before_export(self):
        """Validate documents before export - check for empty documents"""
        empty_docs = []
        
        for group in self.documentgroups:
            if group.is_empty():
                doc_name = f"{group.document_counter:04d} {group.categoryname}"
                empty_docs.append((group, doc_name))
        
        if empty_docs:
            # Crea messaggio con lista documenti vuoti
            empty_list = "\n".join([f"  • {name}" for _, name in empty_docs])
            
            message = (
                f"Attenzione: trovati {len(empty_docs)} documenti senza pagine:\n\n"
                f"{empty_list}\n\n"
                "Questi documenti verranno saltati nell'export, causando buchi nella numerazione.\n\n"
                "Vuoi eliminarli automaticamente prima dell'export?"
            )
            
            response = messagebox.askyesnocancel(
                "Documenti Vuoti Rilevati",
                message,
                icon='warning'
            )
            
            if response is None:  # Cancel
                return False  # Annulla export
            elif response:  # Yes - elimina documenti vuoti
                for group, _ in empty_docs:
                    if group in self.documentgroups:
                        self.documentgroups.remove(group)
                    group.destroy()
                
                # Rinumera documenti
                self.renumber_documents()
                self.after_idle(self.update_scroll_region)
                
                messagebox.showinfo(
                    "Documenti Eliminati",
                    f"Eliminati {len(empty_docs)} documenti vuoti.\n"
                    "Numerazione aggiornata."
                )
                return True  # Procedi con export
            else:  # No - procedi comunque
                messagebox.showwarning(
                    "Attenzione",
                    "L'export procederà con buchi nella numerazione dei file.\n"
                    "Es: doc001, doc003, doc005..."
                )
                return True  # Procedi con export
        
        return True  # Nessun documento vuoto, procedi
    
    # inserire qui def complete_sequence
    def complete_sequence_export(self):
        """Export images and CSV with thread-safe progress updates"""
        if not self.documentgroups:
            messagebox.showwarning("Attenzione", "Nessun documento caricato")
            return

        # Validation before export
        if not self.validate_before_export():
            return

        # Get output folder
        base_output_folder = self.config_manager.get('default_output_folder', '')
        if not base_output_folder:
            messagebox.showerror("Errore", "Cartella output non configurata. Configura la cartella nelle Preferenze.")
            return

        # Handle folder structure preservation
        preserve_structure = self.config_manager.get('preserve_folder_structure', False)
        if preserve_structure and self.input_folder_name:
            output_folder = os.path.join(base_output_folder, self.input_folder_name)
        else:
            output_folder = base_output_folder

        # Create output folder if needed
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile creare cartella output: {str(e)}")
                return

        # Setup progress window
        self.setup_export_progress_window()
        
        # Start thread-safe export
        self.export_manager.export_documents_threaded(
            output_folder=output_folder,
            document_groups=self.documentgroups,
            document_name=self.current_document_name,
            ui_callback=self.handle_export_update
        )
        
        # Export CSV metadata dopo aver avviato l'export PDF
        try:
            documents_metadata = []
            
            for group in self.documentgroups:
                if not group.is_empty():
                    # Colleziona metadati per ogni documento
                    doc_metadata = {
                        'Numero_Documento': f"{group.document_counter:04d}",
                        'Categoria': group.categoryname,
                        'Numero_Pagine': group.get_page_count(),
                        'Nome_File': f"completo_doc{group.document_counter:04d}_{group.categoryname}",
                    }
                    
                    # Aggiungi metadati header se presenti
                    for key, value in self.header_metadata.items():
                        if value:  # Solo se il valore non è vuoto
                            doc_metadata[key] = value
                    
                    documents_metadata.append(doc_metadata)
            
            # ✅ Export CSV usando il metodo CORRETTO (self.export_csv_metadata)
            if documents_metadata:
                csv_path = self.export_csv_metadata(
                    output_folder=output_folder,
                    exported_files=[],
                    input_file_name=self.current_document_name  # ✅ AGGIUNTO
                )
                
                if csv_path:
                    self.debug_print(f"✅ CSV exported successfully: {csv_path}")
                else:
                    self.debug_print("⚠️ CSV export skipped by user")
                    
        except Exception as e:
            self.debug_print(f"❌ CSV Export Error: {str(e)}")
            import traceback
            traceback.print_exc()

        # Start processing UI queue
        self.process_export_queue()
        
        # Start processing UI queue
        self.process_export_queue()

    def setup_export_progress_window(self):
        """Setup progress window for export operation"""
        export_format = self.config_manager.get('export_format', 'JPEG')
        
        self.export_progress_window = tk.Toplevel(self)
        self.export_progress_window.title(f"Export in Corso - {export_format}")
        self.export_progress_window.geometry("500x180")
        self.export_progress_window.transient(self)
        self.export_progress_window.resizable(False, False)
        
        # Center the window
        self.export_progress_window.geometry("+%d+%d" % (
            self.winfo_rootx() + 100, 
            self.winfo_rooty() + 100
        ))
        
        # Main frame
        frame = tk.Frame(self.export_progress_window, padx=20, pady=20)
        frame.pack(fill='both', expand=True)
        
        # Status label
        self.export_status_label = tk.Label(
            frame, text="Inizializzazione export...", font=('Arial', 10)
        )
        self.export_status_label.pack(pady=(0, 10))
        
        # Progress bar
        self.export_progress_bar = ttk.Progressbar(
            frame, mode='determinate', length=400
        )
        self.export_progress_bar.pack(pady=10)
        
        # Percentage label
        self.export_percent_label = tk.Label(
            frame, text="0%", font=('Arial', 9)
        )
        self.export_percent_label.pack()
        
        # Cancel button
        cancel_btn = tk.Button(
            frame, text="Annulla", 
            command=self.cancel_export,
            bg='#E74C3C', fg='white', font=('Arial', 9, 'bold'),
            relief='flat', cursor='hand2'
        )
        cancel_btn.pack(pady=(10, 0))
        
        # Handle window close
        self.export_progress_window.protocol("WM_DELETE_WINDOW", self.cancel_export)

    def handle_export_update(self, message_type, data):
        """Handle export updates from background thread"""
        try:
            if message_type == 'progress':
                # Update progress message
                if isinstance(data, str):
                    self.export_status_label.config(text=data)
                elif isinstance(data, dict):
                    if 'message' in data:
                        self.export_status_label.config(text=data['message'])
                    if 'progress' in data:
                        progress = float(data['progress'])
                        self.export_progress_bar.config(value=progress)
                        self.export_percent_label.config(text=f"{progress:.1f}%")
                        
            elif message_type == 'completed':
                # Export completed successfully
                self.export_completed(data)
                
            elif message_type == 'error':
                # Export failed
                self.export_failed(data)
                
        except Exception as e:
            print(f"Error handling export update: {e}")
            self.export_failed(f"UI update error: {str(e)}")

    def process_export_queue(self):
        """Process export queue updates periodically"""
        if hasattr(self, 'export_progress_window') and self.export_progress_window.winfo_exists():
            # Process queue messages
            self.export_manager._process_ui_queue(self.handle_export_update)
            
            # Schedule next check if not cancelled
            if not self.export_manager.cancel_event.is_set():
                self.after(100, self.process_export_queue)

    def export_completed(self, data):
        """Handle successful export completion"""
        try:
            exported_files = data.get('files', [])
            output_folder = data.get('folder', '')
            export_format = data.get('format', 'JPEG')
            
            # Close progress window
            if hasattr(self, 'export_progress_window'):
                self.export_progress_window.destroy()
            
            # Show success message
            file_count = len(exported_files)
            message = f"Export completato!\n\n"
            message += f"Esportati {file_count} file in formato {export_format}\n"
            message += f"Cartella: {output_folder}\n\n"
            message += "Vuoi aprire la cartella di destinazione?"
            
            if messagebox.askyesno("Export Completato", message):
                self.open_folder(output_folder)
                
        except Exception as e:
            print(f"Error in export completion: {e}")
            messagebox.showerror("Errore", f"Export completato ma errore nella finalizzazione: {str(e)}")

    def export_failed(self, error_message):
        """Handle export failure"""
        try:
            # Close progress window
            if hasattr(self, 'export_progress_window'):
                self.export_progress_window.destroy()
            
            # Show error message
            messagebox.showerror("Errore Export", f"Export fallito:\n\n{error_message}")
            
        except Exception as e:
            print(f"Error in export failure handling: {e}")

    def cancel_export(self):
        """Cancel ongoing export operation"""
        try:
            # Signal cancellation to export manager
            self.export_manager.cancel_export()
            
            # Close progress window
            if hasattr(self, 'export_progress_window'):
                self.export_progress_window.destroy()
            
            messagebox.showinfo("Annullato", "Export annullato dall'utente.")
            
        except Exception as e:
            print(f"Error cancelling export: {e}")

    def validate_before_export(self) -> bool:
        """Validate documents before export - check for empty documents"""
        empty_docs = []
        for group in self.documentgroups:
            if group.is_empty():
                doc_name = f"{group.document_counter:04d}_{group.categoryname}"
                empty_docs.append((group, doc_name))
        
        if empty_docs:
            empty_list = '\n'.join([f"• {name}" for _, name in empty_docs])
            message = f"Attenzione: trovati {len(empty_docs)} documenti senza pagine:\n\n{empty_list}\n\n"
            message += "Questi documenti verranno saltati nell'export, causando buchi nella numerazione.\n"
            message += "Vuoi eliminarli automaticamente prima dell'export?"
            
            response = messagebox.askyesnocancel("Documenti Vuoti Rilevati", message, icon='warning')
            
            if response is None:  # Cancel
                return False  # Annulla export
            elif response:  # Yes - elimina documenti vuoti
                for group, _ in empty_docs:
                    if group in self.documentgroups:
                        self.documentgroups.remove(group)
                        group.destroy()
                
                self.renumber_documents()
                self.after_idle(self.update_scroll_region)
                messagebox.showinfo("Documenti Eliminati", 
                                f"Eliminati {len(empty_docs)} documenti vuoti. Numerazione aggiornata.")
                return True  # Procedi con export
            else:  # No - procedi comunque
                messagebox.showwarning("Attenzione", 
                                    "L'export procederà con buchi nella numerazione dei file.\n"
                                    "Es: doc001, doc003, doc005...")
                return True  # Procedi con export
        
        return True  # Nessun documento vuoto, procedi


    def open_folder(self, folder_path):
        """Open folder in system file manager"""
        try:
            import platform
            import subprocess
            
            system = platform.system()
            if system == "Windows":
                os.startfile(folder_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", folder_path])
            else:  # Linux
                subprocess.run(["xdg-open", folder_path])
                
        except Exception as e:
            print(f"Error opening folder: {e}")
            messagebox.showwarning("Attenzione", f"Impossibile aprire la cartella: {str(e)}")

    def validate_before_export(self) -> bool:
        """Validate documents before export - check for empty documents"""
        empty_docs = []
        for group in self.documentgroups:
            if group.is_empty():
                doc_name = f"{group.document_counter:04d}_{group.categoryname}"
                empty_docs.append((group, doc_name))
        
        if empty_docs:
            empty_list = '\n'.join([f"• {name}" for _, name in empty_docs])
            message = f"Attenzione: trovati {len(empty_docs)} documenti senza pagine:\n\n{empty_list}\n\n"
            message += "Questi documenti verranno saltati nell'export, causando buchi nella numerazione.\n"
            message += "Vuoi eliminarli automaticamente prima dell'export?"
            
            response = messagebox.askyesnocancel("Documenti Vuoti Rilevati", message, icon='warning')
            
            if response is None:  # Cancel
                return False  # Annulla export
            elif response:  # Yes - elimina documenti vuoti
                for group, _ in empty_docs:
                    if group in self.documentgroups:
                        self.documentgroups.remove(group)
                        group.destroy()
                
                self.renumber_documents()
                self.after_idle(self.update_scroll_region)
                messagebox.showinfo("Documenti Eliminati", 
                                f"Eliminati {len(empty_docs)} documenti vuoti. Numerazione aggiornata.")
                return True  # Procedi con export
            else:  # No - procedi comunque
                messagebox.showwarning("Attenzione", 
                                    "L'export procederà con buchi nella numerazione dei file.\n"
                                    "Es: doc001, doc003, doc005...")
                return True  # Procedi con export
        
        return True  # Nessun documento vuoto, procedi
    
    def _update_export_status(self, message):
        """Aggiorna status label durante export (chiamato da thread)"""
        if hasattr(self, 'export_progress_window') and self.export_progress_window.winfo_exists():
            self.export_status_label.config(text=message)
            self.export_progress_window.update()

    def _export_completed(self, output_folder, exported_files, csv_filename, export_format):
        """Callback quando export completato"""
        if hasattr(self, 'export_progress_window') and self.export_progress_window.winfo_exists():
            self.export_progress_window.destroy()
        
        summary = (
            f"✅ Export completato!\n\n"
            f"Formato: {export_format}\n"
            f"Cartella: {output_folder}\n"
            f"File immagini: {len(exported_files)}\n"
            f"File CSV: {csv_filename}\n"
        )
        
        if export_format in ['PDF_MULTI', 'TIFF_MULTI']:
            summary += f"Documenti processati: {len(self.documentgroups)}"
        
        messagebox.showinfo("Export Completato", summary)
        
        if messagebox.askyesno("Reset Workspace", "Vuoi resettare il workspace per un nuovo documento?"):
            self.reset_workspace()
        
        self.config_manager.set('last_folder', output_folder)
        if self.config_manager.get('auto_save_changes', True):
            self.save_config()

    def _export_error(self, error_msg):
        """Callback quando export fallito"""
        if hasattr(self, 'export_progress_window') and self.export_progress_window.winfo_exists():
            self.export_progress_window.destroy()
        
        messagebox.showerror("Errore Export", f"Errore durante l'export:\n\n{error_msg}")
    
    def reset_workspace(self):
        """Reset the workspace to initial state with workflow management - COMPLETO"""
        try:
            self.debug_print("[WORKFLOW] Resetting workspace...")
            
            # ✅ CLEAR DOCUMENT GROUPS E PANNELLO SINISTRO
            for group in self.document_groups:
                try:
                    group.destroy()
                except:
                    pass
            self.document_groups.clear()
            
            # ✅ CLEAR ANCHE CONTENT FRAME (Pannello sinistro documenti)
            if hasattr(self, 'content_frame'):
                for child in self.content_frame.winfo_children():
                    try:
                        child.destroy()
                    except:
                        pass
            
            # Reset core variables CORRETTO con underscore
            self.document_loader = None
            self.original_data = None
            self.current_document_name = ""
            self.all_categories = set()
            self.input_folder_name = ""
            
            # ✅ RESET METADATA FIELDS COMPLETAMENTE
            if hasattr(self, 'header_metadata'):
                for field in self.header_metadata:
                    self.header_metadata[field] = ""
                    if hasattr(self, 'metadata_vars') and field in self.metadata_vars:
                        self.metadata_vars[field].set("")
            
            self.selected_thumbnail = None
            self.selected_group = None
            
            # ✅ CLEAR CENTRAL IMAGE CANVAS
            try:
                self.image_canvas.delete("all")
                self.current_image = None
            except:
                pass
            
            # Reset UI elements
            try:
                self.selection_info.config(text="Nessuna selezione")
            except:
                pass
            
            try:
                self.page_info_label.config(text="")
            except:
                pass
            
            try:
                self.category_var.set("")
            except:
                pass
            
            # ✅ RESET PDF FILES LIST (Pannello documenti)
            if hasattr(self, 'pdf_files'):
                self.pdf_files = []
            
            # ✅ RESET DOCUMENT CACHE
            if hasattr(self, 'document_metadata_cache'):
                self.document_metadata_cache.clear()
            
            # ✅ RESET WORKFLOW MANAGER
            if hasattr(self, 'workflow_manager'):
                self.workflow_manager.reset_to_idle()
            
            # Update scroll region
            self.after_idle(self.update_scroll_region)
            
            self.debug_print("Workspace reset completed - TUTTO PULITO!")
            
        except Exception as e:
            self.debug_print(f"Error in reset_workspace: {e}")
            import traceback
            self.debug_print(f"Full traceback: {traceback.format_exc()}")

    def load_single_document(self, doc_path: str, json_path: str = None):
        """Load single document with workflow management"""
        try:
            self.debug_print(f"[WORKFLOW] Loading single document: {doc_path}")
            
            # Reset workspace
            self.reset_workspace()
            
            # Load JSON if available
            json_data = {}
            if json_path and os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)
                except Exception as e:
                    self.debug_print(f"[WORKFLOW] Error loading JSON: {e}")
            
            # Determine what we have
            categories = json_data.get('categories', [])
            header = json_data.get('header', {})
            has_categories = bool(categories)
            has_metadata = bool(header)
            
            # ✅ PREPARE WORKFLOW
            workflow, interface = self.workflow_manager.prepare_for_document_load(
                has_categories, has_metadata, is_batch=False
            )
            
            # Create document loader
            from loaders import create_document_loader
            self.document_loader = create_document_loader(doc_path)
            self.document_loader.load()
            
            # Load content based on workflow
            if has_categories and self.workflow_manager.can_load_thumbnails():
                self.build_document_groups_from_categories(categories)
                
            if has_metadata and self.workflow_manager.can_load_metadata():
                self.load_header_metadata(header)
            
            self.debug_print(f"[WORKFLOW] Single document loaded in {interface.value} mode")
            
        except Exception as e:
            self.debug_print(f"[WORKFLOW] Error loading single document: {e}")
            import traceback
            self.debug_print(f"[WORKFLOW] Full traceback: {traceback.format_exc()}")

    def debug_workflow_status(self):
        """Debug method to check workflow manager status"""
        try:
            if hasattr(self, 'workflow_manager'):
                wm = self.workflow_manager
                self.debug_print("=== WORKFLOW MANAGER STATUS ===")
                self.debug_print(f"Current Workflow: {wm.current_workflow.value}")
                self.debug_print(f"Current Interface: {wm.current_interface.value}")
                self.debug_print(f"Batch Context: {wm.batch_context}")
                self.debug_print(f"Document Loaded: {wm.document_loaded}")
                self.debug_print(f"Categories Present: {wm.categories_present}")
                self.debug_print(f"Can Load Metadata: {wm.can_load_metadata()}")
                self.debug_print(f"Can Load Thumbnails: {wm.can_load_thumbnails()}")
                self.debug_print("===============================")
            else:
                self.debug_print("[WORKFLOW] Workflow Manager not initialized")
        except Exception as e:
            self.debug_print(f"[WORKFLOW] Error checking status: {e}")

    def open_document_dialog(self):
        """Open a document file with workflow management - NEW MENU OPTION"""
        try:
            file_path = filedialog.askopenfilename(
                title="Seleziona documento",
                filetypes=[
                    ("PDF files", "*.pdf"),
                    ("TIFF files", "*.tiff;*.tif"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                self.debug_print(f"[WORKFLOW] Opening single document: {file_path}")
                
                # Check for JSON file
                json_path = os.path.splitext(file_path)[0] + '.json'
                
                # ✅ USE NEW WORKFLOW-AWARE METHOD
                self.load_single_document(file_path, json_path if os.path.exists(json_path) else None)
                
                self.document_path = file_path
                self.debug_print(f"[WORKFLOW] Document opened successfully")
                
        except Exception as e:
            self.debug_print(f"Error opening document: {e}")
            messagebox.showerror("Errore", f"Errore nell'apertura del documento: {e}")
        
    def export_csv_metadata(self, output_folder: str, exported_files: List[str], 
                       input_file_name: Optional[str] = None) -> str:
        """Export CSV file with dynamic metadata - respects file handling settings
        
        Args:
            output_folder: Output directory path
            exported_files: List of exported file names
            input_file_name: Original document name (for naming CSV file)
        
        Returns:
            CSV filename or empty string if cancelled
        """
        # Logica nome file CSV - Priorità: Custom > Documento > Cartella
        # ========================================
        # 🔧 FIX: Logica nome file CSV corretta
        # ========================================
        custom_name = self.config_manager.get('csv_custom_name', '').strip()
        use_doc_name = self.config_manager.get('csv_use_document_name', False)

        if custom_name:
            # Priorità 1: Nome personalizzato
            csv_filename = f"{custom_name}.csv"
            self.debug_print(f"CSV naming: CUSTOM - {csv_filename}")
            
        elif use_doc_name:
            # Priorità 2: Nome documento (FLAG ABILITATO)
            if input_file_name:
                csv_filename = f"{input_file_name}.csv"
                self.debug_print(f"CSV naming: DOCUMENT NAME (from param) - {csv_filename}")
            elif self.current_document_name:
                csv_filename = f"{self.current_document_name}.csv"
                self.debug_print(f"CSV naming: DOCUMENT NAME (current) - {csv_filename}")
            else:
                # Fallback: nome cartella
                csv_filename = f"{self.input_folder_name}.csv" if self.input_folder_name else "metadata.csv"
                self.debug_print(f"CSV naming: FALLBACK - {csv_filename}")
                
        else:
            # Priorità 3: Nome cartella (FLAG DISABILITATO - DEFAULT)
            if self.input_folder_name:
                csv_filename = f"{self.input_folder_name}.csv"
                self.debug_print(f"CSV naming: FOLDER NAME - {csv_filename}")
            else:
                # ❌ RIMUOVI FALLBACK input_file_name quando flag è disabilitato!
                # Usa solo metadata.csv generico
                csv_filename = "metadata.csv"
                self.debug_print(f"CSV naming: GENERIC FALLBACK (no folder name) - {csv_filename}")
        
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
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=delimiter, quoting=csv.QUOTE_MINIMAL)
            
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
        
        # ✅ CARICA IMMAGINE ON-DEMAND se non ancora caricata
        if not thumbnail.image_loaded and thumbnail.document_loader:
            try:
                img = thumbnail.document_loader.get_page(thumbnail.pagenum)
                if img:
                    thumbnail.set_image(img)
                    self.debug_print(f"On-demand loaded image for page {thumbnail.pagenum}")
            except Exception as e:
                self.debug_print(f"Error loading image on-demand: {e}")
        
        # Deseleziona precedenti
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
        
        # Imposta nuova selezione    
        self.selected_thumbnail = thumbnail
        self.selected_group = thumbnail.document_group
        
        # Seleziona visualmente
        thumbnail.select()
        self.selected_group.select_group()
        
        # ✅ CARICA METADATI IMMEDIATAMENTE (priorità massima)
        if hasattr(self, 'document_metadata_cache') and self.selected_group.document_counter in self.document_metadata_cache:
            doc_metadata = self.document_metadata_cache[self.selected_group.document_counter]
            self.load_metadata_from_json(doc_metadata)
            self.current_document_name = self.selected_group.categoryname
            self.update_idletasks()  # Forza aggiornamento UI
            self.debug_print(f"✅ Loaded metadata for document: {self.selected_group.categoryname}")
        
        # Mostra immagine
        try:
            if thumbnail.image:
                self.display_image(thumbnail.image)
                self.debug_print(f"Image displayed for page {thumbnail.pagenum}")
            else:
                self.debug_print(f"No image for page {thumbnail.pagenum}")
        except Exception as e:
            self.debug_print(f"Error displaying image: {e}")
        
        # Aggiorna UI
        self.category_var.set(thumbnail.categoryname)
        self.selection_info.config(text=f"Selezionata: Pagina {thumbnail.pagenum}")
        self.page_info_label.config(text=f"Documento: {thumbnail.categoryname}")
        
    def select_document_group(self, group: DocumentGroup):
        """Select an entire document group and update metadata"""
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
        
        # Carica metadati specifici del documento selezionato
        if hasattr(self, 'document_metadata_cache') and group.document_counter in self.document_metadata_cache:
            doc_metadata = self.document_metadata_cache[group.document_counter]
            self.load_metadata_from_json(doc_metadata)
            self.current_document_name = group.categoryname
            self.debug_print(f"Loaded metadata for document: {group.categoryname}")
        
        # Carica thumbnail del documento selezionato se non caricate
        for thumb in group.thumbnails[:5]:  # Prime 5 pagine
            if not thumb.image_loaded and thumb.document_loader:
                try:
                    img = thumb.document_loader.get_page(thumb.pagenum)
                    if img:
                        thumb.set_image(img)
                        self.debug_print(f"Loaded thumbnail on selection: page {thumb.pagenum}")
                except Exception as e:
                    self.debug_print(f"Error loading thumbnail on selection: {e}")

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
        
        self.after_idle(self.fit_width)  # ← CAMBIATO da zoom_fit a fit_width
        
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

    def fit_width(self):
        """Fit image to canvas width (full width)"""
        if not self.current_image:
            return
        
        try:
            # Get canvas width
            canvas_width = self.image_canvas.winfo_width()
            
            if canvas_width <= 1:
                canvas_width = 800  # Default fallback
            
            # Calculate scale to fit width
            img_width = self.current_image.size[0]
            scale_factor = canvas_width / img_width
            
            # Apply zoom
            self.zoom_factor = scale_factor * 0.95  # 95% per margini
            self.image_offset_x = 0
            self.image_offset_y = 0
            self.auto_fit_on_resize = False
            
            self.update_image_display()
            
            # Center vertically if image is smaller than canvas
            self.image_canvas.update_idletasks()
            canvas_height = self.image_canvas.winfo_height()
            img_height = self.current_image.size[1] * self.zoom_factor
            
            if img_height < canvas_height:
                # Image fits vertically, center it
                self.image_canvas.yview_moveto(0)
            else:
                # Image is taller, position at top
                self.image_canvas.yview_moveto(0)
            
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%} (Full Width)")
            self.debug_print(f"Full width: scale={self.zoom_factor:.2f}")
            
        except Exception as e:
            self.debug_print(f"Error in fit_width: {e}")
            
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
        self.zoom_area_active = self.zoom_area_mode
        
        if self.zoom_area_mode:
            # Disattiva pan se attivo
            if self.pan_mode:
                self.pan_mode = False
                self.pan_active = False
                self.btn_pan.config(bg="#7F8C8D")
            
            self.image_canvas.config(cursor="crosshair")
            self.zoom_status.config(text="Seleziona area per zoom")
            self.btn_zoom_area.config(bg="#E67E22")  # Arancione attivo
        else:
            self.image_canvas.config(cursor="cross")
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")
            self.btn_zoom_area.config(bg="#7F8C8D")  # Grigio normale

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
            
            # Disattiva zoom area mode dopo l'uso
            self.zoom_area_mode = False
            self.zoom_area_active = False
            self.image_canvas.config(cursor="cross")
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")
            self.btn_zoom_area.config(bg="#7F8C8D")  # Reset colore

    def toggle_pan_mode(self):
        """Toggle pan mode"""
        self.pan_mode = not self.pan_mode
        self.pan_active = self.pan_mode
        
        if self.pan_mode:
            # Disattiva zoom area se attivo
            if self.zoom_area_mode:
                self.zoom_area_mode = False
                self.zoom_area_active = False
                self.btn_zoom_area.config(bg="#7F8C8D")
            
            self.image_canvas.config(cursor="fleur")
            self.zoom_status.config(text="Modalità Pan attiva")
            self.btn_pan.config(bg="#E67E22")  # Arancione attivo
        else:
            self.image_canvas.config(cursor="cross")
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")
            self.btn_pan.config(bg="#7F8C8D")  # Grigio normale

    def on_pan_start(self, event):
        """Start canvas panning"""
        if self.pan_mode and self.current_image:
            self.image_canvas.scan_mark(event.x, event.y)

    def on_pan_move(self, event):
        """Canvas panning drag"""
        if self.pan_mode and self.current_image:
            self.image_canvas.scan_dragto(event.x, event.y, gain=1)
    def zoom_to_area(self, x: int, y: int, w: int, h: int):
        """Zoom to specific area - FIXED: calcolo + centratura corretta"""
        if not self.current_image:
            return
        
        canvas_w = self.image_canvas.winfo_width()
        canvas_h = self.image_canvas.winfo_height()
        img_w, img_h = self.current_image.size
        
        # STEP 1: Leggi scroll offset corrente
        scroll_x = self.image_canvas.xview()[0]
        scroll_y = self.image_canvas.yview()[0]
        
        # Dimensioni immagine visualizzata
        display_w = int(img_w * self.zoom_factor)
        display_h = int(img_h * self.zoom_factor)
        
        # Calcola scroll offset in pixel
        scroll_region = self.image_canvas.cget('scrollregion').split()
        if len(scroll_region) == 4:
            total_scroll_w = float(scroll_region[2])
            total_scroll_h = float(scroll_region[3])
            offset_x = scroll_x * total_scroll_w
            offset_y = scroll_y * total_scroll_h
        else:
            offset_x = 0
            offset_y = 0
        
        # STEP 2: Padding centratura
        pad_x = max(0, (canvas_w - display_w) // 2)
        pad_y = max(0, (canvas_h - display_h) // 2)
        
        # Coordinate assolute nell'immagine visualizzata
        abs_x = x + offset_x - pad_x
        abs_y = y + offset_y - pad_y
        
        # STEP 3: Converti in coordinate immagine originale
        orig_x = abs_x / self.zoom_factor
        orig_y = abs_y / self.zoom_factor
        orig_w = w / self.zoom_factor
        orig_h = h / self.zoom_factor
        
        # STEP 4: Calcola centro dell'area selezionata (nell'immagine originale)
        center_x = orig_x + (orig_w / 2)
        center_y = orig_y + (orig_h / 2)
        
        # STEP 5: Calcola nuovo zoom
        new_zoom_w = canvas_w / orig_w
        new_zoom_h = canvas_h / orig_h
        new_zoom = min(new_zoom_w, new_zoom_h) * 0.90
        
        # STEP 6: Applica zoom
        self.zoom_factor = new_zoom
        self.image_offset_x = 0
        self.image_offset_y = 0
        
        # STEP 7: Aggiorna display
        self.update_image_display()
        
        # STEP 8: CENTRA l'area selezionata nello scroll
        # Dopo update_image_display, l'immagine è stata ridisegnata
        # Ora dobbiamo scrollare per centrare l'area
        new_display_w = int(img_w * new_zoom)
        new_display_h = int(img_h * new_zoom)
        
        # Coordinate del centro nell'immagine zoomata
        center_x_zoomed = center_x * new_zoom
        center_y_zoomed = center_y * new_zoom
        
        # Calcola quanto scrollare per centrare
        target_scroll_x = (center_x_zoomed - canvas_w / 2) / new_display_w
        target_scroll_y = (center_y_zoomed - canvas_h / 2) / new_display_h
        
        # Limita scroll tra 0 e 1
        target_scroll_x = max(0, min(1, target_scroll_x))
        target_scroll_y = max(0, min(1, target_scroll_y))
        
        # Applica scroll
        self.image_canvas.xview_moveto(target_scroll_x)
        self.image_canvas.yview_moveto(target_scroll_y)
        
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
        # Rimuovi tutti i pack esistenti
        for group in self.documentgroups:
            group.pack_forget()
        
        # Ripacchetta tutti i documenti nell'ordine corretto
        for group in self.documentgroups:
            group.pack(pady=5, fill="x", padx=5)
        
        # Aggiorna scroll region
        self.after_idle(self.update_scroll_region)
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
        
    def get_category_statistics(self):
        """Get comprehensive category statistics for debugging/admin"""
        try:
            stats = self.category_db.get_category_stats()
            
            print("\n" + "="*50)
            print("CATEGORY STATISTICS")
            print("="*50)
            print(f"Total categories: {stats['total_categories']}")
            print(f"JSON categories: {stats['json_categories']}")
            print(f"Manual categories: {stats['manual_categories']}")
            print(f"Protected categories: {stats['protected_categories']}")
            print(f"Current JSON categories: {stats['current_json_categories']}")
            print(f"Most used: {stats['most_used_category']} ({stats['most_used_count']} uses)")
            print("="*50 + "\n")
            
            # Show in dialog too
            stats_text = f"""STATISTICHE CATEGORIE:

Categorie totali: {stats['total_categories']}
Categorie JSON: {stats['json_categories']}
Categorie manuali: {stats['manual_categories']}
Categorie protette: {stats['protected_categories']}
Categorie JSON correnti: {stats['current_json_categories']}

Più utilizzata: {stats['most_used_category']} ({stats['most_used_count']} volte)"""
            
            messagebox.showinfo("Statistiche Categorie", stats_text)
            return stats
            
        except Exception as e:
            print(f"Error getting category statistics: {e}")
            messagebox.showerror("Errore", f"Errore nel recupero statistiche: {e}")
            return {}
    
    def cleanup_old_categories(self):
        """Menu action to cleanup old unused categories"""
        try:
            if messagebox.askyesno("Pulizia Categorie", 
                                 "Eliminare le categorie manuali inutilizzate degli ultimi 30 giorni?"):
                deleted_count = self.category_db.cleanup_unused_categories(keep_days=30)
                if deleted_count > 0:
                    messagebox.showinfo("Pulizia Completata", 
                                      f"Eliminate {deleted_count} categorie inutilizzate!")
                    self.update_category_combo()
                else:
                    messagebox.showinfo("Pulizia Completata", "Nessuna categoria da eliminare!")
                    
        except Exception as e:
            print(f"Error cleaning up categories: {e}")
            messagebox.showerror("Errore", f"Errore nella pulizia categorie: {e}")
            
    def fix_database_schema(self):
        """Fix database schema for dynamic categories (run once)"""
        try:
            print("🔧 Fixing database schema...")
            import sqlite3
            
            with sqlite3.connect(DB_FILE) as conn:
                cursor = conn.cursor()
                
                # Check existing table structure
                cursor.execute("PRAGMA table_info(categories)")
                columns = [row[1] for row in cursor.fetchall()]
                print(f"[DEBUG] Existing columns: {columns}")
                
                # Check for categories with NULL values in new fields
                cursor.execute("""
                    SELECT COUNT(*) FROM categories 
                    WHERE source IS NULL OR source = '' 
                    OR usage_count IS NULL OR usage_count = 0
                    OR is_protected IS NULL
                """)
                null_count = cursor.fetchone()[0]
                
                if null_count > 0:
                    print(f"[DEBUG] Found {null_count} categories with missing data, updating...")
                    
                    # Update existing categories to have proper defaults
                    cursor.execute("UPDATE categories SET source = 'manual' WHERE source IS NULL OR source = ''")
                    cursor.execute("UPDATE categories SET usage_count = 1 WHERE usage_count IS NULL OR usage_count = 0")
                    cursor.execute("UPDATE categories SET is_protected = 0 WHERE is_protected IS NULL")
                    
                    conn.commit()
                    print("✅ Updated existing categories with default values!")
                    
                    # Show current categories
                    cursor.execute("SELECT name, source, usage_count, is_protected FROM categories ORDER BY name")
                    categories = cursor.fetchall()
                    
                    print(f"\n📊 Updated {len(categories)} categories:")
                    for cat in categories:
                        print(f"   - {cat[0]} (source: {cat[1]}, usage: {cat[2]}, protected: {cat[3]})")
                    
                    messagebox.showinfo("Database Update", 
                        f"✅ Updated {len(categories)} existing categories!\n\n"
                        f"All categories now have proper source, usage_count, and protection status.\n"
                        f"Categories are ready for the dynamic system.")
                else:
                    # Show current categories anyway
                    cursor.execute("SELECT name, source, usage_count, is_protected FROM categories ORDER BY name")
                    categories = cursor.fetchall()
                    
                    print(f"\n📊 Current {len(categories)} categories:")
                    for cat in categories:
                        print(f"   - {cat[0]} (source: {cat[1]}, usage: {cat[2]}, protected: {cat[3]})")
                    
                    if len(categories) > 0:
                        messagebox.showinfo("Database Check", 
                            f"✅ Database has {len(categories)} categories, all properly configured!\n\n"
                            f"Schema and data are up to date.")
                    else:
                        messagebox.showinfo("Database Check", 
                            "✅ Database schema is up to date!\n\nNo categories found in database.")
                    
        except Exception as e:
            print(f"❌ Error fixing database: {e}")
            messagebox.showerror("Database Error", f"Error updating database:\n{e}")
