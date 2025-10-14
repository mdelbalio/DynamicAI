"""
Settings Dialog for DynamicAI v3.6 (BATCH EDITION)
Aggiunte:
- Tab "Percorsi" con gestione JSON separato
- Tab "CSV" per modalità incremental/per_file
- Tab "Batch" per abilitazione batch manager
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
# Add import for new CategoryDatabase
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SettingsDialog:
    """Dialog per configurazione applicazione"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None

        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Impostazioni DynamicAI")
        self.dialog.geometry("700x720")  # Un po' più alta
        self.dialog.minsize(700, 720)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # ⭐ STEP 1: CREA I PULSANTI PRIMA!
        self.create_buttons()
        
        # ⭐ STEP 2: POI il notebook
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 10))  # Meno spazio in basso

        # STEP 3: Crea i tab
        self.create_paths_tab()
        self.create_fonts_tab()
        self.create_thumbnails_tab()
        self.create_export_tab()
        self.create_csv_tab()
        self.create_batch_tab()
        self.create_categories_tab()
        self.create_advanced_tab()       
        
    def create_paths_tab(self):
        """Tab percorsi input/output e JSON"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Percorsi")
        
        # Input folder
        self.create_folder_setting(frame, "Cartella Input Documenti:",
                                   'default_input_folder', 0)
        
        # Output folder
        self.create_folder_setting(frame, "Cartella Output Documenti:",
                                   'default_output_folder', 1)
        
        # Checkbox per mantenere struttura directory
        self.preserve_structure_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('preserve_folder_structure', False))
        
        ttk.Checkbutton(frame, text="Mantieni struttura directory di input nell'output",
                       variable=self.preserve_structure_var).grid(
            row=2, column=0, columnspan=3, sticky="w", padx=20, pady=(5, 10))
        
        # Label esplicativa
        tk.Label(frame, 
                text="Se abilitato: INPUT/00001 → OUTPUT/00001/[files]",
                font=("Arial", 8), fg="gray").grid(
            row=3, column=0, columnspan=3, sticky="w", padx=40, pady=(0, 10))        
                       
        # Separator
        ttk.Separator(frame, orient="horizontal").grid(row=4, column=0, columnspan=3,
                                                       sticky="ew", pady=20, padx=10)
        
        # JSON settings
        tk.Label(frame, text="Gestione File JSON:", font=("Arial", 10, "bold")).grid(
            row=5, column=0, columnspan=3, sticky="w", padx=10, pady=(10, 5))
        
        # Use input folder for JSON checkbox
        self.use_input_json_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('use_same_folder_for_json', True))
        ttk.Checkbutton(frame, text="Usa stessa cartella dei documenti per file JSON",
                       variable=self.use_input_json_var,
                       command=self.toggle_json_folder).grid(
            row=6, column=0, columnspan=3, sticky="w", padx=20, pady=5)
        
        # JSON folder (conditional)
        self.json_folder_label = tk.Label(frame, text="Cartella JSON Separata:")
        self.json_folder_label.grid(row=7, column=0, sticky="w", padx=20, pady=5)
        
        self.json_folder_var = tk.StringVar(
            value=self.config_manager.config_data.get('json_folder', ''))
        self.json_folder_entry = tk.Entry(frame, textvariable=self.json_folder_var, width=40)
        self.json_folder_entry.grid(row=7, column=1, sticky="ew", padx=5)
        
        self.json_folder_btn = tk.Button(frame, text="Sfoglia",
                                        command=lambda: self.browse_folder('json_input_path'))
        self.json_folder_btn.grid(row=7, column=2, padx=5)
        
        # Initial state
        self.toggle_json_folder()
        
        # Grid weights
        frame.columnconfigure(1, weight=1)
        
    def create_folder_setting(self, parent, label_text, config_key, row):
        """Helper to create folder setting row"""
        tk.Label(parent, text=label_text, font=("Arial", 9)).grid(
            row=row, column=0, sticky="w", padx=10, pady=10)
        
        var = tk.StringVar(value=self.config_manager.config_data.get(config_key, ''))
        setattr(self, f"{config_key}_var", var)
        
        entry = tk.Entry(parent, textvariable=var, width=40)
        entry.grid(row=row, column=1, sticky="ew", padx=5)
        
        btn = tk.Button(parent, text="Sfoglia",
                       command=lambda k=config_key: self.browse_folder(k))
        btn.grid(row=row, column=2, padx=5)
        
    def toggle_json_folder(self):
        """Toggle JSON folder entry based on checkbox"""
        if self.use_input_json_var.get():
            self.json_folder_label.config(state="disabled")
            self.json_folder_entry.config(state="disabled")
            self.json_folder_btn.config(state="disabled")
        else:
            self.json_folder_label.config(state="normal")
            self.json_folder_entry.config(state="normal")
            self.json_folder_btn.config(state="normal")
            
    def create_fonts_tab(self):
        """Tab font documenti"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Font")
        
        tk.Label(frame, text="Font Intestazione Documenti:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=10)
        
        # Font family
        font_frame = tk.Frame(frame)
        font_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(font_frame, text="Nome Font:").pack(side="left")
        self.font_name_var = tk.StringVar(
            value=self.config_manager.config_data['fonts'].get('document_font_name', 'Arial'))
        fonts_available = ['Arial', 'Helvetica', 'Times New Roman', 'Courier New', 'Verdana']
        ttk.Combobox(font_frame, textvariable=self.font_name_var,
                    values=fonts_available, width=20).pack(side="left", padx=5)
        
        # Font size
        size_frame = tk.Frame(frame)
        size_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(size_frame, text="Dimensione:").pack(side="left")
        self.font_size_var = tk.IntVar(
            value=self.config_manager.config_data['fonts'].get('document_font_size', 10))
        tk.Spinbox(size_frame, from_=8, to=16, textvariable=self.font_size_var,
                  width=5).pack(side="left", padx=5)
        
        # Font bold
        self.font_bold_var = tk.BooleanVar(
            value=self.config_manager.config_data['fonts'].get('document_font_bold', True))
        ttk.Checkbutton(frame, text="Grassetto", variable=self.font_bold_var).pack(
            anchor="w", padx=20, pady=10)
        
    def create_thumbnails_tab(self):
        """Tab thumbnails"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Miniature")
        
        tk.Label(frame, text="Dimensioni Miniature:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=10)
        
        # Width
        width_frame = tk.Frame(frame)
        width_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(width_frame, text="Larghezza:").pack(side="left")
        self.thumb_width_var = tk.IntVar(
            value=self.config_manager.get('thumbnail_width', 80))
        self.width_spinbox = tk.Spinbox(width_frame, from_=60, to=200, 
                                        textvariable=self.thumb_width_var,
                                        width=8, command=self.on_width_changed)
        self.width_spinbox.pack(side="left", padx=5)
        tk.Label(width_frame, text="px").pack(side="left")

        # Height
        height_frame = tk.Frame(frame)
        height_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(height_frame, text="Altezza:").pack(side="left")
        self.thumb_height_var = tk.IntVar(
            value=self.config_manager.get('thumbnail_height', 100))
        self.height_spinbox = tk.Spinbox(height_frame, from_=80, to=250, 
                                        textvariable=self.thumb_height_var,
                                        width=8)
        self.height_spinbox.pack(side="left", padx=5)
        tk.Label(height_frame, text="px").pack(side="left")

        # Keep aspect ratio checkbox
        self.keep_aspect_var = tk.BooleanVar(
            value=self.config_manager.get('thumbnail_keep_aspect_ratio', False))
        ttk.Checkbutton(frame, text="Mantieni proporzioni (rapporto larghezza/altezza)",
                    variable=self.keep_aspect_var).pack(anchor="w", padx=20, pady=10)
        
    def create_export_tab(self):
        """Tab export"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Export")
        
        # Format
        tk.Label(frame, text="Formato Export:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=10)
        
        self.export_format_var = tk.StringVar(
            value=self.config_manager.config_data.get('export_format', 'JPEG'))
        
        formats = [
            ('JPEG (file singoli)', 'JPEG'),
            ('PDF Singolo (file per pagina)', 'PDF_SINGLE'),
            ('PDF Multi-pagina (file per documento)', 'PDF_MULTI'),
            ('TIFF Singolo (file per pagina)', 'TIFF_SINGLE'),
            ('TIFF Multi-pagina (file per documento)', 'TIFF_MULTI')
        ]
        
        for text, value in formats:
            ttk.Radiobutton(frame, text=text, variable=self.export_format_var,
                           value=value).pack(anchor="w", padx=20, pady=2)
        
        # JPEG quality
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=15, padx=10)
        
        tk.Label(frame, text="Qualità JPEG:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        
        quality_frame = tk.Frame(frame)
        quality_frame.pack(fill="x", padx=20, pady=5)
        
        self.jpeg_quality_var = tk.IntVar(
            value=self.config_manager.config_data.get('jpeg_quality', 95))
        
        tk.Scale(quality_frame, from_=50, to=100, orient="horizontal",
                variable=self.jpeg_quality_var, length=300).pack(side="left")
        tk.Label(quality_frame, textvariable=self.jpeg_quality_var).pack(side="left", padx=5)
        tk.Label(quality_frame, text="%").pack(side="left")
        
        # File handling
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=15, padx=10)
        
        tk.Label(frame, text="Gestione File Esistenti:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        
        self.file_handling_var = tk.StringVar(
            value=self.config_manager.config_data.get('file_handling_mode', 'auto_rename'))
        
        ttk.Radiobutton(frame, text="Rinomina automaticamente (file(1).pdf)",
                       variable=self.file_handling_var,
                       value='auto_rename').pack(anchor="w", padx=20, pady=2)
        ttk.Radiobutton(frame, text="Chiedi conferma",
                       variable=self.file_handling_var,
                       value='ask_overwrite').pack(anchor="w", padx=20, pady=2)
        ttk.Radiobutton(frame, text="Sovrascrivi sempre",
                       variable=self.file_handling_var,
                       value='always_overwrite').pack(anchor="w", padx=20, pady=2)
        
    def create_csv_tab(self):
        """Tab CSV (NUOVO)"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="CSV")
        
        tk.Label(frame, text="Modalità Export CSV:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=10)
               
        # CSV mode
        self.csv_mode_var = tk.StringVar(
            value=self.config_manager.config_data.get('csv_mode', 'incremental'))
        
        ttk.Radiobutton(frame, text="Incrementale (unico metadata.csv con tutti i documenti)",
                       variable=self.csv_mode_var,
                       value='incremental').pack(anchor="w", padx=20, pady=5)
        
        ttk.Radiobutton(frame, text="Per File (un CSV separato per ogni documento)",
                       variable=self.csv_mode_var,
                       value='per_file').pack(anchor="w", padx=20, pady=5)
        
        # CSV delimiter
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=15, padx=10)
        
        tk.Label(frame, text="Delimitatore CSV:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        
        delim_frame = tk.Frame(frame)
        delim_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(delim_frame, text="Carattere:").pack(side="left")
        self.csv_delimiter_var = tk.StringVar(
            value=self.config_manager.config_data.get('csv_delimiter', ';'))
        
        delimiters = [
            ('Punto e virgola (;)', ';'),
            ('Virgola (,)', ','),
            ('Tab', '\t'),
            ('Pipe (|)', '|')
        ]
        
        for text, value in delimiters:
            ttk.Radiobutton(delim_frame, text=text, variable=self.csv_delimiter_var,
                           value=value).pack(anchor="w", padx=10, pady=2)
        
        # CSV output folder
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=15, padx=10)
        
        tk.Label(frame, text="Cartella Output CSV (opzionale):",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        
        tk.Label(frame, text="Lascia vuoto per usare la stessa cartella output documenti",
                font=("Arial", 8), fg="gray").pack(anchor="w", padx=20, pady=2)
        
        csv_folder_frame = tk.Frame(frame)
        csv_folder_frame.pack(fill="x", padx=20, pady=5)
        
        self.csv_output_var = tk.StringVar(
            value=self.config_manager.config_data.get('csv_output_path', ''))
        tk.Entry(csv_folder_frame, textvariable=self.csv_output_var,
                width=40).pack(side="left", fill="x", expand=True)
        tk.Button(csv_folder_frame, text="Sfoglia",
                 command=lambda: self.browse_folder('csv_output_path')).pack(
            side="right", padx=(5, 0))
        
        # Nome file CSV
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=15, padx=10)
        
        tk.Label(frame, text="Nome File CSV:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=5)
        
        # Checkbox - Usa nome documento
        self.csv_use_doc_name_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('csv_use_document_name', False))
        ttk.Checkbutton(frame, text="Usa nome file documento (invece di nome cartella)",
                       variable=self.csv_use_doc_name_var).pack(anchor="w", padx=20, pady=5)
        
        # Nome personalizzato
        custom_name_frame = tk.Frame(frame)
        custom_name_frame.pack(fill="x", padx=20, pady=5)
        
        tk.Label(custom_name_frame, text="Nome personalizzato:").pack(side="left")
        self.csv_custom_name_var = tk.StringVar(
            value=self.config_manager.config_data.get('csv_custom_name', ''))
        tk.Entry(custom_name_frame, textvariable=self.csv_custom_name_var,
                width=30).pack(side="left", padx=(5, 0))
        
        # Help label
        tk.Label(frame, text="(Lascia vuoto per nome automatico. Nome personalizzato ha priorità)",
                font=("Arial", 8), fg="gray").pack(anchor="w", padx=20, pady=(0, 5))
        
        # ========================================
        # BATCH CSV SETTINGS
        # ========================================
        batch_csv_frame = tk.LabelFrame(
            frame,
            text="Configurazione CSV Batch",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10
        )
        batch_csv_frame.pack(fill="x", padx=10, pady=10)

        # CSV Location
        tk.Label(
            batch_csv_frame,
            text="Posizione CSV:",
            font=("Arial", 9, "bold")
        ).pack(anchor="w", pady=(5, 2))

        self.csv_location_var = tk.StringVar(value=self.config_manager.config_data.get('batch_csv_location', 'per_folder'))
        
        tk.Radiobutton(
            batch_csv_frame,
            text="Per Cartella (un CSV per ogni cartella output)",
            variable=self.csv_location_var,
            value='per_folder',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        tk.Radiobutton(
            batch_csv_frame,
            text="Globale Root (un CSV unico nella cartella output principale)",
            variable=self.csv_location_var,
            value='root',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        # Separator
        ttk.Separator(batch_csv_frame, orient="horizontal").pack(fill="x", pady=10)

        # CSV Naming
        tk.Label(
            batch_csv_frame,
            text="Naming CSV:",
            font=("Arial", 9, "bold")
        ).pack(anchor="w", pady=(5, 2))

        self.csv_naming_var = tk.StringVar(value=self.config_manager.config_data.get('batch_csv_naming', 'auto'))

        tk.Radiobutton(
            batch_csv_frame,
            text="Auto (usa nome cartella)",
            variable=self.csv_naming_var,  # ✅
            value='auto',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        tk.Radiobutton(
            batch_csv_frame,
            text="Nome Cartella",
            variable=self.csv_naming_var,  # ✅
            value='folder_name',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        tk.Radiobutton(
            batch_csv_frame,
            text="Personalizzato (specifica prefisso sotto)",
            variable=self.csv_naming_var,  # ✅
            value='custom',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        tk.Radiobutton(
            batch_csv_frame,
            text="Timestamp (YYYYMMDD_HHMMSS)",
            variable=self.csv_naming_var,  # ✅
            value='timestamp',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        # Custom Prefix
        prefix_frame = tk.Frame(batch_csv_frame, bg="white")
        prefix_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            prefix_frame,
            text="Prefisso personalizzato:",
            font=("Arial", 9),
            bg="white"
        ).pack(side="left")

        self.csv_prefix_var = tk.StringVar(value=self.config_manager.config_data.get('batch_csv_custom_prefix', 'metadata'))
        tk.Entry(
            prefix_frame,
            textvariable=self.csv_prefix_var,  # ✅
            font=("Arial", 9),
            width=20
        ).pack(side="left", padx=5)

        # Separator
        ttk.Separator(batch_csv_frame, orient="horizontal").pack(fill="x", pady=10)

        # CSV Suffixes
        tk.Label(
            batch_csv_frame,
            text="Suffissi Opzionali:",
            font=("Arial", 9, "bold")
        ).pack(anchor="w", pady=(5, 2))

        self.csv_timestamp_var = tk.BooleanVar(value=self.config_manager.config_data.get('batch_csv_add_timestamp', False))
        tk.Checkbutton(
            batch_csv_frame,
            text="Aggiungi timestamp al nome file (es: metadata_20250110_153045.csv)",
            variable=self.csv_timestamp_var,  # ✅
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        self.csv_counter_var = tk.BooleanVar(value=self.config_manager.config_data.get('batch_csv_add_counter', False))
        tk.Checkbutton(
            batch_csv_frame,
            text="Aggiungi contatore sequenziale (es: metadata_001.csv, metadata_002.csv)",
            variable=self.csv_counter_var,  # ✅
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        # Example Preview
        example_label = tk.Label(
            batch_csv_frame,
            text="",
            font=("Arial", 8),
            fg="gray",
            bg="white",
            justify="left"
        )
        example_label.pack(anchor="w", padx=20, pady=5)

        def update_example(*args):
            """Aggiorna esempio nome file"""
            naming = self.csv_naming_var.get()  # ✅
            prefix = self.csv_prefix_var.get()  # ✅
            add_ts = self.csv_timestamp_var.get()  # ✅
            add_cnt = self.csv_counter_var.get()  # ✅
            
            if naming == 'folder_name':
                base = "Insegne_multi-B001"
            elif naming == 'custom':
                base = prefix or "metadata"
            elif naming == 'timestamp':
                base = "20250110_153045"
            else:
                base = "Insegne_multi-B001"
            
            suffixes = []
            if add_cnt:
                suffixes.append("001")
            if add_ts:
                suffixes.append("20250110_153045")
            
            if suffixes:
                example = f"{base}_{'_'.join(suffixes)}.csv"
            else:
                example = f"{base}.csv"
            
            example_label.config(text=f"Esempio: {example}")

        self.csv_naming_var.trace('w', update_example)  # ✅
        self.csv_prefix_var.trace('w', update_example)  # ✅
        self.csv_timestamp_var.trace('w', update_example)  # ✅
        self.csv_counter_var.trace('w', update_example)  # ✅
        update_example()
                
    def create_batch_tab(self):
        """Tab Batch (NUOVO)"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Batch")
        
        tk.Label(frame, text="Gestione Batch:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=10)
        
        self.batch_enabled_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('batch_mode_enabled', True))
        
        ttk.Checkbutton(frame, text="Abilita Batch Manager (elaborazione multipla documenti)",
                       variable=self.batch_enabled_var).pack(anchor="w", padx=20, pady=10)
        
        # Info
        info_frame = tk.LabelFrame(frame, text="Informazioni Batch", padx=10, pady=10)
        info_frame.pack(fill="x", padx=20, pady=20)
        
        info_text = """Il Batch Manager permette di elaborare multipli documenti in sequenza:

- Seleziona una cartella contenente PDF/TIFF + JSON
- Il sistema rileva automaticamente le coppie documento-metadati
- Elabora documenti uno alla volta in sequenza
- Export finale CSV con tutti i metadati (modalità configurabile)

Workflow supportati:
- JSON con "categories": split documento in categorie
- JSON flat metadati: documento unico con metadati tabellari"""
        
        tk.Label(info_frame, text=info_text, justify="left",
                font=("Arial", 9)).pack(anchor="w")

    def create_categories_tab(self):
        """Create categories management tab with dynamic JSON awareness"""
        categories_frame = ttk.Frame(self.notebook)
        self.notebook.add(categories_frame, text="Categorie")
        
        # Main container
        main_frame = ttk.Frame(categories_frame)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title and stats
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill="x", pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="Gestione Categorie", font=("Arial", 12, "bold"))
        title_label.pack(side="left")
        
        # Stats label (updated dynamically)
        self.stats_label = ttk.Label(title_frame, text="", font=("Arial", 9))
        self.stats_label.pack(side="right")
        
        # Categories list with enhanced display
        list_frame = ttk.LabelFrame(main_frame, text="Categorie Disponibili", padding=10)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create Treeview for better category display
        columns = ('name', 'source', 'usage', 'status')
        self.categories_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=12)
        
        # Configure columns
        self.categories_tree.heading('name', text='Nome Categoria')
        self.categories_tree.heading('source', text='Origine')
        self.categories_tree.heading('usage', text='Utilizzi')
        self.categories_tree.heading('status', text='Stato')
        
        self.categories_tree.column('name', width=200, anchor='w')
        self.categories_tree.column('source', width=80, anchor='center')
        self.categories_tree.column('usage', width=80, anchor='center')
        self.categories_tree.column('status', width=120, anchor='center')
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.categories_tree.yview)
        self.categories_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.categories_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        # Left side buttons
        left_buttons = ttk.Frame(buttons_frame)
        left_buttons.pack(side="left")
        
        add_btn = ttk.Button(left_buttons, text="➕ Aggiungi", command=self.add_category)
        add_btn.pack(side="left", padx=(0, 5))
        
        edit_btn = ttk.Button(left_buttons, text="✏️ Modifica", command=self.edit_category)
        edit_btn.pack(side="left", padx=5)
        
        delete_btn = ttk.Button(left_buttons, text="🗑️ Elimina", command=self.delete_category)
        delete_btn.pack(side="left", padx=5)
        
        # Right side buttons
        right_buttons = ttk.Frame(buttons_frame)
        right_buttons.pack(side="right")
        
        refresh_btn = ttk.Button(right_buttons, text="🔄 Aggiorna", command=self.refresh_categories)
        refresh_btn.pack(side="left", padx=5)
        
        cleanup_btn = ttk.Button(right_buttons, text="🧹 Pulizia", command=self.cleanup_categories)
        cleanup_btn.pack(side="left", padx=(5, 0))
        
        # Info frame for explanations
        info_frame = ttk.LabelFrame(main_frame, text="Legenda", padding=10)
        info_frame.pack(fill="x", pady=(10, 0))
        
        info_text = """🔒 Categorie JSON: Protette, derivate dal file JSON corrente (non eliminabili)
👤 Categorie Manuali: Aggiunte dall'utente (eliminabili se non utilizzate)
📊 Utilizzi: Numero di volte che la categoria è stata utilizzata"""
        
        info_label = ttk.Label(info_frame, text=info_text, font=("Arial", 9))
        info_label.pack(anchor="w")
        
        # Load categories initially
        self.refresh_categories()
        
        # Bind double-click for editing
        self.categories_tree.bind("<Double-1>", lambda e: self.edit_category())
        
    def create_advanced_tab(self):
        """Tab avanzate"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Avanzate")
        
        # NUOVO: Split documents by category
        tk.Label(frame, text="Gestione Documenti:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
        
        self.split_by_category_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('split_documents_by_category', True))
        ttk.Checkbutton(frame, text="Dividi documenti per categoria (se presente campo 'categories' in JSON)",
                       variable=self.split_by_category_var).pack(anchor="w", padx=20, pady=5)
        
        tk.Label(frame, text="Se disabilitato, crea un singolo documento con tutte le pagine",
                font=("Arial", 8), fg="gray").pack(anchor="w", padx=40, pady=(0, 10))
        
        # Separator
        ttk.Separator(frame, orient="horizontal").pack(fill="x", pady=10, padx=10)
        
        # Existing checkboxes remain below
        tk.Label(frame, text="Preferenze Generali:",
                font=("Arial", 10, "bold")).pack(anchor="w", padx=10, pady=(10, 5))
    
        # Auto-save
        self.auto_save_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('auto_save_changes', True))
        ttk.Checkbutton(frame, text="Salvataggio automatico modifiche",
                       variable=self.auto_save_var).pack(anchor="w", padx=20, pady=10)
        
        # Save layout
        self.save_layout_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('save_window_layout', True))
        ttk.Checkbutton(frame, text="Salva layout finestra",
                       variable=self.save_layout_var).pack(anchor="w", padx=20, pady=5)
        
        # Auto-fit images
        self.auto_fit_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('auto_fit_images', True))
        ttk.Checkbutton(frame, text="Adatta automaticamente immagini",
                       variable=self.auto_fit_var).pack(anchor="w", padx=20, pady=5)
        
        # Debug info
        self.debug_var = tk.BooleanVar(
            value=self.config_manager.config_data.get('show_debug_info', False))
        ttk.Checkbutton(frame, text="Mostra informazioni debug",
                       variable=self.debug_var).pack(anchor="w", padx=20, pady=5)
        
    def create_buttons(self):
        """Create bottom buttons"""
        button_frame = tk.Frame(self.dialog, height=50, bg="lightblue")  # Altezza fissa + debug
        button_frame.pack(fill="x", side="bottom", pady=10)
        button_frame.pack_propagate(False)  # ← CHIAVE: impedisce il collasso
        
        tk.Button(button_frame, text="OK", command=self.on_ok,
                 bg="lightgreen", font=("Arial", 10, "bold"),
                 width=10).pack(side="right", padx=10)
        
        tk.Button(button_frame, text="Annulla", command=self.on_cancel,
                 font=("Arial", 10), width=10).pack(side="right", padx=5)
        
    def browse_folder(self, config_key):
        """Browse for folder - starts from currently configured folder"""
        # Determina cartella iniziale basata sul config_key
        initial_dir = None
        
        if config_key == 'json_input_path':
            initial_dir = self.json_folder_var.get()
        elif config_key == 'csv_output_path':
            initial_dir = self.csv_output_var.get()
        elif config_key == 'default_input_folder':
            initial_dir = self.default_input_folder_var.get()
        elif config_key == 'default_output_folder':
            initial_dir = self.default_output_folder_var.get()
        
        # Se la cartella configurata non esiste, usa la parent directory
        if initial_dir and os.path.exists(initial_dir):
            start_dir = initial_dir
        elif initial_dir:
            # Usa la directory parent se la cartella configurata non esiste
            start_dir = os.path.dirname(initial_dir)
            if not os.path.exists(start_dir):
                start_dir = None
        else:
            start_dir = None
        
        # Apri dialog con directory iniziale
        folder = filedialog.askdirectory(initialdir=start_dir)
        
        if folder:
            if config_key == 'json_input_path':
                self.json_folder_var.set(folder)
            elif config_key == 'csv_output_path':
                self.csv_output_var.set(folder)
            elif config_key == 'default_input_folder':
                self.default_input_folder_var.set(folder)
            elif config_key == 'default_output_folder':
                self.default_output_folder_var.set(folder)
    
    def on_width_changed(self):
        """Update height proportionally when width changes"""
        if self.keep_aspect_var.get():
            # Calcola rapporto d'aspetto originale
            original_width = self.config_manager.get('thumbnail_width', 80)
            original_height = self.config_manager.get('thumbnail_height', 100)
            aspect_ratio = original_height / original_width
        
            # Applica a nuova larghezza
            new_width = self.thumb_width_var.get()
            new_height = int(new_width * aspect_ratio)
        
            # Limita altezza ai bounds
            new_height = max(80, min(250, new_height))
            self.thumb_height_var.set(new_height)
            
    def on_ok(self):
        """Save settings and close"""
        # Paths
        self.config_manager.config_data['default_input_folder'] = \
            self.default_input_folder_var.get()
        self.config_manager.config_data['default_output_folder'] = \
            self.default_output_folder_var.get()
        self.config_manager.config_data['json_folder'] = \
            self.json_folder_var.get()
        self.config_manager.config_data['use_same_folder_for_json'] = \
            self.use_input_json_var.get()
        self.config_manager.config_data['preserve_folder_structure'] = \
            self.preserve_structure_var.get()
        
        # Fonts
        self.config_manager.config_data['fonts']['document_font_name'] = \
            self.font_name_var.get()
        self.config_manager.config_data['fonts']['document_font_size'] = \
            self.font_size_var.get()
        self.config_manager.config_data['fonts']['document_font_bold'] = \
            self.font_bold_var.get()
        
        # Thumbnails
        self.config_manager.config_data['thumbnail_width'] = \
            self.thumb_width_var.get()
        self.config_manager.config_data['thumbnail_height'] = \
            self.thumb_height_var.get()
        self.config_manager.config_data['thumbnail_keep_aspect_ratio'] = \
            self.keep_aspect_var.get()
            
        # Export
        self.config_manager.config_data['export_format'] = \
            self.export_format_var.get()
        self.config_manager.config_data['jpeg_quality'] = \
            self.jpeg_quality_var.get()
        self.config_manager.config_data['file_handling_mode'] = \
            self.file_handling_var.get()
        
        # CSV
        self.config_manager.config_data['csv_mode'] = self.csv_mode_var.get()
        self.config_manager.config_data['csv_delimiter'] = self.csv_delimiter_var.get()
        self.config_manager.config_data['csv_output_path'] = self.csv_output_var.get()
        self.config_manager.config_data['csv_use_document_name'] = self.csv_use_doc_name_var.get()
        self.config_manager.config_data['csv_custom_name'] = self.csv_custom_name_var.get().strip()
        
        # Batch CSV (NUOVO)
        self.config_manager.config_data['batch_csv_location'] = self.csv_location_var.get()
        self.config_manager.config_data['batch_csv_naming'] = self.csv_naming_var.get()
        self.config_manager.config_data['batch_csv_custom_prefix'] = self.csv_prefix_var.get().strip()
        self.config_manager.config_data['batch_csv_add_timestamp'] = self.csv_timestamp_var.get()
        self.config_manager.config_data['batch_csv_add_counter'] = self.csv_counter_var.get()
        
        # Batch
        self.config_manager.config_data['batch_mode_enabled'] = self.batch_enabled_var.get()
        
        # Advanced
        self.config_manager.config_data['auto_save_changes'] = self.auto_save_var.get()
        self.config_manager.config_data['save_window_layout'] = self.save_layout_var.get()
        self.config_manager.config_data['auto_fit_images'] = self.auto_fit_var.get()
        self.config_manager.config_data['show_debug_info'] = self.debug_var.get()
        
        # Save
        self.config_manager.save_config()
        
        self.result = True
        self.dialog.destroy()
        
    def on_cancel(self):
        """Cancel and close"""
        self.result = False
        self.dialog.destroy()
        
    def refresh_categories(self):
        """Refresh categories list with enhanced information"""
        # 🛡️ PROTEZIONE ANTI-LOOP
        if hasattr(self, '_refreshing') and self._refreshing:
            print("[DEBUG] ⚠️ Refresh already in progress, skipping...")
            return
        
        try:
            self._refreshing = True  # Set flag
            print("[DEBUG] 🔄 Starting refresh_categories...")
            
            # Clear existing items
            for item in self.categories_tree.get_children():
                self.categories_tree.delete(item)
            
            # Initialize category database if not exists
            if not hasattr(self, 'category_db'):
                from config import DB_FILE
                from database.category_db import CategoryDatabase
                self.category_db = CategoryDatabase(DB_FILE)
                print("[DEBUG] CategoryDatabase initialized in settings")
            
            # Get categories with detailed info
            all_categories = self.category_db.get_all_categories()
            stats = self.category_db.get_category_stats()
            
            print(f"[DEBUG] Found {len(all_categories)} categories: {all_categories}")
            print(f"[DEBUG] Stats: {stats}")
            
            for category_name in all_categories:
                info = self.category_db.get_category_info(category_name)
                if info:
                    print(f"[DEBUG] Processing category: {category_name} - {info}")
                    
                    # Determine display values
                    source_display = "🔒 JSON" if info['source'] == 'json' else "👤 Manual"
                    status_display = "Protetto" if info['is_protected'] else "Eliminabile"
                    
                    # Add to tree
                    item_id = self.categories_tree.insert("", "end", values=(
                        f"{'🔒' if info['source'] == 'json' else '👤'} {category_name}",
                        source_display,
                        info['usage_count'],
                        status_display
                    ))
            
            # Update stats display
            self.stats_label.config(text=f"Totale: {stats['total_categories']} | JSON: {stats['json_categories']} | Manuali: {stats['manual_categories']}")
            print(f"[DEBUG] ✅ TreeView updated with {len(all_categories)} items")
            
        except Exception as e:
            print(f"Error refreshing categories: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Errore", f"Errore nel caricamento categorie: {e}")
        finally:
            self._refreshing = False  # ✅ Always reset flag
            print("[DEBUG] ✅ Refresh completed")
    
    def add_category(self):
        """Add new manual category"""
        try:
            category_name = simpledialog.askstring(
                "Nuova Categoria",
                "Inserisci il nome della nuova categoria:",
                parent=self.dialog
            )
            
            if category_name and category_name.strip():
                category_name = category_name.strip()
                
                if self.category_db.category_exists(category_name):
                    messagebox.showwarning("Attenzione", f"La categoria '{category_name}' esiste già!")
                    return
                
                if self.category_db.add_category(category_name, source='manual'):
                    messagebox.showinfo("Successo", f"Categoria '{category_name}' aggiunta con successo!")
                    self.refresh_categories()
                else:
                    messagebox.showerror("Errore", "Errore nell'aggiunta della categoria!")
        except Exception as e:
            print(f"Error adding category: {e}")
            messagebox.showerror("Errore", f"Errore nell'aggiunta categoria: {e}")
    
    def edit_category(self):
        """Edit selected category (only manual categories)"""
        try:
            selected_item = self.categories_tree.selection()
            if not selected_item:
                messagebox.showwarning("Attenzione", "Seleziona una categoria da modificare!")
                return
            
            # Get selected category name (remove emoji)
            current_name = self.categories_tree.item(selected_item[0])['values'][0]
            if current_name.startswith('🔒'):
                current_name = current_name[2:].strip()  # Remove JSON emoji
            elif current_name.startswith('👤'):
                current_name = current_name[2:].strip()  # Remove manual emoji
            
            # Check if category can be edited
            info = self.category_db.get_category_info(current_name)
            if not info or info['is_protected']:
                messagebox.showwarning("Attenzione", 
                    "Non puoi modificare categorie protette o derivate da JSON!")
                return
            
            new_name = simpledialog.askstring(
                "Modifica Categoria",
                f"Modifica il nome della categoria:",
                initialvalue=current_name,
                parent=self.dialog
            )
            
            if new_name and new_name.strip() and new_name.strip() != current_name:
                new_name = new_name.strip()
                
                if self.category_db.category_exists(new_name):
                    messagebox.showwarning("Attenzione", f"La categoria '{new_name}' esiste già!")
                    return
                
                # Add new and delete old (manual transaction)
                if (self.category_db.add_category(new_name, source='manual') and 
                    self.category_db.delete_category(current_name)):
                    messagebox.showinfo("Successo", f"Categoria rinominata in '{new_name}'!")
                    self.refresh_categories()
                else:
                    messagebox.showerror("Errore", "Errore nella modifica della categoria!")
                    
        except Exception as e:
            print(f"Error editing category: {e}")
            messagebox.showerror("Errore", f"Errore nella modifica categoria: {e}")
    
    def delete_category(self):
        """Delete selected category (only if allowed)"""
        try:
            selected_item = self.categories_tree.selection()
            if not selected_item:
                messagebox.showwarning("Attenzione", "Seleziona una categoria da eliminare!")
                return
            
            # Get selected category name (remove emoji)
            category_name = self.categories_tree.item(selected_item[0])['values'][0]
            if category_name.startswith('🔒'):
                category_name = category_name[2:].strip()  # Remove JSON emoji
            elif category_name.startswith('👤'):
                category_name = category_name[2:].strip()  # Remove manual emoji
            
            # Check if can delete
            if not self.category_db.can_delete_category(category_name):
                info = self.category_db.get_category_info(category_name)
                if info and info['is_protected']:
                    messagebox.showwarning("Attenzione", 
                        f"Non puoi eliminare '{category_name}': è una categoria protetta dal JSON corrente!")
                else:
                    messagebox.showwarning("Attenzione", 
                        f"Non puoi eliminare '{category_name}': categoria in uso o protetta!")
                return
            
            # Confirm deletion
            if messagebox.askyesno("Conferma Eliminazione", 
                                 f"Sei sicuro di voler eliminare la categoria '{category_name}'?",
                                 parent=self.dialog):
                if self.category_db.delete_category(category_name):
                    messagebox.showinfo("Successo", f"Categoria '{category_name}' eliminata con successo!")
                    self.refresh_categories()
                else:
                    messagebox.showerror("Errore", "Errore nell'eliminazione della categoria!")
                    
        except Exception as e:
            print(f"Error deleting category: {e}")
            messagebox.showerror("Errore", f"Errore nell'eliminazione categoria: {e}")
    
    def cleanup_categories(self):
        """Clean up unused manual categories"""
        print("[DEBUG] 🧹 Cleanup button pressed!")
        try:
            # Test con 0 giorni (elimina tutte le categorie manuali non utilizzate)
            if messagebox.askyesno("Pulizia Categorie", 
                                "Eliminare TUTTE le categorie manuali inutilizzate? (Test)",
                                parent=self.dialog):
                print("[DEBUG] User confirmed cleanup")
                deleted_count = self.category_db.cleanup_unused_categories(keep_days=0)
                print(f"[DEBUG] cleanup_unused_categories returned: {deleted_count}")
                
                if deleted_count > 0:
                    messagebox.showinfo("Pulizia Completata", 
                                    f"Eliminate {deleted_count} categorie inutilizzate!")
                else:
                    messagebox.showinfo("Pulizia Completata", "Nessuna categoria da eliminare!")
                
                print("[DEBUG] About to refresh categories...")
                self.refresh_categories()
                print("[DEBUG] Refresh completed")
                
        except Exception as e:
            print(f"[DEBUG] Error in cleanup_categories: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Errore", f"Errore nella pulizia categorie: {e}")
    