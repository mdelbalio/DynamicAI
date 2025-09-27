"""
Document loaders for PDF and TIFF files
"""

import fitz
from PIL import Image, ImageSequence
from typing import Optional, Dict

class PDFDocumentLoader:
    """Loads and manages PDF documents"""
    
    def __init__(self, path: str):
        self.path = path
        self.doc = None
        self.cache: Dict[int, Image.Image] = {}
        self.totalpages = 0
        
    def load(self):
        """Load the PDF document"""
        try:
            self.doc = fitz.open(self.path)
            self.totalpages = len(self.doc)
        except Exception as e:
            print(f"Error loading PDF {self.path}: {e}")
            raise
        
    def get_page(self, pagenum: int) -> Optional[Image.Image]:
        """Get a specific page as PIL Image
        
        Args:
            pagenum: Page number (1-based indexing)
            
        Returns:
            PIL Image or None if error
        """
        if pagenum in self.cache:
            return self.cache[pagenum]
        
        if not self.doc:
            print("Document not loaded")
            return None
            
        try:
            # Convert to 0-based indexing
            page_index = pagenum - 1
            if page_index < 0 or page_index >= self.totalpages:
                print(f"Page {pagenum} out of range (1-{self.totalpages})")
                return None
                
            page = self.doc[page_index]
            # Use 2x scaling for better quality
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Cache the image
            self.cache[pagenum] = img
            return img
            
        except Exception as e:
            print(f"Error getting page {pagenum}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the image cache to free memory"""
        self.cache.clear()
    
    def close(self):
        """Close the document and clear cache"""
        if self.doc:
            self.doc.close()
            self.doc = None
        self.clear_cache()
    
    def get_page_info(self, pagenum: int) -> Optional[dict]:
        """Get information about a specific page"""
        if not self.doc:
            return None
            
        try:
            page_index = pagenum - 1
            if page_index < 0 or page_index >= self.totalpages:
                return None
                
            page = self.doc[page_index]
            rect = page.rect
            return {
                'width': rect.width,
                'height': rect.height,
                'rotation': page.rotation
            }
        except Exception as e:
            print(f"Error getting page info {pagenum}: {e}")
            return None


class TIFFDocumentLoader:
    """Loads and manages TIFF documents"""
    
    def __init__(self, path: str):
        self.path = path
        self.pages = []
        self.totalpages = 0
        
    def load(self):
        """Load the TIFF document"""
        try:
            img = Image.open(self.path)
            # Extract all pages from multi-page TIFF
            self.pages = []
            for page in ImageSequence.Iterator(img):
                # Make a copy to avoid issues with the iterator
                self.pages.append(page.copy())
            img.close()
            self.totalpages = len(self.pages)
            
        except Exception as e:
            print(f"Error loading TIFF {self.path}: {e}")
            raise
        
    def get_page(self, pagenum: int) -> Optional[Image.Image]:
        """Get a specific page as PIL Image
        
        Args:
            pagenum: Page number (1-based indexing)
            
        Returns:
            PIL Image or None if error
        """
        try:
            # Convert to 0-based indexing
            page_index = pagenum - 1
            if 0 <= page_index < len(self.pages):
                return self.pages[page_index]
            else:
                print(f"Page {pagenum} out of range (1-{len(self.pages)})")
                return None
                
        except Exception as e:
            print(f"Error getting page {pagenum}: {e}")
            return None
    
    def close(self):
        """Close and cleanup"""
        self.pages.clear()
        
    def get_page_info(self, pagenum: int) -> Optional[dict]:
        """Get information about a specific page"""
        try:
            page_index = pagenum - 1
            if 0 <= page_index < len(self.pages):
                page = self.pages[page_index]
                return {
                    'width': page.width,
                    'height': page.height,
                    'mode': page.mode,
                    'format': page.format
                }
            return None
        except Exception as e:
            print(f"Error getting page info {pagenum}: {e}")
            return None


def create_document_loader(file_path: str):
    """Factory function to create appropriate document loader
    
    Args:
        file_path: Path to the document file
        
    Returns:
        PDFDocumentLoader or TIFFDocumentLoader
        
    Raises:
        ValueError: If file type is not supported
    """
    ext = file_path.lower().split('.')[-1]
    
    if ext == "pdf":
        return PDFDocumentLoader(file_path)
    elif ext in ("tiff", "tif"):
        return TIFFDocumentLoader(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
