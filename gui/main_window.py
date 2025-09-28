"""
Main window for DynamicAI application with multi-row grid support
"""

import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk
from typing import List, Optional, Set

# Internal imports
from config import ConfigManager, DB_FILE
from database import CategoryDatabase
from loaders import create_document_loader
from export import ExportManager
from gui.dialogs import CategorySelectionDialog, SettingsDialog
from gui.components import DocumentGroup, PageThumbnail
from utils import create_progress_dialog, show_help_dialog, show_about_dialog
from config.constants import RESAMPLEFILTER

class AIDOXAApp(tk.Tk):
    """Main application window for DynamicAI with multi-row grid support"""
    
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

    def setup_window(self):
        """Setup main window properties"""
        self.title("DynamicAI - Editor Lineare Avanzato")
        
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
        # Image display area
        self.image_canvas = tk.Canvas(self.center_panel, bg="black", cursor="cross")
        self.image_canvas.pack(fill="both", expand=True, padx=2, pady=2)

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

        # Status label
        self.zoom_status = tk.Label(zoom_frame, text="", bg="darkgray", fg="white", font=("Arial", 8))
        self.zoom_status.pack(side="right", padx=10)

    def bind_image_events(self):
        """Bind events for image canvas"""
        self.image_canvas.bind("<Button-1>", self.on_image_click)
        self.image_canvas.bind("<ButtonPress-1>", self.on_zoom_rect_start)
        self.image_canvas.bind("<B1-Motion>", self.on_zoom_rect_drag)
        self.image_canvas.bind("<ButtonRelease-1>", self.on_zoom_rect_end)
        self.image_canvas.bind("<Configure>", self.on_canvas_resize)
        
        # Hover effects
        self.image_canvas.bind("<Enter>", self.on_canvas_enter)
        self.image_canvas.bind("<Leave>", self.on_canvas_leave)

    def setup_right_panel(self):
        """Setup right panel with controls and details"""
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
        # Editable combobox (not readonly)
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

    def setup_instructions_area(self):
        """Setup instructions text area"""
        instructions_label = tk.Label(self.right_panel, text="Pannello Informazioni:", 
                                     font=("Arial", 10, "bold"), bg="lightgray")
        instructions_label.pack(pady=(20, 5))

        self.instructions_text = ScrolledText(self.right_panel, height=15, width=35)
        self.instructions_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Default instructions
        self.update_instructions("Configura le cartelle input/output nelle Preferenze e usa 'Aggiorna Lista (Preview)' per iniziare.\n\nUsa il menu 'Aiuto > Istruzioni' per vedere le funzionalità complete.\n\nNuova funzionalità: Layout a griglia multi-riga per i documenti con molte pagine!")

    def bind_events(self):
        """Bind keyboard shortcuts and window events"""
        # Keyboard shortcuts
        self.bind_all('<Control-r>', lambda e: self.refresh_document_list())
        self.bind_all('<Control-e>', lambda e: self.complete_sequence_export())
        self.bind_all('<Control-q>', lambda e: self.on_closing())
        
        # Window events
        if self.config_manager.get('save_window_layout', True):
            self.bind('<Configure>', self.on_window_configure)
            self.bind_all('<B1-Motion>', self.on_paned_motion)
            self.bind_all('<ButtonRelease-1>', self.on_paned_release)
        
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
                # Update the entire group's category
                old_category = self.selected_group.categoryname
                self.selected_group.update_category_name(new_category)
                self.page_info_label.config(text=f"Documento: {new_category} ({len(self.selected_group.pages)} pagine)")
                
                # Save new category to database
                self.category_db.add_category(new_category)
                
                # If a thumbnail is also selected, update its display
                if self.selected_thumbnail:
                    self.selection_info.config(text=f"Selezionata: Pagina {self.selected_thumbnail.pagenum}")
                
                self.debug_print(f"Category changed from {old_category} to {new_category}")

    def on_category_enter(self, event):
        """Handle Enter key in category combo"""
        self.save_new_category()

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
            # Update window settings
            if self.config_manager.get('save_window_layout', True):
                self.config_manager.config_data['window_settings'] = {
                    'geometry': self.geometry(),
                    'state': self.state()
                }
                
                # Save panel positions
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
            
            # Restore panel positions
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
        self.instructions_text.delete("1.0", tk.END)
        self.instructions_text.insert(tk.END, text)

    # Menu handlers
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
            
            # Refresh if settings changed
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
            # Force grid repack after size changes
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
            # Save to database
            if self.category_db.add_category(new_category):
                # Update combobox values
                self.update_category_combo()
                # Apply to selected group if any
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

    # Document loading and management
    def refresh_document_list(self):
        """Load document from configured input folder"""
        input_folder = self.config_manager.get('default_input_folder', '')
        
        if not input_folder or not os.path.exists(input_folder):
            messagebox.showerror("Errore", 
                               "Cartella input non configurata o non esistente.\n"
                               "Configura la cartella nelle Preferenze.")
            return

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
            categories = data.get("categories", [])

            # Store document name for export
            self.current_document_name = os.path.splitext(os.path.basename(doc_file))[0]

            # Collect all unique categories
            self.all_categories = set(cat['categoria'] for cat in categories if cat['categoria'] != "Pagina vuota")
            
            # Update category combo with both JSON and DB categories
            self.update_category_combo()

            self.load_document(doc_file)
            self.build_document_groups(categories)
            
            # Update instructions with loaded document info
            self.update_document_instructions(json_file, doc_file, input_folder, categories)
            
            self.debug_print(f"Document loaded: {len(categories)} categories, {len(self.documentgroups)} documents, {self.documentloader.totalpages if self.documentloader else 0} pages")
            
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

        # Clear existing groups
        for group in self.documentgroups:
            group.destroy()
        self.documentgroups.clear()

        current_group = None
        current_pages = []
        documents = []

        # Process categories and merge "Pagina vuota" with previous group
        for cat in categories:
            cat_name = cat['categoria']
            start = cat['inizio']
            end = cat['fine']
            
            if cat_name == "Pagina vuota" and current_group is not None:
                # Add empty pages to current group
                for p in range(start, end+1):
                    current_pages.append(p)
            else:
                # Save previous group if exists
                if current_group is not None:
                    documents.append({
                        "categoria": current_group,
                        "pagine": current_pages.copy()
                    })
                # Start new group
                current_group = cat_name
                current_pages = list(range(start, end+1))
        
        # Add last group
        if current_group is not None:
            documents.append({
                "categoria": current_group,
                "pagine": current_pages.copy()
            })

        # Create UI groups with document counter
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

        # Force update of scroll region after all groups are added
        self.after_idle(self.update_scroll_region)
        
        self.updating_ui = False
        self.debug_print(f"Created {len(documents)} document groups with grid layout")

    def update_scroll_region(self):
        """Update scroll region for document groups"""
        self.canvas.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def update_document_instructions(self, json_file: str, doc_file: str, input_folder: str, categories: List):
        """Update instructions panel with document information including grid layout info"""
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
        
        # Count total pages per document for grid info
        grid_info = ""
        for i, group in enumerate(self.documentgroups):
            page_count = group.get_page_count()
            group_info = group.get_info()
            grid_rows = group_info.get('grid_rows', 0)
            per_row = group_info.get('thumbnails_per_row', 4)
            if page_count > 0:
                grid_info += f"  Doc {i+1}: {page_count} pagine ({grid_rows} righe, {per_row}/riga)\n"
        
        instructions = f"""DOCUMENTO CARICATO:

File JSON: {os.path.basename(json_file)}
Documento: {os.path.basename(doc_file)}
Cartella Input: {input_folder}
Categorie JSON: {len(self.all_categories)}
Categorie Database: {db_categories_count}
Documenti: {len(self.documentgroups)}
Pagine totali: {self.documentloader.totalpages if self.documentloader else 0}

LAYOUT A GRIGLIA MULTI-RIGA:
✓ Adattamento automatico alla larghezza finestra
✓ 2-6 miniature per riga (configurabile)
✓ Altezza documento si adatta alle righe necessarie
✓ Drag & drop compatibile con layout a griglia

{grid_info}

CONFIGURAZIONE DOCUMENTI:
Cifre contatore: {self.config_manager.get('document_counter_digits', 4)}
Font: {self.config_manager.get('document_font_name', 'Arial')} {self.config_manager.get('document_font_size', 10)}pt
Allineamento: Sinistra
Layout: Griglia multi-riga adattiva

EXPORT CONFIGURATO:
Formato: {format_display}
Qualità JPEG: {self.config_manager.get('jpeg_quality', 95)}%
File esistenti: {file_handling_display}
Backup: {'Abilitato' if self.config_manager.get('create_backup_on_overwrite', False) else 'Disabilitato'}

DATABASE CATEGORIE:
• Database SQLite: {os.path.basename(DB_FILE)}
• Categorie salvate: {db_categories_count}
• Combobox modificabile nel pannello destro
• Salvataggio automatico di nuove categorie

GESTIONE FILE ESISTENTI (v3.3):
• Auto-rinomina: documento.pdf → documento(1).pdf
• Chiedi conferma: popup per sovrascrivere
• Sovrascrivi sempre: backup opzionale
• Sistema numerazione Windows-style

OPERAZIONI DISPONIBILI:
• Click su miniature: visualizza immagine
• Drag miniature: riorganizza tra documenti (grid-compatible)
• Click intestazioni: seleziona intero documento
• Tasto destro su intestazioni: menu con categorie
• Combobox categoria: modifica e salva nuove
• Click su immagine centrale: zoom fit
• Hover su elementi per feedback visivo
• Export intelligente con gestione duplicati
• Ridimensionamento finestra: layout griglia si adatta

EXPORT:
Nome base file: {self.current_document_name}
Usa il menu 'Aiuto > Istruzioni' per dettagli completi.
        """
        
        self.update_instructions(instructions)

    # Export functionality
    def complete_sequence_export(self):
        """Export images to configured output folder"""
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
            
            # Create progress dialog
            progress_window, progress_var, _ = create_progress_dialog(self, f"Export in formato {export_format}...")
            
            # Export using export manager
            def progress_callback(message):
                progress_var.set(message)
                progress_window.update()
            
            exported_files = self.export_manager.export_documents(
                output_folder, self.documentgroups, self.current_document_name, progress_callback
            )
            
            progress_window.destroy()
            
            # Show summary
            summary_message = f"Export completato!\n\n"
            summary_message += f"Formato: {export_format}\n"
            summary_message += f"Cartella: {output_folder}\n"
            summary_message += f"File creati: {len(exported_files)}\n"
            if export_format in ['PDF_MULTI', 'TIFF_MULTI']:
                summary_message += f"Documenti processati: {len(self.documentgroups)}"
            
            messagebox.showinfo("Export Completato", summary_message)
            
            # Update last folder
            self.config_manager.set('last_folder', output_folder)
            if self.config_manager.get('auto_save_changes', True):
                self.save_config()
                
            self.debug_print(f"Exported {len(exported_files)} files to {output_folder} in format {export_format}")
            
        except Exception as e:
            if 'progress_window' in locals():
                progress_window.destroy()
            messagebox.showerror("Errore", f"Errore durante l'export: {str(e)}")

    # Selection management
    def select_thumbnail(self, thumbnail: PageThumbnail):
        """Select a thumbnail and display its image"""
        self.debug_print(f"select_thumbnail called for page {thumbnail.pagenum}")
        
        # Deselect previous thumbnail and group
        if self.selected_thumbnail:
            self.selected_thumbnail.deselect()
        if self.selected_group:
            self.selected_group.deselect_group()
            
        self.selected_thumbnail = thumbnail
        self.selected_group = thumbnail.document_group
        
        # Select new thumbnail and its group
        thumbnail.select()
        self.selected_group.select_group()
        
        # Display the image
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
        
        # Update right panel
        self.category_var.set(thumbnail.categoryname)
        self.selection_info.config(text=f"Selezionata: Pagina {thumbnail.pagenum}")
        self.page_info_label.config(text=f"Documento: {thumbnail.categoryname}")

    def select_document_group(self, group: DocumentGroup):
        """Select an entire document group"""
        # Deselect previous selections
        if self.selected_thumbnail:
            self.selected_thumbnail.deselect()
            self.selected_thumbnail = None
        if self.selected_group:
            self.selected_group.deselect_group()
            
        self.selected_group = group
        group.select_group()
        
        # Update right panel for group
        self.category_var.set(group.categoryname)
        self.selection_info.config(text=f"Selezionato: Documento")
        self.page_info_label.config(text=f"Documento: {group.categoryname} ({len(group.pages)} pagine)")

    # Image display and zoom functionality
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
        
        # Auto-fit the image
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
        if not self.zoom_area_mode and self.current_image:
            # Single click on image = return to fit
            self.auto_fit_on_resize = True
            if self.config_manager.get('auto_fit_images', True):
                self.zoom_fit()

    def on_zoom_rect_start(self, event):
        """Start zoom rectangle selection"""
        if self.zoom_area_mode and self.current_image:
            self.zoom_rect_start = (event.x, event.y)
            if self.zoom_rect_id:
                self.image_canvas.delete(self.zoom_rect_id)

    def on_zoom_rect_drag(self, event):
        """Drag zoom rectangle"""
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
            
            # Calculate zoom area
            x1, y1 = self.zoom_rect_start
            x2, y2 = self.zoom_rect_end
            if abs(x2-x1) > 10 and abs(y2-y1) > 10:
                self.auto_fit_on_resize = False
                self.zoom_to_area(min(x1,x2), min(y1,y2), abs(x2-x1), abs(y2-y1))
            
            self.zoom_area_mode = False
            self.image_canvas.config(cursor="cross")
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def zoom_to_area(self, x: int, y: int, w: int, h: int):
        """Zoom to specific area"""
        if not self.current_image:
            return
        
        canvas_w = self.image_canvas.winfo_width()
        canvas_h = self.image_canvas.winfo_height()
        
        # Calculate new zoom factor
        zoom_w = canvas_w / w
        zoom_h = canvas_h / h
        new_zoom = min(zoom_w, zoom_h) * self.zoom_factor
        
        # Calculate new offset
        center_x = x + w/2
        center_y = y + h/2
        
        self.zoom_factor = new_zoom
        self.image_offset_x = canvas_w/2 - center_x * (new_zoom / self.zoom_factor)
        self.image_offset_y = canvas_h/2 - center_y * (new_zoom / self.zoom_factor)
        
        self.update_image_display()
        self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def update_image_display(self):
        """Update the image display on canvas"""
        if not self.current_image:
            return
        
        self.image_canvas.delete("all")
        
        # Resize image
        img_w, img_h = self.current_image.size
        new_w = int(img_w * self.zoom_factor)
        new_h = int(img_h * self.zoom_factor)
        
        if new_w > 0 and new_h > 0:
            try:
                resized_img = self.current_image.resize((new_w, new_h), RESAMPLEFILTER)
                self.photo = ImageTk.PhotoImage(resized_img)
                
                canvas_w = self.image_canvas.winfo_width()
                canvas_h = self.image_canvas.winfo_height()
                
                x = canvas_w // 2 + self.image_offset_x
                y = canvas_h // 2 + self.image_offset_y
                
                self.image_canvas.create_image(x, y, image=self.photo)
            except Exception as e:
                self.debug_print(f"Error updating image display: {e}")

    # Drag and drop functionality - Enhanced for grid layout
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
            # Get original group
            original_group = None
            for group in self.documentgroups:
                if self.drag_item in group.thumbnails:
                    original_group = group
                    break
            
            if original_group == target_group:
                # Reorder within same group
                self.reorder_within_group(self.drag_item, target_group, x_root, y_root)
            else:
                # Move to different group
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
        
        # Use enhanced drop position calculation for grid
        new_index = self.calculate_grid_drop_position(group, x_root, y_root)
        
        # Adjust new index if we're moving to the right
        if new_index > old_index:
            new_index -= 1
            
        if old_index == new_index:
            return
        
        # Remove thumbnail from old position
        group.thumbnails.pop(old_index)
        group.pages.pop(old_index)
        
        # Insert at new position
        group.thumbnails.insert(new_index, thumbnail)
        group.pages.insert(new_index, thumbnail.pagenum)
        
        # Repack all thumbnails in grid
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
        
        # Calculate grid position
        col = max(0, relative_x // (thumb_width + padding))
        row = max(0, relative_y // (thumb_height + 20 + padding))  # 20 for label height
        
        # Convert grid position to list index
        thumbnails_per_row = group.thumbnails_per_row
        estimated_position = row * thumbnails_per_row + col
        
        return min(estimated_position, len(group.thumbnails))

    def move_page_to_group(self, thumbnail: PageThumbnail, target_group: DocumentGroup):
        """Move page to different group"""
        # Find original group
        original_group = None
        for group in self.documentgroups:
            if thumbnail in group.thumbnails:
                original_group = group
                break
                
        if not original_group or original_group == target_group:
            return

        # Remove from original group
        original_group.remove_thumbnail(thumbnail)
        
        # Destroy old thumbnail frame
        thumbnail.frame.destroy()
        
        # Create new thumbnail in target group
        new_thumbnail = target_group.add_page(thumbnail.pagenum, thumbnail.image)
        
        # Select the new thumbnail if the old one was selected
        if self.selected_thumbnail == thumbnail:
            self.selected_thumbnail = new_thumbnail
            self.selected_group = target_group
            new_thumbnail.select()
            target_group.select_group()
            self.category_var.set(target_group.categoryname)
            self.selection_info.config(text=f"Selezionata: Pagina {thumbnail.pagenum}")
            self.page_info_label.config(text=f"Documento: {target_group.categoryname}")

        self.debug_print(f"Moved page {thumbnail.pagenum} from {original_group.categoryname} to {target_group.categoryname}")

    # Document context menu functionality
    def show_document_context_menu(self, document_group: DocumentGroup, event):
        """Show context menu for document group"""
        context_menu = tk.Menu(self, tearoff=0)
        
        # Menu options
        context_menu.add_command(label="Nuovo documento prima", 
                               command=lambda: self.create_new_document(document_group, "before"))
        context_menu.add_command(label="Nuovo documento dopo", 
                               command=lambda: self.create_new_document(document_group, "after"))
        context_menu.add_separator()
        
        # Only if document is empty
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
        # Get categories from JSON and database
        json_categories = list(self.all_categories)
        db_categories = self.category_db.get_all_categories()
        
        # Show category selection dialog
        dialog = CategorySelectionDialog(self, json_categories, db_categories, 
                                       "Seleziona Categoria per Nuovo Documento")
        
        if dialog.result:
            selected_category = dialog.result
            
            # Save category to database
            self.category_db.add_category(selected_category)
            
            # Find reference document index
            ref_index = self.documentgroups.index(reference_document)
            
            if position == "after":
                new_index = ref_index + 1
            else:  # before
                new_index = ref_index
            
            # Create new document
            new_counter = self.get_next_counter_for_position(new_index)
            new_group = DocumentGroup(self.content_frame, selected_category, self, new_counter)
            
            # Insert in list
            self.documentgroups.insert(new_index, new_group)
            
            # Renumber all documents
            self.renumber_documents()
            
            # Reorganize UI
            self.repack_all_documents()
            
            # Update categories if new
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
            
            # Remove from list
            if document_group in self.documentgroups:
                self.documentgroups.remove(document_group)
            
            # Destroy widget
            document_group.destroy()
            
            # Renumber remaining documents
            self.renumber_documents()
            
            # Reorganize UI
            self.repack_all_documents()
            
            # Reset selections if necessary
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
            # Middle insertion, counter will be updated by renumbering
            return position + 1

    def renumber_documents(self):
        """Renumber all document counters sequentially"""
        for i, group in enumerate(self.documentgroups, 1):
            group.update_document_counter(i)

    def repack_all_documents(self):
        """Repack all document groups in UI"""
        for group in self.documentgroups:
            group.pack_forget()
        
        for group in self.documentgroups:
            group.pack(pady=5, fill="x", padx=5)
        
        # Update scroll region after repacking
        self.after_idle(self.update_scroll_region)