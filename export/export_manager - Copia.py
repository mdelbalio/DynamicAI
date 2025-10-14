"""
Export Manager for DynamicAI v3.6 (BATCH EDITION)
Gestisce export di documenti in formati multipli (JPEG, PDF, TIFF) e CSV.
AGGIUNTO: export_metadata_csv() per gestione CSV incremental/per-file
"""

import os
import csv
from PIL import Image
from typing import List, Dict, Optional
from tempfile import NamedTemporaryFile
import queue
import threading

# NUOVA: Import per numerazione personalizzata
from utils.helpers import generate_numbered_filename, get_document_counter_manager
class ExportManager:
    """Gestisce export documenti e metadati"""
    
    def __init__(self, config_manager):
        """
        Args:
            config_manager: Oggetto ConfigManager (non dict!)
        """
        self.config_manager = config_manager
        # NUOVA: Gestione contatori numerazione
        self.document_counters = {}
        self.current_export_session = 0
        # Thread-safe communication
        self.ui_update_queue = queue.Queue()
        self.cancel_event = threading.Event()
        
    def sanitize_filename(self, filename: str) -> str:
        """
        Remove invalid characters from filename.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for filesystem
        """
        invalid_chars = '<>:"/\\|?*'
        sanitized = (filename or '').strip().strip('.')
        for c in invalid_chars:
            sanitized = sanitized.replace(c, '_')
        return sanitized or 'untitled'
    
    def prepare_image_for_save(self, img: Image.Image) -> Image.Image:
        """
        Normalize image before saving.
        
        Args:
            img: PIL Image
            
        Returns:
            Normalized PIL Image
        """
        if img.mode not in ["RGB", "L"]:
            img = img.convert("RGB")
        return img
    
    def get_unique_filepath(self, base_path: str) -> str:
        """
        Create unique filepath if file exists (Windows style: file(1).ext).
        
        Args:
            base_path: Original file path
            
        Returns:
            Unique file path
        """
        if not os.path.exists(base_path):
            return base_path
        
        base, ext = os.path.splitext(base_path)
        counter = 1
        new_path = f"{base}({counter}){ext}"
        
        while os.path.exists(new_path):
            counter += 1
            new_path = f"{base}({counter}){ext}"
            
            if counter > 9999:
                raise Exception("Troppi file con lo stesso nome base")
        
        return new_path
    
    def export_documents(self, output_folder: str, document_groups: List, document_name: str, progress_callback=None) -> List[str]:
        """Export documents to configured format.
        
        Args:
            output_folder: Output directory 
            # Thread-safe communication
            document_groups: List of DocumentGroup objects
            document_name: Base document name
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of exported file basenames
        """
        # NUOVA: Inizializza sessione export con contatori
        self.current_export_session += 1
        numbering_mode = self.config_manager.config_data.get('document_numbering', {}).get('numbering_mode', 'per_category')
        self.document_counters = get_document_counter_manager(self.config_manager, numbering_mode)
        
        # Debug info
        if self.config_manager.config_data.get('show_debug_info', False):
            print(f"[DEBUG] Export session {self.current_export_session} - Numbering mode: {numbering_mode}")
        
        export_format = self.config_manager.get('export_format', 'JPEG')
        exported_files = []  # Thread-safe communication
        
        is_split_mode = len(document_groups) > 1
        
        if progress_callback:
            mode_text = "SPLIT (categorie)" if is_split_mode else "SINGLE (documento unico)"
            progress_callback(f"Modalità export: {mode_text}")
        
        if is_split_mode:
            # SPLIT MODE: Usa naming con _doc001_categoria
            if export_format == 'JPEG':
                exported_files = self._export_jpeg_single(
                    output_folder, document_groups, document_name, progress_callback)
            elif export_format == 'PDF_SINGLE':
                exported_files = self._export_pdf_single(
                    output_folder, document_groups, document_name, progress_callback)
            elif export_format == 'PDF_MULTI':
                exported_files = self._export_pdf_multi(
                    output_folder, document_groups, document_name, progress_callback)
            elif export_format == 'TIFF_SINGLE':
                exported_files = self._export_tiff_single(
                    output_folder, document_groups, document_name, progress_callback)
            elif export_format == 'TIFF_MULTI':
                exported_files = self._export_tiff_multi(
                    output_folder, document_groups, document_name, progress_callback)
        else:
            # SINGLE MODE: Nome file originale (senza _doc001_)
            if export_format == 'JPEG':
                exported_files = self._export_jpeg_single_mode(
                    output_folder, document_groups, document_name, progress_callback)
            elif export_format == 'PDF_SINGLE':
                exported_files = self._export_pdf_single_mode(
                    output_folder, document_groups, document_name, progress_callback)
            elif export_format == 'PDF_MULTI':
                exported_files = self._export_pdf_multi_single_mode(
                    output_folder, document_groups, document_name, progress_callback)
            elif export_format == 'TIFF_SINGLE':
                exported_files = self._export_tiff_single_mode(
                    output_folder, document_groups, document_name, progress_callback)
            elif export_format == 'TIFF_MULTI':
                exported_files = self._export_tiff_multi_single_mode(
                    output_folder, document_groups, document_name, progress_callback)
        
        return exported_files
    
    def _export_jpeg_single(self, output_folder: str, document_groups: List,
                           document_name: str, progress_callback) -> List[str]:
        """Export each page as single JPEG file"""
        exported_files = []
        quality = self.config_manager.get('jpeg_quality', 95)
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        
        page_counter = 1
        total_pages = sum(len(group.thumbnails) for group in document_groups)
        
        for group in document_groups:
            for thumbnail in group.thumbnails:
                if progress_callback:
                    progress_callback(f"Esportando pagina {page_counter}/{total_pages}")
                
                # NUOVA: Numerazione personalizzata
                counter = self._get_next_counter(group.category_name)
                numbered_filename = generate_numbered_filename(
                    base_name=document_name,
                    counter=counter,
                    config_manager=self.config_manager,
                    is_multi_document=True,
                    category_name=group.category_name
                )
                
                filename = f"{numbered_filename}.jpg"
                filepath = os.path.join(output_folder, filename)
                
                if os.path.exists(filepath):
                    filepath = self._handle_existing_file(filepath, file_handling, filename)
                    if filepath is None:
                        continue
                    filename = os.path.basename(filepath)
                
                # Save image
                img = self.prepare_image_for_save(thumbnail.image)
                img.save(filepath, 'JPEG', quality=quality, optimize=True)
                
                exported_files.append(filename)
                page_counter += 1
        
        return exported_files
    
    def _export_pdf_multi(self, output_folder: str, document_groups: List,
                         document_name: str, progress_callback) -> List[str]:
        """Export each document as multi-page PDF"""
        exported_files = []
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        
        for idx, group in enumerate(document_groups, 1):
            if not group.thumbnails:
                continue
                
            if progress_callback:
                progress_callback(f"Esportando documento {idx}/{len(document_groups)}")
            
            # NUOVA: Numerazione personalizzata
            counter = self._get_next_counter(group.category_name)
            numbered_filename = generate_numbered_filename(
                base_name=document_name,
                counter=counter,
                config_manager=self.config_manager,
                is_multi_document=True,
                category_name=group.category_name
            )
            
            filename = f"{numbered_filename}.pdf"
            filepath = os.path.join(output_folder, filename)
            
            # Handle existing files
            if os.path.exists(filepath):
                filepath = self._handle_existing_file(filepath, file_handling, filename)
                if filepath is None:
                    continue
                filename = os.path.basename(filepath)
            
            # Prepare images
            images = [self.prepare_image_for_save(t.image) for t in group.thumbnails]
            
            # Save multi-page PDF
            if images:
                images[0].save(filepath, 'PDF', save_all=True,
                             append_images=images[1:] if len(images) > 1 else [])
                exported_files.append(filename)
        
        return exported_files
    
    def _export_pdf_single(self, output_folder: str, document_groups: List,
                          document_name: str, progress_callback) -> List[str]:
        """Export each page as single PDF file"""
        exported_files = []
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        
        page_counter = 1
        total_pages = sum(len(group.thumbnails) for group in document_groups)
        
        for group in document_groups:
            for thumbnail in group.thumbnails:
                if progress_callback:
                    progress_callback(f"Esportando pagina {page_counter}/{total_pages}")
                
                # NUOVA: Numerazione personalizzata
                counter = self._get_next_counter(group.category_name)
                numbered_filename = generate_numbered_filename(
                    base_name=document_name,
                    counter=counter,
                    config_manager=self.config_manager,
                    is_multi_document=True,
                    category_name=group.category_name
                )
                
                filename = f"{numbered_filename}.pdf"
                filepath = os.path.join(output_folder, filename)
                
                if os.path.exists(filepath):
                    filepath = self._handle_existing_file(filepath, file_handling, filename)
                    if filepath is None:
                        continue
                    filename = os.path.basename(filepath)
                
                img = self.prepare_image_for_save(thumbnail.image)
                img.save(filepath, 'PDF')
                
                exported_files.append(filename)
                page_counter += 1
        
        return exported_files
    
    def _export_tiff_single(self, output_folder: str, document_groups: List,
                           document_name: str, progress_callback) -> List[str]:
        """Export each page as single TIFF file"""
        exported_files = []
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        compression = self.config_manager.get('export', {}).get('tiff_compression', 'tiff_lzw')
        
        page_counter = 1
        total_pages = sum(len(group.thumbnails) for group in document_groups)
        
        for group in document_groups:
            for thumbnail in group.thumbnails:
                if progress_callback:
                    progress_callback(f"Esportando pagina {page_counter}/{total_pages}")
                
                # NUOVA: Numerazione personalizzata
                counter = self._get_next_counter(group.category_name)
                numbered_filename = generate_numbered_filename(
                    base_name=document_name,
                    counter=counter,
                    config_manager=self.config_manager,
                    is_multi_document=True,
                    category_name=group.category_name
                )
                
                filename = f"{numbered_filename}.tiff"
                filepath = os.path.join(output_folder, filename)
                
                if os.path.exists(filepath):
                    filepath = self._handle_existing_file(filepath, file_handling, filename)
                    if filepath is None:
                        continue
                    filename = os.path.basename(filepath)
                
                img = self.prepare_image_for_save(thumbnail.image)
                img.save(filepath, 'TIFF', compression=compression)
                
                exported_files.append(filename)
                page_counter += 1
        
        return exported_files
    
    def _export_tiff_multi(self, output_folder: str, document_groups: List,
                          document_name: str, progress_callback) -> List[str]:
        """Export each document as multi-page TIFF"""
        exported_files = []
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        compression = self.config_manager.get('export', {}).get('tiff_compression', 'tiff_lzw')
        
        for idx, group in enumerate(document_groups, 1):
            if not group.thumbnails:
                continue
                
            if progress_callback:
                progress_callback(f"Esportando documento {idx}/{len(document_groups)}")
            
            # NUOVA: Numerazione personalizzata
            counter = self._get_next_counter(group.category_name)
            numbered_filename = generate_numbered_filename(
                base_name=document_name,
                counter=counter,
                config_manager=self.config_manager,
                is_multi_document=True,
                category_name=group.category_name
            )
            
            filename = f"{numbered_filename}.tiff"
            filepath = os.path.join(output_folder, filename)
            
            if os.path.exists(filepath):
                filepath = self._handle_existing_file(filepath, file_handling, filename)
                if filepath is None:
                    continue
                filename = os.path.basename(filepath)
            
            images = [self.prepare_image_for_save(t.image) for t in group.thumbnails]
            
            if images:
                images[0].save(filepath, 'TIFF', save_all=True,
                             append_images=images[1:] if len(images) > 1 else [],
                             compression=compression)
                exported_files.append(filename)
        
        return exported_files

    # ==========================================
    # SINGLE MODE EXPORT METHODS
    # ==========================================
    
    def _export_jpeg_single_mode(self, output_folder: str, document_groups: List,
                                 document_name: str, progress_callback) -> List[str]:
        """Export all pages as single JPEG files with original document name"""
        exported_files = []
        quality = self.config_manager.get('jpeg_quality', 95)
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        
        group = document_groups[0]  # Solo un gruppo in single mode
        total_pages = len(group.thumbnails)
        
        for page_num, thumbnail in enumerate(group.thumbnails, 1):
            if progress_callback:
                progress_callback(f"Esportando pagina {page_num}/{total_pages}")
                
        # NUOVA: Numerazione personalizzata per single mode  
        counter = self.get_next_counter('')  # Categoria vuota per single mode
        numbered_filename = generate_numbered_filename(
            base_name=document_name,
            counter=counter,
            config_manager=self.config_manager,
            is_multi_document=False,
            category_name=''
        )
        
        filename = f"{numbered_filename}.pdf"
        filepath = os.path.join(output_folder, filename)
        
        if os.path.exists(filepath):
            filepath = self._handle_existing_file(filepath, file_handling, filename)
            if filepath is None:
                continue
            filename = os.path.basename(filepath)
        
        img = self.prepare_image_for_save(thumbnail.image)
        img.save(filepath, 'JPEG', quality=quality, optimize=True)
        exported_files.append(filename)
    
    return exported_files
    
    def _export_pdf_single_mode(self, output_folder: str, document_groups: List,
                                document_name: str, progress_callback) -> List[str]:
        """Export all pages as single PDF files with original document name"""
        exported_files = []
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        
        group = document_groups[0]
        total_pages = len(group.thumbnails)
    for page_num, thumbnail in enumerate(group.thumbnails, 1):
        if progress_callback:
            progress_callback(f"Esportando pagina {page_num}/{total_pages}")
            
        # NUOVA: Numerazione personalizzata per single mode
        counter = self._get_next_counter('')  # Categoria vuota per single mode
        numbered_filename = generate_numbered_filename(
            base_name=document_name,
            counter=counter,
            config_manager=self.config_manager,
            is_multi_document=False,
            category_name=''
        )
            
            filename = f"{numbered_filename}.pdf"
            filepath = os.path.join(output_folder, filename)
            
            if os.path.exists(filepath):
                filepath = self._handle_existing_file(filepath, file_handling, filename)
                if filepath is None:
                    continue
                filename = os.path.basename(filepath)
            
            img = self.prepare_image_for_save(thumbnail.image)
            img.save(filepath, 'PDF')
            exported_files.append(filename)
        
        return exported_files
    
    def _export_pdf_multi_single_mode(self, output_folder: str, document_groups: List,
                                      document_name: str, progress_callback) -> List[str]:
        """Export as single multi-page PDF with original document name"""
        exported_files = []
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        
        group = document_groups[0]
        
        if progress_callback:
            progress_callback("Esportando documento unico PDF")
        
        # NUOVA: Numerazione personalizzata per single mode
        counter = self._get_next_counter('')  # Categoria vuota per single mode
        numbered_filename = generate_numbered_filename(
            base_name=document_name,
            counter=counter,
            config_manager=self.config_manager,
            is_multi_document=False,
            category_name=''
        )
        
        # Create single PDF
        filename = f"{numbered_filename}.pdf"
        filepath = os.path.join(output_folder, filename)
        
        if os.path.exists(filepath):
            filepath = self._handle_existing_file(filepath, file_handling, filename)
            if filepath is None:
                return []
            filename = os.path.basename(filepath)
        
        images = [self.prepare_image_for_save(t.image) for t in group.thumbnails]
        
        if images:
            images[0].save(filepath, 'PDF', save_all=True,
                         append_images=images[1:] if len(images) > 1 else [])
            exported_files.append(filename)
        
        return exported_files
    
    def _export_tiff_single_mode(self, output_folder: str, document_groups: List,
                                 document_name: str, progress_callback) -> List[str]:
        """Export all pages as single TIFF files with original document name"""
        exported_files = []
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        compression = self.config_manager.get('export', {}).get('tiff_compression', 'tiff_lzw')
        
        group = document_groups[0]
        total_pages = len(group.thumbnails)
        
        for page_num, thumbnail in enumerate(group.thumbnails, 1):
            if progress_callback:
                progress_callback(f"Esportando pagina {page_num}/{total_pages}")
                
            # NUOVA: Numerazione personalizzata per single mode
            counter = self._get_next_counter('')  # Categoria vuota per single mode
            numbered_filename = generate_numbered_filename(
                base_name=document_name,
                counter=counter,
                config_manager=self.config_manager,
                is_multi_document=False,
                category_name=''
            )
            
            filename = f"{numbered_filename}.tiff"
            filepath = os.path.join(output_folder, filename)
            
            if os.path.exists(filepath):
                filepath = self._handle_existing_file(filepath, file_handling, filename)
                if filepath is None:
                    continue
                filename = os.path.basename(filepath)
            
            img = self.prepare_image_for_save(thumbnail.image)
            img.save(filepath, 'TIFF', compression=compression)
            exported_files.append(filename)
        
        return exported_files
    
    def _export_tiff_multi_single_mode(self, output_folder: str, document_groups: List,
                                       document_name: str, progress_callback) -> List[str]:
        """Export as single multi-page TIFF with original document name"""
        exported_files = []
        file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
        compression = self.config_manager.get('export', {}).get('tiff_compression', 'tiff_lzw')
        
        group = document_groups[0]
        
        if progress_callback:
            progress_callback("Esportando documento unico TIFF")
        
       # NUOVA: Numerazione personalizzata per single mode
        counter = self._get_next_counter('')  # Categoria vuota per single mode
        numbered_filename = generate_numbered_filename(
            base_name=document_name,
            counter=counter,
            config_manager=self.config_manager,
            is_multi_document=False,
            category_name=''
        )
        
        # Create single multi-page TIFF
        filename = f"{numbered_filename}.tiff"
        filepath = os.path.join(output_folder, filename)
        
        if os.path.exists(filepath):
            filepath = self._handle_existing_file(filepath, file_handling, filename)
            if filepath is None:
                return []
            filename = os.path.basename(filepath)
        
        images = [self.prepare_image_for_save(t.image) for t in group.thumbnails]
        
        if images:
            images[0].save(filepath, 'TIFF', save_all=True,
                         append_images=images[1:] if len(images) > 1 else [],
                         compression=compression)
            exported_files.append(filename)
        
        return exported_files
    
    def _handle_existing_file(self, filepath: str, mode: str, 
                             original_filename: str) -> Optional[str]:
        """
        Handle existing file based on configured mode.
        
        Args:
            filepath: Full file path
            mode: Handling mode (auto_rename, ask_overwrite, always_overwrite)
            original_filename: Original filename for messages
            
        Returns:
            New filepath or None if should skip
        """
        if mode == 'auto_rename':
            return self.get_unique_filepath(filepath)
        elif mode == 'ask_overwrite':
            from tkinter import messagebox
            response = messagebox.askyesnocancel(
                "File Esistente",
                f"Il file '{original_filename}' esiste già.\n\n"
                "Sì = Sovrascrivi\n"
                "No = Rinomina automaticamente\n"
                "Annulla = Salta file"
            )
            if response is None:
                return None
            elif response is False:
                return self.get_unique_filepath(filepath)
            return filepath
        elif mode == 'always_overwrite':
            return filepath
        
        return filepath
    
    def export_metadata_csv(self, metadata_rows: List[Dict], 
                           input_file_name: Optional[str] = None,
                           output_folder: Optional[str] = None) -> str:
        """
        Export metadata to CSV file.
        NUOVO: Supporta modalità incremental e per_file.
        
        Args:
            metadata_rows: List of metadata dictionaries
            input_file_name: Input document name (for per_file mode)
            output_folder: Override output folder (optional)
            
        Returns:
            Path to CSV file created
        """
        csv_mode = self.config_manager.get('csv_mode', 'incremental')
        csv_output_path = self.config_manager.get('csv_output_path', '')
        delimiter = self.config_manager.get('csv_delimiter', ';')
        
        # Determine output folder
        if output_folder:
            csv_folder = output_folder
        elif csv_output_path:
            csv_folder = csv_output_path
        else:
            csv_folder = self.config_manager.get('default_output_folder', '')
        
        if not os.path.exists(csv_folder):
            os.makedirs(csv_folder, exist_ok=True)
        
        # Determine CSV filename
        if csv_mode == 'incremental':
            csv_filename = "metadata.csv"
            csv_path = os.path.join(csv_folder, csv_filename)
            write_header = not os.path.exists(csv_path)
            mode = 'a'  # Append mode
        else:  # per_file
            if not input_file_name:
                raise ValueError("Per la modalità per_file serve input_file_name")
                
            # NUOVA: Numerazione personalizzata per CSV per-file
            counter = self._get_next_counter('')  # Categoria vuota per CSV
            numbered_filename = generate_numbered_filename(
                base_name=os.path.splitext(os.path.basename(input_file_name))[0],
                counter=counter,
                config_manager=self.config_manager,
                is_multi_document=False,
                category_name=''
            )
            
            csv_filename = f"{numbered_filename}.csv"
            csv_path = os.path.join(csv_folder, csv_filename)
            
            # Handle existing file
            file_handling = self.config_manager.get('file_handling_mode', 'auto_rename')
            if os.path.exists(csv_path):
                csv_path = self._handle_existing_file(csv_path, file_handling, csv_filename)
                if csv_path is None:
                    return ""
            
            write_header = True
            mode = 'w'  # Write mode
        
        # Write CSV
        if metadata_rows:
            fieldnames = list(metadata_rows[0].keys())
            
            try:
                with open(csv_path, mode, newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
                    
                    if write_header:
                        writer.writeheader()
                    
                    for row in metadata_rows:
                        writer.writerow(row)
                
                return csv_path
                
            except Exception as e:
                raise Exception(f"Errore scrittura CSV: {str(e)}")
        
        return csv_path
    
    def create_export_summary(self, exported_files: List[str], 
                             metadata_file: Optional[str] = None) -> Dict:
        """
        Create export summary.
        
        Args:
            exported_files: List of exported file basenames
            metadata_file: Path to CSV metadata file
            
        Returns:
            Summary dictionary
        """
        summary = {
            'files_count': len(exported_files),
            'files': exported_files,
            'metadata_csv': metadata_file,
            'export_format': self.config_manager.get('export_format', 'JPEG')
        }
        return summary
    
    def export_documents_threaded(self, output_folder: str, document_groups: List,
                             document_name: str, ui_callback=None) -> None:
        """
        Thread-safe export with progress updates via queue
        
        Args:
            output_folder: Output directory
            document_groups: List of DocumentGroup objects  
            document_name: Base document name
            ui_callback: Main UI callback for processing queue messages
        """
        def worker_thread():
            """Background worker thread for export operations"""
            try:
                self.cancel_event.clear()
                
                def progress_callback(message):
                    """Thread-safe progress callback"""
                    if not self.cancel_event.is_set():
                        self.ui_update_queue.put(('progress', message))
                
                # Perform export in background
                exported_files = self.export_documents(
                    output_folder, document_groups, document_name, progress_callback
                )
                
                if not self.cancel_event.is_set():
                    self.ui_update_queue.put(('completed', {
                        'files': exported_files,
                        'folder': output_folder,
                        'format': self.config_manager.get('export_format', 'JPEG')
                    }))
                    
            except Exception as e:
                if not self.cancel_event.is_set():
                    self.ui_update_queue.put(('error', str(e)))
        
        # Start background thread
        thread = threading.Thread(target=worker_thread, daemon=True)
        thread.start()
        
        # Start UI queue processor if callback provided
        if ui_callback:
            self._process_ui_queue(ui_callback)

    def _process_ui_queue(self, ui_callback):
        """Process UI updates from background thread"""
        try:
            # Non-blocking queue check
            while True:
                try:
                    message_type, data = self.ui_update_queue.get_nowait()
                    ui_callback(message_type, data)
                    self.ui_update_queue.task_done()
                except queue.Empty:
                    break
            
            # Schedule next check if not cancelled
            if not self.cancel_event.is_set():
                # Use a proper UI callback mechanism instead of direct after()
                # This will be called by main UI thread
                pass
                
        except Exception as e:
            ui_callback('error', f'Queue processing error: {str(e)}')

    def cancel_export(self):
        """Cancel ongoing export operation"""
        self.cancel_event.set()
        
        # Clear remaining queue items
        try:
            while True:
                self.ui_update_queue.get_nowait()
                self.ui_update_queue.task_done()
        except queue.Empty:
            pass

    def get_export_stats(self) -> dict:
        """Get export operation statistics"""
        return {
            'queue_size': self.ui_update_queue.qsize(),
            'is_cancelled': self.cancel_event.is_set()
        }

    def _get_next_counter(self, category_name: str = '') -> int:
        """
        Ottiene il prossimo numero contatore per la categoria
        
        Args:
            category_name: Nome categoria per numerazione per_category
            
        Returns:
            int: Prossimo numero contatore
        """
        numbering_mode = self.config_manager.config_data.get('document_numbering', {}).get('numbering_mode', 'per_category')
        
        if numbering_mode == 'global':
            # Contatore globale
            key = '_global'
            if key not in self.document_counters:
                self.document_counters[key] = self.config_manager.config_data.get('document_numbering', {}).get('start_number', 1)
            
            current = self.document_counters[key]
            self.document_counters[key] += 1
            return current
            
        else:  # per_category
            # Contatore per categoria
            safe_category = category_name or 'Documento'
            if safe_category not in self.document_counters:
                self.document_counters[safe_category] = self.config_manager.config_data.get('document_numbering', {}).get('start_number', 1)
            
            current = self.document_counters[safe_category]
            self.document_counters[safe_category] += 1
            return current
