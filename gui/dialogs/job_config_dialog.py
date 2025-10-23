import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from models.job import Job
import os

class JobConfigDialog:
    """Dialog per configurare un nuovo Job"""
    
    def __init__(self, parent, input_folder: str, config_manager):
        self.parent = parent
        self.input_folder = input_folder
        self.config_manager = config_manager
        self.result = None
        
        self.create_dialog()
    
    def create_dialog(self):
        """Crea dialog configurazione"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Configurazione Nuovo JOB")
        self.dialog.geometry("600x450")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Header
        header = tk.Label(
            self.dialog,
            text="📋 Configurazione Nuovo JOB",
            font=("Arial", 14, "bold"),
            bg="#4A90E2",
            fg="white",
            pady=15
        )
        header.pack(fill="x")
        
        # Form frame
        form_frame = tk.Frame(self.dialog, padx=20, pady=20)
        form_frame.pack(fill="both", expand=True)
        
        # Nome Job (pre-compilato con nome cartella)
        tk.Label(
            form_frame, 
            text="Nome JOB:",
            font=("Arial", 10, "bold")
        ).grid(row=0, column=0, sticky="w", pady=5)
        
        folder_name = os.path.basename(os.path.normpath(self.input_folder))
        self.name_var = tk.StringVar(value=folder_name)
        
        tk.Entry(
            form_frame,
            textvariable=self.name_var,
            font=("Arial", 10),
            width=40
        ).grid(row=0, column=1, pady=5, sticky="ew")
        
        # Descrizione
        tk.Label(
            form_frame,
            text="Descrizione:",
            font=("Arial", 10, "bold")
        ).grid(row=1, column=0, sticky="nw", pady=5)
        
        self.description_text = tk.Text(
            form_frame,
            height=4,
            width=40,
            font=("Arial", 9),
            wrap="word"
        )
        self.description_text.grid(row=1, column=1, pady=5, sticky="ew")
        
        # Cartella Input (read-only)
        tk.Label(
            form_frame,
            text="Cartella Input:",
            font=("Arial", 10, "bold")
        ).grid(row=2, column=0, sticky="w", pady=5)
        
        input_label = tk.Label(
            form_frame,
            text=self.input_folder,
            font=("Arial", 9),
            fg="blue",
            anchor="w"
        )
        input_label.grid(row=2, column=1, pady=5, sticky="w")
        
        # Cartella Output
        tk.Label(
            form_frame,
            text="Cartella Output:",
            font=("Arial", 10, "bold")
        ).grid(row=3, column=0, sticky="w", pady=5)
        
        output_frame = tk.Frame(form_frame)
        output_frame.grid(row=3, column=1, pady=5, sticky="ew")
        
        default_output = self.config_manager.get('default_output_folder', '')
        self.output_var = tk.StringVar(value=default_output)
        
        tk.Entry(
            output_frame,
            textvariable=self.output_var,
            font=("Arial", 9),
            state="readonly"
        ).pack(side="left", fill="x", expand=True)
        
        tk.Button(
            output_frame,
            text="📁",
            command=self.browse_output,
            font=("Arial", 10)
        ).pack(side="right", padx=(5, 0))
        
        # Opzioni avanzate
        options_frame = tk.LabelFrame(
            form_frame,
            text="Opzioni",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10
        )
        options_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        
        self.auto_export_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Export automatico al completamento",
            variable=self.auto_export_var,
            font=("Arial", 9)
        ).pack(anchor="w")
        
        self.validate_metadata_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            options_frame,
            text="Richiedi validazione metadati",
            variable=self.validate_metadata_var,
            font=("Arial", 9)
        ).pack(anchor="w")
        
        # Configure grid weights
        form_frame.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = tk.Frame(self.dialog)
        button_frame.pack(side="bottom", pady=15)
        
        tk.Button(
            button_frame,
            text="✅ Crea JOB",
            command=self.create_job,
            bg="#50C878",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8
        ).pack(side="left", padx=5)
        
        tk.Button(
            button_frame,
            text="❌ Annulla",
            command=self.dialog.destroy,
            bg="#E74C3C",
            fg="white",
            font=("Arial", 11, "bold"),
            padx=20,
            pady=8
        ).pack(side="left", padx=5)
    
    def browse_output(self):
        """Seleziona cartella output"""
        folder = filedialog.askdirectory(
            title="Seleziona Cartella Output",
            initialdir=self.output_var.get()
        )
        
        if folder:
            self.output_var.set(folder)
    
    def create_job(self):
        """Crea Job con dati inseriti"""
        # Validazione
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Errore", "Inserisci un nome per il JOB")
            return
        
        output = self.output_var.get().strip()
        if not output:
            messagebox.showerror("Errore", "Seleziona una cartella di output")
            return
        
        # Crea Job
        description = self.description_text.get("1.0", "end-1c").strip()
        
        job = Job(
            name=name,
            description=description,
            input_folder=self.input_folder,
            output_folder=output,
            status='pending',
            metadata={
                'auto_export': self.auto_export_var.get(),
                'validate_metadata': self.validate_metadata_var.get()
            }
        )
        
        self.result = job
        self.dialog.destroy()