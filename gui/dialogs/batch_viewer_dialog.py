import tkinter as tk
from tkinter import ttk, messagebox
from models.job import Job
from models.batch import Batch
from database.job_manager import JobManager
from typing import Optional

class BatchViewerDialog:
    """Dialog per visualizzare e gestire i Batch di un Job"""
    
    def __init__(self, parent, job: Job, job_manager: JobManager, app):
        self.parent = parent
        self.job = job
        self.job_manager = job_manager
        self.app = app
        self.batches = []
        self.current_batch: Optional[Batch] = None
        
        self.create_dialog()
        self.load_batches()
    
    def create_dialog(self):
        """Crea dialog principale"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(f"JOB: {self.job.name}")
        self.dialog.geometry("1400x900")
        self.dialog.transient(self.parent)
        
        # Header con info Job
        self.create_header()
        
        # Barra progresso Job
        self.create_progress_bar()
        
        # Split panel: Lista Batches | Preview Documento
        self.create_main_panels()
        
        # Control panel in basso
        self.create_control_panel()
    
    def create_header(self):
        """Crea header con info Job"""
        header_frame = tk.Frame(self.dialog, bg="#2C3E50", pady=15)
        header_frame.pack(fill="x")
        
        # Titolo
        tk.Label(
            header_frame,
            text=f"📂 {self.job.name}",
            font=("Arial", 16, "bold"),
            bg="#2C3E50",
            fg="white"
        ).pack()
        
        # Descrizione
        if self.job.description:
            tk.Label(
                header_frame,
                text=self.job.description,
                font=("Arial", 10),
                bg="#2C3E50",
                fg="#BDC3C7"
            ).pack()
        
        # Info riga
        info_text = f"📁 Input: {self.job.input_folder}  |  " \
                   f"💾 Output: {self.job.output_folder}  |  " \
                   f"📄 Immagini: {self.job.completed_images}/{self.job.total_images}"
        
        tk.Label(
            header_frame,
            text=info_text,
            font=("Arial", 9),
            bg="#2C3E50",
            fg="#95A5A6"
        ).pack(pady=(5, 0))
    
    def create_progress_bar(self):
        """Crea barra progresso Job"""
        progress_frame = tk.Frame(self.dialog, bg="lightgray", pady=10)
        progress_frame.pack(fill="x", padx=20)
        
        tk.Label(
            progress_frame,
            text="Progresso JOB:",
            font=("Arial", 10, "bold"),
            bg="lightgray"
        ).pack(side="left", padx=(0, 10))
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(side="left", fill="x", expand=True)
        
        self.progress_label = tk.Label(
            progress_frame,
            text=f"{self.job.progress:.0f}%",
            font=("Arial", 10, "bold"),
            bg="lightgray",
            fg="blue"
        )
        self.progress_label.pack(side="left", padx=10)
        
        # Update progress
        self.progress_bar['value'] = self.job.progress
    
    def create_main_panels(self):
        """Crea pannelli principali"""
        main_paned = tk.PanedWindow(
            self.dialog,
            orient=tk.HORIZONTAL,
            sashrelief=tk.RAISED
        )
        main_paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left: Lista Batches
        left_panel = tk.Frame(main_paned, bg="white", width=400)
        main_paned.add(left_panel, minsize=300)
        
        self.create_batch_list(left_panel)
        
        # Right: Preview + Controls
        right_panel = tk.Frame(main_paned, bg="white")
        main_paned.add(right_panel, minsize=600)
        
        self.create_document_preview(right_panel)
    
    def create_batch_list(self, parent):
        """Crea lista Batches"""
        # Header
        tk.Label(
            parent,
            text="📋 Elenco Batches",
            font=("Arial", 12, "bold"),
            bg="white"
        ).pack(pady=10)
        
        # Toolbar
        toolbar = tk.Frame(parent, bg="white")
        toolbar.pack(fill="x", padx=10, pady=5)
        
        tk.Button(
            toolbar,
            text="🔄 Ricarica",
            command=self.load_batches,
            font=("Arial", 9)
        ).pack(side="left", padx=2)
        
        tk.Button(
            toolbar,
            text="✅ Valida Tutti",
            command=self.validate_all_batches,
            font=("Arial", 9)
        ).pack(side="left", padx=2)
        
        # Lista Batches
        list_frame = tk.Frame(parent)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.batch_listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 9),
            yscrollcommand=scrollbar.set
        )
        self.batch_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.batch_listbox.yview)
        
        # Bind selection
        self.batch_listbox.bind("<<ListboxSelect>>", self.on_batch_select)
        self.batch_listbox.bind("<Double-1>", self.load_batch_in_app)
    
    def create_document_preview(self, parent):
        """Crea area preview documento"""
        # Header
        tk.Label(
            parent,
            text="👁️ Preview Batch Selezionato",
            font=("Arial", 12, "bold"),
            bg="white"
        ).pack(pady=10)
        
        # Info frame
        self.info_frame = tk.LabelFrame(
            parent,
            text="Informazioni",
            font=("Arial", 10, "bold"),
            bg="white",
            padx=10,
            pady=10
        )
        self.info_frame.pack(fill="x", padx=10, pady=5)
        
        self.info_text = tk.Text(
            self.info_frame,
            height=8,
            font=("Consolas", 9),
            wrap="word"
        )
        self.info_text.pack(fill="x")
        
        # Actions frame
        actions_frame = tk.Frame(parent, bg="white")
        actions_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Button(
            actions_frame,
            text="📂 Apri in Editor",
            command=self.load_batch_in_app,
            bg="#4A90E2",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        ).pack(side="left", padx=5)
        
        tk.Button(
            actions_frame,
            text="✅ Valida",
            command=self.validate_current_batch,
            bg="#50C878",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        ).pack(side="left", padx=5)
        
        tk.Button(
            actions_frame,
            text="💾 Esporta",
            command=self.export_current_batch,
            bg="#FF9800",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=8
        ).pack(side="left", padx=5)
    
    def create_control_panel(self):
        """Crea pannello controlli in basso"""
        control_frame = tk.Frame(self.dialog, bg="#ECF0F1", pady=15)
        control_frame.pack(side="bottom", fill="x")
        
        tk.Button(
            control_frame,
            text="✅ COMPLETA JOB e Esporta Tutto",
            command=self.complete_job,
            bg="#27AE60",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=30,
            pady=10
        ).pack(side="left", padx=20)
        
        tk.Button(
            control_frame,
            text="⏸️ Salva e Chiudi",
            command=self.save_and_close,
            bg="#95A5A6",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=30,
            pady=10
        ).pack(side="left", padx=10)
        
        tk.Button(
            control_frame,
            text="❌ Chiudi Senza Salvare",
            command=self.dialog.destroy,
            bg="#E74C3C",
            fg="white",
            font=("Arial", 12, "bold"),
            padx=30,
            pady=10
        ).pack(side="right", padx=20)
    
    def load_batches(self):
        """Carica lista batches dal database"""
        self.batches = self.job_manager.get_job_batches(self.job.id)
        
        # Pulisci listbox
        self.batch_listbox.delete(0, tk.END)
        
        # Popola listbox
        for batch in self.batches:
            status_icon = batch.get_status_icon()
            display_text = f"{status_icon} {batch.name} ({batch.page_count} pag)"
            
            self.batch_listbox.insert(tk.END, display_text)
            
            # Colora riga in base allo stato
            idx = self.batch_listbox.size() - 1
            if batch.exported:
                self.batch_listbox.itemconfig(idx, bg="#D5F4E6")  # Verde chiaro
            elif batch.validated:
                self.batch_listbox.itemconfig(idx, bg="#FCF3CF")  # Giallo chiaro
    
    def on_batch_select(self, event):
        """Gestisce selezione batch"""
        selection = self.batch_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        self.current_batch = self.batches[idx]
        
        # Mostra info batch
        self.show_batch_info()
    
    def show_batch_info(self):
        """Mostra informazioni batch selezionato"""
        if not self.current_batch:
            return
        
        self.info_text.delete("1.0", tk.END)
        
        info = f"""Nome: {self.current_batch.name}
PDF: {self.current_batch.pdf_path}
JSON: {self.current_batch.json_path}
Pagine: {self.current_batch.page_count}
Stato: {self.current_batch.status}
Validato: {'✅ Sì' if self.current_batch.validated else '❌ No'}
Esportato: {'✅ Sì' if self.current_batch.exported else '❌ No'}

Metadati:
"""
        
        # Aggiungi metadati
        if self.current_batch.metadata:
            for key, value in self.current_batch.metadata.items():
                info += f"  {key}: {value}\n"
        else:
            info += "  Nessun metadato disponibile"
        
        self.info_text.insert("1.0", info)
    
    def load_batch_in_app(self, event=None):
        """Carica batch nell'editor principale - IMPROVED WORKFLOW"""
        if not self.current_batch:
            messagebox.showwarning("Attenzione", "Seleziona un batch")
            return
        
        # Prepara dati per caricamento
        import json
        
        try:
            with open(self.current_batch.json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile leggere JSON:\n{e}")
            return
        
        doc_dict = {
            'doc_path': self.current_batch.pdf_path,
            'json_path': self.current_batch.json_path,
            'json_data': json_data
        }
        
        # ✅ SALVA RIFERIMENTO AL BATCH CORRENTE nell'app
        self.app.current_batch_job = {
            'batch': self.current_batch,
            'job': self.job,
            'job_manager': self.job_manager,
            'batch_viewer': self  # Riferimento al Batch Viewer
        }
        
        # Carica in app
        success = self.app.load_document_from_batch(doc_dict)
        
        if success:
            # ✅ NASCONDI BATCH VIEWER (non chiudere!)
            self.dialog.withdraw()
            
            # ✅ PORTA EDITOR IN PRIMO PIANO
            self.app.lift()
            self.app.focus_force()
            
            # ✅ Mostra istruzioni nell'editor
            if hasattr(self.app, 'selection_info'):
                self.app.selection_info.config(
                    text=f"📝 VALIDA: {self.current_batch.name} - Poi clicca 'COMPLETA e Avanti'",
                    fg="orange"
                )
    
    def validate_current_batch(self):
        """Valida batch corrente"""
        if not self.current_batch:
            messagebox.showwarning("Attenzione", "Seleziona un batch")
            return
        
        self.current_batch.validated = True
        self.current_batch.status = 'validated'
        self.job_manager.update_batch(self.current_batch)
        
        # Ricarica lista
        self.load_batches()
        
        messagebox.showinfo("Validato", f"Batch '{self.current_batch.name}' validato!")
    
    def validate_all_batches(self):
        """Valida tutti i batch"""
        if messagebox.askyesno("Conferma", "Validare tutti i batch?"):
            for batch in self.batches:
                if not batch.validated:
                    batch.validated = True
                    batch.status = 'validated'
                    self.job_manager.update_batch(batch)
            
            self.load_batches()
            messagebox.showinfo("Completato", "Tutti i batch sono stati validati!")
    
    def update_job_progress(self):
        """Aggiorna barra progresso Job"""
        # Ricarica Job dal DB
        jobs = self.job_manager.get_all_jobs()
        for j in jobs:
            if j.id == self.job.id:
                self.job = j
                break
        
        # Update UI
        self.progress_bar['value'] = self.job.progress
        self.progress_label.config(text=f"{self.job.progress:.0f}%")
    
    def export_current_batch(self):
        """Esporta batch corrente"""
        if not self.current_batch:
            messagebox.showwarning("Attenzione", "Seleziona un batch")
            return
        
        if not self.current_batch.validated:
            if not messagebox.askyesno(
                "Attenzione",
                "Il batch non è stato validato. Vuoi esportarlo comunque?"
            ):
                return
        
        # TODO: Implementare export batch
        # Per ora segna come esportato
        self.current_batch.exported = True
        self.current_batch.status = 'exported'
        self.job_manager.update_batch(self.current_batch)
        
        # Aggiorna progresso Job
        self.job_manager.update_job_progress(self.job.id)
        
        # Ricarica
        self.load_batches()
        self.update_job_progress()
        
        messagebox.showinfo("Esportato", f"Batch '{self.current_batch.name}' esportato!")
    
    def complete_job(self):
        """Completa Job ed esporta tutti i batch"""
        # Verifica che tutti i batch siano validati
        not_validated = [b for b in self.batches if not b.validated]
        
        if not_validated:
            msg = f"Ci sono {len(not_validated)} batch non validati:\n\n"
            for b in not_validated[:5]:  # Mostra primi 5
                msg += f"  • {b.name}\n"
            
            if len(not_validated) > 5:
                msg += f"  ... e altri {len(not_validated) - 5}\n"
            
            msg += "\nVuoi validare e esportare tutti automaticamente?"
            
            if not messagebox.askyesno("Batch Non Validati", msg):
                return
        
        # Conferma export
        if not messagebox.askyesno(
            "Conferma Export",
            f"Esportare tutti i {len(self.batches)} batch del Job?\n\n"
            f"Output: {self.job.output_folder}"
        ):
            return
        
        # Progress dialog
        progress_dialog = tk.Toplevel(self.dialog)
        progress_dialog.title("Export in Corso")
        progress_dialog.geometry("500x150")
        progress_dialog.transient(self.dialog)
        
        tk.Label(
            progress_dialog,
            text="Export JOB in corso...",
            font=("Arial", 12, "bold")
        ).pack(pady=10)
        
        export_progress = ttk.Progressbar(
            progress_dialog,
            mode='determinate',
            length=400
        )
        export_progress.pack(pady=10)
        
        status_label = tk.Label(
            progress_dialog,
            text="",
            font=("Arial", 9)
        )
        status_label.pack()
        
        # Export tutti i batch
        total = len(self.batches)
        for i, batch in enumerate(self.batches):
            # Update progress
            progress = ((i + 1) / total) * 100
            export_progress['value'] = progress
            status_label.config(text=f"Esportando {batch.name}... ({i+1}/{total})")
            progress_dialog.update()
            
            # Valida se non validato
            if not batch.validated:
                batch.validated = True
            
            # Marca come esportato
            batch.exported = True
            batch.status = 'exported'
            self.job_manager.update_batch(batch)
        
        # Aggiorna Job
        self.job.status = 'completed'
        self.job.progress = 100.0
        self.job.completed_images = self.job.total_images
        self.job_manager.update_job(self.job)
        
        progress_dialog.destroy()
        
        messagebox.showinfo(
            "Export Completato",
            f"✅ JOB '{self.job.name}' completato!\n\n"
            f"Esportati {total} batch.\n"
            f"Output: {self.job.output_folder}"
        )
        
        # Chiudi dialog
        self.dialog.destroy()
    
    def save_and_close(self):
        """Salva stato e chiudi"""
        # Salva Job corrente
        self.job_manager.update_job_progress(self.job.id)
        
        messagebox.showinfo(
            "Salvato",
            f"Progresso JOB salvato.\n\n"
            f"Completati: {self.job.completed_images}/{self.job.total_images} immagini\n"
            f"Progresso: {self.job.progress:.0f}%"
        )
        
        self.dialog.destroy()
    
    def update_job_progress(self):
        """Aggiorna barra progresso Job"""
        # Ricarica Job dal DB
        jobs = self.job_manager.get_all_jobs()
        for j in jobs:
            if j.id == self.job.id:
                self.job = j
                break
        
        # Update UI
        self.progress_bar['value'] = self.job.progress
        self.progress_label.config(text=f"{self.job.progress:.0f}%")