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
        
        # Metadata management
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
        self.title("DynamicAI - Editor Lineare Avanzato v3.6 Batch")
        
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
        help_menu.add_command(label="Informazioni", command=lambda: show_about_dialog(self))

    def create_widgets(self):
        """Create main application widgets"""
        # Single horizontal PanedWindow with three independent panels
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, 
                                        sashrelief=tk.RAISED, sashwidth=4, sashpad=2,
                                        bg="gray")
        self.main_paned.pack(fill="both", expand=True, padx=2, pady=2)

        # Left panel for documents and thumbnails
        self.left_panel = tk.Frame(self.main_paned, bg="lightgray", bd=1, relief="solid")
        self.main_paned.add(self.left_panel, width=400, minsize=250, sticky="nsew")

        # Center panel for image display
        self.center_panel = tk.Frame(self.main_paned, bg="black", bd=1, relief="solid")
        self.main_paned.add(self.center_panel, width=700, minsize=300, sticky="nsew")

        # Right panel for controls
        self.right_panel = tk.Frame(self.main_paned, bg="lightgray", bd=1, relief="solid")
        self.main_paned.add(self.right_panel, width=300, minsize=200, sticky="nsew")

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

        # Metadata frame
        self.setup_metadata_controls()

        # Instructions text area
        self.setup_instructions_area()

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
        """Setup metadata editing controls"""
        metadata_frame = tk.LabelFrame(
            self.right_panel, text="Metadati Documento",
            font=("Arial", 10, "bold"), bg="lightgray",
            relief="ridge", bd=2
        )
        metadata_frame.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(metadata_frame, bg="lightgray", highlightthickness=0)
        scrollbar = tk.Scrollbar(metadata_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="lightgray")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        self.metadata_vars = {}
        self.metadata_entries = {}

        metadata_labels = {
            'NumeroProgetto': 'Numero Progetto:',
            'Intestatario': 'Intestatario:',
            'IndirizzoImmobile': 'Indirizzo Immobile:',
            'LavoroEseguito': 'Lavoro Eseguito:',
            'EstremiCatastali': 'Estremi Catastali:'
        }

        row = 0
        for field, label_text in metadata_labels.items():
            lbl = tk.Label(
                scrollable_frame, text=label_text,
                font=("Arial", 9, "bold"), bg="lightgray", anchor="w"
            )
            lbl.grid(row=row, column=0, sticky="w", padx=5, pady=(5, 0))

            self.metadata_vars[field] = tk.StringVar()
            entry = tk.Entry(
                scrollable_frame, textvariable=self.metadata_vars[field],
                font=("Arial", 9), bg="white"
            )
            entry.grid(row=row+1, column=0, sticky="ew", padx=5, pady=(0, 5), ipady=3)
            self.metadata_entries[field] = entry

            self.metadata_vars[field].trace('w', lambda *args, f=field: self.on_metadata_changed(f))

            row += 2

        def sync_entry_width(event=None):
            try:
                target_width = self.category_combo.winfo_width()
                if target_width > 50:
                    for entry in self.metadata_entries.values():
                        entry.config(width=0)
                        entry.update_idletasks()
                        entry.configure(width=int(target_width/7))
            except Exception as e:
                self.debug_print(f"Sync entry width failed: {e}")

        self.category_combo.bind("<Configure>", sync_entry_width)
        self.right_panel.bind("<Configure>", sync_entry_width)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def on_metadata_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind("<MouseWheel>", on_metadata_mousewheel)
        scrollable_frame.bind("<MouseWheel>", on_metadata_mousewheel)

    def setup_instructions_area(self):
        """Setup instructions text area"""
        instructions_label = tk.Label(self.right_panel, text="Pannello Informazioni:", 
                                     font=("Arial", 10, "bold"), bg="lightgray")
        instructions_label.pack(pady=(20, 5))

        self.instructions_text = ScrolledText(self.right_panel, height=10, width=35)
        self.instructions_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.update_instructions("Configura le cartelle input/output nelle Preferenze e usa 'Aggiorna Lista (Preview)' per iniziare.\n\nNuovo in v3.6: Batch Manager per elaborazione multipla!")

    def bind_events(self):
        """Bind keyboard shortcuts and window events"""
        self.bind_all('<Control-r>', lambda e: self.refresh_document_list())
        self.bind_all('<Control-e>', lambda e: self.complete_sequence_export())
        self.bind_all('<Control-q>', lambda e: self.on_closing())
        
        if self.config_manager.get('batch_mode_enabled', True):
            self.bind_all('<Control-b>', lambda e: self.open_batch_manager())
            
        if self.config_manager.get('save_window_layout', True):
            self.bind('<Configure>', self.on_window_configure)
            self.bind_all('<B1-Motion>', self.on_paned_motion)
            self.bind_all('<ButtonRelease-1>', self.on_paned_release)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

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
        if event.widget == self and self.config_manager.get('save_window_layout', True):
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
        """Handle metadata field change"""
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

    def debug_print(self, message: str):
        """Print debug messages only if enabled in config"""
        if self.config_manager.get('show_debug_info', False):
            print(f"[DEBUG] {message}")

    def update_instructions(self, text: str):
        """Update instructions text area"""
        self.instructions_text.delete("1.0", tk.END)
        self.instructions_text.insert(tk.END, text)

    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.config_manager.config_data)
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
        """Load metadata from JSON header"""
        header = data.get('header', {})
        
        self.header_metadata['NumeroProgetto'] = header.get('NumeroProgetto', '')
        self.header_metadata['Intestatario'] = header.get('Intestatario', '')
        self.header_metadata['IndirizzoImmobile'] = header.get('IndirizzoImmobile', '')
        self.header_metadata['LavoroEseguito'] = header.get('LavoroEseguito', '')
        self.header_metadata['EstremiCatastali'] = header.get('EstremiCatastali', '')
        
        for field, value in self.header_metadata.items():
            self.metadata_vars[field].set(value)
        
        self.debug_print(f"Loaded metadata: {self.header_metadata}")

    def refresh_document_list(self):
        """Load document from configured input folder"""
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
            
            self.load_metadata_from_json(data)
            
            categories = data.get("categories", [])

            self.current_document_name = os.path.splitext(os.path.basename(doc_file))[0]

            self.all_categories = set(cat['categoria'] for cat in categories if cat['categoria'] != "Pagina vuota")
            
            self.update_category_combo()

            self.load_document(doc_file)
            self.build_document_groups(categories)
            
            self.update_document_instructions(json_file, doc_file, input_folder, categories)
            
            self.debug_print(f"Document loaded: {len(categories)} categories, {len(self.documentgroups)} documents")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {str(e)}")

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
            
            self.config_manager.set('last_folder', output_folder)
            if self.config_manager.get('auto_save_changes', True):
                self.save_config()
                
            self.debug_print(f"Exported {len(exported_files)} files and CSV to {output_folder}")
            
        except Exception as e:
            if 'progress_window' in locals():
                progress_window.destroy()
            messagebox.showerror("Errore", f"Errore durante l'export: {str(e)}")
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
    
    def load_document_from_batch(self, doc_path: str, json_path: str):
        """
        Load document from batch processing.
        
        Args:
            doc_path: Path to PDF/TIFF document
            json_path: Path to JSON metadata file
        """
        try:
            # Load JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.original_data = data
            
            # Detect workflow type
            if 'categories' in data:
                # WORKFLOW 1: Split categories (existing)
                self.load_metadata_from_json(data)
                categories = data.get('categories', [])
                self.current_document_name = os.path.splitext(os.path.basename(doc_path))[0]
                
                # Extract all categories
                self.all_categories = set(cat['categoria'] for cat in categories 
                                         if cat['categoria'] != "Pagina vuota")
                self.update_category_combo()
                
                # Load document
                self.load_document(doc_path)
                self.build_document_groups(categories)
                
                self.update_document_instructions(json_path, doc_path, 
                                                os.path.dirname(doc_path), categories)
            else:
                # WORKFLOW 2: Simple metadata (new)
                self.load_simple_metadata_document(doc_path, data)
        
        except Exception as e:
            raise Exception(f"Errore caricamento documento batch: {str(e)}")
    
    def load_simple_metadata_document(self, doc_path: str, metadata: dict):
        """
        Load document with simple flat metadata (no categories split).
        NEW: Workflow for JSON without 'categories' key.
        
        Args:
            doc_path: Path to document
            metadata: Flat metadata dictionary
        """
        # Load metadata as header
        flat_metadata = {str(k): "" if v is None else str(v) 
                        for k, v in metadata.items()}
        self.load_metadata_from_json({'header': flat_metadata})
        
        self.current_document_name = os.path.splitext(os.path.basename(doc_path))[0]
        
        # Load document
        self.load_document(doc_path)
        
        # Create single document group with all pages
        if self.documentloader:
            single_group = DocumentGroup(self.content_frame, 
                                        "Documento Completo", self, 1)
            
            for pagenum in range(1, self.documentloader.totalpages + 1):
                img = self.documentloader.get_page(pagenum)
                if img:
                    single_group.add_page(pagenum, img)
            
            single_group.pack(pady=5, fill="x", padx=5)
            self.documentgroups = [single_group]
            
            self.after_idle(self.update_scroll_region)
        
        # Update instructions
        self.update_instructions(
            f"DOCUMENTO CARICATO (Workflow Semplice):\n\n"
            f"File: {os.path.basename(doc_path)}\n"
            f"Pagine: {self.documentloader.totalpages if self.documentloader else 0}\n"
            f"Modalità: Documento unico con metadati\n\n"
            f"METADATI:\n" + 
            "\n".join([f"  {k}: {v}" for k, v in flat_metadata.items() if v])
        )
    
    # ==========================================
    # CSV EXPORT METHODS
    # ==========================================
    
    def export_csv_metadata(self, output_folder: str, exported_files: List[str]) -> str:
        """
        Export metadata to CSV file with proper handling of export format.
        
        Args:
            output_folder: Output directory path
            exported_files: List of exported file basenames
            
        Returns:
            CSV filename (basename only)
        """
        csv_filename = f"{self.input_folder_name}.csv"
        csv_path = os.path.join(output_folder, csv_filename)
        
        # Handle existing CSV file
        file_handling_mode = self.config_manager.get('file_handling_mode', 'auto_rename')
        if os.path.exists(csv_path):
            if file_handling_mode == 'auto_rename':
                csv_path = self._get_unique_csv_filename(csv_path)
                csv_filename = os.path.basename(csv_path)
            elif file_handling_mode == 'ask_overwrite':
                response = messagebox.askyesnocancel(
                    "CSV Esistente",
                    f"Il file CSV '{csv_filename}' esiste già.\n\n"
                    "Sì = Sovrascrivi\nNo = Rinomina\nAnnulla = Salta"
                )
                if response is None:
                    return ""
                elif response is False:
                    csv_path = self._get_unique_csv_filename(csv_path)
                    csv_filename = os.path.basename(csv_path)
        
        # Get CSV delimiter
        delimiter = self.config_manager.get('csv_delimiter', ';')
        
        # Get export format
        export_format = self.config_manager.get('export_format', 'JPEG')
        
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Nome File', 'Categoria'] + list(self.header_metadata.keys())
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                
                if export_format in ['PDF_MULTI', 'TIFF_MULTI']:
                    # Multi-page format: one row per document
                    for idx, group in enumerate(self.documentgroups):
                        safe_category = self.export_manager.sanitize_filename(group.categoryname)
                        filename = f"{self.current_document_name}_doc{idx+1:03d}_{safe_category}.{export_format.split('_')[0].lower()}"
                        
                        row = {'Nome File': filename, 'Categoria': group.categoryname}
                        row.update(self.header_metadata)
                        writer.writerow(row)
                else:
                    # Single-page format: one row per file
                    file_index = 0
                    for group in self.documentgroups:
                        for _ in group.thumbnails:
                            if file_index < len(exported_files):
                                filename = exported_files[file_index]
                                row = {'Nome File': filename, 'Categoria': group.categoryname}
                                row.update(self.header_metadata)
                                writer.writerow(row)
                                file_index += 1
            
            return csv_filename
            
        except Exception as e:
            raise Exception(f"Errore generazione CSV: {str(e)}")
    
    def _get_unique_csv_filename(self, base_path: str) -> str:
        """Generate unique CSV filename if file exists"""
        if not os.path.exists(base_path):
            return base_path
        
        base, ext = os.path.splitext(base_path)
        counter = 1
        new_path = f"{base}({counter}){ext}"
        
        while os.path.exists(new_path):
            counter += 1
            new_path = f"{base}({counter}){ext}"
            
            if counter > 9999:
                raise Exception("Troppi file CSV con lo stesso nome")
        
        return new_path
    
    # ==========================================
    # SELECTION AND INTERACTION METHODS
    # ==========================================
    
    def select_thumbnail(self, thumbnail: PageThumbnail):
        """Select a thumbnail and display its image"""
        if self.selected_thumbnail:
            self.selected_thumbnail.deselect()
        
        thumbnail.select()
        self.selected_thumbnail = thumbnail
        
        # Update selection info
        self.selection_info.config(text=f"Selezionata: Pagina {thumbnail.pagenum}")
        
        # Display image
        self.current_image = thumbnail.image
        self.display_image(thumbnail.image)
        
        # Update category combo if group selected
        if thumbnail.parent_group:
            self.category_var.set(thumbnail.parent_group.categoryname)
            self.page_info_label.config(
                text=f"Documento: {thumbnail.parent_group.categoryname} ({len(thumbnail.parent_group.pages)} pagine)"
            )
        
        self.debug_print(f"Selected thumbnail page {thumbnail.pagenum}")
    
    def select_document_group(self, group: DocumentGroup):
        """Select a document group"""
        if self.selected_group:
            self.selected_group.deselect_group()
        
        group.select_group()
        self.selected_group = group
        
        self.category_var.set(group.categoryname)
        self.page_info_label.config(text=f"Documento: {group.categoryname} ({len(group.pages)} pagine)")
        self.selection_info.config(text=f"Selezionato: Documento {group.categoryname}")
        
        self.debug_print(f"Selected document group: {group.categoryname}")
    
    def display_image(self, image: Image.Image):
        """Display image in center panel"""
        if not image:
            return
        
        self.current_image = image
        
        if self.config_manager.get('auto_fit_images', True):
            self.zoom_fit()
        else:
            self.update_image_display()
    
    def update_image_display(self):
        """Update image display with current zoom and pan"""
        if not self.current_image:
            return
        
        try:
            # Calculate display size
            display_width = int(self.current_image.width * self.zoom_factor)
            display_height = int(self.current_image.height * self.zoom_factor)
            
            # Resize image
            resized_image = self.current_image.resize(
                (display_width, display_height),
                RESAMPLEFILTER
            )
            
            # Convert to PhotoImage
            self.photo_image = ImageTk.PhotoImage(resized_image)
            
            # Clear canvas
            self.image_canvas.delete("all")
            
            # Display image
            self.image_canvas.create_image(
                self.image_offset_x, self.image_offset_y,
                anchor="nw", image=self.photo_image
            )
            
            # Update scroll region
            self.image_canvas.configure(scrollregion=(
                0, 0, display_width, display_height
            ))
            
            # Update status
            zoom_percent = int(self.zoom_factor * 100)
            self.zoom_status.config(text=f"Zoom: {zoom_percent}%")
            
        except Exception as e:
            self.debug_print(f"Error updating image display: {e}")
    
    # ==========================================
    # ZOOM AND PAN METHODS
    # ==========================================
    
    def zoom_in(self):
        """Zoom in on image"""
        if self.current_image:
            self.zoom_factor *= 1.2
            self.update_image_display()
    
    def zoom_out(self):
        """Zoom out on image"""
        if self.current_image:
            self.zoom_factor /= 1.2
            if self.zoom_factor < 0.1:
                self.zoom_factor = 0.1
            self.update_image_display()
    
    def zoom_fit(self):
        """Fit image to canvas"""
        if not self.current_image:
            return
        
        canvas_width = self.image_canvas.winfo_width()
        canvas_height = self.image_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            return
        
        img_width = self.current_image.width
        img_height = self.current_image.height
        
        zoom_width = canvas_width / img_width
        zoom_height = canvas_height / img_height
        
        self.zoom_factor = min(zoom_width, zoom_height) * 0.95
        self.image_offset_x = 0
        self.image_offset_y = 0
        
        self.update_image_display()
    
    def toggle_zoom_area(self):
        """Toggle zoom area selection mode"""
        self.zoom_area_mode = not self.zoom_area_mode
        if self.zoom_area_mode:
            self.image_canvas.config(cursor="crosshair")
            self.pan_mode = False
        else:
            self.image_canvas.config(cursor="arrow")
    
    def toggle_pan_mode(self):
        """Toggle pan mode"""
        self.pan_mode = not self.pan_mode
        if self.pan_mode:
            self.image_canvas.config(cursor="fleur")
            self.zoom_area_mode = False
        else:
            self.image_canvas.config(cursor="arrow")
    
    def on_image_click(self, event):
        """Handle image click (fit if not in special mode)"""
        if not self.zoom_area_mode and not self.pan_mode:
            self.zoom_fit()
    
    def on_zoom_rect_start(self, event):
        """Start zoom rectangle selection"""
        if self.zoom_area_mode:
            self.zoom_rect_start = (event.x, event.y)
    
    def on_zoom_rect_drag(self, event):
        """Drag zoom rectangle"""
        if self.zoom_area_mode and self.zoom_rect_start:
            if self.zoom_rect_id:
                self.image_canvas.delete(self.zoom_rect_id)
            
            x0, y0 = self.zoom_rect_start
            x1, y1 = event.x, event.y
            
            self.zoom_rect_id = self.image_canvas.create_rectangle(
                x0, y0, x1, y1, outline="yellow", width=2
            )
    
    def on_zoom_rect_end(self, event):
        """End zoom rectangle and zoom to selected area"""
        if self.zoom_area_mode and self.zoom_rect_start:
            if self.zoom_rect_id:
                self.image_canvas.delete(self.zoom_rect_id)
                self.zoom_rect_id = None
            
            # Calculate zoom
            x0, y0 = self.zoom_rect_start
            x1, y1 = event.x, event.y
            
            rect_width = abs(x1 - x0)
            rect_height = abs(y1 - y0)
            
            if rect_width > 10 and rect_height > 10:
                canvas_width = self.image_canvas.winfo_width()
                canvas_height = self.image_canvas.winfo_height()
                
                zoom_x = canvas_width / rect_width
                zoom_y = canvas_height / rect_height
                
                self.zoom_factor *= min(zoom_x, zoom_y)
                self.update_image_display()
            
            self.zoom_rect_start = None
            self.zoom_area_mode = False
            self.image_canvas.config(cursor="arrow")
    
    def on_pan_start(self, event):
        """Start panning"""
        if self.pan_mode:
            self.pan_start = (event.x, event.y)
            self.image_canvas.scan_mark(event.x, event.y)
    
    def on_pan_move(self, event):
        """Pan image"""
        if self.pan_mode and self.pan_start:
            self.image_canvas.scan_dragto(event.x, event.y, gain=1)
    
    # ==========================================
    # DRAG AND DROP METHODS
    # ==========================================
    
    def stop_drag(self, thumbnail: PageThumbnail, x_root: int, y_root: int):
        """Handle end of thumbnail drag"""
        target_group = None
        
        for group in self.documentgroups:
            frame_x = group.frame.winfo_rootx()
            frame_y = group.frame.winfo_rooty()
            frame_width = group.frame.winfo_width()
            frame_height = group.frame.winfo_height()
            
            if (frame_x <= x_root <= frame_x + frame_width and
                frame_y <= y_root <= frame_y + frame_height):
                target_group = group
                break
        
        if not target_group:
            return
        
        source_group = thumbnail.parent_group
        
        if target_group == source_group:
            # Reorder within same group
            new_position = target_group.get_drop_position(x_root)
            self.reorder_within_group(source_group, thumbnail, new_position)
        else:
            # Move to different group
            self.move_page_to_group(thumbnail, source_group, target_group, x_root)
    
    def reorder_within_group(self, group: DocumentGroup, thumbnail: PageThumbnail, new_position: int):
        """Reorder thumbnail within its group"""
        old_index = group.remove_thumbnail(thumbnail)
        
        if new_position > old_index:
            new_position -= 1
        
        new_thumbnail = group.add_page(thumbnail.pagenum, thumbnail.image, new_position)
        new_thumbnail.select()
        self.selected_thumbnail = new_thumbnail
        
        self.debug_print(f"Reordered page {thumbnail.pagenum} in {group.categoryname}")
    
    def move_page_to_group(self, thumbnail: PageThumbnail, source_group: DocumentGroup, 
                          target_group: DocumentGroup, x_root: int):
        """Move thumbnail to different group"""
        source_group.remove_thumbnail(thumbnail)
        
        insert_position = target_group.get_drop_position(x_root)
        new_thumbnail = target_group.add_page(thumbnail.pagenum, thumbnail.image, insert_position)
        
        new_thumbnail.select()
        self.selected_thumbnail = new_thumbnail
        
        self.category_var.set(target_group.categoryname)
        self.page_info_label.config(
            text=f"Documento: {target_group.categoryname} ({len(target_group.pages)} pagine)"
        )
        
        self.debug_print(f"Moved page {thumbnail.pagenum} from {source_group.categoryname} to {target_group.categoryname}")
        
        if source_group.is_empty():
            if messagebox.askyesno("Documento Vuoto", 
                                  f"Il documento '{source_group.categoryname}' è ora vuoto.\nEliminarlo?"):
                self.remove_empty_document(source_group)
    
    def remove_empty_document(self, group: DocumentGroup):
        """Remove empty document group"""
        if group in self.documentgroups:
            self.documentgroups.remove(group)
            group.destroy()
            self.renumber_documents()
            self.after_idle(self.update_scroll_region)
    
    # ==========================================
    # CONTEXT MENU METHODS
    # ==========================================
    
    def show_document_context_menu(self, group: DocumentGroup, event):
        """Show context menu for document group"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Nuovo Documento Prima", 
                        command=lambda: self.create_new_document_before(group))
        menu.add_command(label="Nuovo Documento Dopo", 
                        command=lambda: self.create_new_document_after(group))
        menu.add_separator()
        
        if group.is_empty():
            menu.add_command(label="Elimina Documento Vuoto", 
                           command=lambda: self.remove_empty_document(group))
        
        menu.post(event.x_root, event.y_root)
    
    def create_new_document_before(self, reference_group: DocumentGroup):
        """Create new document before reference group"""
        dialog = CategorySelectionDialog(self, self.all_categories, self.category_db)
        
        if dialog.result:
            new_category = dialog.result
            index = self.documentgroups.index(reference_group)
            
            new_counter = reference_group.document_counter
            new_group = DocumentGroup(self.content_frame, new_category, self, new_counter)
            
            # Repack groups
            for group in self.documentgroups:
                group.pack_forget()
            
            self.documentgroups.insert(index, new_group)
            
            for group in self.documentgroups:
                group.pack(pady=5, fill="x", padx=5)
            
            self.renumber_documents()
            self.after_idle(self.update_scroll_region)
            
            self.debug_print(f"Created new document '{new_category}' before '{reference_group.categoryname}'")
    
    def create_new_document_after(self, reference_group: DocumentGroup):
        """Create new document after reference group"""
        dialog = CategorySelectionDialog(self, self.all_categories, self.category_db)
        
        if dialog.result:
            new_category = dialog.result
            index = self.documentgroups.index(reference_group)
            
            new_counter = reference_group.document_counter + 1
            new_group = DocumentGroup(self.content_frame, new_category, self, new_counter)
            
            for group in self.documentgroups:
                group.pack_forget()
            
            self.documentgroups.insert(index + 1, new_group)
            
            for group in self.documentgroups:
                group.pack(pady=5, fill="x", padx=5)
            
            self.renumber_documents()
            self.after_idle(self.update_scroll_region)
            
            self.debug_print(f"Created new document '{new_category}' after '{reference_group.categoryname}'")
    
    def renumber_documents(self):
        """Renumber all documents sequentially"""
        for counter, group in enumerate(self.documentgroups, start=1):
            group.update_document_counter(counter)


def main():
    """Main application entry point"""
    app = AIDOXAApp()
    app.mainloop()


if __name__ == "__main__":
    main()