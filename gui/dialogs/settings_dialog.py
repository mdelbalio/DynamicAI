"""
Settings Dialog for DynamicAI v3.6 (BATCH EDITION)
Aggiunte:
- Tab "Percorsi" con gestione JSON separato
- Tab "CSV" per modalità incremental/per_file
- Tab "Batch" per abilitazione batch manager
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class SettingsDialog:
    """Dialog per configurazione applicazione"""
    
    def __init__(self, parent, config_manager):
        self.parent = parent
        self.config_manager = config_manager
        self.result = None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Impostazioni DynamicAI")
        self.dialog.geometry("700x650")
        self.dialog.minsize(700, 650)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Create notebook
        self.notebook = ttk.Notebook(self.dialog)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_paths_tab()
        self.create_fonts_tab()
        self.create_thumbnails_tab()
        self.create_export_tab()
        self.create_csv_tab()
        self.create_batch_tab()
        self.create_advanced_tab()
        
        # Buttons
        self.create_buttons()
        
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
            value=self.config_manager.config_data.get('use_input_folder_for_json', True))
        ttk.Checkbutton(frame, text="Usa stessa cartella dei documenti per file JSON",
                       variable=self.use_input_json_var,
                       command=self.toggle_json_folder).grid(
            row=6, column=0, columnspan=3, sticky="w", padx=20, pady=5)
        
        # JSON folder (conditional)
        self.json_folder_label = tk.Label(frame, text="Cartella JSON Separata:")
        self.json_folder_label.grid(row=7, column=0, sticky="w", padx=20, pady=5)
        
        self.json_folder_var = tk.StringVar(
            value=self.config_manager.config_data.get('json_input_path', ''))
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
            csv_tab,
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

        csv_location_var = tk.StringVar(value=self.config.get('batch_csv_location', 'per_folder'))

        tk.Radiobutton(
            batch_csv_frame,
            text="Per Cartella (un CSV per ogni cartella output)",
            variable=csv_location_var,
            value='per_folder',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        tk.Radiobutton(
            batch_csv_frame,
            text="Globale Root (un CSV unico nella cartella output principale)",
            variable=csv_location_var,
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

        csv_naming_var = tk.StringVar(value=self.config.get('batch_csv_naming', 'auto'))

        tk.Radiobutton(
            batch_csv_frame,
            text="Auto (usa nome cartella)",
            variable=csv_naming_var,
            value='auto',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        tk.Radiobutton(
            batch_csv_frame,
            text="Nome Cartella",
            variable=csv_naming_var,
            value='folder_name',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        tk.Radiobutton(
            batch_csv_frame,
            text="Personalizzato (specifica prefisso sotto)",
            variable=csv_naming_var,
            value='custom',
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        tk.Radiobutton(
            batch_csv_frame,
            text="Timestamp (YYYYMMDD_HHMMSS)",
            variable=csv_naming_var,
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

        csv_prefix_var = tk.StringVar(value=self.config.get('batch_csv_custom_prefix', 'metadata'))
        tk.Entry(
            prefix_frame,
            textvariable=csv_prefix_var,
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

        csv_timestamp_var = tk.BooleanVar(value=self.config.get('batch_csv_add_timestamp', False))
        tk.Checkbutton(
            batch_csv_frame,
            text="Aggiungi timestamp al nome file (es: metadata_20250110_153045.csv)",
            variable=csv_timestamp_var,
            bg="white",
            font=("Arial", 9)
        ).pack(anchor="w", padx=20)

        csv_counter_var = tk.BooleanVar(value=self.config.get('batch_csv_add_counter', False))
        tk.Checkbutton(
            batch_csv_frame,
            text="Aggiungi contatore sequenziale (es: metadata_001.csv, metadata_002.csv)",
            variable=csv_counter_var,
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
            naming = csv_naming_var.get()
            prefix = csv_prefix_var.get()
            add_ts = csv_timestamp_var.get()
            add_cnt = csv_counter_var.get()
            
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

        csv_naming_var.trace('w', update_example)
        csv_prefix_var.trace('w', update_example)
        csv_timestamp_var.trace('w', update_example)
        csv_counter_var.trace('w', update_example)
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
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(fill="x", side="bottom", pady=10)
        
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
        self.config_manager.config_data['json_input_path'] = \
            self.json_folder_var.get()
        self.config_manager.config_data['use_input_folder_for_json'] = \
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