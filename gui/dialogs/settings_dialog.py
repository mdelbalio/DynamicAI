"""
Settings dialog for DynamicAI configuration
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Optional, Dict

class SettingsDialog:
    """Dialog for application settings and preferences"""
    
    def __init__(self, parent: tk.Widget, config_data: Dict):
        self.parent = parent
        self.config_data = config_data.copy()
        self.result: Optional[Dict] = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Impostazioni DynamicAI")
        self.dialog.geometry("700x750")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        """Create settings dialog widgets"""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title = tk.Label(main_frame, text="Impostazioni DynamicAI Editor", 
                        font=("Arial", 14, "bold"), fg="darkblue")
        title.pack(pady=(0, 20))
        
        # Create notebook for tabbed interface
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True, pady=(0, 20))
        
        # Create tabs
        self.create_paths_tab(notebook)
        self.create_documents_tab(notebook)
        self.create_export_tab(notebook)
        self.create_interface_tab(notebook)
        
        # Info frame
        self.create_info_frame(main_frame)
        
        # Buttons
        self.create_buttons(main_frame)
        
        # Update initial preview
        self.update_font_preview()

    def create_paths_tab(self, notebook):
        """Create paths configuration tab"""
        paths_frame = ttk.Frame(notebook)
        notebook.add(paths_frame, text="Percorsi")
        
        # Input folder
        input_frame = tk.LabelFrame(paths_frame, text="Cartella Input Predefinita", 
                                   font=("Arial", 10, "bold"))
        input_frame.pack(fill="x", padx=10, pady=10)
        
        self.input_folder_var = tk.StringVar(value=self.config_data.get('default_input_folder', ''))
        input_entry_frame = tk.Frame(input_frame)
        input_entry_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Entry(input_entry_frame, textvariable=self.input_folder_var, 
                font=("Arial", 9), width=50).pack(side="left", fill="x", expand=True)
        tk.Button(input_entry_frame, text="Sfoglia", 
                 command=self.browse_input_folder, bg="lightblue").pack(side="right", padx=(5, 0))
        
        # Output folder
        output_frame = tk.LabelFrame(paths_frame, text="Cartella Output Predefinita", 
                                    font=("Arial", 10, "bold"))
        output_frame.pack(fill="x", padx=10, pady=10)
        
        self.output_folder_var = tk.StringVar(value=self.config_data.get('default_output_folder', ''))
        output_entry_frame = tk.Frame(output_frame)
        output_entry_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Entry(output_entry_frame, textvariable=self.output_folder_var, 
                font=("Arial", 9), width=50).pack(side="left", fill="x", expand=True)
        tk.Button(output_entry_frame, text="Sfoglia", 
                 command=self.browse_output_folder, bg="lightblue").pack(side="right", padx=(5, 0))

    def create_documents_tab(self, notebook):
        """Create documents configuration tab"""
        doc_frame = ttk.Frame(notebook)
        notebook.add(doc_frame, text="Documenti")
        
        # Document counter settings
        counter_frame = tk.LabelFrame(doc_frame, text="Contatore Documenti", 
                                     font=("Arial", 10, "bold"))
        counter_frame.pack(fill="x", padx=10, pady=10)
        
        counter_digits_frame = tk.Frame(counter_frame)
        counter_digits_frame.pack(padx=10, pady=10)
        
        tk.Label(counter_digits_frame, text="Numero minimo di cifre:", font=("Arial", 9)).pack(side="left")
        self.counter_digits_var = tk.IntVar(value=self.config_data.get('document_counter_digits', 4))
        tk.Spinbox(counter_digits_frame, from_=1, to=6, width=5, 
                  textvariable=self.counter_digits_var).pack(side="left", padx=(5, 0))
        
        # Font settings
        font_frame = tk.LabelFrame(doc_frame, text="Impostazioni Font", 
                                  font=("Arial", 10, "bold"))
        font_frame.pack(fill="x", padx=10, pady=10)
        
        self.create_font_settings(font_frame)
        self.create_font_preview(font_frame)

    def create_font_settings(self, parent):
        """Create font configuration widgets"""
        font_name_frame = tk.Frame(parent)
        font_name_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(font_name_frame, text="Font:", font=("Arial", 9)).pack(side="left")
        self.font_name_var = tk.StringVar(value=self.config_data.get('document_font_name', 'Arial'))
        font_combo = ttk.Combobox(font_name_frame, textvariable=self.font_name_var, 
                                 values=['Arial', 'Times New Roman', 'Helvetica', 'Courier New', 'Verdana'],
                                 width=15)
        font_combo.pack(side="left", padx=(5, 15))
        
        tk.Label(font_name_frame, text="Dimensione:", font=("Arial", 9)).pack(side="left")
        self.font_size_var = tk.IntVar(value=self.config_data.get('document_font_size', 10))
        tk.Spinbox(font_name_frame, from_=6, to=16, width=5, 
                  textvariable=self.font_size_var).pack(side="left", padx=(5, 0))
        
        # Font style
        font_style_frame = tk.Frame(parent)
        font_style_frame.pack(fill="x", padx=10, pady=5)
        
        self.font_bold_var = tk.BooleanVar(value=self.config_data.get('document_font_bold', True))
        tk.Checkbutton(font_style_frame, text="Grassetto", 
                      variable=self.font_bold_var, font=("Arial", 9)).pack(side="left")

    def create_font_preview(self, parent):
        """Create font preview widget"""
        preview_frame = tk.Frame(parent)
        preview_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(preview_frame, text="Anteprima:", font=("Arial", 9)).pack(anchor="w")
        self.font_preview = tk.Label(preview_frame, text="0001 Categoria Documento", 
                                    bg="white", relief="sunken", bd=1, padx=10, pady=5,
                                    anchor="w", justify="left")
        self.font_preview.pack(fill="x", pady=(5, 0))
        
        # Bind events to update preview
        self.font_name_var.trace('w', self.update_font_preview)
        self.font_size_var.trace('w', self.update_font_preview)
        self.font_bold_var.trace('w', self.update_font_preview)
        self.counter_digits_var.trace('w', self.update_font_preview)

    def create_export_tab(self, notebook):
        """Create export configuration tab"""
        save_frame = ttk.Frame(notebook)
        notebook.add(save_frame, text="Export")
        
        # Export format settings
        export_format_frame = tk.LabelFrame(save_frame, text="Formato Export", 
                                          font=("Arial", 10, "bold"))
        export_format_frame.pack(fill="x", padx=10, pady=5)
        
        self.export_format_var = tk.StringVar(value=self.config_data.get('export_format', 'JPEG'))
        format_options = [
            ('JPEG (Pagina singola)', 'JPEG'),
            ('PDF (Pagina singola)', 'PDF_SINGLE'),
            ('PDF (Multi-pagina per documento)', 'PDF_MULTI'),
            ('TIFF (Pagina singola)', 'TIFF_SINGLE'),
            ('TIFF (Multi-pagina per documento)', 'TIFF_MULTI')
        ]
        
        for text, value in format_options:
            tk.Radiobutton(export_format_frame, text=text, variable=self.export_format_var, 
                          value=value, font=("Arial", 8)).pack(anchor="w", padx=10, pady=1)
        
        # Quality settings for JPEG
        quality_frame = tk.LabelFrame(save_frame, text="Qualità JPEG", 
                                     font=("Arial", 10, "bold"))
        quality_frame.pack(fill="x", padx=10, pady=5)
        
        quality_control_frame = tk.Frame(quality_frame)
        quality_control_frame.pack(padx=10, pady=5)
        
        tk.Label(quality_control_frame, text="Qualità (1-100):", font=("Arial", 9)).pack(side="left")
        self.jpeg_quality_var = tk.IntVar(value=self.config_data.get('jpeg_quality', 95))
        tk.Spinbox(quality_control_frame, from_=1, to=100, width=5, 
                  textvariable=self.jpeg_quality_var).pack(side="left", padx=(5, 0))
        
        # GESTIONE FILE ESISTENTI - SEZIONE COMPLETA RIPRISTINATA
        save_options_frame = tk.LabelFrame(save_frame, text="Gestione File Esistenti", 
                                          font=("Arial", 10, "bold"))
        save_options_frame.pack(fill="x", padx=10, pady=5)
        
        # Radio buttons per modalità gestione file
        self.file_handling_var = tk.StringVar(value=self.config_data.get('file_handling_mode', 'auto_rename'))
        
        tk.Label(save_options_frame, text="Quando un file esiste già:", 
                font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=(5, 3))
        
        tk.Radiobutton(save_options_frame, text="Rinomina automaticamente (es: file(1).pdf, file(2).pdf)", 
                      variable=self.file_handling_var, value="auto_rename", 
                      font=("Arial", 8)).pack(anchor="w", padx=20, pady=1)
        
        tk.Radiobutton(save_options_frame, text="Chiedi conferma prima di sovrascrivere", 
                      variable=self.file_handling_var, value="ask_overwrite", 
                      font=("Arial", 8)).pack(anchor="w", padx=20, pady=1)
        
        tk.Radiobutton(save_options_frame, text="Sovrascrivi sempre senza chiedere", 
                      variable=self.file_handling_var, value="always_overwrite", 
                      font=("Arial", 8)).pack(anchor="w", padx=20, pady=1)
        
        # Frame per opzioni backup
        backup_frame = tk.Frame(save_options_frame)
        backup_frame.pack(fill="x", padx=10, pady=(5, 3))
        
        self.create_backup_var = tk.BooleanVar(value=self.config_data.get('create_backup_on_overwrite', False))
        self.backup_checkbox = tk.Checkbutton(backup_frame, text="Crea backup (.backup) quando sovrascrivi", 
                                            variable=self.create_backup_var, font=("Arial", 8))
        self.backup_checkbox.pack(anchor="w")
        
        # Abilita/disabilita backup checkbox in base alla selezione
        def on_file_handling_change():
            if self.file_handling_var.get() in ["ask_overwrite", "always_overwrite"]:
                self.backup_checkbox.config(state="normal")
            else:
                self.backup_checkbox.config(state="disabled")
        
        self.file_handling_var.trace('w', lambda *args: on_file_handling_change())
        on_file_handling_change()  # Chiamata iniziale
        
        # Auto save checkbox
        self.auto_save_var = tk.BooleanVar(value=self.config_data.get('auto_save_changes', True))
        tk.Checkbutton(save_options_frame, text="Salva automaticamente le modifiche alla configurazione", 
                      variable=self.auto_save_var, font=("Arial", 8)).pack(anchor="w", padx=10, pady=3)

    def create_interface_tab(self, notebook):
        """Create interface configuration tab"""
        ui_frame = ttk.Frame(notebook)
        notebook.add(ui_frame, text="Interfaccia")
        
        # Layout settings
        layout_frame = tk.LabelFrame(ui_frame, text="Layout e Finestre", 
                                    font=("Arial", 10, "bold"))
        layout_frame.pack(fill="x", padx=10, pady=10)
        
        self.save_layout_var = tk.BooleanVar(value=self.config_data.get('save_window_layout', True))
        tk.Checkbutton(layout_frame, text="Salva posizione finestre e pannelli", 
                      variable=self.save_layout_var, font=("Arial", 9)).pack(anchor="w", padx=10, pady=3)
        
        self.auto_fit_var = tk.BooleanVar(value=self.config_data.get('auto_fit_images', True))
        tk.Checkbutton(layout_frame, text="Adatta automaticamente immagini alla finestra", 
                      variable=self.auto_fit_var, font=("Arial", 9)).pack(anchor="w", padx=10, pady=3)
        
        self.show_debug_var = tk.BooleanVar(value=self.config_data.get('show_debug_info', False))
        tk.Checkbutton(layout_frame, text="Mostra informazioni di debug nella console", 
                      variable=self.show_debug_var, font=("Arial", 9)).pack(anchor="w", padx=10, pady=3)
        
        # Thumbnail size settings
        thumb_frame = tk.LabelFrame(ui_frame, text="Dimensione Miniature", 
                                   font=("Arial", 10, "bold"))
        thumb_frame.pack(fill="x", padx=10, pady=10)
        
        thumb_size_frame = tk.Frame(thumb_frame)
        thumb_size_frame.pack(padx=10, pady=10)
        
        tk.Label(thumb_size_frame, text="Larghezza:", font=("Arial", 9)).pack(side="left")
        self.thumb_width_var = tk.IntVar(value=self.config_data.get('thumbnail_width', 80))
        tk.Spinbox(thumb_size_frame, from_=60, to=150, width=5, 
                  textvariable=self.thumb_width_var).pack(side="left", padx=(5, 15))
        
        tk.Label(thumb_size_frame, text="Altezza:", font=("Arial", 9)).pack(side="left")
        self.thumb_height_var = tk.IntVar(value=self.config_data.get('thumbnail_height', 100))
        tk.Spinbox(thumb_size_frame, from_=80, to=200, width=5, 
                  textvariable=self.thumb_height_var).pack(side="left", padx=(5, 0))

    def create_info_frame(self, parent):
        """Create info frame with file paths"""
        from config.settings import CONFIG_FILE, DB_FILE
        
        info_frame = tk.Frame(parent)
        info_frame.pack(fill="x", pady=(5, 0))
        
        info_text = tk.Label(info_frame, 
                            text=f"File configurazione: {CONFIG_FILE.split('/')[-1]}", 
                            font=("Arial", 7), fg="gray")
        info_text.pack()
        
        db_info_text = tk.Label(info_frame, 
                               text=f"Database categorie: {DB_FILE.split('/')[-1]}", 
                               font=("Arial", 7), fg="gray")
        db_info_text.pack()

    def create_buttons(self, parent):
        """Create dialog buttons - sempre visibili in basso"""
        button_frame = tk.Frame(parent, bg="lightgray", relief="raised", bd=1)
        button_frame.pack(fill="x", side="bottom", pady=(10, 0))
        
        tk.Button(button_frame, text="Ripristina Default", command=self.reset_defaults, 
                 bg="orange", font=("Arial", 9), width=15).pack(side="left", padx=10, pady=5)
        
        tk.Button(button_frame, text="Annulla", command=self.cancel_clicked, 
                 font=("Arial", 9), width=8).pack(side="right", padx=5, pady=5)
        
        tk.Button(button_frame, text="OK", command=self.ok_clicked, 
                 bg="lightgreen", font=("Arial", 9, "bold"), width=8).pack(side="right", padx=5, pady=5)

    def update_font_preview(self, *args):
        """Update font preview label"""
        try:
            font_name = self.font_name_var.get()
            font_size = self.font_size_var.get()
            font_bold = self.font_bold_var.get()
            digits = self.counter_digits_var.get()
            
            font_style = "bold" if font_bold else "normal"
            font_tuple = (font_name, font_size, font_style)
            
            counter_example = f"{1:0{digits}d}"
            preview_text = f"{counter_example} Categoria Documento"
            
            self.font_preview.config(text=preview_text, font=font_tuple)
        except:
            self.font_preview.config(text="0001 Categoria Documento", font=("Arial", 10))

    def browse_input_folder(self):
        """Browse for input folder"""
        folder = filedialog.askdirectory(title="Seleziona cartella input predefinita", 
                                        initialdir=self.input_folder_var.get())
        if folder:
            self.input_folder_var.set(folder)

    def browse_output_folder(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory(title="Seleziona cartella output predefinita", 
                                        initialdir=self.output_folder_var.get())
        if folder:
            self.output_folder_var.set(folder)

    def reset_defaults(self):
        """Reset all settings to defaults"""
        if messagebox.askyesno("Conferma", "Ripristinare tutte le impostazioni predefinite?"):
            from config.constants import DEFAULT_CONFIG
            
            self.input_folder_var.set("")
            self.output_folder_var.set("")
            self.counter_digits_var.set(DEFAULT_CONFIG['document_counter_digits'])
            self.font_name_var.set(DEFAULT_CONFIG['document_font_name'])
            self.font_size_var.set(DEFAULT_CONFIG['document_font_size'])
            self.font_bold_var.set(DEFAULT_CONFIG['document_font_bold'])
            self.export_format_var.set(DEFAULT_CONFIG['export_format'])
            self.jpeg_quality_var.set(DEFAULT_CONFIG['jpeg_quality'])
            self.file_handling_var.set(DEFAULT_CONFIG['file_handling_mode'])
            self.create_backup_var.set(DEFAULT_CONFIG['create_backup_on_overwrite'])
            self.auto_save_var.set(DEFAULT_CONFIG['auto_save_changes'])
            self.save_layout_var.set(DEFAULT_CONFIG['save_window_layout'])
            self.auto_fit_var.set(DEFAULT_CONFIG['auto_fit_images'])
            self.show_debug_var.set(DEFAULT_CONFIG['show_debug_info'])
            self.thumb_width_var.set(DEFAULT_CONFIG['thumbnail_width'])
            self.thumb_height_var.set(DEFAULT_CONFIG['thumbnail_height'])

    def ok_clicked(self):
        """Handle OK button click"""
        self.config_data.update({
            'default_input_folder': self.input_folder_var.get(),
            'default_output_folder': self.output_folder_var.get(),
            'document_counter_digits': self.counter_digits_var.get(),
            'document_font_name': self.font_name_var.get(),
            'document_font_size': self.font_size_var.get(),
            'document_font_bold': self.font_bold_var.get(),
            'export_format': self.export_format_var.get(),
            'jpeg_quality': self.jpeg_quality_var.get(),
            'file_handling_mode': self.file_handling_var.get(),  # AGGIUNTO
            'create_backup_on_overwrite': self.create_backup_var.get(),  # AGGIUNTO
            'auto_save_changes': self.auto_save_var.get(),  # AGGIUNTO
            'save_window_layout': self.save_layout_var.get(),
            'auto_fit_images': self.auto_fit_var.get(),
            'show_debug_info': self.show_debug_var.get(),
            'thumbnail_width': self.thumb_width_var.get(),
            'thumbnail_height': self.thumb_height_var.get()
        })
        self.result = self.config_data
        self.dialog.destroy()

    def cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.dialog.destroy()