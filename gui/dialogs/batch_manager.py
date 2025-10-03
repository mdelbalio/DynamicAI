"""
Batch Manager Dialog for DynamicAI
Gestisce elaborazione sequenziale di multipli documenti PDF/TIFF + JSON
Supporta due workflow:
1. JSON con categories → split documento in categorie
2. JSON flat metadati → documento unico con metadati
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Dict, Optional
import json

class BatchManagerDialog:
    """Dialog per gestione batch processing"""
    
    # Stati documento
    STATE_PENDING = "In attesa"
    STATE_PROCESSING = "In elaborazione"
    STATE_COMPLETED = "Completato"
    STATE_ERROR = "Errore"
    STATE_SKIPPED = "Saltato"
    
    def __init__(self, parent, config_manager, main_app):
        self.parent = parent
        self.config_manager = config_manager
        self.main_app = main_app
        self.result = None
        
        # State
        self.documents: List[Dict] = []
        self.current_index = 0
        self.batch_active = False
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Batch Manager - Elaborazione Multipla")
        self.dialog.geometry("900x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.create_widgets()
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def create_widgets(self):
        """Create dialog widgets"""
        # Header
        header_frame = tk.Frame(self.dialog, bg="#2c3e50", height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        tk.Label(header_frame, text="Gestione Batch - Elaborazione Sequenziale",
                font=("Arial", 14, "bold"), bg="#2c3e50", fg="white").pack(pady=15)
        
        # Main content
        content_frame = tk.Frame(self.dialog, padx=20, pady=20)
        content_frame.pack(fill="both", expand=True)
        
        # Folder selection
        self.create_folder_selection(content_frame)
        
        # Document list
        self.create_document_list(content_frame)
        
        # Progress info
        self.create_progress_info(content_frame)
        
        # Control buttons
        self.create_control_buttons(content_frame)
        
    def create_folder_selection(self, parent):
        """Folder selection frame"""
        folder_frame = tk.LabelFrame(parent, text="Selezione Cartella Batch",
                                     font=("Arial", 10, "bold"), padx=10, pady=10)
        folder_frame.pack(fill="x", pady=(0, 10))
        
        # Input folder
        input_frame = tk.Frame(folder_frame)
        input_frame.pack(fill="x", pady=5)
        
        tk.Label(input_frame, text="Cartella Input:", font=("Arial", 9)).pack(side="left")
        self.input_folder_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=self.input_folder_var,
                font=("Arial", 9), width=60).pack(side="left", padx=5, fill="x", expand=True)
        tk.Button(input_frame, text="Sfoglia", command=self.browse_input,
                 bg="lightblue", font=("Arial", 9)).pack(side="right")
        
        # Scan button
        tk.Button(folder_frame, text="Scansiona Documenti",
                 command=self.scan_documents, bg="orange",
                 font=("Arial", 10, "bold")).pack(pady=(10, 0))
        
    def create_document_list(self, parent):
        """Document list with treeview"""
        list_frame = tk.LabelFrame(parent, text="Documenti Rilevati",
                                   font=("Arial", 10, "bold"))
        list_frame.pack(fill="both", expand=True, pady=10)
        
        # Treeview
        tree_frame = tk.Frame(list_frame)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.tree = ttk.Treeview(tree_frame, columns=("Documento", "JSON", "Tipo", "Stato"),
                                show="headings", yscrollcommand=scrollbar.set, height=12)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)
        
        # Columns
        self.tree.heading("Documento", text="Documento PDF/TIFF")
        self.tree.heading("JSON", text="File JSON")
        self.tree.heading("Tipo", text="Tipo Workflow")
        self.tree.heading("Stato", text="Stato")
        
        self.tree.column("Documento", width=250)
        self.tree.column("JSON", width=250)
        self.tree.column("Tipo", width=150)
        self.tree.column("Stato", width=120)
        
        # Tags for colors
        self.tree.tag_configure("pending", foreground="black")
        self.tree.tag_configure("processing", foreground="blue", font=("Arial", 9, "bold"))
        self.tree.tag_configure("completed", foreground="green")
        self.tree.tag_configure("error", foreground="red")
        self.tree.tag_configure("skipped", foreground="gray")
        
    def create_progress_info(self, parent):
        """Progress information frame"""
        progress_frame = tk.Frame(parent)
        progress_frame.pack(fill="x", pady=10)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                           maximum=100, length=400)
        self.progress_bar.pack(side="left", padx=(0, 10))
        
        # Status label
        self.status_label = tk.Label(progress_frame, text="Nessun batch attivo",
                                     font=("Arial", 9))
        self.status_label.pack(side="left")
        
    def create_control_buttons(self, parent):
        """Control buttons frame"""
        button_frame = tk.Frame(parent, bg="lightgray", relief="raised", bd=2)
        button_frame.pack(fill="x", side="bottom", pady=(10, 0))
        
        self.start_btn = tk.Button(button_frame, text="Avvia Sequenza",
                                   command=self.start_batch, bg="lightgreen",
                                   font=("Arial", 10, "bold"), width=15, state="disabled")
        self.start_btn.pack(side="left", padx=10, pady=10)
        
        self.skip_btn = tk.Button(button_frame, text="Salta Documento",
                                  command=self.skip_current, bg="yellow",
                                  font=("Arial", 10), width=15, state="disabled")
        self.skip_btn.pack(side="left", padx=5, pady=10)
        
        self.stop_btn = tk.Button(button_frame, text="Termina Sequenza",
                                  command=self.stop_batch, bg="orange",
                                  font=("Arial", 10), width=15, state="disabled")
        self.stop_btn.pack(side="left", padx=5, pady=10)
        
        tk.Button(button_frame, text="Chiudi", command=self.on_close,
                 font=("Arial", 10), width=10).pack(side="right", padx=10, pady=10)
        
    def browse_input(self):
        """Browse input folder"""
        folder = filedialog.askdirectory(title="Seleziona cartella contenente documenti PDF/TIFF + JSON")
        if folder:
            self.input_folder_var.set(folder)
            
    def scan_documents(self):
        """Scan folder for PDF/TIFF + JSON pairs"""
        folder = self.input_folder_var.get()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Errore", "Cartella non valida")
            return
        
        # Clear existing
        self.documents.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Scan files
        try:
            files = os.listdir(folder)
            doc_files = [f for f in files if f.lower().endswith(('.pdf', '.tiff', '.tif'))]
            json_files = [f for f in files if f.lower().endswith('.json')]
            
            if not doc_files:
                messagebox.showwarning("Attenzione", "Nessun documento PDF/TIFF trovato nella cartella")
                return
            
            # Match documents with JSON
            for doc_file in sorted(doc_files):
                base_name = os.path.splitext(doc_file)[0]
                json_file = f"{base_name}.json"
                
                if json_file in json_files:
                    # Determine workflow type
                    json_path = os.path.join(folder, json_file)
                    workflow_type = self.detect_workflow_type(json_path)
                    
                    doc_info = {
                        'doc_file': doc_file,
                        'doc_path': os.path.join(folder, doc_file),
                        'json_file': json_file,
                        'json_path': json_path,
                        'workflow_type': workflow_type,
                        'state': self.STATE_PENDING,
                        'error_msg': None
                    }
                    self.documents.append(doc_info)
                    
                    # Add to tree
                    self.tree.insert("", "end", values=(
                        doc_file,
                        json_file,
                        workflow_type,
                        self.STATE_PENDING
                    ), tags=("pending",))
                else:
                    # Document without JSON
                    messagebox.showwarning("Attenzione",
                                         f"Documento '{doc_file}' non ha JSON associato (cercato: {json_file})")
            
            if self.documents:
                self.start_btn.config(state="normal")
                self.status_label.config(text=f"Trovati {len(self.documents)} documenti pronti")
                messagebox.showinfo("Scansione Completata",
                                  f"Trovati {len(self.documents)} documenti da elaborare")
            else:
                messagebox.showwarning("Attenzione", "Nessun documento con JSON valido trovato")
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante scansione: {str(e)}")
            
    def detect_workflow_type(self, json_path: str) -> str:
        """Detect workflow type from JSON structure"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'categories' in data:
                return "Split Categorie"
            else:
                return "Metadati Semplici"
        except Exception:
            return "Sconosciuto"
            
    def start_batch(self):
        """Start batch processing"""
        if not self.documents:
            messagebox.showwarning("Attenzione", "Nessun documento da elaborare")
            return
        
        self.batch_active = True
        self.current_index = 0
        
        # Update UI
        self.start_btn.config(state="disabled")
        self.skip_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        
        # Process first document
        self.process_next_document()
        
    def process_next_document(self):
        """Process next document in queue"""
        if not self.batch_active or self.current_index >= len(self.documents):
            self.finish_batch()
            return
        
        doc_info = self.documents[self.current_index]
        
        # Update tree
        item_id = self.tree.get_children()[self.current_index]
        self.tree.item(item_id, values=(
            doc_info['doc_file'],
            doc_info['json_file'],
            doc_info['workflow_type'],
            self.STATE_PROCESSING
        ), tags=("processing",))
        
        # Update progress
        progress = (self.current_index / len(self.documents)) * 100
        self.progress_var.set(progress)
        self.status_label.config(text=f"Elaborazione {self.current_index + 1}/{len(self.documents)}: {doc_info['doc_file']}")
        
        # Load document in main app
        try:
            self.main_app.load_document_from_batch(doc_info['doc_path'], doc_info['json_path'])
            
            # Wait for user validation (this is a simplified version)
            # In real implementation, you'd need a proper callback system
            self.dialog.after(1000, self.check_document_ready)
            
        except Exception as e:
            doc_info['state'] = self.STATE_ERROR
            doc_info['error_msg'] = str(e)
            self.tree.item(item_id, values=(
                doc_info['doc_file'],
                doc_info['json_file'],
                doc_info['workflow_type'],
                self.STATE_ERROR
            ), tags=("error",))
            messagebox.showerror("Errore", f"Errore caricamento documento: {str(e)}")
            self.current_index += 1
            self.process_next_document()
            
    def check_document_ready(self):
        """Check if user has completed document validation"""
        # This would be triggered by main_app after export completion
        # For now, just show a dialog
        result = messagebox.askyesno("Documento Pronto",
                                    "Validazione completata. Procedere al prossimo documento?")
        if result:
            self.mark_current_completed()
            self.current_index += 1
            self.process_next_document()
        else:
            self.stop_batch()
            
    def mark_current_completed(self):
        """Mark current document as completed"""
        if self.current_index < len(self.documents):
            doc_info = self.documents[self.current_index]
            doc_info['state'] = self.STATE_COMPLETED
            
            item_id = self.tree.get_children()[self.current_index]
            self.tree.item(item_id, values=(
                doc_info['doc_file'],
                doc_info['json_file'],
                doc_info['workflow_type'],
                self.STATE_COMPLETED
            ), tags=("completed",))
            
    def skip_current(self):
        """Skip current document"""
        if self.current_index < len(self.documents):
            doc_info = self.documents[self.current_index]
            doc_info['state'] = self.STATE_SKIPPED
            
            item_id = self.tree.get_children()[self.current_index]
            self.tree.item(item_id, values=(
                doc_info['doc_file'],
                doc_info['json_file'],
                doc_info['workflow_type'],
                self.STATE_SKIPPED
            ), tags=("skipped",))
            
            self.current_index += 1
            self.process_next_document()
            
    def stop_batch(self):
        """Stop batch processing"""
        if messagebox.askyesno("Conferma", "Interrompere l'elaborazione batch?"):
            self.batch_active = False
            self.finish_batch()
            
    def finish_batch(self):
        """Finish batch processing"""
        self.batch_active = False
        self.progress_var.set(100)
        
        # Count states
        completed = sum(1 for d in self.documents if d['state'] == self.STATE_COMPLETED)
        skipped = sum(1 for d in self.documents if d['state'] == self.STATE_SKIPPED)
        errors = sum(1 for d in self.documents if d['state'] == self.STATE_ERROR)
        
        self.status_label.config(text=f"Batch completato: {completed} OK, {skipped} saltati, {errors} errori")
        
        # Update buttons
        self.start_btn.config(state="normal")
        self.skip_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        
        # Generate final CSV if incremental mode
        if self.config_manager.get('csv_mode') == 'incremental':
            self.generate_final_csv()
        
        messagebox.showinfo("Batch Completato",
                          f"Elaborazione completata!\n\n"
                          f"Completati: {completed}\n"
                          f"Saltati: {skipped}\n"
                          f"Errori: {errors}")
        
    def generate_final_csv(self):
        """Generate final incremental CSV with all metadata"""
        # This would call export_manager.export_metadata_csv()
        # with accumulated metadata from all processed documents
        pass
        
    def on_close(self):
        """Handle dialog close"""
        if self.batch_active:
            if not messagebox.askyesno("Conferma",
                                      "Batch in corso. Chiudere comunque?"):
                return
        self.dialog.destroy()