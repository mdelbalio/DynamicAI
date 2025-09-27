"""
Export manager for DynamicAI - handles all export operations
"""

import os
import time
import shutil
from PIL import Image
from typing import List, Callable, Optional
import tkinter as tk
from tkinter import messagebox

class ExportManager:
    """Manages export operations for all supported formats"""
    
    def __init__(self, config_data: dict):
        self.config_data = config_data
    
    def export_documents(self, output_folder: str, document_groups: List, 
                        current_document_name: str, progress_callback: Optional[Callable] = None) -> List[str]:
        """Main export method that delegates to specific format handlers
        
        Args:
            output_folder: Output directory path
            document_groups: List of DocumentGroup objects
            current_document_name: Base name for exported files
            progress_callback: Function to call with progress updates
            
        Returns:
            List of exported filenames
        """
        export_format = self.config_data.get('export_format', 'JPEG')
        
        if export_format == 'JPEG':
            return self.export_as_jpeg(output_folder, document_groups, current_document_name, progress_callback)
        elif export_format == 'PDF_SINGLE':
            return self.export_as_pdf_single(output_folder, document_groups, current_document_name, progress_callback)
        elif export_format == 'PDF_MULTI':
            return self.export_as_pdf_multi_per_document(output_folder, document_groups, current_document_name, progress_callback)
        elif export_format == 'TIFF_SINGLE':
            return self.export_as_tiff_single(output_folder, document_groups, current_document_name, progress_callback)
        elif export_format == 'TIFF_MULTI':
            return self.export_as_tiff_multi_per_document(output_folder, document_groups, current_document_name, progress_callback)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def export_as_jpeg(self, output_folder: str, document_groups: List, 
                      current_document_name: str, progress_callback: Optional[Callable] = None) -> List[str]:
        """Export as individual JPEG files"""
        exported_files = []
        page_counter = 1
        quality = self.config_data.get('jpeg_quality', 95)
        
        for group in document_groups:
            for thumbnail in group.thumbnails:
                filename = f"{current_document_name}_{page_counter:03d}.jpg"
                original_filepath = os.path.join(output_folder, filename)
                
                # Handle existing files with new system
                final_filepath = self.check_overwrite(original_filepath, filename)
                if final_filepath is None:  # User cancelled
                    continue
                    
                final_filename = os.path.basename(final_filepath)
                
                if progress_callback:
                    progress_callback(f"JPEG: {final_filename}...")
                
                try:
                    img = self.prepare_image_for_save(thumbnail.image)
                    img.save(final_filepath, 'JPEG', quality=quality)
                    exported_files.append(final_filename)
                except Exception as e:
                    print(f"Error saving {final_filename}: {e}")
                
                page_counter += 1
        
        return exported_files
    
    def export_as_pdf_single(self, output_folder: str, document_groups: List, 
                           current_document_name: str, progress_callback: Optional[Callable] = None) -> List[str]:
        """Export as individual PDF files"""
        exported_files = []
        page_counter = 1
        
        for group in document_groups:
            for thumbnail in group.thumbnails:
                filename = f"{current_document_name}_{page_counter:03d}.pdf"
                original_filepath = os.path.join(output_folder, filename)
                
                final_filepath = self.check_overwrite(original_filepath, filename)
                if final_filepath is None:  # User cancelled
                    continue
                    
                final_filename = os.path.basename(final_filepath)
                
                if progress_callback:
                    progress_callback(f"PDF: {final_filename}...")
                
                try:
                    img = self.prepare_image_for_save(thumbnail.image)
                    img.save(final_filepath, 'PDF')
                    exported_files.append(final_filename)
                except Exception as e:
                    print(f"Error saving {final_filename}: {e}")
                
                page_counter += 1
        
        return exported_files
    
    def export_as_pdf_multi_per_document(self, output_folder: str, document_groups: List, 
                                       current_document_name: str, progress_callback: Optional[Callable] = None) -> List[str]:
        """Export as multi-page PDF per document"""
        exported_files = []
        
        for doc_index, group in enumerate(document_groups, 1):
            if not group.thumbnails:  # Skip empty documents
                continue
                
            # Create safe filename
            safe_category = self.sanitize_filename(group.categoryname)
            filename = f"{current_document_name}_doc{doc_index:03d}_{safe_category}.pdf"
            original_filepath = os.path.join(output_folder, filename)
            
            final_filepath = self.check_overwrite(original_filepath, filename)
            if final_filepath is None:  # User cancelled
                continue
                
            final_filename = os.path.basename(final_filepath)
            
            if progress_callback:
                progress_callback(f"PDF Documento {doc_index}: {group.categoryname}...")
            
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
    
    def export_as_tiff_single(self, output_folder: str, document_groups: List, 
                            current_document_name: str, progress_callback: Optional[Callable] = None) -> List[str]:
        """Export as individual TIFF files"""
        exported_files = []
        page_counter = 1
        
        for group in document_groups:
            for thumbnail in group.thumbnails:
                filename = f"{current_document_name}_{page_counter:03d}.tiff"
                original_filepath = os.path.join(output_folder, filename)
                
                final_filepath = self.check_overwrite(original_filepath, filename)
                if final_filepath is None:  # User cancelled
                    continue
                    
                final_filename = os.path.basename(final_filepath)
                
                if progress_callback:
                    progress_callback(f"TIFF: {final_filename}...")
                
                try:
                    # TIFF can maintain original mode
                    img = thumbnail.image
                    img.save(final_filepath, 'TIFF')
                    exported_files.append(final_filename)
                except Exception as e:
                    print(f"Error saving {final_filename}: {e}")
                
                page_counter += 1
        
        return exported_files
    
    def export_as_tiff_multi_per_document(self, output_folder: str, document_groups: List, 
                                        current_document_name: str, progress_callback: Optional[Callable] = None) -> List[str]:
        """Export as multi-page TIFF per document"""
        exported_files = []
        
        for doc_index, group in enumerate(document_groups, 1):
            if not group.thumbnails:  # Skip empty documents
                continue
                
            safe_category = self.sanitize_filename(group.categoryname)
            filename = f"{current_document_name}_doc{doc_index:03d}_{safe_category}.tiff"
            original_filepath = os.path.join(output_folder, filename)
            
            final_filepath = self.check_overwrite(original_filepath, filename)
            if final_filepath is None:  # User cancelled
                continue
                
            final_filename = os.path.basename(final_filepath)
            
            if progress_callback:
                progress_callback(f"TIFF Documento {doc_index}: {group.categoryname}...")
            
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
    
    def check_overwrite(self, filepath: str, filename: str) -> Optional[str]:
        """Check if file should be overwritten or renamed - Sistema completo di gestione file esistenti"""
        file_handling_mode = self.config_data.get('file_handling_mode', 'auto_rename')
        
        if not os.path.exists(filepath):
            return filepath
        
        if file_handling_mode == 'auto_rename':
            # Rinomina automaticamente stile Windows (1), (2), (3)...
            return self.get_unique_filepath(filepath)
            
        elif file_handling_mode == 'ask_overwrite':
            # Chiedi conferma all'utente con popup a 3 opzioni
            try:
                result = messagebox.askyesnocancel(
                    "File Esistente", 
                    f"Il file '{filename}' esiste già.\n\n" +
                    "• Sì = Sovrascrivi il file esistente\n" +
                    "• No = Rinomina automaticamente\n" +
                    "• Annulla = Salta questo file"
                )
                
                if result is True:  # Yes - Sovrascrivi
                    if self.config_data.get('create_backup_on_overwrite', False):
                        self.create_file_backup(filepath)
                    return filepath
                elif result is False:  # No - Rinomina
                    return self.get_unique_filepath(filepath)
                else:  # Cancel - Salta
                    return None
                    
            except Exception as e:
                print(f"Error in dialog: {e}")
                # Fallback: rinomina automaticamente
                return self.get_unique_filepath(filepath)
                
        elif file_handling_mode == 'always_overwrite':
            # Sovrascrivi sempre senza chiedere
            if self.config_data.get('create_backup_on_overwrite', False):
                self.create_file_backup(filepath)
            return filepath
        
        # Default fallback
        return filepath
    
    def get_unique_filepath(self, filepath: str) -> str:
        """Get unique filepath using Windows-style numbering (1), (2), etc."""
        if not os.path.exists(filepath):
            return filepath
        
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
    
    def create_file_backup(self, filepath: str):
        """Create backup of existing file"""
        backup_path = filepath + '.backup'
        try:
            # Se esiste già un backup, usa numerazione progressiva
            if os.path.exists(backup_path):
                backup_path = self.get_unique_filepath(backup_path)
            
            shutil.copy2(filepath, backup_path)
            print(f"Backup created: {backup_path}")
        except Exception as e:
            print(f"Error creating backup: {e}")
    
    def prepare_image_for_save(self, image: Image.Image) -> Image.Image:
        """Prepare image for saving (convert to RGB if needed for JPEG/PDF)"""
        if image.mode in ('RGBA', 'LA', 'P'):
            # Create white background for transparency
            rgb_img = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            # Paste with alpha mask if available
            rgb_img.paste(image, mask=image.split()[-1] if image.mode in ('RGBA', 'LA') else None)
            return rgb_img
        return image
    
    def sanitize_filename(self, filename: str) -> str:
        """Remove invalid characters from filename"""
        # Remove or replace invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        
        # Limit length to avoid filesystem issues
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
            
        # Ensure we don't have an empty filename
        if not sanitized:
            sanitized = "documento"
            
        return sanitized
    
    def get_export_summary(self, exported_files: List[str], export_format: str) -> str:
        """Generate a summary message for the export operation"""
        summary = f"Export completato!\n\n"
        summary += f"Formato: {export_format}\n"
        summary += f"File creati: {len(exported_files)}\n\n"
        
        if export_format in ['PDF_MULTI', 'TIFF_MULTI']:
            summary += "Nota: Ogni documento è stato salvato come file multi-pagina\n"
        else:
            summary += "Nota: Ogni pagina è stata salvata come file separato\n"
            
        if len(exported_files) > 10:
            summary += f"\nPrimi file creati:\n"
            for i, filename in enumerate(exported_files[:10]):
                summary += f"• {filename}\n"
            summary += f"... e altri {len(exported_files) - 10} file"
        else:
            summary += f"\nFile creati:\n"
            for filename in exported_files:
                summary += f"• {filename}\n"
        
        return summary