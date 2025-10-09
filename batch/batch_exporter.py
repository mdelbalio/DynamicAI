"""
Batch Exporter - Gestisce export documenti preservando struttura directory
"""

import os
from typing import List, Dict, Callable
from PIL import Image

from loaders import create_document_loader
from export import ExportManager


class BatchExporter:
    """Gestisce export batch con preservazione struttura multi-livello"""
    
    def __init__(self, config_manager, export_manager: ExportManager = None):
        """
        Inizializza exporter
        
        Args:
            config_manager: Gestore configurazione
            export_manager: ExportManager esistente (opzionale)
        """
        self.config_manager = config_manager
        
        if export_manager:
            self.export_manager = export_manager
        else:
            self.export_manager = ExportManager(config_manager.config_data)
    
    def export_document(self, doc_dict: Dict, base_output: str,
                       progress_callback: Callable = None) -> List[str]:
        """
        Esporta singolo documento preservando struttura directory
        
        Args:
            doc_dict: Dizionario documento da database
            base_output: Cartella output base
            progress_callback: Funzione callback per progress (opzionale)
            
        Returns:
            Lista file esportati
        """
        try:
            # ⭐ NUOVO: Determina output directory con flag configurazione
            preserve_structure = self.config_manager.get('batch_preserve_structure', True)
            
            if preserve_structure:
                # Preserva struttura cartelle
                relative_path = doc_dict.get('relative_path', '.')
                
                # ⭐ FIX: Se relative_path è '.', estrai nome cartella dal doc_path
                if relative_path == '.':
                    # Estrai nome cartella parent del documento
                    doc_path = doc_dict['doc_path']
                    folder_name = os.path.basename(os.path.dirname(doc_path))
                    
                    # Se la cartella parent è la root batch, usa il nome
                    if folder_name:
                        output_dir = os.path.join(base_output, folder_name)
                        print(f"[BATCH EXPORT] Extracted folder name: {folder_name}")
                    else:
                        # Fallback: usa base_output
                        output_dir = base_output
                        print(f"[BATCH EXPORT] No folder name, using base output")
                else:
                    # relative_path è valido, usalo
                    output_dir = os.path.join(base_output, relative_path)
                    print(f"[BATCH EXPORT] Using relative_path: {relative_path}")
                
                print(f"[BATCH EXPORT] Preserving structure → {output_dir}")
            else:
                # Modalità flat: tutto nella cartella base
                output_dir = base_output
                print(f"[BATCH EXPORT] Flat mode: {output_dir}")
            
            # Crea cartella se non esiste
            os.makedirs(output_dir, exist_ok=True)
            
            # Carica documento
            doc_path = doc_dict['doc_path']
            loader = create_document_loader(doc_path)
            loader.load()
            
            # Estrai nome base documento
            doc_basename = os.path.splitext(os.path.basename(doc_path))[0]
            
            # Elabora in base a workflow
            workflow_type = doc_dict['workflow_type']
            json_data = doc_dict.get('json_data', {})
            
            if workflow_type == 'split_categorie':
                exported = self._export_split_categorie(
                    loader, doc_basename, json_data, output_dir, progress_callback
                )
            else:
                exported = self._export_metadati_semplici(
                    loader, doc_basename, json_data, output_dir, progress_callback
                )
            
            return exported
            
        except Exception as e:
            raise Exception(f"Errore export documento {doc_dict['doc_path']}: {str(e)}")
    
    def _export_split_categorie(self, loader, doc_basename: str, json_data: Dict,
                                output_dir: str, progress_callback: Callable) -> List[str]:
        """Export per workflow Split Categorie"""
        from gui.components import DocumentGroup
        
        # Crea document groups temporanei
        categories = json_data.get('categories', [])
        document_groups = []
        
        # Raggruppa pagine per categoria (come in main_window.py)
        current_group_name = None
        current_pages = []
        documents = []
        
        for cat in categories:
            cat_name = cat['categoria']
            start = cat['inizio']
            end = cat['fine']
            
            if cat_name == "Pagina vuota" and current_group_name is not None:
                for p in range(start, end + 1):
                    current_pages.append(p)
            else:
                if current_group_name is not None:
                    documents.append({
                        "categoria": current_group_name,
                        "pagine": current_pages.copy()
                    })
                current_group_name = cat_name
                current_pages = list(range(start, end + 1))
        
        if current_group_name is not None:
            documents.append({
                "categoria": current_group_name,
                "pagine": current_pages.copy()
            })
        
        # Simula DocumentGroup per export
        class TempDocumentGroup:
            def __init__(self, category_name, pages, counter):
                self.categoryname = category_name
                self.pages = pages
                self.document_counter = counter
                self.thumbnails = []
                
                # Crea thumbnails mock
                for page_num in pages:
                    thumb = type('obj', (object,), {
                        'pagenum': page_num,
                        'image': loader.get_page(page_num)
                    })()
                    self.thumbnails.append(thumb)
        
        # Crea groups temporanei
        temp_groups = []
        for idx, doc in enumerate(documents, 1):
            group = TempDocumentGroup(doc["categoria"], doc["pagine"], idx)
            temp_groups.append(group)
        
        # Export usando ExportManager
        exported_files = self.export_manager.export_documents(
            output_dir, temp_groups, doc_basename, progress_callback
        )
        
        return exported_files
    
    def _export_metadati_semplici(self, loader, doc_basename: str, json_data: Dict,
                                  output_dir: str, progress_callback: Callable) -> List[str]:
        """Export per workflow Metadati Semplici"""
        # Crea singolo document group con tutte le pagine
        class TempDocumentGroup:
            def __init__(self, category_name, total_pages):
                self.categoryname = category_name
                self.pages = list(range(1, total_pages + 1))
                self.document_counter = 1
                self.thumbnails = []
                
                for page_num in self.pages:
                    thumb = type('obj', (object,), {
                        'pagenum': page_num,
                        'image': loader.get_page(page_num)
                    })()
                    self.thumbnails.append(thumb)
        
        # Usa nome documento come categoria
        group = TempDocumentGroup(doc_basename, loader.totalpages)
        
        # Export
        exported_files = self.export_manager.export_documents(
            output_dir, [group], doc_basename, progress_callback
        )
        
        return exported_files
    
    def _get_unique_filename(self, output_dir: str, filename: str) -> str:
        """
        Genera nome file unico con suffisso (1), (2) stile Windows
        
        Args:
            output_dir: Directory output
            filename: Nome file originale
            
        Returns:
            Path completo con nome univoco
            
        Example:
            doc.pdf → doc.pdf (se non esiste)
            doc.pdf → doc(1).pdf (se esiste)
            doc.pdf → doc(2).pdf (se esiste doc(1).pdf)
        """
        base_path = os.path.join(output_dir, filename)
        
        if not os.path.exists(base_path):
            return base_path
        
        name, ext = os.path.splitext(filename)
        counter = 1
        
        while True:
            new_name = f"{name}({counter}){ext}"
            new_path = os.path.join(output_dir, new_name)
            
            if not os.path.exists(new_path):
                return new_path
            
            counter += 1
            
            # Safety limit
            if counter > 9999:
                raise Exception(f"Troppi file con nome simile: {filename}")
    
    def export_batch_csv(self, session_docs: List[Dict], output_dir: str,
                        csv_mode: str = 'per_folder') -> List[str]:
        """
        Genera CSV per batch con naming e location configurabili
        
        Args:
            session_docs: Documenti sessione con exported_files
            output_dir: Directory output base
            csv_mode: 'per_folder' | 'global' (deprecato, usa config)
            
        Returns:
            Lista file CSV creati
        """
        import csv
        from datetime import datetime
        
        csv_files_created = []
        
        # ⭐ NUOVO: Leggi configurazione avanzata CSV
        csv_location = self.config_manager.get('batch_csv_location', 'per_folder')
        csv_naming = self.config_manager.get('batch_csv_naming', 'auto')
        csv_prefix = self.config_manager.get('batch_csv_custom_prefix', 'metadata')
        add_timestamp = self.config_manager.get('batch_csv_add_timestamp', False)
        add_counter = self.config_manager.get('batch_csv_add_counter', False)
        
        # Funzione helper per generare nome CSV
        def generate_csv_name(folder_name: str = None, counter: int = 0) -> str:
            """Genera nome file CSV in base a configurazione"""
            
            # Base name
            if csv_naming == 'folder_name' and folder_name:
                base_name = folder_name
            elif csv_naming == 'custom':
                base_name = csv_prefix
            elif csv_naming == 'timestamp':
                base_name = datetime.now().strftime('%Y%m%d_%H%M%S')
            else:  # 'auto'
                base_name = folder_name if folder_name else 'metadata'
            
            # Aggiungi suffissi opzionali
            suffixes = []
            
            if add_counter and counter > 0:
                suffixes.append(f"{counter:03d}")
            
            if add_timestamp:
                suffixes.append(datetime.now().strftime('%Y%m%d_%H%M%S'))
            
            # Costruisci nome finale
            if suffixes:
                filename = f"{base_name}_{'_'.join(suffixes)}.csv"
            else:
                filename = f"{base_name}.csv"
            
            return filename
        
        # ========================================
        # MODALITÀ: Root (CSV globale unico)
        # ========================================
        if csv_location == 'root':
            csv_filename = generate_csv_name()
            csv_path = os.path.join(output_dir, csv_filename)
            
            # Gestisci file esistente
            csv_path = self._get_unique_csv_path(csv_path)
            
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                # Raccogli tutti i metadati univoci
                all_keys = set()
                for doc in session_docs:
                    if doc.get('json_data'):
                        metadata = doc['json_data'].get('header', doc['json_data'])
                        all_keys.update(metadata.keys())
                
                # Header: Path, Nome File, Categoria, ...metadati
                fieldnames = ['Path Relativo', 'Nome File', 'Categoria'] + sorted(all_keys)
                writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                writer.writeheader()
                
                # Righe
                for doc in session_docs:
                    if doc['status'] != 'completed':
                        continue
                    
                    exported = doc.get('exported_files', [])
                    if not exported:
                        continue
                    
                    metadata = {}
                    if doc.get('json_data'):
                        metadata = doc['json_data'].get('header', doc['json_data'])
                    
                    for exported_file in exported:
                        row = {
                            'Path Relativo': doc['relative_path'],
                            'Nome File': os.path.basename(exported_file),
                            'Categoria': os.path.splitext(os.path.basename(doc['doc_path']))[0]
                        }
                        row.update(metadata)
                        writer.writerow(row)
            
            csv_files_created.append(csv_path)
            print(f"[CSV] Created global CSV: {csv_path}")
        
        # ========================================
        # MODALITÀ: Per Folder (CSV per cartella)
        # ========================================
        elif csv_location == 'per_folder':
            # Raggruppa per cartella
            by_folder = {}
            for doc in session_docs:
                if doc['status'] != 'completed':
                    continue
                folder = doc['relative_path']
                if folder not in by_folder:
                    by_folder[folder] = []
                by_folder[folder].append(doc)
            
            # Crea CSV per ogni cartella
            counter = 0
            for folder, docs in by_folder.items():
                counter += 1
                
                # Determina directory CSV
                if folder == '.':
                    csv_dir = output_dir
                    # ⭐ FIX: Estrai nome cartella da doc_path
                    if docs:
                        first_doc_path = docs[0]['doc_path']
                        folder_name = os.path.basename(os.path.dirname(first_doc_path))
                    else:
                        folder_name = 'metadata'
                else:
                    csv_dir = os.path.join(output_dir, folder)
                    folder_name = folder
                
                os.makedirs(csv_dir, exist_ok=True)
                
                # Genera nome CSV
                csv_filename = generate_csv_name(folder_name, counter)
                csv_path = os.path.join(csv_dir, csv_filename)
                
                # Gestisci file esistente
                csv_path = self._get_unique_csv_path(csv_path)
                
                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
                    # Raccogli metadati univoci per questa cartella
                    all_keys = set()
                    for doc in docs:
                        if doc.get('json_data'):
                            metadata = doc['json_data'].get('header', doc['json_data'])
                            all_keys.update(metadata.keys())
                    
                    # Header: Nome File, Categoria, ...metadati
                    fieldnames = ['Nome File', 'Categoria'] + sorted(all_keys)
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=';')
                    writer.writeheader()
                    
                    # Righe
                    for doc in docs:
                        exported = doc.get('exported_files', [])
                        if not exported:
                            continue
                        
                        metadata = {}
                        if doc.get('json_data'):
                            metadata = doc['json_data'].get('header', doc['json_data'])
                        
                        for exported_file in exported:
                            row = {
                                'Nome File': os.path.basename(exported_file),
                                'Categoria': os.path.splitext(os.path.basename(doc['doc_path']))[0]
                            }
                            row.update(metadata)
                            writer.writerow(row)
                
                csv_files_created.append(csv_path)
                print(f"[CSV] Created folder CSV: {csv_path}")
        
        return csv_files_created
    
    def _get_unique_csv_path(self, original_path: str) -> str:
        """Genera path CSV univoco se file esiste"""
        if not os.path.exists(original_path):
            return original_path
        
        base_dir = os.path.dirname(original_path)
        filename = os.path.basename(original_path)
        name, ext = os.path.splitext(filename)
        
        counter = 1
        while True:
            new_filename = f"{name}({counter}){ext}"
            new_path = os.path.join(base_dir, new_filename)
            
            if not os.path.exists(new_path):
                print(f"[CSV] File exists, renamed to: {new_filename}")
                return new_path
            
            counter += 1
            
            if counter > 999:
                raise Exception(f"Troppi file CSV con nome simile: {filename}")