import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from database.job_manager import JobManager
from models.job import Job
import os
import json

class JobManagerDialog:
    """Dialog per gestione Job (simile alla tua UI)"""
    
    def __init__(self, parent, config_manager, app):
        self.parent = parent
        self.config_manager = config_manager
        self.app = app
        
        # ✅ FIX: Usa AppData/Roaming direttamente
        config_dir = os.path.join(
            os.path.expanduser('~'),
            'AppData', 'Roaming', 'DynamicAI'
        )
        
        # Crea cartella se non esiste
        os.makedirs(config_dir, exist_ok=True)
        
        db_path = os.path.join(config_dir, 'jobs.db')
        
        # Inizializza Job Manager
        self.job_manager = JobManager(db_path)
        
        self.create_dialog()
        self.load_jobs()
    
    def create_dialog(self):
        """Crea dialog principale"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Gestione JOB (Lavori)")
        self.dialog.geometry("1000x600")
        self.dialog.transient(self.parent)
        
        # Header con titolo
        header = tk.Label(
            self.dialog, 
            text="Gestione JOB (Lavori)",
            font=("Arial", 16, "bold"),
            bg="#4A90E2",
            fg="white",
            pady=10
        )
        header.pack(fill="x")
        
        # Toolbar con pulsanti
        self.create_toolbar()
        
        # Tabella Job
        self.create_job_table()
        
        # Footer con info
        footer = tk.Label(
            self.dialog,
            text="Un JOB rappresenta una cartella di immagini da processare. "
                 "Puoi avere più JOB e lavorare su uno alla volta. Doppio click per aprire un JOB.",
            font=("Arial", 8),
            fg="gray",
            pady=5
        )
        footer.pack(side="bottom", fill="x")
        
        # Bottone chiudi
        tk.Button(
            self.dialog,
            text="Chiudi",
            command=self.dialog.destroy,
            bg="#50C878",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            pady=5
        ).pack(side="bottom", pady=10)
    
    def create_toolbar(self):
        """Crea toolbar con pulsanti azione"""
        toolbar = tk.Frame(self.dialog, bg="lightgray", pady=10)
        toolbar.pack(fill="x", padx=10)
        
        buttons = [
            ("Nuovo JOB", self.new_job, "#50C878"),
            ("Riprendi JOB", self.resume_job, "#4A90E2"),
            ("Esporta JOB", self.export_job, "#FF9800"),
            ("Elimina JOB", self.delete_job, "#E74C3C")
        ]
        
        for text, command, color in buttons:
            tk.Button(
                toolbar,
                text=text,
                command=command,
                bg=color,
                fg="white",
                font=("Arial", 10, "bold"),
                padx=15,
                pady=5
            ).pack(side="left", padx=5)
    
    def create_job_table(self):
        """Crea tabella Job con Treeview"""
        table_frame = tk.Frame(self.dialog)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Treeview
        columns = ("Nome JOB", "Stato", "Progresso", "Totale Img", "Completate", 
                  "Data Creazione", "Cartella")
        
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            yscrollcommand=scrollbar.set
        )
        
        # Configura colonne
        widths = [150, 100, 80, 80, 80, 120, 250]
        for col, width in zip(columns, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width)
        
        self.tree.pack(fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Bind doppio click
        self.tree.bind("<Double-1>", self.on_job_double_click)
    
    def load_jobs(self):
        """Carica Job dal database"""
        # Pulisci tabella
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Carica Job
        jobs = self.job_manager.get_all_jobs()
        
        for job in jobs:
            # Icona stato
            status_icon = {
                'pending': '⏸️',
                'in_progress': '▶️',
                'completed': '✅',
                'error': '❌'
            }.get(job.status, '')
            
            self.tree.insert('', 'end', values=(
                job.name,
                f"{status_icon} {job.status.capitalize()}",
                f"{job.progress:.0f}%",
                job.total_images,
                job.completed_images,
                job.created_at or "",
                job.input_folder
            ), tags=(str(job.id),))
    
    def new_job(self):
        """Crea nuovo Job"""
        # Selezione cartella
        folder = filedialog.askdirectory(title="Seleziona Cartella Input per Nuovo JOB")
        
        if not folder:
            return
        
        # Dialog config Job
        from gui.dialogs.job_config_dialog import JobConfigDialog
        config_dialog = JobConfigDialog(self.dialog, folder, self.config_manager)
        self.dialog.wait_window(config_dialog.dialog)
        
        if config_dialog.result:
            job = config_dialog.result
            
            # Salva Job
            job_id = self.job_manager.create_job(job)
            job.id = job_id
            
            # Crea batches
            batch_count = self.job_manager.create_batches_from_folder(job)
            
            # Ricarica tabella
            self.load_jobs()
            
            messagebox.showinfo(
                "Job Creato",
                f"Job '{job.name}' creato con {batch_count} batches!"
            )
    
    def resume_job(self):
        """Riprendi Job selezionato"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona un Job")
            return
        
        job_id = int(self.tree.item(selected[0])['tags'][0])
        
        # Carica Job
        jobs = self.job_manager.get_all_jobs()
        job = next((j for j in jobs if j.id == job_id), None)
        
        if not job:
            messagebox.showerror("Errore", "Job non trovato")
            return
        
        # ✅ NASCONDI JOB MANAGER
        self.dialog.withdraw()
        
        # ✅ APRI BATCH VIEWER DOPO UN DELAY
        self.dialog.after(100, lambda: self._open_batch_viewer_delayed(job))

    def _open_batch_viewer_delayed(self, job):
        """Apri Batch Viewer con delay"""
        try:
            from gui.dialogs.batch_viewer_dialog import BatchViewerDialog
            
            # Usa parent principale invece di self.dialog
            BatchViewerDialog(self.parent, job, self.job_manager, self.app)
            
        except Exception as e:
            print(f"Error opening Batch Viewer: {e}")
            import traceback
            traceback.print_exc()
            
            # Mostra di nuovo Job Manager in caso di errore
            self.dialog.deiconify()
            messagebox.showerror("Errore", f"Impossibile aprire Batch Viewer:\n{e}")
    
    def on_job_double_click(self, event):
        """Gestisce doppio click su Job"""
        self.resume_job()
    
    def export_job(self):
        """Esporta TUTTI i batch del Job selezionato"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona un Job da esportare")
            return
        
        job_id = int(self.tree.item(selected[0])['tags'][0])
        
        # Carica Job
        jobs = self.job_manager.get_all_jobs()
        job = next((j for j in jobs if j.id == job_id), None)
        
        if not job:
            messagebox.showerror("Errore", "Job non trovato")
            return
        
        # Verifica cartella output
        if not job.output_folder:
            messagebox.showerror("Errore", "Cartella output non configurata per questo Job")
            return
        
        if not os.path.exists(job.output_folder):
            try:
                os.makedirs(job.output_folder, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile creare cartella output:\n{e}")
                return
        
        # Conferma export
        batches = self.job_manager.get_job_batches(job.id)
        
        if not batches:
            messagebox.showwarning("Attenzione", "Nessun batch trovato in questo Job")
            return
        
        result = messagebox.askyesno(
            "Conferma Export",
            f"Esportare tutti i {len(batches)} batch del Job '{job.name}'?\n\n"
            f"Destinazione: {job.output_folder}\n\n"
            "Questa operazione esporterà tutti i documenti processati."
        )
        
        if not result:
            return
        
        # Progress tracking
        exported_count = 0
        error_count = 0
        error_messages = []
        
        # ✅ NASCONDI JOB MANAGER durante export
        self.dialog.withdraw()
        
        # Export ogni batch
        for i, batch in enumerate(batches, 1):
            try:
                print(f"\n[EXPORT] Processing batch {i}/{len(batches)}: {batch.name}")
                
                # Carica JSON
                with open(batch.json_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                
                # ✅ ESPORTA usando il sistema dell'app
                success = self._export_single_batch(batch, json_data, job.output_folder)
                
                if success:
                    # Marca come esportato
                    batch.exported = True
                    batch.status = 'exported'
                    self.job_manager.update_batch(batch)
                    exported_count += 1
                    print(f"[EXPORT] ✅ Batch {batch.name} esportato con successo")
                else:
                    error_count += 1
                    error_msg = f"Batch '{batch.name}' - Export fallito"
                    error_messages.append(error_msg)
                    print(f"[EXPORT] ❌ {error_msg}")
                    
            except Exception as e:
                error_count += 1
                error_msg = f"Batch '{batch.name}' - {str(e)}"
                error_messages.append(error_msg)
                print(f"[EXPORT] ❌ Error exporting batch {batch.name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Aggiorna progresso Job
        self.job_manager.update_job_progress(job.id)
        
        # ✅ MOSTRA DI NUOVO JOB MANAGER
        self.dialog.deiconify()
        self.dialog.lift()
        
        # Ricarica lista
        self.load_jobs()
        
        # Messaggio risultato
        if error_count == 0:
            messagebox.showinfo(
                "Export Completato",
                f"✅ Esportati con successo {exported_count} batch!\n\n"
                f"Destinazione: {job.output_folder}"
            )
        else:
            error_details = "\n".join(error_messages[:5])  # Mostra primi 5 errori
            if len(error_messages) > 5:
                error_details += f"\n... e altri {len(error_messages) - 5} errori"
            
            messagebox.showwarning(
                "Export Parziale",
                f"✅ Esportati: {exported_count}\n"
                f"❌ Errori: {error_count}\n\n"
                f"Destinazione: {job.output_folder}\n\n"
                f"Errori:\n{error_details}"
            )

    def _export_single_batch(self, batch, json_data, output_folder):
        """Esporta singolo batch usando il metodo dell'app principale"""
        try:
            print(f"[EXPORT] Caricamento batch {batch.name} nell'app...")
            
            # 1. Prepara dati batch
            doc_dict = {
                'doc_path': batch.pdf_path,
                'json_path': batch.json_path,
                'json_data': json_data
            }
            
            # 2. Salva output folder corrente
            old_output = self.app.config_manager.get('default_output_folder', '')
            print(f"[EXPORT] Old output folder: {old_output}")
            print(f"[EXPORT] New output folder: {output_folder}")
            
            # 3. Imposta temporaneamente output folder del Job
            self.app.config_manager.set('default_output_folder', output_folder)
            
            # 4. Carica documento nell'app (questo popola self.app.documentgroups)
            print(f"[EXPORT] Loading document from batch...")
            success = self.app.load_document_from_batch(doc_dict)
            
            if not success:
                print(f"[EXPORT] ❌ Failed to load document")
                # Ripristina output folder
                self.app.config_manager.set('default_output_folder', old_output)
                return False
            
            print(f"[EXPORT] ✅ Document loaded successfully")
            print(f"[EXPORT] Document groups: {len(self.app.documentgroups)}")
            
            # 5. Esporta usando il metodo esistente dell'app
            print(f"[EXPORT] Calling complete_sequence_export()...")
            self.app.complete_sequence_export()
            
            print(f"[EXPORT] ✅ Export completed for {batch.name}")
            
            # 6. Ripristina output folder originale
            self.app.config_manager.set('default_output_folder', old_output)
            
            # 7. Pulisci workspace app
            self.app.reset_workspace()
            
            return True
            
        except Exception as e:
            print(f"[EXPORT] ❌ Error in _export_single_batch: {e}")
            import traceback
            traceback.print_exc()
            
            # Ripristina output folder in caso di errore
            try:
                self.app.config_manager.set('default_output_folder', old_output)
            except:
                pass
            
            return False
    
    def delete_job(self):
        """Elimina Job"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attenzione", "Seleziona un Job")
            return
        
        if messagebox.askyesno("Conferma", "Eliminare il Job selezionato?"):
            job_id = int(self.tree.item(selected[0])['tags'][0])
            self.job_manager.delete_job(job_id)
            self.load_jobs()