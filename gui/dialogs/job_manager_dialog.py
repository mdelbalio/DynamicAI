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
        print(f"[BUTTON_DEBUG] 🔘 Export button clicked!")
        
        # Verifica selezione
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
        export_files = []  # 🔥 FIX: Lista per tenere traccia dei file esportati
        
        # ✅ NASCONDI JOB MANAGER durante export
        self.dialog.withdraw()
        
        try:
            # Export ogni batch
            for i, batch in enumerate(batches, 1):
                try:
                    print(f"\n[EXPORT] Processing batch {i}/{len(batches)}: {batch.name}")
                    
                    # Carica JSON
                    if not os.path.exists(batch.json_path):
                        error_msg = f"Batch '{batch.name}' - JSON file not found: {batch.json_path}"
                        error_messages.append(error_msg)
                        error_count += 1
                        print(f"[EXPORT] ❌ {error_msg}")
                        continue
                    
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
                        export_files.append(batch.name)  # 🔥 FIX: Traccia file esportato
                        print(f"[EXPORT] ✅ Batch {batch.name} esportato con successo")
                    else:
                        error_count += 1
                        error_msg = f"Batch '{batch.name}' - Export fallito"
                        error_messages.append(error_msg)
                        print(f"[EXPORT] ❌ {error_msg}")
                        
                except Exception as e:
                    error_count += 1
                    error_msg = f"Batch '{batch.name}' - Errore: {str(e)}"
                    error_messages.append(error_msg)
                    print(f"[EXPORT] ❌ Error exporting batch {batch.name}: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Aggiorna progresso Job
            try:
                self.job_manager.update_job_progress(job.id)
            except Exception as e:
                print(f"[EXPORT] Warning: Could not update job progress: {e}")
        
        except Exception as e:
            print(f"[EXPORT] ❌ Critical error during export: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Errore Critico", f"Errore durante l'export:\n{e}")
        
        finally:
            # ✅ MOSTRA DI NUOVO JOB MANAGER
            self.dialog.deiconify()
            self.dialog.lift()
            
            # Ricarica lista
            try:
                self.load_jobs()
            except Exception as e:
                print(f"[EXPORT] Warning: Could not reload jobs: {e}")
        
        # Messaggio risultato
        if error_count == 0:
            messagebox.showinfo(
                "Export Completato",
                f"✅ Esportati con successo {exported_count} batch!\n\n"
                f"📁 Destinazione: {job.output_folder}\n"
                f"📄 File processati: {len(export_files)}\n\n"
                f"Tutti i documenti sono stati esportati correttamente."
            )
        elif exported_count > 0:
            # Export parziale
            error_details = "\n".join(error_messages[:5])  # Mostra primi 5 errori
            if len(error_messages) > 5:
                error_details += f"\n... e altri {len(error_messages) - 5} errori"
            
            messagebox.showwarning(
                "Export Parziale", 
                f"✅ Esportati con successo: {exported_count}\n"
                f"❌ Errori riscontrati: {error_count}\n\n"
                f"📁 Destinazione: {job.output_folder}\n"
                f"📄 File processati: {len(export_files)}\n\n"
                f"Errori:\n{error_details}"
            )
        else:
            # Tutti falliti
            error_details = "\n".join(error_messages[:5])  # Mostra primi 5 errori
            if len(error_messages) > 5:
                error_details += f"\n... e altri {len(error_messages) - 5} errori"
            
            messagebox.showerror(
                "Export Fallito",
                f"❌ Nessun batch è stato esportato!\n\n"
                f"📁 Destinazione: {job.output_folder}\n"
                f"🚫 Errori: {error_count}\n\n"
                f"Dettagli errori:\n{error_details}"
            )

    def _export_single_batch(self, batch, json_data, output_folder, job=None):
        """Esporta singolo batch usando ExportManager - VERSIONE FINALE + CSV + STRUTTURA"""
        from datetime import datetime
        
        print("="*50)
        print(f"[EXPORT_DEBUG] 🚀 STARTING EXPORT DEBUG")
        print(f"[EXPORT_DEBUG] Batch name: {batch.name}")
        print(f"[EXPORT_DEBUG] Batch PDF: {batch.pdf_path}")
        print(f"[EXPORT_DEBUG] Output folder: {output_folder}")
        print(f"[EXPORT_DEBUG] JSON data keys: {list(json_data.keys())}")
        print(f"[EXPORT_DEBUG] Categories count: {len(json_data.get('categories', []))}")
        
        # 🔥 GESTIONE STRUTTURA DIRECTORY
        final_output_folder = output_folder
        if job and hasattr(job, 'maintain_structure') and job.maintain_structure:
            # Estrae il nome della sottocartella dall'input
            # Es: C:/FLUIDO-IN/Insegne_multi-B001/B001_F001.pdf → Insegne_multi-B001
            input_parent = os.path.dirname(batch.pdf_path)
            folder_name = os.path.basename(input_parent)
            final_output_folder = os.path.join(output_folder, folder_name)
            print(f"[EXPORT_DEBUG] 📁 Directory structure maintained: {final_output_folder}")
        else:
            print(f"[EXPORT_DEBUG] 📁 Flat output structure: {final_output_folder}")
        
        try:
            # 1. Import ExportManager
            print(f"[EXPORT_DEBUG] 📦 Testing ExportManager import...")
            from export.export_manager import ExportManager
            print(f"[EXPORT_DEBUG] ✅ ExportManager imported successfully")
            
            # 2. Creazione ExportManager
            print(f"[EXPORT_DEBUG] 🏗️ Creating ExportManager instance...")
            export_manager = ExportManager(self.config_manager)
            print(f"[EXPORT_DEBUG] ✅ ExportManager created successfully")
            
            # 3. Path verification
            print(f"[EXPORT_DEBUG] 📁 Verifying paths...")
            if not os.path.exists(batch.pdf_path):
                print(f"[EXPORT_DEBUG] ❌ PDF file not found: {batch.pdf_path}")
                return False
            else:
                print(f"[EXPORT_DEBUG] ✅ PDF file exists")
            
            if not os.path.exists(final_output_folder):
                print(f"[EXPORT_DEBUG] 📁 Creating output folder: {final_output_folder}")
                os.makedirs(final_output_folder, exist_ok=True)
            
            # 4. CREA DOCUMENT GROUPS per ExportManager
            print(f"[EXPORT_DEBUG] 📄 Converting batch to document_groups...")
            
            # Carica il documento per creare gli thumbnails
            from loaders import create_document_loader
            doc_loader = create_document_loader(batch.pdf_path)
            
            # FIX: Carica il documento
            doc_loader.load()
            print(f"[EXPORT_DEBUG] Document loaded with {doc_loader.totalpages} pages")
            
            # Crea mock DocumentGroup objects per ExportManager
            document_groups = []
            
            # Per ogni categoria nel JSON, crea un gruppo
            categories_data = json_data.get('categories', [])
            print(f"[EXPORT_DEBUG] Processing {len(categories_data)} categories...")
            
            for cat_info in categories_data:
                categoria = cat_info['categoria']
                inizio = cat_info['inizio']
                fine = cat_info['fine']
                
                print(f"[EXPORT_DEBUG] Category '{categoria}': pages {inizio}-{fine}")
                
                # Crea mock group object
                class MockGroup:
                    def __init__(self, category_name, pages):
                        self.categoryname = category_name      # 🔥 Per ExportManager
                        self.category_name = category_name     # Mantiene quello vecchio
                        self.thumbnails = []
                        
                        # Crea mock thumbnails per ogni pagina
                        for page_num in pages:
                            try:
                                # FIX: Usa get_page() con 1-based indexing!
                                page_image = doc_loader.get_page(page_num)  # 1-based
                                
                                if page_image:  # Verifica che l'immagine sia valida
                                    class MockThumbnail:
                                        def __init__(self, image):
                                            self.image = image
                                    
                                    self.thumbnails.append(MockThumbnail(page_image))
                                    print(f"[EXPORT_DEBUG] ✅ Loaded page {page_num} successfully")
                                else:
                                    print(f"[EXPORT_DEBUG] ⚠️ Page {page_num} returned None")
                                    
                            except Exception as e:
                                print(f"[EXPORT_DEBUG] Warning: Could not load page {page_num}: {e}")
                
                # Crea lista pagine per questa categoria
                pages = list(range(inizio, fine + 1))
                group = MockGroup(categoria, pages)
                
                if group.thumbnails:  # Solo se ha thumbnails validi
                    document_groups.append(group)
                    print(f"[EXPORT_DEBUG] ✅ Added group '{categoria}' with {len(group.thumbnails)} pages")
                else:
                    print(f"[EXPORT_DEBUG] ⚠️ Skipped group '{categoria}' - no valid thumbnails")

            print(f"[EXPORT_DEBUG] ✅ Created {len(document_groups)} document groups")
            
            # AGGIUNTA: Verifica che abbiamo almeno un gruppo
            if len(document_groups) == 0:
                print(f"[EXPORT_DEBUG] ❌ No document groups created - cannot export")
                return False
            
            # 5. CHIAMATA EXPORT CORRETTA con tutti i parametri
            document_name = os.path.splitext(os.path.basename(batch.pdf_path))[0]
            print(f"[EXPORT_DEBUG] 🚀 CALLING export_manager.export_documents()...")
            print(f"[EXPORT_DEBUG] Args:")
            print(f"[EXPORT_DEBUG]   output_folder: {final_output_folder}")
            print(f"[EXPORT_DEBUG]   document_groups: {len(document_groups)} groups")
            print(f"[EXPORT_DEBUG]   document_name: {document_name}")
            
            # Salva configurazione output temporanea
            old_output = self.config_manager.get('default_output_folder', '')
            self.config_manager.set('default_output_folder', final_output_folder)
            
            # CHIAMATA CORRETTA: export_documents(output_folder, document_groups, document_name, callback)
            exported_files = export_manager.export_documents(
                final_output_folder, 
                document_groups, 
                document_name, 
                None  # progress_callback
            )
            
            # Ripristina configurazione
            self.config_manager.set('default_output_folder', old_output)
            
            print(f"[EXPORT_DEBUG] 📤 Export completed!")
            print(f"[EXPORT_DEBUG] Returned: {exported_files}")
            print(f"[EXPORT_DEBUG] Type: {type(exported_files)}")
            
            # 6. Verifica risultato
            if exported_files and len(exported_files) > 0:
                print(f"[EXPORT_DEBUG] ✅ SUCCESS! {len(exported_files)} files exported")
                
                # 7. 🔥 GENERA CSV CON METADATI
                print(f"[EXPORT_DEBUG] 📊 Generating CSV metadata...")
                try:
                    # Crea metadata rows dalle categorie JSON
                    metadata_rows = []
                    
                    categories_data = json_data.get('categories', [])
                    for i, cat_info in enumerate(categories_data, 1):
                        categoria = cat_info['categoria']
                        inizio = cat_info['inizio']
                        fine = cat_info['fine']
                        
                        metadata_row = {
                            'Documento': document_name,
                            'Categoria': categoria,
                            'Pagina_Inizio': inizio,
                            'Pagina_Fine': fine,
                            'Totale_Pagine': (fine - inizio + 1),
                            'Posizione': i,
                            'Data_Export': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'Path_Input': batch.pdf_path,
                            'Path_Output': final_output_folder
                        }
                        metadata_rows.append(metadata_row)
                    
                    if metadata_rows:
                        # Chiama export CSV
                        csv_file = export_manager.export_metadata_csv(
                            metadata_rows=metadata_rows,
                            input_filename=document_name,
                            output_folder=final_output_folder
                        )
                        
                        if csv_file:
                            print(f"[EXPORT_DEBUG] ✅ CSV generated: {csv_file}")
                        else:
                            print(f"[EXPORT_DEBUG] ⚠️ CSV generation failed")
                    else:
                        print(f"[EXPORT_DEBUG] ⚠️ No metadata rows to export")
                        
                except Exception as csv_error:
                    print(f"[EXPORT_DEBUG] ❌ CSV Error: {csv_error}")
                    # Non fallire l'export per errori CSV
                
                return True
            else:
                print(f"[EXPORT_DEBUG] ❌ FAILURE: No files exported")
                return False
                
        except Exception as e:
            print(f"[EXPORT_DEBUG] 💥 EXCEPTION in _export_single_batch:")
            print(f"[EXPORT_DEBUG] Error: {e}")
            print(f"[EXPORT_DEBUG] Type: {type(e)}")
            
            import traceback
            print(f"[EXPORT_DEBUG] 📋 Full traceback:")
            traceback.print_exc()
            
            # Ripristina config
            try:
                self.config_manager.set('default_output_folder', old_output)
            except:
                pass
            
            return False
        
        finally:
            print(f"[EXPORT_DEBUG] 🏁 Export debug completed")
            print("="*50)
    
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