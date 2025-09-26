import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk, ImageSequence
import fitz
import sys
import sqlite3
import time

try:
    RESAMPLEFILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLEFILTER = Image.LANCZOS

# File di configurazione JSON specifico per questa applicazione
def get_config_file_path():
    if getattr(sys, 'frozen', False):
        # Se il programma è compilato (exe)
        app_dir = os.path.dirname(sys.executable)
    else:
        # Se eseguito da script Python
        app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, "DynamicAI_config.json")

def get_db_file_path():
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(app_dir, "DynamicAI_categories.db")

CONFIG_FILE = get_config_file_path()
DB_FILE = get_db_file_path()

class CategoryDatabase:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for categories"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")

    def add_category(self, category_name):
        """Add a new category or update last_used if exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO categories (name, last_used) 
                    VALUES (?, CURRENT_TIMESTAMP)
                """, (category_name,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding category: {e}")
            return False

    def get_all_categories(self):
        """Get all categories ordered by last_used desc"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM categories ORDER BY last_used DESC")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []

class CategorySelectionDialog:
    def __init__(self, parent, json_categories, db_categories, title="Seleziona Categoria"):
        self.parent = parent
        self.json_categories = set(json_categories)
        self.db_categories = set(db_categories)
        self.all_categories = sorted(self.json_categories.union(self.db_categories))
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))

        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title = tk.Label(main_frame, text="Seleziona o Crea Categoria", 
                        font=("Arial", 14, "bold"), fg="darkblue")
        title.pack(pady=(0, 20))

        # Search frame
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        tk.Label(search_frame, text="Cerca:", font=("Arial", 10)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.search_var.trace('w', self.on_search_changed)

        # Categories frame
        categories_frame = tk.LabelFrame(main_frame, text="Categorie Disponibili", 
                                        font=("Arial", 10, "bold"))
        categories_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Scrollable listbox
        list_frame = tk.Frame(categories_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")

        self.categories_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                           font=("Arial", 10), height=15)
        self.categories_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.categories_listbox.yview)

        # Populate listbox
        self.populate_listbox()

        # Legend
        legend_frame = tk.Frame(categories_frame)
        legend_frame.pack(fill="x", padx=10, pady=(0, 10))

        json_label = tk.Label(legend_frame, text="● Dal JSON corrente", 
                             fg="darkgreen", font=("Arial", 9))
        json_label.pack(anchor="w")

        db_label = tk.Label(legend_frame, text="● Dal database (usate precedentemente)", 
                           fg="darkblue", font=("Arial", 9))
        db_label.pack(anchor="w")

        # New category frame
        new_frame = tk.LabelFrame(main_frame, text="Crea Nuova Categoria", 
                                 font=("Arial", 10, "bold"))
        new_frame.pack(fill="x", pady=(0, 20))

        new_entry_frame = tk.Frame(new_frame)
        new_entry_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(new_entry_frame, text="Nome:", font=("Arial", 10)).pack(side="left")
        self.new_category_var = tk.StringVar()
        self.new_category_entry = tk.Entry(new_entry_frame, textvariable=self.new_category_var, 
                                          font=("Arial", 10))
        self.new_category_entry.pack(side="left", fill="x", expand=True, padx=(5, 10))

        tk.Button(new_entry_frame, text="Usa Nuova", command=self.use_new_category, 
                 bg="lightgreen", font=("Arial", 9)).pack(side="right")

        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x")

        tk.Button(button_frame, text="Usa Selezionata", command=self.use_selected_category, 
                 bg="lightblue", font=("Arial", 10, "bold"), width=15).pack(side="left")

        tk.Button(button_frame, text="Annulla", command=self.cancel, 
                 font=("Arial", 10), width=10).pack(side="right")

        # Bind double-click
        self.categories_listbox.bind("<Double-Button-1>", lambda e: self.use_selected_category())

        # Focus on search
        self.search_entry.focus()

    def populate_listbox(self, filter_text=""):
        """Populate listbox with categories"""
        self.categories_listbox.delete(0, tk.END)

        filtered_categories = []
        if filter_text:
            filtered_categories = [cat for cat in self.all_categories 
                                 if filter_text.lower() in cat.lower()]
        else:
            filtered_categories = self.all_categories

        for category in filtered_categories:
            self.categories_listbox.insert(tk.END, category)
            # Color code based on source
            index = self.categories_listbox.size() - 1
            if category in self.json_categories:
                self.categories_listbox.itemconfig(index, fg="darkgreen")
            else:
                self.categories_listbox.itemconfig(index, fg="darkblue")

    def on_search_changed(self, *args):
        """Handle search text change"""
        search_text = self.search_var.get()
        self.populate_listbox(search_text)

    def use_selected_category(self):
        """Use the selected category from list"""
        selection = self.categories_listbox.curselection()
        if selection:
            selected_category = self.categories_listbox.get(selection[0])
            self.result = selected_category
            self.dialog.destroy()
        else:
            messagebox.showwarning("Attenzione", "Seleziona una categoria dalla lista")

    def use_new_category(self):
        """Use the new category entered"""
        new_category = self.new_category_var.get().strip()
        if new_category:
            self.result = new_category
            self.dialog.destroy()
        else:
            messagebox.showwarning("Attenzione", "Inserisci il nome della nuova categoria")

    def cancel(self):
        """Cancel selection"""
        self.result = None
        self.dialog.destroy()

class SettingsDialog:
    def __init__(self, parent, config_data):
        self.parent = parent
        self.config_data = config_data.copy()
        self.result = None

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Impostazioni DynamicAI")
        # MODIFICATO: Rimossa dimensione fissa e impostata dimensione minima
        self.dialog.minsize(700, 600)  # Dimensione minima
        self.dialog.resizable(True, True)  # Finestra ridimensionabile
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))

        self.create_widgets()

        # AGGIUNTO: Calcola e imposta dimensione ottimale dopo creazione widget
        self.dialog.update_idletasks()
        width = max(700, self.dialog.winfo_reqwidth() + 50)
        height = max(600, self.dialog.winfo_reqheight() + 50)
        self.dialog.geometry(f"{width}x{height}")

        self.dialog.wait_window()

    def create_widgets(self):
        # MODIFICATO: Aggiunto frame principale scrollabile
        main_container = tk.Frame(self.dialog)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # AGGIUNTO: Canvas e scrollbar per contenuto scrollabile
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack canvas e scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # MODIFICATO: Contenuto ora va in scrollable_frame invece di main_frame
        content_frame = tk.Frame(scrollable_frame, padx=10, pady=10)
        content_frame.pack(fill="both", expand=True)

        # Title
        title = tk.Label(content_frame, text="Impostazioni DynamicAI Editor", 
                        font=("Arial", 14, "bold"), fg="darkblue")
        title.pack(pady=(0, 20))

        # Create notebook for tabbed interface
        notebook = ttk.Notebook(content_frame)
        notebook.pack(fill="both", expand=True, pady=(0, 20))

        # Tab 1: Percorsi
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

        # Tab 2: Configurazione Documenti
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

        font_name_frame = tk.Frame(font_frame)
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
        font_style_frame = tk.Frame(font_frame)
        font_style_frame.pack(fill="x", padx=10, pady=5)

        self.font_bold_var = tk.BooleanVar(value=self.config_data.get('document_font_bold', True))
        tk.Checkbutton(font_style_frame, text="Grassetto", 
                      variable=self.font_bold_var, font=("Arial", 9)).pack(side="left")

        # Preview
        preview_frame = tk.Frame(font_frame)
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

        # Tab 3: Export e Gestione File - MIGLIORATO
        save_frame = ttk.Frame(notebook)
        notebook.add(save_frame, text="Export")

        # Export format settings
        export_format_frame = tk.LabelFrame(save_frame, text="Formato Export", 
                                          font=("Arial", 10, "bold"))
        export_format_frame.pack(fill="x", padx=10, pady=10)

        self.export_format_var = tk.StringVar(value=self.config_data.get('export_format', 'JPEG'))
        format_options = [
            ('JPEG (Pagina singola)', 'JPEG'),
            ('PDF (Pagina singola)', 'PDF_SINGLE'),
            ('PDF (Multi-pagina per documento)', 'PDF_MULTI'),
            ('TIFF (Pagina singola)', 'TIFF_SINGLE'),
            ('TIFF (Multi-pagina per documento)', 'TIFF_MULTI')
        ]

        for i, (text, value) in enumerate(format_options):
            tk.Radiobutton(export_format_frame, text=text, variable=self.export_format_var, 
                          value=value, font=("Arial", 9)).pack(anchor="w", padx=10, pady=2)

        # Quality settings for JPEG
        quality_frame = tk.LabelFrame(save_frame, text="Qualità JPEG", 
                                     font=("Arial", 10, "bold"))
        quality_frame.pack(fill="x", padx=10, pady=10)

        quality_control_frame = tk.Frame(quality_frame)
        quality_control_frame.pack(padx=10, pady=10)

        tk.Label(quality_control_frame, text="Qualità (1-100):", font=("Arial", 9)).pack(side="left")
        self.jpeg_quality_var = tk.IntVar(value=self.config_data.get('jpeg_quality', 95))
        tk.Spinbox(quality_control_frame, from_=1, to=100, width=5, 
                  textvariable=self.jpeg_quality_var).pack(side="left", padx=(5, 0))

        # NUOVO: Gestione File Esistenti
        save_options_frame = tk.LabelFrame(save_frame, text="Gestione File Esistenti", 
                                          font=("Arial", 10, "bold"))
        save_options_frame.pack(fill="x", padx=10, pady=10)

        # Radio buttons per modalità gestione file
        self.file_handling_var = tk.StringVar(value=self.config_data.get('file_handling_mode', 'auto_rename'))

        tk.Label(save_options_frame, text="Quando un file esiste già:", 
                font=("Arial", 9, "bold")).pack(anchor="w", padx=10, pady=(10, 5))

        tk.Radiobutton(save_options_frame, text="Rinomina automaticamente (es: file(1).pdf, file(2).pdf)", 
                      variable=self.file_handling_var, value="auto_rename", 
                      font=("Arial", 9)).pack(anchor="w", padx=20, pady=2)

        tk.Radiobutton(save_options_frame, text="Chiedi conferma prima di sovrascrivere", 
                      variable=self.file_handling_var, value="ask_overwrite", 
                      font=("Arial", 9)).pack(anchor="w", padx=20, pady=2)

        tk.Radiobutton(save_options_frame, text="Sovrascrivi sempre senza chiedere", 
                      variable=self.file_handling_var, value="always_overwrite", 
                      font=("Arial", 9)).pack(anchor="w", padx=20, pady=2)

        # Frame per opzioni backup
        backup_frame = tk.Frame(save_options_frame)
        backup_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.create_backup_var = tk.BooleanVar(value=self.config_data.get('create_backup_on_overwrite', False))
        self.backup_checkbox = tk.Checkbutton(backup_frame, text="Crea backup (.backup) quando sovrascrivi", 
                                            variable=self.create_backup_var, font=("Arial", 9))
        self.backup_checkbox.pack(anchor="w")

        # Abilita/disabilita backup checkbox in base alla selezione
        def on_file_handling_change():
            if self.file_handling_var.get() in ["ask_overwrite", "always_overwrite"]:
                self.backup_checkbox.config(state="normal")
            else:
                self.backup_checkbox.config(state="disabled")

        self.file_handling_var.trace('w', lambda *args: on_file_handling_change())
        on_file_handling_change()  # Chiamata iniziale

        self.auto_save_var = tk.BooleanVar(value=self.config_data.get('auto_save_changes', True))
        tk.Checkbutton(save_options_frame, text="Salva automaticamente le modifiche alla configurazione", 
                      variable=self.auto_save_var, font=("Arial", 9)).pack(anchor="w", padx=10, pady=5)

        # Tab 4: Interfaccia
        ui_frame = ttk.Frame(notebook)
        notebook.add(ui_frame, text="Interfaccia")

        layout_frame = tk.LabelFrame(ui_frame, text="Layout e Finestre", 
                                    font=("Arial", 10, "bold"))
        layout_frame.pack(fill="x", padx=10, pady=10)

        self.save_layout_var = tk.BooleanVar(value=self.config_data.get('save_window_layout', True))
        tk.Checkbutton(layout_frame, text="Salva posizione finestre e pannelli", 
                      variable=self.save_layout_var, font=("Arial", 9)).pack(anchor="w", padx=10, pady=5)

        self.auto_fit_var = tk.BooleanVar(value=self.config_data.get('auto_fit_images', True))
        tk.Checkbutton(layout_frame, text="Adatta automaticamente immagini alla finestra", 
                      variable=self.auto_fit_var, font=("Arial", 9)).pack(anchor="w", padx=10, pady=5)

        self.show_debug_var = tk.BooleanVar(value=self.config_data.get('show_debug_info', False))
        tk.Checkbutton(layout_frame, text="Mostra informazioni di debug nella console", 
                      variable=self.show_debug_var, font=("Arial", 9)).pack(anchor="w", padx=10, pady=5)

        # Thumbnail size
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

        # Info frame
        info_frame = tk.Frame(content_frame)
        info_frame.pack(fill="x", pady=(10, 0))

        info_text = tk.Label(info_frame, 
                            text=f"File configurazione: {CONFIG_FILE}", 
                            font=("Arial", 8), fg="gray")
        info_text.pack()

        db_info_text = tk.Label(info_frame, 
                               text=f"Database categorie: {DB_FILE}", 
                               font=("Arial", 8), fg="gray")
        db_info_text.pack()

        # MODIFICATO: Buttons fissi in fondo al main_container (non scrollabili)
        button_frame = tk.Frame(main_container, bg="lightgray", relief="raised", bd=1)
        button_frame.pack(side="bottom", fill="x", pady=(10, 0))

        # Frame interno per centrare i pulsanti
        inner_button_frame = tk.Frame(button_frame, bg="lightgray")
        inner_button_frame.pack(pady=10)

        tk.Button(inner_button_frame, text="Ripristina Default", command=self.reset_defaults, 
                 bg="orange", font=("Arial", 10)).pack(side="left", padx=(0, 20))

        tk.Button(inner_button_frame, text="Annulla", command=self.cancel_clicked, 
                 font=("Arial", 10), width=8).pack(side="right", padx=(5, 0))

        tk.Button(inner_button_frame, text="OK", command=self.ok_clicked, 
                 bg="lightgreen", font=("Arial", 10, "bold"), width=8).pack(side="right")

        # Update initial preview
        self.update_font_preview()

        # AGGIUNTO: Bind mousewheel per scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        # Bind mousewheel events
        self.dialog.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)

    def update_font_preview(self, *args):
        """Update font preview label"""
        font_name = self.font_name_var.get()
        font_size = self.font_size_var.get()
        font_bold = self.font_bold_var.get()
        digits = self.counter_digits_var.get()

        font_style = "bold" if font_bold else "normal"
        font_tuple = (font_name, font_size, font_style)

        counter_example = f"{1:0{digits}d}"
        preview_text = f"{counter_example} Categoria Documento"

        try:
            self.font_preview.config(text=preview_text, font=font_tuple)
        except:
            self.font_preview.config(text=preview_text, font=("Arial", font_size, font_style))

    def browse_input_folder(self):
        folder = filedialog.askdirectory(title="Seleziona cartella input predefinita", 
                                        initialdir=self.input_folder_var.get())
        if folder:
            self.input_folder_var.set(folder)

    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Seleziona cartella output predefinita", 
                                        initialdir=self.output_folder_var.get())
        if folder:
            self.output_folder_var.set(folder)

    def reset_defaults(self):
        if messagebox.askyesno("Conferma", "Ripristinare tutte le impostazioni predefinite?"):
            self.input_folder_var.set("")
            self.output_folder_var.set("")
            self.counter_digits_var.set(4)
            self.font_name_var.set("Arial")
            self.font_size_var.set(10)
            self.font_bold_var.set(True)
            self.export_format_var.set("JPEG")
            self.jpeg_quality_var.set(95)
            self.file_handling_var.set("auto_rename")
            self.create_backup_var.set(False)
            self.auto_save_var.set(True)
            self.save_layout_var.set(True)
            self.auto_fit_var.set(True)
            self.show_debug_var.set(False)
            self.thumb_width_var.set(80)
            self.thumb_height_var.set(100)

    def ok_clicked(self):
        self.config_data.update({
            'default_input_folder': self.input_folder_var.get(),
            'default_output_folder': self.output_folder_var.get(),
            'document_counter_digits': self.counter_digits_var.get(),
            'document_font_name': self.font_name_var.get(),
            'document_font_size': self.font_size_var.get(),
            'document_font_bold': self.font_bold_var.get(),
            'export_format': self.export_format_var.get(),
            'jpeg_quality': self.jpeg_quality_var.get(),
            'file_handling_mode': self.file_handling_var.get(),  # NUOVO
            'create_backup_on_overwrite': self.create_backup_var.get(),  # MODIFICATO
            'auto_save_changes': self.auto_save_var.get(),
            'save_window_layout': self.save_layout_var.get(),
            'auto_fit_images': self.auto_fit_var.get(),
            'show_debug_info': self.show_debug_var.get(),
            'thumbnail_width': self.thumb_width_var.get(),
            'thumbnail_height': self.thumb_height_var.get()
        })
        self.result = self.config_data
        self.dialog.destroy()

    def cancel_clicked(self):
        self.result = None
        self.dialog.destroy()


class PageThumbnail:
    def __init__(self, parent, pagenum, image, categoryname, mainapp, document_group):
        self.parent = parent
        self.pagenum = pagenum
        self.image = image
        self.categoryname = categoryname
        self.mainapp = mainapp
        self.document_group = document_group
        self.isselected = False
        
        # Variabili per gestire drag vs click
        self.is_dragging = False
        self.drag_start_pos = None
        
        # Get thumbnail size from config
        thumb_width = mainapp.config_data.get('thumbnail_width', 80)
        thumb_height = mainapp.config_data.get('thumbnail_height', 100)
        self.thumbnail_imgtk = self.create_thumbnail(image, (thumb_width, thumb_height))
        
        # Main frame with enhanced selection styling
        self.frame = tk.Frame(parent, bd=2, relief="solid", bg="white")
        
        # Image Label
        self.img_label = tk.Label(self.frame, image=self.thumbnail_imgtk, bg="white", cursor="hand2")
        self.img_label.pack(padx=2, pady=2)
        
        # Page label
        self.text_label = tk.Label(self.frame, text=f"Pagina {pagenum}", font=("Arial", 8, "bold"), bg="white")
        self.text_label.pack(pady=(0,2))
        
        # Bind separati per click e drag
        self.frame.bind("<Button-1>", self.on_button_press)
        self.frame.bind("<B1-Motion>", self.on_drag_motion)
        self.frame.bind("<ButtonRelease-1>", self.on_button_release)
        
        self.img_label.bind("<Button-1>", self.on_button_press)
        self.img_label.bind("<B1-Motion>", self.on_drag_motion)
        self.img_label.bind("<ButtonRelease-1>", self.on_button_release)
        
        self.text_label.bind("<Button-1>", self.on_button_press)
        self.text_label.bind("<B1-Motion>", self.on_drag_motion)
        self.text_label.bind("<ButtonRelease-1>", self.on_button_release)
        
        # Bind hover events for visual feedback
        self.bind_hover_events(self.frame)
        self.bind_hover_events(self.img_label)
        self.bind_hover_events(self.text_label)
        
        self.drag_data = {"x":0, "y":0, "item":None}
        self.drag_window = None

    def bind_hover_events(self, widget):
        """Bind hover events for visual feedback"""
        widget.bind("<Enter>", self.on_enter)
        widget.bind("<Leave>", self.on_leave)

    def create_thumbnail(self, image, size=(80,100)):
        img_copy = image.copy()
        img_copy.thumbnail(size, RESAMPLEFILTER)
        return ImageTk.PhotoImage(img_copy)

    def on_enter(self, event):
        """Handle mouse enter - show hover effect"""
        if not self.isselected:
            self.frame.configure(bg="#E0E0E0")
            self.img_label.configure(bg="#E0E0E0")
            self.text_label.configure(bg="#E0E0E0")

    def on_leave(self, event):
        """Handle mouse leave - remove hover effect"""
        if not self.isselected:
            self.frame.configure(bg="white")
            self.img_label.configure(bg="white")
            self.text_label.configure(bg="white")

    def on_button_press(self, event):
        """Handle button press - inizia potenziale drag"""
        self.drag_start_pos = (event.x_root, event.y_root)
        self.is_dragging = False
        self.mainapp.debug_print(f"Button press on page {self.pagenum}")

    def on_drag_motion(self, event):
        """Handle drag motion - determina se è drag o click"""
        if self.drag_start_pos:
            dx = event.x_root - self.drag_start_pos[0]
            dy = event.y_root - self.drag_start_pos[1]
            distance = (dx**2 + dy**2)**0.5
            
            # Se si muove più di 5 pixel, inizia il drag
            if distance > 5 and not self.is_dragging:
                self.is_dragging = True
                self.mainapp.debug_print(f"Starting drag for page {self.pagenum}")
                self.start_drag()
                
            if self.is_dragging:
                self.continue_drag(event)

    def on_button_release(self, event):
        """Handle button release - esegue click o termina drag"""
        if self.is_dragging:
            # Era un drag, terminalo
            self.mainapp.debug_print(f"Ending drag for page {self.pagenum}")
            self.end_drag(event)
        else:
            # Era un click semplice, seleziona la miniatura
            self.mainapp.debug_print(f"Click detected on page {self.pagenum}")
            self.mainapp.select_thumbnail(self)
        
        # Reset stato
        self.is_dragging = False
        self.drag_start_pos = None

    def start_drag(self):
        """Inizia il drag"""
        self.mainapp.dragging = True
        self.mainapp.drag_item = self

    def continue_drag(self, event):
        """Continua il drag"""
        if self.mainapp.drag_preview is None:
            self.mainapp.create_drag_preview(self)
        self.mainapp.move_drag_preview(event.x_root + 20, event.y_root + 20)

    def end_drag(self, event):
        """Termina il drag"""
        self.mainapp.stop_drag(event.x_root, event.y_root)

    def select(self):
        self.isselected = True
        self.frame.configure(bg="#87CEEB", relief="raised", bd=3)
        self.img_label.configure(bg="#87CEEB")
        self.text_label.configure(bg="#87CEEB")

    def deselect(self):
        self.isselected = False
        self.frame.configure(bg="white", relief="solid", bd=2)
        self.img_label.configure(bg="white")
        self.text_label.configure(bg="white")

    def updatecategory(self, new_category):
        self.categoryname = new_category
        self.text_label.configure(text=f"Pagina {self.pagenum}")


class DocumentGroup:
    def __init__(self, parent, categoryname, mainapp, document_counter):
        self.mainapp = mainapp
        self.categoryname = categoryname
        self.document_counter = document_counter
        self.isselected = False
        
        # Main frame with colored background
        self.frame = tk.Frame(parent, bd=2, relief="ridge", bg="#f0f0f0")
        
        # Get font settings from config
        font_name = mainapp.config_data.get('document_font_name', 'Arial')
        font_size = mainapp.config_data.get('document_font_size', 10)
        font_bold = mainapp.config_data.get('document_font_bold', True)
        font_style = "bold" if font_bold else "normal"
        
        # Create header text with counter
        digits = mainapp.config_data.get('document_counter_digits', 4)
        counter_text = f"{document_counter:0{digits}d}"
        header_text = f"{counter_text} {categoryname}"
        
        # Category label con hover effect
        self.label = tk.Label(self.frame, text=header_text, 
                             font=(font_name, font_size, font_style), 
                             bg="#d0d0d0", cursor="hand2", padx=5, pady=3,
                             anchor="w", justify="left")
        self.label.pack(fill="x", padx=2, pady=2)
        
        # Bind click to category label for group selection
        self.label.bind("<Button-1>", self.on_group_click)
        # Bind per menu contestuale
        self.label.bind("<Button-3>", self.on_right_click)
        # Bind hover events per evidenziazione
        self.label.bind("<Enter>", self.on_header_enter)
        self.label.bind("<Leave>", self.on_header_leave)
        
        # Container per miniature SENZA wrapping (layout originale)
        self.pages_frame = tk.Frame(self.frame, bg="white")
        self.pages_frame.pack(fill="x", padx=5, pady=5)
        
        self.thumbnails = []
        self.pages = []

    def on_header_enter(self, event):
        """Handle mouse enter on header"""
        if not self.isselected:
            self.label.configure(bg="#e0e0e0")

    def on_header_leave(self, event):
        """Handle mouse leave on header"""
        if not self.isselected:
            self.label.configure(bg="#d0d0d0")

    def on_group_click(self, event):
        """Handle click on group header"""
        self.mainapp.select_document_group(self)

    def on_right_click(self, event):
        """Handle right click on group header"""
        self.mainapp.show_document_context_menu(self, event)

    def select_group(self):
        """Highlight the group header when selected"""
        self.isselected = True
        self.label.configure(bg="#FFD700", relief="raised", bd=2)
        self.frame.configure(bg="#FFFACD")

    def deselect_group(self):
        """Remove highlight from group header"""
        self.isselected = False
        self.label.configure(bg="#d0d0d0", relief="flat", bd=1)
        self.frame.configure(bg="#f0f0f0")

    def add_page(self, pagenum, image, position=None):
        thumbnail = PageThumbnail(self.pages_frame, pagenum, image, self.categoryname, self.mainapp, self)
        
        if position is None:
            thumbnail.frame.pack(side="left", padx=3, pady=3)
            self.thumbnails.append(thumbnail)
            if pagenum not in self.pages:
                self.pages.append(pagenum)
        else:
            self.thumbnails.insert(position, thumbnail)
            if pagenum not in self.pages:
                self.pages.insert(position, pagenum)
            self.repack_thumbnails()
        
        return thumbnail

    def repack_thumbnails(self):
        """Repack all thumbnails in the correct order"""
        for thumb in self.thumbnails:
            thumb.frame.pack_forget()
        for thumb in self.thumbnails:
            thumb.frame.pack(side="left", padx=3, pady=3)

    def remove_thumbnail(self, thumbnail):
        if thumbnail in self.thumbnails:
            index = self.thumbnails.index(thumbnail)
            self.thumbnails.remove(thumbnail)
            thumbnail.frame.pack_forget()
            if thumbnail.pagenum in self.pages:
                self.pages.remove(thumbnail.pagenum)
            return index
        return -1

    def get_drop_position(self, x_root):
        """Determine where to insert based on x coordinate"""
        if not self.thumbnails:
            return 0
            
        frame_x = self.pages_frame.winfo_rootx()
        relative_x = x_root - frame_x
        
        for i, thumb in enumerate(self.thumbnails):
            try:
                thumb_x = thumb.frame.winfo_x() + thumb.frame.winfo_width() // 2
                if relative_x < thumb_x:
                    return i
            except tk.TclError:
                continue
        
        return len(self.thumbnails)

    def update_category_name(self, new_name):
        """Update the category name display"""
        self.categoryname = new_name
        
        # Get font settings from config
        font_name = self.mainapp.config_data.get('document_font_name', 'Arial')
        font_size = self.mainapp.config_data.get('document_font_size', 10)
        font_bold = self.mainapp.config_data.get('document_font_bold', True)
        font_style = "bold" if font_bold else "normal"
        
        # Update header text with counter
        digits = self.mainapp.config_data.get('document_counter_digits', 4)
        counter_text = f"{self.document_counter:0{digits}d}"
        header_text = f"{counter_text} {new_name}"
        
        # Update with LEFT alignment
        self.label.configure(text=header_text, font=(font_name, font_size, font_style),
                           anchor="w", justify="left")
        
        # Update all thumbnails in this group
        for thumb in self.thumbnails:
            thumb.categoryname = new_name

    def update_document_counter(self, new_counter):
        """Update document counter"""
        self.document_counter = new_counter
        
        # Get font settings from config
        font_name = self.mainapp.config_data.get('document_font_name', 'Arial')
        font_size = self.mainapp.config_data.get('document_font_size', 10)
        font_bold = self.mainapp.config_data.get('document_font_bold', True)
        font_style = "bold" if font_bold else "normal"
        
        # Update header text with new counter
        digits = self.mainapp.config_data.get('document_counter_digits', 4)
        counter_text = f"{new_counter:0{digits}d}"
        header_text = f"{counter_text} {self.categoryname}"
        
        # Update with LEFT alignment
        self.label.configure(text=header_text, font=(font_name, font_size, font_style),
                           anchor="w", justify="left")

    def is_empty(self):
        """Check if document group has no thumbnails"""
        return len(self.thumbnails) == 0

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def destroy(self):
        for thumb in self.thumbnails:
            thumb.frame.destroy()
        self.frame.destroy()


class AIDOXAApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DynamicAI - Editor Lineare Avanzato")
        
        # Initialize configuration and database
        self.config_data = self.load_config()
        self.category_db = CategoryDatabase(DB_FILE)
        
        # Set window geometry from config
        window_settings = self.config_data.get('window_settings', {})
        geometry = window_settings.get('geometry', '1400x800+100+50')
        self.geometry(geometry)
        
        # Restore window state
        state = window_settings.get('state', 'normal')
        if state == 'zoomed':
            self.state('zoomed')
        
        # Initialize variables
        self.documentgroups = []
        self.documentloader = None
        self.selected_thumbnail = None
        self.selected_group = None
        self.dragging = False
        self.drag_preview = None
        self.drag_item = None
        self.updating_ui = False
        self.current_image = None
        self.zoom_factor = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.all_categories = set()
        self.zoom_rect_start = None
        self.zoom_rect_end = None
        self.zoom_rect_id = None
        self.zoom_area_mode = False
        self.current_document_name = ""
        
        self.create_menu()
        self.create_widgets()
        
        # Bind events for saving configuration
        if self.config_data.get('save_window_layout', True):
            self.bind('<Configure>', self.on_window_configure)
            self.bind_all('<B1-Motion>', self.on_paned_motion)
            self.bind_all('<ButtonRelease-1>', self.on_paned_release)
        
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bind hover events for center panel
        self.bind_center_hover_events()
        
        # Schedule restoration of paned window positions
        self.after(200, self.restore_paned_positions)

    def bind_center_hover_events(self):
        """Bind hover events to center panel for image preview feedback"""
        def on_center_enter(event):
            if self.current_image:
                self.image_canvas.configure(bg="#1a1a1a")
                
        def on_center_leave(event):
            if self.current_image:
                self.image_canvas.configure(bg="black")
                
        self.image_canvas.bind("<Enter>", on_center_enter)
        self.image_canvas.bind("<Leave>", on_center_leave)

    def debug_print(self, message):
        """Print debug messages only if enabled in config"""
        if self.config_data.get('show_debug_info', False):
            print(f"[DEBUG] {message}")

    def show_document_context_menu(self, document_group, event):
        """Show context menu for document group"""
        context_menu = tk.Menu(self, tearoff=0)
        
        # Opzioni del menu
        context_menu.add_command(label="Nuovo documento prima", 
                               command=lambda: self.create_new_document(document_group, "before"))
        context_menu.add_command(label="Nuovo documento dopo", 
                               command=lambda: self.create_new_document(document_group, "after"))
        context_menu.add_separator()
        
        # Solo se il documento è vuoto
        if document_group.is_empty():
            context_menu.add_command(label="Elimina documento vuoto", 
                                   command=lambda: self.delete_empty_document(document_group))
        else:
            context_menu.add_command(label="Elimina documento vuoto", state="disabled")
        
        try:
            context_menu.post(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()

    def create_new_document(self, reference_document, position):
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
            
            # Trova l'indice del documento di riferimento
            ref_index = self.documentgroups.index(reference_document)
            
            if position == "after":
                new_index = ref_index + 1
            else:  # before
                new_index = ref_index
            
            # Crea nuovo documento
            new_counter = self.get_next_counter_for_position(new_index)
            new_group = DocumentGroup(self.content_frame, selected_category, self, new_counter)
            
            # Inserisci nella lista
            self.documentgroups.insert(new_index, new_group)
            
            # Rinumera tutti i documenti
            self.renumber_documents()
            
            # Riorganizza UI
            self.repack_all_documents()
            
            # Aggiorna categorie se nuova
            if selected_category not in self.all_categories:
                self.all_categories.add(selected_category)
                self.update_category_combo()
            
            self.debug_print(f"Created new document: {selected_category} at position {new_index}")

    def delete_empty_document(self, document_group):
        """Delete empty document group"""
        if not document_group.is_empty():
            messagebox.showwarning("Attenzione", "Il documento contiene pagine e non può essere eliminato")
            return
        
        doc_name = f"{document_group.document_counter:04d} {document_group.categoryname}"
        if messagebox.askyesno("Conferma Eliminazione", 
                             f"Eliminare il documento vuoto:\n{doc_name}?"):
            
            # Rimuovi dalla lista
            if document_group in self.documentgroups:
                self.documentgroups.remove(document_group)
            
            # Distruggi widget
            document_group.destroy()
            
            # Rinumera documenti rimanenti
            self.renumber_documents()
            
            # Riorganizza UI
            self.repack_all_documents()
            
            # Reset selezioni se necessario
            if self.selected_group == document_group:
                self.selected_group = None
                self.selected_thumbnail = None
                self.selection_info.config(text="Nessuna selezione")
                self.page_info_label.config(text="")
            
            self.debug_print(f"Deleted empty document: {doc_name}")

    def get_next_counter_for_position(self, position):
        """Get appropriate counter for new document at position"""
        if position == 0:
            return 1
        elif position >= len(self.documentgroups):
            return len(self.documentgroups) + 1
        else:
            # Inserimento in mezzo, il contatore verrà aggiornato dalla rinumerazione
            return position + 1

    def renumber_documents(self):
        """Renumber all document counters sequentially"""
        for i, group in enumerate(self.documentgroups, 1):
            group.update_document_counter(i)

    def repack_all_documents(self):
        """Repack all document groups in UI"""
        for group in self.documentgroups:
            group.frame.pack_forget()
        
        for group in self.documentgroups:
            group.pack(pady=5, fill="x", padx=5)

    def update_category_combo(self):
        """Update category combo with all available categories"""
        json_categories = list(self.all_categories)
        db_categories = self.category_db.get_all_categories()
        all_cats = sorted(set(json_categories + db_categories))
        self.category_combo['values'] = all_cats

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
        help_menu.add_command(label="Istruzioni", command=self.show_help)
        help_menu.add_command(label="Informazioni", command=self.show_about)
        
        # Bind keyboard shortcuts
        self.bind_all('<Control-r>', lambda e: self.refresh_document_list())
        self.bind_all('<Control-e>', lambda e: self.complete_sequence_export())
        self.bind_all('<Control-q>', lambda e: self.on_closing())

    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self, self.config_data)
        if dialog.result:
            old_thumb_size = (self.config_data.get('thumbnail_width', 80), 
                            self.config_data.get('thumbnail_height', 100))
            old_font_settings = (
                self.config_data.get('document_font_name', 'Arial'),
                self.config_data.get('document_font_size', 10),
                self.config_data.get('document_font_bold', True),
                self.config_data.get('document_counter_digits', 4)
            )
            
            self.config_data.update(dialog.result)
            self.save_config()
            
            new_thumb_size = (self.config_data.get('thumbnail_width', 80), 
                            self.config_data.get('thumbnail_height', 100))
            new_font_settings = (
                self.config_data.get('document_font_name', 'Arial'),
                self.config_data.get('document_font_size', 10),
                self.config_data.get('document_font_bold', True),
                self.config_data.get('document_counter_digits', 4)
            )
            
            # Refresh if settings changed
            if old_thumb_size != new_thumb_size:
                self.refresh_thumbnails()
            
            if old_font_settings != new_font_settings:
                self.refresh_document_headers()
                
            messagebox.showinfo("Impostazioni", "Impostazioni salvate con successo!")

    def refresh_thumbnails(self):
        """Refresh all thumbnails with new size settings"""
        if not self.documentgroups:
            return
            
        thumb_width = self.config_data.get('thumbnail_width', 80)
        thumb_height = self.config_data.get('thumbnail_height', 100)
        
        for group in self.documentgroups:
            for thumbnail in group.thumbnails:
                thumbnail.thumbnail_imgtk = thumbnail.create_thumbnail(
                    thumbnail.image, (thumb_width, thumb_height))
                thumbnail.img_label.configure(image=thumbnail.thumbnail_imgtk)

    def refresh_document_headers(self):
        """Refresh all document headers with new font settings"""
        if not self.documentgroups:
            return
        
        font_name = self.config_data.get('document_font_name', 'Arial')
        font_size = self.config_data.get('document_font_size', 10)
        font_bold = self.config_data.get('document_font_bold', True)
        font_style = "bold" if font_bold else "normal"
        digits = self.config_data.get('document_counter_digits', 4)
        
        for group in self.documentgroups:
            counter_text = f"{group.document_counter:0{digits}d}"
            header_text = f"{counter_text} {group.categoryname}"
            group.label.configure(text=header_text, font=(font_name, font_size, font_style),
                                anchor="w", justify="left")

    def reset_layout(self):
        """Reset window layout to default"""
        if messagebox.askyesno("Conferma", "Ripristinare il layout predefinito della finestra?"):
            self.geometry("1400x800+100+50")
            if hasattr(self, 'main_paned'):
                # Reset per tre pannelli
                self.main_paned.sash_place(0, 400, 0)   # Separatore sinistra-centro
                self.main_paned.sash_place(1, 1100, 0)  # Separatore centro-destra
            self.save_config()

    def show_help(self):
        """Show help dialog"""
        help_text = """ISTRUZIONI OPERATIVE DynamicAI:

CARICAMENTO DOCUMENTI:
• Configura cartelle input/output nelle Preferenze
• Usa "Aggiorna Lista (Preview)" per caricare automaticamente
• I documenti vengono caricati dalla cartella input configurata

CONFIGURAZIONE DOCUMENTI:
• Contatore documenti con numero di cifre personalizzabile
• Font e dimensione personalizzabili per le intestazioni
• Formato intestazione: [NNNN] Categoria (es: 0001 Documentazione)
• Allineamento testo a sinistra
• Hover su intestazione per evidenziazione

SELEZIONE:
• Click su miniatura: seleziona pagina e documento
• Click su intestazione documento: seleziona intero documento
• Hover con mouse: evidenziazione automatica
• Elementi selezionati sono evidenziati in blu/oro

DRAG & DROP:
• Trascina miniature per spostarle tra documenti
• Trascina per riordinare dentro stesso documento
• Il sistema distingue automaticamente tra click e drag
• L'anteprima gialla segue il mouse durante il trascinamento

ZOOM IMMAGINE:
• Zoom +/- : Ingrandisce/rimpicciolisce l'immagine
• Fit: Adatta immagine alla finestra centrale
• Click singolo su immagine: torna al fit automatico
• Zoom Area: Seleziona rettangolo con il mouse per zoom
• Hover su immagine: sfondo più scuro per feedback

PANNELLI INDIPENDENTI:
• Trascina il separatore sinistro per ridimensionare pannello sinistra/centro
• Trascina il separatore destro per ridimensionare pannello centro/destra
• I due separatori sono completamente indipendenti
• Impostazioni salvate automaticamente

GESTIONE DOCUMENTI:
• Tasto destro su intestazione: menu contestuale
• Crea nuovo documento: popup con categorie esistenti + nuove
• Database categorie: salva categorie personali tra sessioni
• Elimina documenti vuoti (senza pagine)
• Rinumerazione automatica della sequenza

GESTIONE CATEGORIE:
• Database SQLite locale per categorie personali
• Colori diversi: verde (da JSON), blu (da database)
• Ricerca categorie nel popup di selezione
• Combobox modificabile nel pannello destro
• Salvataggio automatico di nuove categorie

CAMBIO CATEGORIA:
• Seleziona documento (intestazione o miniatura)
• Combobox modificabile: categorie esistenti + crea nuove
• Salvataggio automatico nel database

GESTIONE FILE ESISTENTI (NUOVO):
• Rinomina automatica: file.pdf → file(1).pdf → file(2).pdf
• Chiedi conferma: popup prima di sovrascrivere
• Sovrascrivi sempre: sovrascrive senza chiedere
• Backup opzionale: crea file.backup prima di sovrascrivere

EXPORT MIGLIORATO:
• JPEG: file singoli per ogni pagina
• PDF Singolo: file PDF per ogni pagina
• PDF Multi-pagina: un PDF per ogni documento
• TIFF Singolo: file TIFF per ogni pagina
• TIFF Multi-pagina: un TIFF per ogni documento
• Qualità JPEG configurabile
• Gestione intelligente file esistenti

SCORCIATOIE:
• Ctrl+R: Aggiorna Lista
• Ctrl+E: Completa Sequenza / Export
• Ctrl+Q: Esci"""
        
        help_window = tk.Toplevel(self)
        help_window.title("Aiuto DynamicAI")
        help_window.geometry("750x950")
        help_window.transient(self)
        
        text_widget = tk.Text(help_window, wrap=tk.WORD, padx=20, pady=20)
        text_widget.insert("1.0", help_text)
        text_widget.config(state=tk.DISABLED)
        text_widget.pack(fill="both", expand=True)
        
        tk.Button(help_window, text="Chiudi", command=help_window.destroy, 
                 bg="lightblue").pack(pady=10)

    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("Informazioni", 
                           f"DynamicAI - Editor Lineare Avanzato\n\n"
                           f"File di configurazione:\n{CONFIG_FILE}\n\n"
                           f"Database categorie:\n{DB_FILE}\n\n"
                           f"Versione: 3.3\n"
                           f"Sviluppato con Python e Tkinter\n\n"
                           f"Nuove Funzionalità v3.3:\n"
                           f"• Gestione intelligente file esistenti\n"
                           f"• Rinominazione automatica stile Windows\n"
                           f"• Modalità backup migliorata\n"
                           f"• Tre opzioni per file duplicati\n"
                           f"• Sistema di numerazione (1), (2), (3)...\n"
                           f"• Controllo avanzato sovrascritture")

    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            'window_settings': {
                'geometry': '1400x800+100+50',
                'state': 'normal'
            },
            'panel_settings': {
                'left_center_position': 400,
                'center_right_position': 1100
            },
            'default_input_folder': '',
            'default_output_folder': '',
            'document_counter_digits': 4,
            'document_font_name': 'Arial',
            'document_font_size': 10,
            'document_font_bold': True,
            'export_format': 'JPEG',
            'jpeg_quality': 95,
            'file_handling_mode': 'auto_rename',  # NUOVO
            'create_backup_on_overwrite': False,  # MODIFICATO
            'auto_save_changes': True,
            'save_window_layout': True,
            'auto_fit_images': True,
            'show_debug_info': False,
            'thumbnail_width': 80,
            'thumbnail_height': 100,
            'last_folder': '',
            'application_info': {
                'name': 'DynamicAI Editor',
                'version': '3.3',
                'created': '2025'
            }
        }
        
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge with default config to ensure all keys exist
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict) and isinstance(config[key], dict):
                        for subkey, subvalue in value.items():
                            if subkey not in config[key]:
                                config[key][subkey] = subvalue
                return config
            else:
                self.save_config_data(default_config)
                return default_config
        except Exception as e:
            print(f"Error loading config: {e}")
            return default_config

    def save_config_data(self, config_data):
        """Save configuration data to JSON file"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            self.debug_print(f"Configuration saved to: {CONFIG_FILE}")
        except Exception as e:
            print(f"Error saving config: {e}")

    def save_config(self):
        """Save current configuration to JSON file"""
        try:
            # Update window settings
            if self.config_data.get('save_window_layout', True):
                self.config_data['window_settings']['geometry'] = self.geometry()
                self.config_data['window_settings']['state'] = self.state()
                
                # Salva le posizioni di entrambi i separatori del main_paned
                try:
                    if hasattr(self, 'main_paned'):
                        # Primo separatore (tra sinistra e centro)
                        left_center_pos = self.main_paned.sash_coord(0)[0]
                        self.config_data['panel_settings']['left_center_position'] = left_center_pos
                        self.debug_print(f"Saving left-center position: {left_center_pos}")
                        
                        # Secondo separatore (tra centro e destra)
                        center_right_pos = self.main_paned.sash_coord(1)[0]
                        self.config_data['panel_settings']['center_right_position'] = center_right_pos
                        self.debug_print(f"Saving center-right position: {center_right_pos}")
                        
                except Exception as e:
                    print(f"Error getting paned positions: {e}")
            
            self.save_config_data(self.config_data)
            
        except Exception as e:
            print(f"Error saving config: {e}")

    def on_window_configure(self, event):
        """Handle window resize/move events"""
        if event.widget == self and self.config_data.get('save_window_layout', True):
            if hasattr(self, '_save_config_after_id'):
                self.after_cancel(self._save_config_after_id)
            self._save_config_after_id = self.after(2000, self.save_config)

    def on_paned_motion(self, event):
        """Handle paned window motion during drag"""
        if hasattr(self, '_is_paned_dragging'):
            self._is_paned_dragging = True

    def on_paned_release(self, event):
        """Handle paned window sash release"""
        if self.config_data.get('save_window_layout', True):
            self.after(100, self.save_config)

    def on_closing(self):
        """Handle application closing"""
        self.debug_print("Application closing, saving configuration...")
        if self.config_data.get('auto_save_changes', True):
            self.save_config()
        self.destroy()

    def restore_paned_positions(self):
        """Restore paned window positions from config"""
        try:
            panel_settings = self.config_data.get('panel_settings', {})
            
            # Ripristina le posizioni di entrambi i separatori
            left_center_pos = panel_settings.get('left_center_position', 400)
            if hasattr(self, 'main_paned') and left_center_pos > 50:
                self.main_paned.sash_place(0, left_center_pos, 0)
                self.debug_print(f"Restored left-center position: {left_center_pos}")
            
            center_right_pos = panel_settings.get('center_right_position', 1100)
            if hasattr(self, 'main_paned') and center_right_pos > left_center_pos + 100:
                self.main_paned.sash_place(1, center_right_pos, 0)
                self.debug_print(f"Restored center-right position: {center_right_pos}")
                
        except Exception as e:
            print(f"Error restoring paned positions: {e}")

    def create_widgets(self):
        # Singolo PanedWindow orizzontale con tre pannelli indipendenti
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, 
                                        sashrelief=tk.RAISED, sashwidth=4, sashpad=2,
                                        bg="gray")
        self.main_paned.pack(fill="both", expand=True, padx=2, pady=2)

        # Left panel for documents and thumbnails
        self.left_panel = tk.Frame(self.main_paned, bg="lightgray", bd=1, relief="solid")
        self.main_paned.add(self.left_panel, width=400, minsize=250, sticky="nsew")

        # Center panel direttamente nel main_paned
        self.center_panel = tk.Frame(self.main_paned, bg="black", bd=1, relief="solid")
        self.main_paned.add(self.center_panel, width=700, minsize=300, sticky="nsew")

        # Right panel direttamente nel main_paned
        self.right_panel = tk.Frame(self.main_paned, bg="lightgray", bd=1, relief="solid")
        self.main_paned.add(self.right_panel, width=300, minsize=200, sticky="nsew")

        self.setup_left_panel()
        self.setup_center_panel()
        self.setup_right_panel()

    def setup_left_panel(self):
        # Header for left panel
        header_left = tk.Label(self.left_panel, text="Documenti e Miniature", 
                              font=("Arial", 12, "bold"), bg="lightgray")
        header_left.pack(pady=10)

        # Action buttons - vertically stacked
        button_frame = tk.Frame(self.left_panel, bg="lightgray")
        button_frame.pack(pady=5)
        
        btn_refresh = tk.Button(button_frame, text="Aggiorna Lista (Preview)", command=self.refresh_document_list, 
                               bg="lightblue", font=("Arial", 10, "bold"), width=25)
        btn_refresh.pack(pady=2)

        btn_export = tk.Button(button_frame, text="Completa Sequenza / Export", command=self.complete_sequence_export, 
                              bg="lightgreen", font=("Arial", 10, "bold"), width=25)
        btn_export.pack(pady=2)

        # Scroll frame for documents
        self.scrollframe = tk.Frame(self.left_panel, bg="lightgray")
        self.scrollframe.pack(fill="both", expand=True, padx=5, pady=5)

        self.vscrollbar = tk.Scrollbar(self.scrollframe, orient=tk.VERTICAL)
        self.vscrollbar.pack(side="right", fill="y")

        self.canvas = tk.Canvas(self.scrollframe, yscrollcommand=self.vscrollbar.set, bg="white")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.vscrollbar.config(command=self.canvas.yview)

        self.content_frame = tk.Frame(self.canvas, bg="white")
        self.canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.content_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        
        # Bind rotellina mouse per scroll verticale
        def on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel to canvas and its children
        self.canvas.bind("<MouseWheel>", on_mousewheel)
        self.content_frame.bind("<MouseWheel>", on_mousewheel)
        
        # For Linux
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))

    def setup_center_panel(self):
        # Image display area
        self.image_canvas = tk.Canvas(self.center_panel, bg="black", cursor="cross")
        self.image_canvas.pack(fill="both", expand=True, padx=2, pady=2)

        # Zoom controls at bottom
        zoom_frame = tk.Frame(self.center_panel, bg="darkgray", height=50)
        zoom_frame.pack(side="bottom", fill="x", padx=2, pady=2)
        zoom_frame.pack_propagate(False)

        tk.Button(zoom_frame, text="Zoom +", command=self.zoom_in, bg="orange", font=("Arial", 9)).pack(side="left", padx=2)
        tk.Button(zoom_frame, text="Zoom -", command=self.zoom_out, bg="orange", font=("Arial", 9)).pack(side="left", padx=2)
        tk.Button(zoom_frame, text="Fit", command=self.zoom_fit, bg="yellow", font=("Arial", 9)).pack(side="left", padx=2)
        tk.Button(zoom_frame, text="Zoom Area", command=self.toggle_zoom_area, bg="lightgreen", font=("Arial", 9)).pack(side="left", padx=2)

        # Status label
        self.zoom_status = tk.Label(zoom_frame, text="", bg="darkgray", fg="white", font=("Arial", 8))
        self.zoom_status.pack(side="right", padx=10)
        
        # Bind events to image canvas
        self.image_canvas.bind("<Button-1>", self.on_image_click)
        self.image_canvas.bind("<ButtonPress-1>", self.on_zoom_rect_start)
        self.image_canvas.bind("<B1-Motion>", self.on_zoom_rect_drag)
        self.image_canvas.bind("<ButtonRelease-1>", self.on_zoom_rect_end)
        self.image_canvas.bind("<Configure>", self.on_canvas_resize)

    def setup_right_panel(self):
        # Header
        header_right = tk.Label(self.right_panel, text="Controlli e Dettagli", 
                               font=("Arial", 12, "bold"), bg="lightgray")
        header_right.pack(pady=10)

        # Selection info
        self.selection_info = tk.Label(self.right_panel, text="Nessuna selezione", 
                                      font=("Arial", 10, "bold"), bg="lightgray", fg="darkblue")
        self.selection_info.pack(pady=5)

        # Category selection frame - MIGLIORATO
        cat_frame = tk.Frame(self.right_panel, bg="lightgray", relief="ridge", bd=2)
        cat_frame.pack(fill="x", padx=10, pady=10)

        tk.Label(cat_frame, text="Categoria Documento:", font=("Arial", 10, "bold"), bg="lightgray").pack(anchor="w", padx=5, pady=2)
        
        # Frame per combobox + pulsante
        combo_frame = tk.Frame(cat_frame, bg="lightgray")
        combo_frame.pack(fill="x", padx=5, pady=5)
        
        self.category_var = tk.StringVar()
        # Combobox modificabile (non readonly)
        self.category_combo = ttk.Combobox(combo_frame, textvariable=self.category_var, 
                                          font=("Arial", 9))
        self.category_combo.pack(side="left", fill="x", expand=True)
        
        # Pulsante per salvare nuova categoria
        save_cat_btn = tk.Button(combo_frame, text="Salva", command=self.save_new_category, 
                                bg="lightgreen", font=("Arial", 8), width=6)
        save_cat_btn.pack(side="right", padx=(5, 0))
        
        # Bind eventi
        self.category_combo.bind("<<ComboboxSelected>>", self.on_category_changed)
        self.category_combo.bind("<Return>", self.on_category_enter)

        # Page info
        self.page_info_label = tk.Label(self.right_panel, text="", 
                                       font=("Arial", 10), bg="lightgray")
        self.page_info_label.pack(pady=10)

        # Instructions text area
        instructions_label = tk.Label(self.right_panel, text="Pannello Informazioni:", 
                                     font=("Arial", 10, "bold"), bg="lightgray")
        instructions_label.pack(pady=(20, 5))

        self.instructions_text = ScrolledText(self.right_panel, height=15, width=35)
        self.instructions_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Default instructions
        self.update_instructions("Configura le cartelle input/output nelle Preferenze e usa 'Aggiorna Lista (Preview)' per iniziare.\n\nUsa il menu 'Aiuto > Istruzioni' per vedere le funzionalità complete.")

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

    def on_category_enter(self, event):
        """Handle Enter key in category combo"""
        self.save_new_category()

    def on_canvas_resize(self, event):
        """Handle canvas resize to update image display"""
        if self.current_image and hasattr(self, 'auto_fit_on_resize') and self.config_data.get('auto_fit_images', True):
            self.after_idle(self.update_image_display)

    def update_instructions(self, text):
        self.instructions_text.delete("1.0", tk.END)
        self.instructions_text.insert(tk.END, text)

    def refresh_document_list(self):
        """Load document from configured input folder"""
        input_folder = self.config_data.get('default_input_folder', '')
        
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
            
            # Get export format for display
            export_format = self.config_data.get('export_format', 'JPEG')
            format_display = {
                'JPEG': 'JPEG',
                'PDF_SINGLE': 'PDF (pagina singola)',
                'PDF_MULTI': 'PDF (multipagina per documento)',
                'TIFF_SINGLE': 'TIFF (pagina singola)',
                'TIFF_MULTI': 'TIFF (multipagina per documento)'
            }.get(export_format, export_format)
            
            # Get file handling mode
            file_handling_mode = self.config_data.get('file_handling_mode', 'auto_rename')
            file_handling_display = {
                'auto_rename': 'Rinomina automaticamente',
                'ask_overwrite': 'Chiedi conferma',
                'always_overwrite': 'Sovrascrivi sempre'
            }.get(file_handling_mode, file_handling_mode)
            
            # Count database categories
            db_categories_count = len(self.category_db.get_all_categories())
            
            instructions = f"""DOCUMENTO CARICATO:

File JSON: {os.path.basename(json_file)}
Documento: {os.path.basename(doc_file)}
Cartella Input: {input_folder}
Categorie JSON: {len(self.all_categories)}
Categorie Database: {db_categories_count}
Documenti: {len(self.documentgroups)}
Pagine totali: {self.documentloader.totalpages if self.documentloader else 0}

CONFIGURAZIONE DOCUMENTI:
Cifre contatore: {self.config_data.get('document_counter_digits', 4)}
Font: {self.config_data.get('document_font_name', 'Arial')} {self.config_data.get('document_font_size', 10)}pt
Allineamento: Sinistra

EXPORT CONFIGURATO:
Formato: {format_display}
Qualità JPEG: {self.config_data.get('jpeg_quality', 95)}%
File esistenti: {file_handling_display}
Backup: {'Abilitato' if self.config_data.get('create_backup_on_overwrite', False) else 'Disabilitato'}

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
• Drag miniature: riorganizza tra documenti
• Click intestazioni: seleziona intero documento
• Tasto destro su intestazioni: menu con categorie
• Combobox categoria: modifica e salva nuove
• Click su immagine centrale: zoom fit
• Hover su elementi per feedback visivo
• Export intelligente con gestione duplicati

EXPORT:
Nome base file: {self.current_document_name}
Usa il menu 'Aiuto > Istruzioni' per dettagli completi.
            """
            
            self.update_instructions(instructions)
            self.debug_print(f"Document loaded: {len(categories)} categories, {len(self.documentgroups)} documents, {self.documentloader.totalpages if self.documentloader else 0} pages")
            
        except Exception as e:
            messagebox.showerror("Errore", f"Errore nel caricamento: {str(e)}")

    def complete_sequence_export(self):
        """Export images to configured output folder with new file handling - MIGLIORATO"""
        if not self.documentgroups:
            messagebox.showwarning("Attenzione", "Nessun documento caricato")
            return

        output_folder = self.config_data.get('default_output_folder', '')
        
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
            export_format = self.config_data.get('export_format', 'JPEG')
            jpeg_quality = self.config_data.get('jpeg_quality', 95)
            
            # Progress dialog
            progress_window = tk.Toplevel(self)
            progress_window.title("Export in corso...")
            progress_window.geometry("450x150")
            progress_window.transient(self)
            progress_window.grab_set()
            
            progress_label = tk.Label(progress_window, text=f"Esportazione in formato {export_format}...")
            progress_label.pack(pady=20)
            
            progress_var = tk.StringVar()
            progress_info = tk.Label(progress_window, textvariable=progress_var)
            progress_info.pack(pady=10)
            
            progress_window.update()
            
            exported_files = []
            
            if export_format == 'JPEG':
                exported_files = self.export_as_jpeg(output_folder, jpeg_quality, progress_var, progress_window)
            elif export_format == 'PDF_SINGLE':
                exported_files = self.export_as_pdf_single(output_folder, progress_var, progress_window)
            elif export_format == 'PDF_MULTI':
                exported_files = self.export_as_pdf_multi_per_document(output_folder, progress_var, progress_window)
            elif export_format == 'TIFF_SINGLE':
                exported_files = self.export_as_tiff_single(output_folder, progress_var, progress_window)
            elif export_format == 'TIFF_MULTI':
                exported_files = self.export_as_tiff_multi_per_document(output_folder, progress_var, progress_window)
            
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
            self.config_data['last_folder'] = output_folder
            if self.config_data.get('auto_save_changes', True):
                self.save_config()
                
            self.debug_print(f"Exported {len(exported_files)} files to {output_folder} in format {export_format}")
            
        except Exception as e:
            if 'progress_window' in locals():
                progress_window.destroy()
            messagebox.showerror("Errore", f"Errore durante l'export: {str(e)}")

    def check_overwrite(self, filepath, filename):
        """Check if file should be overwritten or renamed - NUOVO SISTEMA MIGLIORATO"""
        file_handling_mode = self.config_data.get('file_handling_mode', 'auto_rename')
        
        if not os.path.exists(filepath):
            # File non esiste, può procedere
            return filepath
        
        if file_handling_mode == 'auto_rename':
            # Rinomina automaticamente stile Windows
            return self.get_unique_filepath(filepath)
        
        elif file_handling_mode == 'ask_overwrite':
            # Chiedi conferma
            if messagebox.askyesno("File Esistente", 
                                 f"Il file {filename} esiste già.\n\nVuoi sovrascriverlo?"):
                # User vuole sovrascrivere
                if self.config_data.get('create_backup_on_overwrite', False):
                    self.create_file_backup(filepath)
                return filepath
            else:
                # User non vuole sovrascrivere, rinomina automaticamente
                return self.get_unique_filepath(filepath)
        
        elif file_handling_mode == 'always_overwrite':
            # Sovrascrivi sempre
            if self.config_data.get('create_backup_on_overwrite', False):
                self.create_file_backup(filepath)
            return filepath
        
        return filepath

    def get_unique_filepath(self, filepath):
        """Get unique filepath using Windows-style numbering (1), (2), etc."""
        if not os.path.exists(filepath):
            return filepath
        
        # Separa percorso, nome e estensione
        directory = os.path.dirname(filepath)
        basename = os.path.basename(filepath)
        name, ext = os.path.splitext(basename)
        
        counter = 1
        while True:
            new_name = f"{name}({counter}){ext}"
            new_filepath = os.path.join(directory, new_name)
            
            if not os.path.exists(new_filepath):
                return new_filepath
            
            counter += 1
            
            # Safety check to avoid infinite loop
            if counter > 1000:
                break
        
        # Fallback with timestamp if too many files
        timestamp = int(time.time())
        new_name = f"{name}_{timestamp}{ext}"
        return os.path.join(directory, new_name)

    def create_file_backup(self, filepath):
        """Create backup of existing file"""
        backup_path = filepath + '.backup'
        try:
            import shutil
            # Se esiste già un backup, rinominalo
            if os.path.exists(backup_path):
                backup_path = self.get_unique_filepath(backup_path)
            
            shutil.copy2(filepath, backup_path)
            self.debug_print(f"Backup created: {backup_path}")
        except Exception as e:
            print(f"Error creating backup: {e}")

    def export_as_jpeg(self, output_folder, quality, progress_var, progress_window):
        """Export as individual JPEG files - AGGIORNATO"""
        exported_files = []
        page_counter = 1
        
        for group in self.documentgroups:
            for thumbnail in group.thumbnails:
                filename = f"{self.current_document_name}_{page_counter:03d}.jpg"
                original_filepath = os.path.join(output_folder, filename)
                
                # MODIFICATO: Ottieni il percorso finale (rinominato se necessario)
                final_filepath = self.check_overwrite(original_filepath, filename)
                final_filename = os.path.basename(final_filepath)
                
                progress_var.set(f"JPEG: {final_filename}...")
                progress_window.update()
                
                try:
                    img = self.prepare_image_for_save(thumbnail.image)
                    img.save(final_filepath, 'JPEG', quality=quality)
                    exported_files.append(final_filename)
                except Exception as e:
                    print(f"Error saving {final_filename}: {e}")
                
                page_counter += 1
        
        return exported_files

    def export_as_pdf_single(self, output_folder, progress_var, progress_window):
        """Export as individual PDF files - AGGIORNATO"""
        exported_files = []
        page_counter = 1
        
        for group in self.documentgroups:
            for thumbnail in group.thumbnails:
                filename = f"{self.current_document_name}_{page_counter:03d}.pdf"
                original_filepath = os.path.join(output_folder, filename)
                
                # MODIFICATO: Ottieni il percorso finale (rinominato se necessario)
                final_filepath = self.check_overwrite(original_filepath, filename)
                final_filename = os.path.basename(final_filepath)
                
                progress_var.set(f"PDF: {final_filename}...")
                progress_window.update()
                
                try:
                    img = self.prepare_image_for_save(thumbnail.image)
                    img.save(final_filepath, 'PDF')
                    exported_files.append(final_filename)
                except Exception as e:
                    print(f"Error saving {final_filename}: {e}")
                
                page_counter += 1
        
        return exported_files

    def export_as_pdf_multi_per_document(self, output_folder, progress_var, progress_window):
        """Export as multi-page PDF per document - AGGIORNATO"""
        exported_files = []
        
        for doc_index, group in enumerate(self.documentgroups, 1):
            if not group.thumbnails:  # Skip empty documents
                continue
                
            filename = f"{self.current_document_name}_doc{doc_index:03d}_{group.categoryname.replace(' ', '_')}.pdf"
            # Remove invalid filename characters
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            original_filepath = os.path.join(output_folder, filename)
            
            # MODIFICATO: Ottieni il percorso finale (rinominato se necessario)
            final_filepath = self.check_overwrite(original_filepath, filename)
            final_filename = os.path.basename(final_filepath)
            
            progress_var.set(f"PDF Documento {doc_index}: {group.categoryname}...")
            progress_window.update()
            
            try:
                images = []
                for thumbnail in group.thumbnails:
                    img = self.prepare_image_for_save(thumbnail.image)
                    images.append(img)
                
                if images:
                    images[0].save(final_filepath, 'PDF', save_all=True, append_images=images[1:])
                    exported_files.append(final_filename)
                    
            except Exception as e:
                print(f"Error saving multi-page PDF for document {group.categoryname}: {e}")
        
        return exported_files

    def export_as_tiff_single(self, output_folder, progress_var, progress_window):
        """Export as individual TIFF files - AGGIORNATO"""
        exported_files = []
        page_counter = 1
        
        for group in self.documentgroups:
            for thumbnail in group.thumbnails:
                filename = f"{self.current_document_name}_{page_counter:03d}.tiff"
                original_filepath = os.path.join(output_folder, filename)
                
                # MODIFICATO: Ottieni il percorso finale (rinominato se necessario)
                final_filepath = self.check_overwrite(original_filepath, filename)
                final_filename = os.path.basename(final_filepath)
                
                progress_var.set(f"TIFF: {final_filename}...")
                progress_window.update()
                
                try:
                    img = thumbnail.image  # TIFF può mantenere modalità originale
                    img.save(final_filepath, 'TIFF')
                    exported_files.append(final_filename)
                except Exception as e:
                    print(f"Error saving {final_filename}: {e}")
                
                page_counter += 1
        
        return exported_files

    def export_as_tiff_multi_per_document(self, output_folder, progress_var, progress_window):
        """Export as multi-page TIFF per document - AGGIORNATO"""
        exported_files = []
        
        for doc_index, group in enumerate(self.documentgroups, 1):
            if not group.thumbnails:  # Skip empty documents
                continue
                
            filename = f"{self.current_document_name}_doc{doc_index:03d}_{group.categoryname.replace(' ', '_')}.tiff"
            # Remove invalid filename characters
            filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
            original_filepath = os.path.join(output_folder, filename)
            
            # MODIFICATO: Ottieni il percorso finale (rinominato se necessario)
            final_filepath = self.check_overwrite(original_filepath, filename)
            final_filename = os.path.basename(final_filepath)
            
            progress_var.set(f"TIFF Documento {doc_index}: {group.categoryname}...")
            progress_window.update()
            
            try:
                images = []
                for thumbnail in group.thumbnails:
                    images.append(thumbnail.image)
                
                if images:
                    images[0].save(final_filepath, 'TIFF', save_all=True, append_images=images[1:])
                    exported_files.append(final_filename)
                    
            except Exception as e:
                print(f"Error saving multi-page TIFF for document {group.categoryname}: {e}")
        
        return exported_files

    def prepare_image_for_save(self, image):
        """Prepare image for saving (convert to RGB if needed)"""
        if image.mode in ('RGBA', 'LA', 'P'):
            rgb_img = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            rgb_img.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            return rgb_img
        return image

    def select_thumbnail(self, thumbnail):
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
        
        # Forza sempre la visualizzazione dell'immagine
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

    def select_document_group(self, group):
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

    def display_image(self, image):
        """Display image in center panel"""
        self.debug_print(f"display_image called with image: {image is not None}")
        
        if not image:
            self.debug_print("Warning: No image provided to display_image")
            # Pulisci il canvas se non c'è immagine
            self.image_canvas.delete("all")
            self.current_image = None
            return
        
        self.current_image = image
        self.zoom_factor = 1.0
        self.image_offset_x = 0
        self.image_offset_y = 0
        self.auto_fit_on_resize = True
        
        self.debug_print(f"Image size: {image.size if image else 'None'}")
        
        # Forza sempre l'aggiornamento del display
        if self.config_data.get('auto_fit_images', True):
            self.after_idle(self.zoom_fit)
        else:
            self.after_idle(self.update_image_display)
        
        self.debug_print("display_image completed")

    def zoom_fit(self):
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
        if self.current_image:
            self.auto_fit_on_resize = False
            self.zoom_factor *= 1.25
            self.update_image_display()
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def zoom_out(self):
        if self.current_image:
            self.auto_fit_on_resize = False
            self.zoom_factor = max(0.1, self.zoom_factor / 1.25)
            self.update_image_display()
            self.zoom_status.config(text=f"Zoom: {self.zoom_factor:.1%}")

    def toggle_zoom_area(self):
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
            # Click singolo su immagine = torna a fit
            self.auto_fit_on_resize = True
            if self.config_data.get('auto_fit_images', True):
                self.zoom_fit()

    def on_zoom_rect_start(self, event):
        if self.zoom_area_mode and self.current_image:
            self.zoom_rect_start = (event.x, event.y)
            if self.zoom_rect_id:
                self.image_canvas.delete(self.zoom_rect_id)

    def on_zoom_rect_drag(self, event):
        if self.zoom_area_mode and self.zoom_rect_start and self.current_image:
            if self.zoom_rect_id:
                self.image_canvas.delete(self.zoom_rect_id)
            self.zoom_rect_id = self.image_canvas.create_rectangle(
                self.zoom_rect_start[0], self.zoom_rect_start[1], 
                event.x, event.y, outline="red", width=2)

    def on_zoom_rect_end(self, event):
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

    def zoom_to_area(self, x, y, w, h):
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

    def on_category_changed(self, event=None):
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

    def load_document(self, doc_path):
        ext = doc_path.lower().split('.')[-1]
        if ext == "pdf":
            self.documentloader = PDFDocumentLoader(doc_path)
        elif ext in ("tiff", "tif"):
            self.documentloader = TIFFDocumentLoader(doc_path)
        else:
            messagebox.showerror("Errore", "Tipo di file non supportato")
            return
        self.documentloader.load()

    def build_document_groups(self, categories):
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

        self.updating_ui = False
        self.debug_print(f"Created {len(documents)} document groups")

    # Metodi drag semplificati
    def start_drag(self):
        self.dragging = True

    def create_drag_preview(self, thumbnail):
        self.drag_item = thumbnail
        self.drag_preview = tk.Toplevel(self)
        self.drag_preview.overrideredirect(True)
        self.drag_preview.attributes('-topmost', True)
        lbl = tk.Label(self.drag_preview, image=thumbnail.thumbnail_imgtk, bd=2, relief="solid", bg="yellow")
        lbl.pack()
        self.drag_preview.geometry(f"+{self.winfo_pointerx()+20}+{self.winfo_pointery()+20}")

    def move_drag_preview(self, x, y):
        if self.drag_preview:
            self.drag_preview.geometry(f"+{x}+{y}")

    def stop_drag(self, x_root, y_root):
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
                self.reorder_within_group(self.drag_item, target_group, x_root)
            else:
                # Move to different group
                self.move_page_to_group(self.drag_item, target_group)
            
        self.drag_item = None

    def reorder_within_group(self, thumbnail, group, x_root):
        """Reorder thumbnail within the same group"""
        old_index = group.thumbnails.index(thumbnail)
        new_index = group.get_drop_position(x_root)
        
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
        
        # Repack all thumbnails
        group.repack_thumbnails()
        
        self.debug_print(f"Reordered page {thumbnail.pagenum} in {group.categoryname} from {old_index} to {new_index}")

    def get_group_at_position(self, x_root, y_root):
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

    def move_page_to_group(self, thumbnail, target_group):
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


class PDFDocumentLoader:
    def __init__(self, path):
        self.path = path
        self.doc = None
        self.cache = {}
        
    def load(self):
        self.doc = fitz.open(self.path)
        self.totalpages = len(self.doc)
        
    def get_page(self, pagenum):
        if pagenum in self.cache:
            return self.cache[pagenum]
        try:
            page = self.doc[pagenum - 1]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            self.cache[pagenum] = img
            return img
        except:
            return None


class TIFFDocumentLoader:
    def __init__(self, path):
        self.path = path
        self.pages = []
        
    def load(self):
        img = Image.open(self.path)
        self.pages = [page.copy() for page in ImageSequence.Iterator(img)]
        img.close()
        self.totalpages = len(self.pages)
        
    def get_page(self, pagenum):
        idx = pagenum - 1
        if 0 <= idx < len(self.pages):
            return self.pages[idx]
        return None


if __name__ == "__main__":
    app = AIDOXAApp()
    app.mainloop()