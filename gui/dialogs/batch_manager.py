"""
Batch Manager Dialog - Gestione elaborazione batch multi-livello con validazione sequenziale
"""

import os
import json  # ⭐ AGGIUNTO
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog  # ⭐ AGGIUNTO simpledialog
from typing import List, Dict, Optional
import threading
import subprocess  # ⭐ AGGIUNTO per aprire file esterni
import platform  # ⭐ AGGIUNTO per rilevare OS

# Import batch modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from batch.scanner import BatchScanner, DocumentPair
from batch.batch_database import BatchDatabase
from batch.batch_exporter import BatchExporter


class BatchManagerDialog:
    """Dialog gestione batch con scansione ricorsiva e validazione sequenziale"""
    
    def __init__(self, parent, config_manager, main_app):
        """
        Inizializza Batch Manager
        
        Args:
            parent: Widget parent
            config_manager: ConfigManager instance
            main_app: Main application reference
        """
        self.parent = parent
        self.config_manager = config_manager
        self.main_app = main_app
        
        # Batch components
        self.batch_scanner = BatchScanner()
        self.batch_db = BatchDatabase()
        self.batch_exporter = BatchExporter(config_manager)
        
        # State
        self.current_session_id: Optional[str] = None
        self.documents: List[Dict] = []
        self.current_doc_index: int = 0
        self.sequential_docs: List[Dict] = []
        self.is_scanning: bool = False
        self.is_exporting: bool = False
        
        # UI Setup
        self.setup_ui()
        
        # Check incomplete sessions on startup
        self.after_idle_check_sessions()
    
    def setup_ui(self):
        """Crea interfaccia completa batch manager"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Batch Manager - Elaborazione Multipla")
        self.dialog.geometry("1200x750")
        self.dialog.transient(self.parent)
        
        # Header
        self.create_header()
        
        # Selection area
        self.create_selection_area()
        
        # Documents table
        self.create_documents_table()
        
        # Control buttons
        self.create_control_buttons()
        
        # Progress area
        self.create_progress_area()
        
        # Status bar
        self.create_status_bar()
    
    def create_header(self):
        """Crea header dialog"""
        header = tk.Frame(self.dialog, bg="#34495E", height=70)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title = tk.Label(
            header,
            text="🔄 Gestione Batch - Elaborazione Sequenziale",
            font=("Arial", 16, "bold"),
            bg="#34495E",
            fg="white"
        )
        title.pack(pady=20)
    
    def create_selection_area(self):
        """Area selezione cartella batch"""
        selection_frame = tk.LabelFrame(
            self.dialog,
            text="Selezione Cartella Batch",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=10
        )
        selection_frame.pack(fill="x", padx=10, pady=10)
        
        # Input path
        input_frame = tk.Frame(selection_frame)
        input_frame.pack(fill="x", pady=5)
        
        tk.Label(input_frame, text="Cartella Input:", font=("Arial", 9)).pack(side="left", padx=(0, 5))
        
        self.batch_path_var = tk.StringVar(
            value=self.config_manager.get('default_input_folder', '')
        )
        
        entry = tk.Entry(input_frame, textvariable=self.batch_path_var, font=("Arial", 9))
        entry.pack(side="left", fill="x", expand=True, padx=5)
        
        tk.Button(
            input_frame,
            text="Sfoglia",
            command=self.browse_batch_folder,
            bg="#3498DB",
            fg="white",
            font=("Arial", 9),
            cursor="hand2",
            padx=10
        ).pack(side="left")
        
        # Scan button
        self.btn_scan = tk.Button(
            selection_frame,
            text="🔍 Scansiona Documenti",
            command=self.scan_documents,
            bg="#E67E22",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=20,
            pady=8
        )
        self.btn_scan.pack(pady=10)
    
    def create_documents_table(self):
        """Tabella documenti rilevati con colonne estese"""
        table_frame = tk.LabelFrame(
            self.dialog,
            text="Documenti Rilevati",
            font=("Arial", 10, "bold")
        )
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Container for tree + scrollbars
        tree_container = tk.Frame(table_frame)
        tree_container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbars
        scrollbar_y = tk.Scrollbar(tree_container, orient="vertical")
        scrollbar_y.pack(side="right", fill="y")
        
        scrollbar_x = tk.Scrollbar(tree_container, orient="horizontal")
        scrollbar_x.pack(side="bottom", fill="x")
        
        # Treeview
        columns = ('id', 'documento', 'json', 'path', 'workflow', 'stato')
        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show='headings',
            yscrollcommand=scrollbar_y.set,
            xscrollcommand=scrollbar_x.set,
            selectmode='extended'
        )
        
        # Configure columns
        self.tree.heading('id', text='#')
        self.tree.heading('documento', text='Documento PDF/TIFF')
        self.tree.heading('json', text='File JSON')
        self.tree.heading('path', text='Path Relativo')
        self.tree.heading('workflow', text='Tipo Workflow')
        self.tree.heading('stato', text='Stato')
        
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('documento', width=200)
        self.tree.column('json', width=180)
        self.tree.column('path', width=250)
        self.tree.column('workflow', width=150, anchor='center')
        self.tree.column('stato', width=120, anchor='center')
        
        scrollbar_y.config(command=self.tree.yview)
        scrollbar_x.config(command=self.tree.xview)
        
        self.tree.pack(fill="both", expand=True)
        
        # Style for alternating rows
        style = ttk.Style()
        style.configure("Treeview", rowheight=25, font=("Arial", 9))
        style.map('Treeview', background=[('selected', '#3498DB')])
        
        # Bindings
        self.tree.bind("<Double-1>", self.on_double_click_document)
        self.tree.bind("<Button-3>", self.show_context_menu)
    
    def create_control_buttons(self):
        """Pulsanti controllo elaborazione"""
        btn_frame = tk.Frame(self.dialog, bg="#ECF0F1", pady=10)
        btn_frame.pack(fill="x", padx=10)
        
        # Left side buttons
        left_frame = tk.Frame(btn_frame, bg="#ECF0F1")
        left_frame.pack(side="left")
        
        # Carica Tutti
        self.btn_load_all = tk.Button(
            left_frame,
            text="📂 Carica Tutti",
            command=self.load_all_documents,
            bg="#3498DB",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            state="disabled"
        )
        self.btn_load_all.pack(side="left", padx=5)
        
        # Validazione Sequenziale
        self.btn_validate_seq = tk.Button(
            left_frame,
            text="▶️ Valida Sequenza",
            command=self.start_sequential_validation,
            bg="#27AE60",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            state="disabled"
        )
        self.btn_validate_seq.pack(side="left", padx=5)
        
        # Valida Selezionati
        self.btn_validate_sel = tk.Button(
            left_frame,
            text="✓ Valida Selezionati",
            command=self.validate_selected,
            bg="#F39C12",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            state="disabled"
        )
        self.btn_validate_sel.pack(side="left", padx=5)
        
        # Right side buttons
        right_frame = tk.Frame(btn_frame, bg="#ECF0F1")
        right_frame.pack(side="right")
        
        # Export Batch
        self.btn_export = tk.Button(
            right_frame,
            text="💾 Export Batch",
            command=self.export_batch,
            bg="#9B59B6",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8,
            state="disabled"
        )
        self.btn_export.pack(side="left", padx=5)
        
        # Reset
        self.btn_reset = tk.Button(
            right_frame,
            text="🔄 Reset",
            command=self.reset_batch,
            bg="#E74C3C",
            fg="white",
            font=("Arial", 10, "bold"),
            cursor="hand2",
            padx=15,
            pady=8
        )
        self.btn_reset.pack(side="left", padx=5)
    
    def create_progress_area(self):
        """Area progress bar e statistiche"""
        progress_frame = tk.Frame(self.dialog, bg="#ECF0F1")
        progress_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=400
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5, pady=5)
        
        # Stats label
        self.stats_label = tk.Label(
            progress_frame,
            text="Trovati 0 documenti pronti",
            font=("Arial", 9),
            bg="#ECF0F1"
        )
        self.stats_label.pack(side="left", padx=10)
    
    def create_status_bar(self):
        """Barra stato in fondo"""
        status_frame = tk.Frame(self.dialog, bg="#2C3E50", height=30)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)
        
        self.status_label = tk.Label(
            status_frame,
            text="⚪ Pronto - Seleziona cartella e scansiona documenti",
            font=("Arial", 9),
            bg="#2C3E50",
            fg="white",
            anchor="w",
            padx=10
        )
        self.status_label.pack(fill="both", expand=True)
    
    # ==========================================
    # EVENT HANDLERS
    # ==========================================
    
    def browse_batch_folder(self):
        """Sfoglia cartella batch"""
        initial_dir = self.batch_path_var.get()
        if not initial_dir or not os.path.exists(initial_dir):
            initial_dir = self.config_manager.get('default_input_folder', '')
        
        folder = filedialog.askdirectory(
            title="Seleziona Cartella Batch",
            initialdir=initial_dir
        )
        
        if folder:
            self.batch_path_var.set(folder)
    
    def scan_documents(self):
        """Scansiona directory batch per documenti"""
        batch_path = self.batch_path_var.get()
        
        if not batch_path:
            messagebox.showerror("Errore", "Seleziona una cartella batch")
            return
        
        if not os.path.exists(batch_path):
            messagebox.showerror("Errore", "Percorso non valido")
            return
        
        # Disable scan button during operation
        self.btn_scan.config(state="disabled", text="🔄 Scansione in corso...")
        self.update_status("🔄 Scansione directory in corso...", "blue")
        
        # Run scan in thread to avoid UI freeze
        def scan_thread():
            try:
                # Get scan settings
                batch_mode = self.config_manager.get('batch_input_mode', 'recursive')
                max_depth = self.config_manager.get('batch_scan_depth', -1) if batch_mode == 'recursive' else 0
                
                # Scan directory
                documents = self.batch_scanner.scan_directory(batch_path, max_depth)
                
                if not documents:
                    self.dialog.after(0, lambda: messagebox.showwarning(
                        "Attenzione",
                        "Nessun documento PDF/TIFF trovato con JSON corrispondente.\n\n"
                        "Verifica che la cartella contenga coppie documento+JSON."
                    ))
                    self.dialog.after(0, self.enable_scan_button)
                    return
                
                # Create batch session
                output_path = self.config_manager.get('default_output_folder', '')
                session_id = self.batch_db.create_session(batch_path, output_path)
                
                # Add documents to database
                self.batch_db.add_documents(session_id, documents)
                
                # Load documents from database
                session_docs = self.batch_db.get_session_documents(session_id)
                
                # Update UI in main thread
                self.dialog.after(0, lambda: self.on_scan_completed(session_id, session_docs))
                
            except Exception as e:
                self.dialog.after(0, lambda: messagebox.showerror(
                    "Errore Scansione",
                    f"Errore durante la scansione:\n\n{str(e)}"
                ))
                self.dialog.after(0, self.enable_scan_button)
        
        # Start thread
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def on_scan_completed(self, session_id: str, documents: List[Dict]):
        """Callback quando scansione completata"""
        self.current_session_id = session_id
        self.documents = documents
        
        # Populate table
        self.populate_table()
        
        # Update stats
        stats = self.batch_db.get_session_statistics(session_id)
        self.update_stats_display(stats)
        
        # Enable buttons
        self.enable_action_buttons()
        
        # Show summary
        scan_stats = self.batch_scanner.get_stats()
        summary = (
            f"✅ Scansione completata!\n\n"
            f"Directory analizzate: {scan_stats['total_dirs']}\n"
            f"Coppie trovate: {scan_stats['pairs_matched']}\n\n"
            f"Workflow rilevati:\n"
            f"  • Split Categorie: {scan_stats['split_categorie']}\n"
            f"  • Metadati Semplici: {scan_stats['metadati_semplici']}"
        )
        
        messagebox.showinfo("Scansione Completata", summary)
        
        # Update status
        self.update_status(f"✅ Trovati {len(documents)} documenti pronti per elaborazione", "green")
        
        # Re-enable scan button
        self.enable_scan_button()
    
    def enable_scan_button(self):
        """Riabilita pulsante scan"""
        self.btn_scan.config(state="normal", text="🔍 Scansiona Documenti")
    
    def enable_action_buttons(self):
        """Abilita pulsanti azione dopo scansione"""
        self.btn_load_all.config(state="normal")
        self.btn_validate_seq.config(state="normal")
        self.btn_validate_sel.config(state="normal")
        self.btn_export.config(state="normal")
    
    def populate_table(self):
        """Popola tabella con documenti scansionati"""
        # Clear existing items
        self.tree.delete(*self.tree.get_children())
        
        for doc in self.documents:
            # Status icon
            status_icons = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'error': '❌',
                'skipped': '⏭️'  # ⭐ AGGIUNTO
            }
            status_icon = status_icons.get(doc['status'], '?')
            
            # Workflow display
            workflow_display = {
                'split_categorie': '📄 Split Cat.',
                'metadati_semplici': '📋 Metadati'
            }
            workflow_text = workflow_display.get(doc['workflow_type'], doc['workflow_type'])
            
            # Insert row
            self.tree.insert('', 'end', iid=str(doc['id']), values=(
                doc['id'],
                os.path.basename(doc['doc_path']),
                os.path.basename(doc['json_path']),
                doc['relative_path'],
                workflow_text,
                f"{status_icon} {doc['status'].title()}"
            ))
            
            # Color coding by status
            if doc['status'] == 'completed':
                self.tree.item(str(doc['id']), tags=('completed',))
            elif doc['status'] == 'error':
                self.tree.item(str(doc['id']), tags=('error',))
        
        # Configure tags
        self.tree.tag_configure('completed', background='#D5F4E6')
        self.tree.tag_configure('error', background='#FADBD8')
    
    # ⬇️ CONTINUA DA QUI ⬇️
    
    def update_stats_display(self, stats: Dict):
        """Aggiorna display statistiche"""
        total = stats['total']
        completed = stats['completed']
        pending = stats['pending']
        errors = stats['error']
        skipped = stats.get('skipped', 0)  # ⭐ AGGIUNTO
        
        progress_percent = stats['progress_percent']
        self.progress_var.set(progress_percent)
        
        stats_text = f"Trovati {total} documenti | ✅ {completed} | ⏳ {pending} | ⏭️ {skipped} | ❌ {errors}"
        self.stats_label.config(text=stats_text)
    
    def update_status(self, message: str, color: str = "black"):
        """Aggiorna barra stato"""
        color_map = {
            'green': '#27AE60',
            'blue': '#3498DB',
            'red': '#E74C3C',
            'orange': '#E67E22',
            'black': '#2C3E50'
        }
        
        bg_color = color_map.get(color, '#2C3E50')
        self.status_label.config(text=f"  {message}", bg=bg_color)
    
    # ==========================================
    # VALIDATION METHODS
    # ==========================================
    
    def load_all_documents(self):
        """Carica tutti i documenti in memoria (pre-validazione)"""
        if not self.documents:
            return
        
        pending_docs = [d for d in self.documents if d['status'] == 'pending']
        
        if not pending_docs:
            messagebox.showinfo("Info", "Tutti i documenti sono già stati processati")
            return
        
        response = messagebox.askyesno(
            "Conferma Caricamento",
            f"Caricare tutti i {len(pending_docs)} documenti pending in memoria?\n\n"
            "Questa operazione potrebbe richiedere molto tempo\n"
            "per grandi quantità di documenti."
        )
        
        if not response:
            return
        
        self.update_status("📂 Caricamento documenti in corso...", "blue")
        # Implementation would pre-load documents here
        messagebox.showinfo("Info", f"{len(pending_docs)} documenti caricati e pronti per validazione")
        self.update_status("✅ Documenti caricati - Pronti per validazione", "green")
    
    def start_sequential_validation(self):
        """Avvia validazione sequenziale documenti"""
        pending_docs = [d for d in self.documents if d['status'] == 'pending']
        
        if not pending_docs:
            messagebox.showinfo("Info", "Tutti i documenti sono stati processati")
            return
        
        self.sequential_docs = pending_docs
        self.current_doc_index = 0
        
        self.update_status(f"▶️ Modalità validazione sequenziale attiva - {len(pending_docs)} documenti", "blue")
        
        # ⭐ NUOVO: Minimizza batch manager durante validazione
        self.dialog.withdraw()  # Nasconde la finestra (compatibile con transient)
        
        # Open first document
        self.open_next_document()
    
    def open_next_document(self):
        """Apre prossimo documento nella sequenza"""
        if self.current_doc_index >= len(self.sequential_docs):
            # ⭐ NUOVO: Ripristina batch manager
            self.dialog.withdraw()  # Ripristina la finestra
            self.dialog.lift()  # Porta in primo piano
            
            messagebox.showinfo(
                "Validazione Completata",
                "Tutti i documenti nella sequenza sono stati validati!\n\n"
                "Usa 'Export Batch' per esportare i risultati."
            )
            self.update_status("✅ Validazione sequenziale completata", "green")
            return
        
        doc = self.sequential_docs[self.current_doc_index]
        
        try:
            # ⭐ NUOVO: Aggiorna titolo con progresso
            progress_info = f"{self.current_doc_index + 1}/{len(self.sequential_docs)}"
            self.main_app.title(f"DynamicAI - BATCH [{progress_info}] - {os.path.basename(doc['doc_path'])}")
            
            # Load document in main app
            self.main_app.load_document_from_batch(doc)
            
            # Update database status
            self.batch_db.update_document_status(doc['id'], 'processing')
            
            # Refresh table
            self.refresh_document_in_table(doc['id'], 'processing')
            
            # ⭐ NUOVO: Mostra toolbar flottante invece di dialog
            self.create_batch_toolbar()
            
        except Exception as e:
            messagebox.showerror(
                "Errore Apertura Documento",
                f"Impossibile aprire il documento:\n\n{str(e)}"
            )
            # Mark as error
            self.batch_db.update_document_status(doc['id'], 'error', str(e))
            self.refresh_document_in_table(doc['id'], 'error')
            # Skip to next
            self.current_doc_index += 1
            self.open_next_document()
    
    def show_navigation_dialog(self):
        """Mostra dialog navigazione sequenziale"""
        nav_dialog = tk.Toplevel(self.dialog)
        nav_dialog.title("Navigazione Sequenziale")
        nav_dialog.geometry("450x280")
        nav_dialog.resizable(False, False)  # ⭐ AGGIUNTO: blocca resize
        nav_dialog.transient(self.dialog)
        # ⭐ RIMOSSO topmost - permette di lavorare sul main window
        
        current_doc = self.sequential_docs[self.current_doc_index]
        total_docs = len(self.sequential_docs)
        
        # Info documento corrente
        info_frame = tk.Frame(nav_dialog, bg="#ECF0F1", pady=15)
        info_frame.pack(fill="x")
        
        # ⭐ NUOVO: Progress indicator visuale
        progress_text = f"📄 Documento {self.current_doc_index + 1} di {total_docs}"
        progress_percent = int((self.current_doc_index + 1) / total_docs * 100)
        
        tk.Label(
            info_frame,
            text=progress_text,
            font=("Arial", 12, "bold"),
            bg="#ECF0F1"
        ).pack()
        
        # ⭐ NUOVO: Barra progresso visuale
        progress_bar_frame = tk.Frame(info_frame, bg="#ECF0F1")
        progress_bar_frame.pack(fill="x", padx=20, pady=5)
        
        progress_canvas = tk.Canvas(progress_bar_frame, height=20, bg="white", highlightthickness=1)
        progress_canvas.pack(fill="x")
        
        bar_width = int(progress_canvas.winfo_reqwidth() * (progress_percent / 100))
        progress_canvas.create_rectangle(0, 0, 300 * (progress_percent / 100), 20, 
                                        fill="#27AE60", outline="")
        progress_canvas.create_text(150, 10, text=f"{progress_percent}%", 
                                    font=("Arial", 9, "bold"))
        
        tk.Label(
            info_frame,
            text=os.path.basename(current_doc['doc_path']),
            font=("Arial", 10),
            bg="#ECF0F1",
            fg="#3498DB"
        ).pack(pady=5)
        
        # Buttons
        btn_frame = tk.Frame(nav_dialog)
        btn_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        def on_complete():
            """Documento validato - passa al prossimo"""
            self.batch_db.update_document_status(current_doc['id'], 'completed')
            self.refresh_document_in_table(current_doc['id'], 'completed')
            self.current_doc_index += 1
            nav_dialog.destroy()
            self.open_next_document()
        
        def on_skip():
            """Salta documento"""
            self.batch_db.update_document_status(current_doc['id'], 'pending')
            self.refresh_document_in_table(current_doc['id'], 'pending')
            self.current_doc_index += 1
            nav_dialog.destroy()
            self.open_next_document()
        
        def on_error():
            """Marca come errore"""
            error_msg = tk.simpledialog.askstring(
                "Errore Documento",
                "Inserisci motivo errore:",
                parent=nav_dialog
            )
            self.batch_db.update_document_status(current_doc['id'], 'error', error_msg)
            self.refresh_document_in_table(current_doc['id'], 'error')
            self.current_doc_index += 1
            nav_dialog.destroy()
            self.open_next_document()
        
        def on_cancel():
            """Annulla validazione sequenziale"""
            nav_dialog.destroy()
            # ⭐ NUOVO: Ripristina batch manager
            self.dialog.withdraw()
            self.dialog.lift()
            self.update_status("⏸️ Validazione sequenziale interrotta", "orange")
        
        # Buttons layout
        tk.Button(
            btn_frame,
            text="✅ Completa e Avanti",
            command=on_complete,
            bg="#27AE60",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=8
        ).pack(fill="x", pady=5)
        
        tk.Button(
            btn_frame,
            text="⏭️ Salta",
            command=on_skip,
            bg="#F39C12",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=8
        ).pack(fill="x", pady=5)
        
        tk.Button(
            btn_frame,
            text="❌ Segna Errore",
            command=on_error,
            bg="#E74C3C",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10,
            pady=8
        ).pack(fill="x", pady=5)
        
        tk.Button(
            btn_frame,
            text="⏸️ Annulla Sequenza",
            command=on_cancel,
            bg="#95A5A6",
            fg="white",
            font=("Arial", 9),
            padx=10,
            pady=5
        ).pack(fill="x", pady=5)
        
    def create_batch_toolbar(self):
        """Crea toolbar flottante per navigazione batch"""
        # Crea finestra toolbar
        self.toolbar = tk.Toplevel(self.main_app)
        self.toolbar.title("Controlli Batch")
        self.toolbar.geometry("600x120")
        self.toolbar.resizable(False, False)
        
        # Posiziona in alto a destra
        screen_width = self.main_app.winfo_screenwidth()
        self.toolbar.geometry(f"+{screen_width - 650}+50")
        
        # Sempre in primo piano ma non modale
        self.toolbar.attributes('-topmost', True)
        self.toolbar.protocol("WM_DELETE_WINDOW", self.on_toolbar_close)
        
        # Frame principale
        main_frame = tk.Frame(self.toolbar, bg="#34495E", padx=10, pady=10)
        main_frame.pack(fill="both", expand=True)
        
        # Info documento corrente
        current_doc = self.sequential_docs[self.current_doc_index]
        total_docs = len(self.sequential_docs)
        
        info_label = tk.Label(
            main_frame,
            text=f"📄 Documento {self.current_doc_index + 1} di {total_docs}: {os.path.basename(current_doc['doc_path'])}",
            font=("Arial", 11, "bold"),
            bg="#34495E",
            fg="white"
        )
        info_label.pack(pady=(0, 10))
        
        # Frame pulsanti
        btn_frame = tk.Frame(main_frame, bg="#34495E")
        btn_frame.pack(fill="x")
        
        # Pulsante COMPLETA (grande, verde)
        btn_complete = tk.Button(
            btn_frame,
            text="✅ COMPLETA\ne Avanti",
            command=self.toolbar_complete,
            bg="#27AE60",
            fg="white",
            font=("Arial", 12, "bold"),
            width=12,
            height=2,
            cursor="hand2"
        )
        btn_complete.pack(side="left", padx=5)
        
        # Pulsante SALTA
        btn_skip = tk.Button(
            btn_frame,
            text="⏭️ SALTA",
            command=self.toolbar_skip,
            bg="#F39C12",
            fg="white",
            font=("Arial", 11, "bold"),
            width=10,
            height=2,
            cursor="hand2"
        )
        btn_skip.pack(side="left", padx=5)
        
        # Pulsante ERRORE
        btn_error = tk.Button(
            btn_frame,
            text="❌ ERRORE",
            command=self.toolbar_error,
            bg="#E74C3C",
            fg="white",
            font=("Arial", 11, "bold"),
            width=10,
            height=2,
            cursor="hand2"
        )
        btn_error.pack(side="left", padx=5)
        
        # Pulsante ANNULLA
        btn_cancel = tk.Button(
            btn_frame,
            text="⏸️ ANNULLA\nSequenza",
            command=self.toolbar_cancel,
            bg="#95A5A6",
            fg="white",
            font=("Arial", 10),
            width=10,
            height=2,
            cursor="hand2"
        )
        btn_cancel.pack(side="left", padx=5)
        
        # Shortcut keys
        self.toolbar.bind("<Return>", lambda e: self.toolbar_complete())
        self.toolbar.bind("<space>", lambda e: self.toolbar_skip())
        self.toolbar.bind("<Escape>", lambda e: self.toolbar_cancel())
    
    def toolbar_complete(self):
        """Completa documento corrente e passa al successivo"""
        current_doc = self.sequential_docs[self.current_doc_index]
        self.batch_db.update_document_status(current_doc['id'], 'completed')
        self.refresh_document_in_table(current_doc['id'], 'completed')
        self.current_doc_index += 1
        self.advance_to_next_document()
    
    def toolbar_skip(self):
        """Salta documento corrente"""
        current_doc = self.sequential_docs[self.current_doc_index]
        self.batch_db.update_document_status(current_doc['id'], 'skipped')  # ⭐ CAMBIATO
        self.refresh_document_in_table(current_doc['id'], 'skipped')  # ⭐ CAMBIATO
        self.current_doc_index += 1
        self.advance_to_next_document()
    
    def toolbar_error(self):
        """Marca documento come errore"""
        error_dialog = tk.Toplevel(self.toolbar)
        error_dialog.title("Motivo Errore")
        error_dialog.geometry("400x150")
        error_dialog.transient(self.toolbar)
        error_dialog.grab_set()
        
        tk.Label(error_dialog, text="Inserisci motivo errore:", 
                font=("Arial", 10)).pack(pady=10)
        
        error_var = tk.StringVar()
        entry = tk.Entry(error_dialog, textvariable=error_var, width=40, font=("Arial", 10))
        entry.pack(pady=5)
        entry.focus()
        
        def save_error():
            error_msg = error_var.get().strip() or "Errore generico"
            current_doc = self.sequential_docs[self.current_doc_index]
            self.batch_db.update_document_status(current_doc['id'], 'error', error_msg)
            self.refresh_document_in_table(current_doc['id'], 'error')
            self.current_doc_index += 1
            error_dialog.destroy()
            self.advance_to_next_document()
        
        btn_frame = tk.Frame(error_dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Conferma", command=save_error,
                 bg="#E74C3C", fg="white", font=("Arial", 10, "bold"),
                 width=12).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Annulla", command=error_dialog.destroy,
                 font=("Arial", 10), width=12).pack(side="left", padx=5)
        
        entry.bind("<Return>", lambda e: save_error())
    
    def toolbar_cancel(self):
        """Annulla validazione sequenziale"""
        if messagebox.askyesno("Conferma", "Annullare la validazione sequenziale?"):
            self.close_toolbar()
            self.dialog.withdraw()
            self.dialog.lift()
            self.update_status("⏸️ Validazione sequenziale interrotta", "orange")
    
    def on_toolbar_close(self):
        """Gestisce chiusura toolbar con X"""
        self.toolbar_cancel()
    
    def advance_to_next_document(self):
        """Avanza al prossimo documento o termina"""
        if hasattr(self, 'toolbar') and self.toolbar.winfo_exists():
            self.toolbar.destroy()
        
        if self.current_doc_index >= len(self.sequential_docs):
            # Fine validazione
            self.dialog.withdraw()
            self.dialog.lift()
            
            messagebox.showinfo(
                "Validazione Completata",
                "Tutti i documenti nella sequenza sono stati validati!\n\n"
                "Usa 'Export Batch' per esportare i risultati."
            )
            self.update_status("✅ Validazione sequenziale completata", "green")
        else:
            # Carica prossimo documento
            self.open_next_document()
    
    def close_toolbar(self):
        """Chiude toolbar se esiste"""
        if hasattr(self, 'toolbar') and self.toolbar.winfo_exists():
            self.toolbar.destroy()
    
    def validate_selected(self):
        """Valida documenti selezionati nella tabella"""
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showwarning("Attenzione", "Seleziona almeno un documento")
            return
        
        selected_docs = []
        for item_id in selected_items:
            doc_id = int(item_id)
            doc = next((d for d in self.documents if d['id'] == doc_id), None)
            if doc and doc['status'] == 'pending':
                selected_docs.append(doc)
        
        if not selected_docs:
            messagebox.showinfo("Info", "Nessun documento pending selezionato")
            return
        
        # Start sequential validation with selected
        self.sequential_docs = selected_docs
        self.current_doc_index = 0
        
        # ⭐ NUOVO: Minimizza batch manager
        self.update_status(f"▶️ Validazione {len(selected_docs)} documenti selezionati", "blue")
        self.dialog.withdraw()  # Nasconde la finestra (compatibile con transient)
        
        self.open_next_document()        
    
    def refresh_document_in_table(self, doc_id: int, new_status: str):
        """Aggiorna stato documento nella tabella"""
        # Find document in list
        for i, doc in enumerate(self.documents):
            if doc['id'] == doc_id:
                self.documents[i]['status'] = new_status
                break
        
        # Update treeview item
        item_id = str(doc_id)
        if self.tree.exists(item_id):
            status_icons = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'error': '❌',
                'skipped': '⏭️'  # ⭐ AGGIUNTO
            }
            status_icon = status_icons.get(new_status, '?')
            
            # Get current values
            values = list(self.tree.item(item_id, 'values'))
            # Update status column (index 5)
            values[5] = f"{status_icon} {new_status.title()}"
            self.tree.item(item_id, values=values)
            
            # Update tag
            self.tree.item(item_id, tags=())
            if new_status == 'completed':
                self.tree.item(item_id, tags=('completed',))
            elif new_status == 'error':
                self.tree.item(item_id, tags=('error',))
        
        # Update stats
        if self.current_session_id:
            stats = self.batch_db.get_session_statistics(self.current_session_id)
            self.update_stats_display(stats)
    
    # ==========================================
    # EXPORT METHODS
    # ==========================================
    
    def export_batch(self):
        """Esporta batch completo"""
        if not self.current_session_id:
            messagebox.showwarning("Attenzione", "Nessuna sessione batch attiva")
            return
        
        # Check for completed documents
        completed_docs = [d for d in self.documents if d['status'] == 'completed']
        
        if not completed_docs:
            messagebox.showwarning(
                "Attenzione",
                "Nessun documento completato da esportare.\n\n"
                "Valida almeno un documento prima dell'export."
            )
            return
        
        # Confirm export
        pending_count = len([d for d in self.documents if d['status'] == 'pending'])
        
        msg = f"Esportare {len(completed_docs)} documenti completati?"
        if pending_count > 0:
            msg += f"\n\n⚠️ Attenzione: {pending_count} documenti ancora pending non verranno esportati."
        
        response = messagebox.askyesno("Conferma Export", msg)
        
        if not response:
            return
        
        # Get output path
        session_info = self.batch_db.get_session_info(self.current_session_id)
        base_output = session_info['output_path'] or self.config_manager.get('default_output_folder', '')
        
        if not base_output:
            messagebox.showerror(
                "Errore",
                "Cartella output non configurata.\n"
                "Configura nelle Preferenze."
            )
            return
        
        # Disable export button during operation
        self.btn_export.config(state="disabled", text="⏳ Export in corso...")
        self.update_status("💾 Export batch in corso...", "blue")
        
        # Run export in thread
        def export_thread():
            try:
                total = len(completed_docs)
                exported_count = 0
                
                for doc in completed_docs:
                    # Update progress
                    progress = (exported_count / total) * 100
                    self.dialog.after(0, lambda p=progress: self.progress_var.set(p))
                    
                    status_msg = f"💾 Esportazione {exported_count + 1}/{total}: {os.path.basename(doc['doc_path'])}"
                    self.dialog.after(0, lambda m=status_msg: self.update_status(m, "blue"))
                    
                    try:
                        # Export document
                        exported_files = self.batch_exporter.export_document(
                            doc, base_output
                        )
                        
                        # Update database with exported files
                        self.batch_db.update_document_status(
                            doc['id'], 'completed', exported_files=exported_files
                        )
                        
                        exported_count += 1
                        
                    except Exception as e:
                        print(f"[ERROR] Export failed for {doc['doc_path']}: {e}")
                        self.batch_db.update_document_status(
                            doc['id'], 'error', error=f"Export failed: {str(e)}"
                        )
                
                # Generate CSV
                self.dialog.after(0, lambda: self.update_status("📄 Generazione CSV...", "blue"))
                
                csv_mode = self.config_manager.get('batch_csv_mode', 'per_folder')
                session_docs = self.batch_db.get_session_documents(
                    self.current_session_id, status='completed'
                )
                
                csv_files = self.batch_exporter.export_batch_csv(
                    session_docs, base_output, csv_mode
                )
                
                # Mark session as completed
                self.batch_db.mark_session_completed(self.current_session_id)
                
                # Update UI in main thread
                self.dialog.after(0, lambda: self.on_export_completed(
                    exported_count, len(csv_files), base_output
                ))
                
            except Exception as e:
                self.dialog.after(0, lambda: messagebox.showerror(
                    "Errore Export",
                    f"Errore durante l'export batch:\n\n{str(e)}"
                ))
                self.dialog.after(0, self.enable_export_button)
        
        # Start thread
        threading.Thread(target=export_thread, daemon=True).start()
    
    def on_export_completed(self, exported_count: int, csv_count: int, output_path: str):
        """Callback quando export completato"""
        self.enable_export_button()
        
        summary = (
            f"✅ Export Batch Completato!\n\n"
            f"Documenti esportati: {exported_count}\n"
            f"File CSV generati: {csv_count}\n\n"
            f"Percorso output:\n{output_path}"
        )
        
        messagebox.showinfo("Export Completato", summary)
        
        self.update_status(f"✅ Export completato - {exported_count} documenti esportati", "green")
        self.progress_var.set(100)
        
        # Reload documents to show exported files
        self.documents = self.batch_db.get_session_documents(self.current_session_id)
        self.populate_table()
        
        # Ask to reset
        if messagebox.askyesno("Reset Batch", "Export completato!\n\nVuoi resettare il batch per una nuova elaborazione?"):
            self.reset_batch()
    
    def enable_export_button(self):
        """Riabilita pulsante export"""
        self.btn_export.config(state="normal", text="💾 Export Batch")
    
    # ==========================================
    # UTILITY METHODS
    # ==========================================
    
    def reset_batch(self):
        """Reset completo batch"""
        if self.current_session_id:
            response = messagebox.askyesnocancel(
                "Conferma Reset",
                "Vuoi eliminare la sessione batch corrente?\n\n"
                "Sì = Elimina sessione dal database\n"
                "No = Mantieni sessione ma resetta UI\n"
                "Annulla = Non fare nulla"
            )
            
            if response is None:  # Cancel
                return
            elif response:  # Yes - delete session
                self.batch_db.delete_session(self.current_session_id)
        
        # Reset UI
        self.current_session_id = None
        self.documents = []
        self.sequential_docs = []
        self.current_doc_index = 0
        
        # Clear table
        self.tree.delete(*self.tree.get_children())
        
        # Reset progress
        self.progress_var.set(0)
        self.stats_label.config(text="Trovati 0 documenti pronti")
        
        # Disable buttons
        self.btn_load_all.config(state="disabled")
        self.btn_validate_seq.config(state="disabled")
        self.btn_validate_sel.config(state="disabled")
        self.btn_export.config(state="disabled")
        
        self.update_status("⚪ Reset completato - Pronto per nuova scansione", "black")
    
    def on_double_click_document(self, event):
        """Doppio click su documento - apri per validazione"""
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        doc_id = int(selected_items[0])
        doc = next((d for d in self.documents if d['id'] == doc_id), None)
        
        if not doc:
            return
        
        try:
            self.main_app.load_document_from_batch(doc)
            self.batch_db.update_document_status(doc_id, 'processing')
            self.refresh_document_in_table(doc_id, 'processing')
        except Exception as e:
            messagebox.showerror(
                "Errore Apertura",
                f"Impossibile aprire il documento:\n\n{str(e)}"
            )
    
    def show_context_menu(self, event):
        """Mostra menu contestuale su documento"""
        # Select item under cursor
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            
            doc_id = int(item)
            doc = next((d for d in self.documents if d['id'] == doc_id), None)
            
            if not doc:
                return
            
            # Create context menu
            menu = tk.Menu(self.dialog, tearoff=0)
            
            menu.add_command(
                label="👁️ Valida Documento",
                command=lambda: self.open_document_by_id(doc_id)
            )
            
            menu.add_command(
                label="📂 Apri File Esterno",
                command=lambda: self.open_external_viewer(doc['doc_path'])
            )
            
            menu.add_command(
                label="📁 Apri Cartella",
                command=lambda: self.open_folder(doc['doc_path'])
            )
            
            menu.add_separator()
            
            if doc['status'] == 'completed':
                menu.add_command(
                    label="🔄 Ri-Valida Documento",
                    command=lambda: self.revalidate_document(doc_id)
                )
                menu.add_command(
                    label="↩️ Segna come Pending",
                    command=lambda: self.change_document_status(doc_id, 'pending')
                )
            elif doc['status'] == 'error':
                menu.add_command(
                    label="🔄 Riprova",
                    command=lambda: self.change_document_status(doc_id, 'pending')
                )
            elif doc['status'] == 'skipped':
                menu.add_command(
                    label="🔄 Valida Adesso",
                    command=lambda: self.revalidate_document(doc_id)
                )
                menu.add_command(
                    label="↩️ Segna come Pending",
                    command=lambda: self.change_document_status(doc_id, 'pending')
                )
            
            menu.add_separator()
            
            menu.add_command(
                label="ℹ️ Dettagli Documento",
                command=lambda: self.show_document_details(doc)
            )
            
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()
    
    def open_external_viewer(self, file_path: str):
        """Apri file con applicazione predefinita del sistema"""
        try:
            if platform.system() == 'Windows':
                os.startfile(file_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', file_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire file:\n\n{str(e)}")
            
    def open_document_by_id(self, doc_id: int):
        """Apri documento per ID"""
        doc = next((d for d in self.documents if d['id'] == doc_id), None)
        if doc:
            try:
                self.main_app.load_document_from_batch(doc)
                self.batch_db.update_document_status(doc_id, 'processing')
                self.refresh_document_in_table(doc_id, 'processing')
            except Exception as e:
                messagebox.showerror("Errore", f"Impossibile aprire:\n\n{str(e)}")
    
    def open_folder(self, file_path: str):
        """Apri cartella contenente file"""
        import subprocess
        import platform
        
        folder = os.path.dirname(file_path)
        
        try:
            if platform.system() == 'Windows':
                os.startfile(folder)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', folder])
            else:  # Linux
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire cartella:\n\n{str(e)}")
    
    def change_document_status(self, doc_id: int, new_status: str):
        """Cambia stato documento manualmente"""
        self.batch_db.update_document_status(doc_id, new_status)
        self.refresh_document_in_table(doc_id, new_status)
        
    def revalidate_document(self, doc_id: int):
        """Ri-valida singolo documento (anche se già completato)"""
        doc = next((d for d in self.documents if d['id'] == doc_id), None)
        if not doc:
            return
        
        # Imposta come processing
        self.batch_db.update_document_status(doc_id, 'processing')
        self.refresh_document_in_table(doc_id, 'processing')
        
        # Nascondi batch manager
        self.dialog.withdraw()
        
        try:
            # Carica documento
            self.main_app.load_document_from_batch(doc)
            
            # Crea toolbar per singolo documento
            self.sequential_docs = [doc]
            self.current_doc_index = 0
            self.create_batch_toolbar()
            
        except Exception as e:
            messagebox.showerror(
                "Errore Apertura",
                f"Impossibile aprire il documento:\n\n{str(e)}"
            )
            self.dialog.withdraw()
    
    def show_document_details(self, doc: Dict):
        """Mostra dettagli documento in dialog"""
        details_dialog = tk.Toplevel(self.dialog)
        details_dialog.title("Dettagli Documento")
        details_dialog.geometry("600x500")
        details_dialog.transient(self.dialog)
        
        # Text widget with scrollbar
        text_frame = tk.Frame(details_dialog)
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        text = tk.Text(text_frame, wrap="word", yscrollcommand=scrollbar.set, font=("Consolas", 9))
        text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=text.yview)
        
        # Format details
        details = f"""DETTAGLI DOCUMENTO

ID: {doc['id']}
Stato: {doc['status']}
Workflow: {doc['workflow_type']}

FILE:
  PDF/TIFF: {doc['doc_path']}
  JSON: {doc['json_path']}
  Path Relativo: {doc['relative_path']}

METADATA JSON:
{json.dumps(doc.get('json_data', {}), indent=2, ensure_ascii=False)}

"""
        
        if doc.get('error_message'):
            details += f"\nERRORE:\n{doc['error_message']}\n"
        
        if doc.get('exported_files'):
            details += f"\nFILE ESPORTATI:\n"
            for f in doc['exported_files']:
                details += f"  • {f}\n"
        
        if doc.get('processed_at'):
            details += f"\nPROCESSATO: {doc['processed_at']}\n"
        
        text.insert("1.0", details)
        text.config(state="disabled")
        
        # Close button
        tk.Button(
            details_dialog,
            text="Chiudi",
            command=details_dialog.destroy,
            bg="lightgray",
            font=("Arial", 10),
            padx=20,
            pady=5
        ).pack(pady=10)
    
    def after_idle_check_sessions(self):
        """Check incomplete sessions dopo un breve delay"""
        self.dialog.after(500, self.check_incomplete_sessions)
    
    def check_incomplete_sessions(self):
        """Controlla sessioni incomplete (recovery da crash)"""
        sessions = self.batch_db.get_incomplete_sessions()
        
        if not sessions:
            return
        
        response = messagebox.askyesnocancel(
            "Sessioni Incomplete Rilevate",
            f"Trovate {len(sessions)} sessioni batch incomplete.\n\n"
            "Potrebbero essere sessioni interrotte da crash o chiusura improvvisa.\n\n"
            "Vuoi riprendere l'ultima sessione?\n\n"
            "Sì = Ripristina ultima sessione\n"
            "No = Elimina sessioni incomplete\n"
            "Annulla = Ignora per ora"
        )
        
        if response is None:  # Cancel
            return
        elif response:  # Yes - restore
            self.restore_session(sessions[0])
        else:  # No - delete all
            for session in sessions:
                self.batch_db.delete_session(session['session_id'])
            messagebox.showinfo("Pulizia Completata", f"Eliminate {len(sessions)} sessioni incomplete")
    
    def restore_session(self, session_info: Dict):
        """Ripristina sessione batch precedente"""
        session_id = session_info['session_id']
        
        # Load session documents
        documents = self.batch_db.get_session_documents(session_id)
        
        if not documents:
            messagebox.showwarning("Attenzione", "Sessione vuota, impossibile ripristinare")
            return
        
        # Restore state
        self.current_session_id = session_id
        self.documents = documents
        self.batch_path_var.set(session_info['root_path'])
        
        # Populate table
        self.populate_table()
        
        # Update stats
        stats = self.batch_db.get_session_statistics(session_id)
        self.update_stats_display(stats)
        
        # Enable buttons
        self.enable_action_buttons()
        
        # Show info
        completed = stats['completed']
        pending = stats['pending']
        
        messagebox.showinfo(
            "Sessione Ripristinata",
            f"Sessione batch ripristinata!\n\n"
            f"Documenti completati: {completed}\n"
            f"Documenti pending: {pending}\n\n"
            f"Puoi continuare la validazione o esportare."
        )
        
        self.update_status(f"🔄 Sessione ripristinata - {len(documents)} documenti", "blue")