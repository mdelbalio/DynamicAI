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
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        # Bind scroll events
        self.content_frame.bind("<Configure>", 
                               lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Mouse wheel scrolling - MIGLIORATO
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"  # Previene propagazione evento
        
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
                self.selected_group.update_categoryname(new_category)
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

        # ========================================
        # 🔧 FIX DEFINITIVO: Supporto cartella JSON separata
        # ========================================

        # Leggi configurazione JSON folder
        use_same_folder_flag = self.config_manager.get('use_same_folder_for_json', True)
        json_folder_config = self.config_manager.get('json_folder', '').strip()

        # 🚨 CRITICAL DEBUG - Stampa configurazione corrente
        self.debug_print("=== JSON Configuration Debug ===")
        self.debug_print(f"input_folder: {input_folder}")
        self.debug_print(f"use_same_folder_for_json FLAG: {use_same_folder_flag}")
        self.debug_print(f"json_folder CONFIG: '{json_folder_config}'")

        # Determina quale cartella usare per il JSON
        # LOGICA: Se flag è TRUE → usa stessa cartella
        #         Se flag è FALSE → usa cartella separata (se configurata)
        if use_same_folder_flag:
            # ✅ MODALITÀ 1: Usa la stessa cartella del documento (checkbox ABILITATO)
            json_folder = input_folder
            self.debug_print(f"✅ MODE: SAME FOLDER → {json_folder}")
        else:
            # ✅ MODALITÀ 2: Usa cartella JSON separata (checkbox DISABILITATO)
            if not json_folder_config:
                # Se non configurata, fallback a stessa cartella
                messagebox.showwarning("Attenzione",
                            "Checkbox 'Usa stessa cartella' disabilitato ma nessuna "
                            "cartella JSON separata configurata.\n\n"
                            "Verrà usata la stessa cartella del documento.")
                json_folder = input_folder
                self.debug_print(f"⚠️ MODE: SEPARATE FOLDER (fallback to same) → {json_folder}")
            else:
                json_folder = json_folder_config
                
                # Verifica che la cartella esista
                if not os.path.exists(json_folder):
                    messagebox.showerror("Errore", 
                                f"La cartella JSON separata non esiste:\n{json_folder}\n\n"
                                "Verifica il percorso nelle Preferenze → Percorsi.")
                    return
                
                self.debug_print(f"✅ MODE: SEPARATE FOLDER → {json_folder}")

        self.debug_print("================================")
        
        json_file = None
        doc_file = None

        # Cerca documento nella cartella input
        for file in os.listdir(input_folder):
            if file.lower().endswith(('.pdf', '.tiff', '.tif')):
                doc_file = os.path.join(input_folder, file)
                break  # Prendi il primo documento trovato
        
        # Cerca JSON nella cartella appropriata (json_folder è già stato determinato sopra)
        try:
            for file in os.listdir(json_folder):
                if file.lower().endswith('.json'):
                    json_file = os.path.join(json_folder, file)
                    break  # Prendi il primo JSON trovato
        except Exception as e:
            messagebox.showerror("Errore", 
                        f"Errore lettura cartella JSON:\n{json_folder}\n\n"
                        f"Dettaglio: {str(e)}")
            return

        # ✅ VALIDAZIONE FILE TROVATI (indentazione corretta - stesso livello del try/except sopra)
        if not doc_file:
            messagebox.showerror("Errore", 
                        "Nessun documento PDF/TIFF trovato nella cartella input:\n"
                        f"{input_folder}")
            return
        
        if not json_file:
            if use_separate_json:
                messagebox.showerror("Errore", 
                            f"Nessun file JSON trovato nella cartella JSON separata:\n"
                            f"{json_folder}")
            else:
                messagebox.showerror("Errore", 
                            "Nessun file JSON trovato nella cartella input:\n"
                            f"{input_folder}")
            return
        
        self.debug_print(f"Found document: {doc_file}")
        self.debug_print(f"Found JSON: {json_file}")

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
            
    def load_document_from_batch(self, doc_dict: Dict):
        """
        Carica documento da batch per validazione
        
        Args:
            doc_dict: Dizionario documento da batch database
        """
        try:
            # Reset workspace
            self.reset_workspace()
            
            # Extract paths
            doc_path = doc_dict['doc_path']
            json_path = doc_dict['json_path']
            json_data = doc_dict.get('json_data', {})
            
            # Set input folder name from relative path
            self.input_folder_name = os.path.basename(doc_dict['relative_path'])
            if self.input_folder_name == '.':
                self.input_folder_name = os.path.basename(os.path.dirname(doc_path))
            
            # Store original data
            self.original_data = json_data
            
            # Load metadata
            self.load_metadata_from_json(json_data)
            
            # Set document name
            self.current_document_name = os.path.splitext(os.path.basename(doc_path))[0]
            
            # Load document
            self.load_document(doc_path)
            
            # Determine workflow and build UI
            workflow_type = doc_dict['workflow_type']
            
            if workflow_type == 'split_categorie':
                # Split categorie workflow
                categories = json_data.get('categories', [])
                self.all_categories = set(
                    cat['categoria'] for cat in categories 
                    if cat['categoria'] != "Pagina vuota"
                )
                self.update_category_combo()
                self.build_document_groups(categories)
                self.debug_print(f"Batch load: SPLIT - {len(categories)} categories")
            else:
                # Metadati semplici workflow
                self.all_categories = set()
                self.update_category_combo()
                self.build_single_document()
                self.debug_print(f"Batch load: SINGLE DOCUMENT - {self.documentloader.totalpages} pages")
            
            # Update window title
            self.title(f"DynamicAI - {self.current_document_name} [BATCH]")
            
            # ⭐ NUOVO: Auto-carica prima immagine
            self.after(100, self.auto_load_first_image)
            
            self.debug_print(f"Document loaded from batch: {doc_path}")
            
        except Exception as e:
            raise Exception(f"Errore caricamento documento da batch: {str(e)}")
        
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

        # Clear existing groups
        for group in self.documentgroups:
            group.destroy()
        self.documentgroups.clear()

        # Crea documento unico
        document_name = self.input_folder_name or "Documento"
        group = DocumentGroup(self.content_frame, document_name, self, 1)

        # ⭐ NUOVO: Lazy loading (VELOCE!)
        for pagenum in range(1, self.documentloader.totalpages + 1):
            group.add_page_lazy(pagenum, self.documentloader)  # ✅ VELOCE!

        group.pack(pady=5, fill="x", padx=5)
        self.documentgroups.append(group)

        self.after_idle(self.update_scroll_region)
        self.updating_ui = False
        self.debug_print(f"Created single document with {self.documentloader.totalpages} pages")
        
        # ⭐ NUOVO: Pre-carica prime thumbnail
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
        try:
            scroll_top = self.left_scrollable_frame.canvasy(0)
            thumbnails_to_load.sort(key=lambda t: t.get_load_priority(scroll_top))
        except:
            pass  # Se errore, mantieni ordine originale
        
        # Carica batch di 3 thumbnail ad alta priorità
        loaded_count = 0
        for thumb in thumbnails_to_load[:3]:
            try:
                if thumb.is_in_viewport(self.left_scrollable_frame):
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
        
        # Carica e mostra immagine
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
        
        # Aggiorna UI
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