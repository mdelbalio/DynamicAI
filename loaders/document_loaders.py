"""
Document loaders for PDF and TIFF files with memory management
"""

import fitz
from PIL import Image, ImageSequence
from typing import Optional, Dict
import sys
from collections import OrderedDict
import gc

class MemoryAwareLRUCache:
    """LRU Cache with memory limit to prevent memory exhaustion"""
    
    def __init__(self, max_items: int = 50, max_memory_mb: int = 100):
        self.max_items = max_items
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache = OrderedDict()
        self.current_memory = 0
    
    def get(self, key):
        """Get item from cache, move to end (most recently used)"""
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key, value):
        """Put item in cache with memory management"""
        if key in self.cache:
            # Update existing item
            old_size = self._get_image_memory_size(self.cache[key])
            self.current_memory -= old_size
            self.cache[key] = value
            self.cache.move_to_end(key)
        else:
            # Add new item
            self.cache[key] = value
        
        # Calculate memory usage
        new_size = self._get_image_memory_size(value)
        self.current_memory += new_size
        
        # Cleanup if needed
        self._cleanup_if_needed()
    
    def clear(self):
        """Clear all cached items"""
        self.cache.clear()
        self.current_memory = 0
        gc.collect()  # Force garbage collection
    
    def _get_image_memory_size(self, img: Image.Image) -> int:
        """Estimate memory size of PIL Image"""
        if img is None:
            return 0
        # Rough estimation: width * height * bytes_per_pixel
        bytes_per_pixel = 4 if img.mode in ('RGBA', 'CMYK') else 3
        return img.width * img.height * bytes_per_pixel
    
    def _cleanup_if_needed(self):
        """Remove old items if memory or count limits exceeded"""
        # Remove items if we exceed limits
        while (len(self.cache) > self.max_items or 
               self.current_memory > self.max_memory_bytes) and self.cache:
            # Remove least recently used (first item)
            key, old_img = self.cache.popitem(last=False)
            if old_img:
                self.current_memory -= self._get_image_memory_size(old_img)
        
        # Force garbage collection if memory usage is high
        if self.current_memory > self.max_memory_bytes * 0.8:
            gc.collect()

class PDFDocumentLoader:
    """Loads and manages PDF documents with memory-aware caching"""

    def __init__(self, path: str):
        self.path = path
        self.doc = None
        # Use memory-aware cache instead of simple dict
        self.cache = MemoryAwareLRUCache(max_items=30, max_memory_mb=80)
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
        """Get a specific page as PIL Image with memory management
        
        Args:
            pagenum: Page number (1-based indexing)
            
        Returns:
            PIL Image or None if error
        """
        # Check cache first
        cached_img = self.cache.get(pagenum)
        if cached_img is not None:
            return cached_img

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
            
            # Cache the image with memory management
            self.cache.put(pagenum, img)
            
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

    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging"""
        return {
            'cached_pages': len(self.cache.cache),
            'memory_usage_mb': self.cache.current_memory / (1024 * 1024),
            'max_memory_mb': self.cache.max_memory_bytes / (1024 * 1024)
        }

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
    """Loads and manages TIFF documents with memory management"""

    def __init__(self, path: str):
        self.path = path
        # Use memory-aware cache instead of loading all pages
        self.cache = MemoryAwareLRUCache(max_items=20, max_memory_mb=60)
        self.totalpages = 0
        self._tiff_img = None

    def load(self):
        """Load the TIFF document"""
        try:
            self._tiff_img = Image.open(self.path)
            # Count pages without loading all of them
            self.totalpages = 0
            try:
                while True:
                    self._tiff_img.seek(self.totalpages)
                    self.totalpages += 1
            except EOFError:
                pass  # End of sequence
            
            # Reset to first page
            self._tiff_img.seek(0)

        except Exception as e:
            print(f"Error loading TIFF {self.path}: {e}")
            raise

    def get_page(self, pagenum: int) -> Optional[Image.Image]:
        """Get a specific page as PIL Image with lazy loading
        
        Args:
            pagenum: Page number (1-based indexing)
            
        Returns:
            PIL Image or None if error
        """
        # Check cache first
        cached_img = self.cache.get(pagenum)
        if cached_img is not None:
            return cached_img

        if not self._tiff_img:
            print("TIFF document not loaded")
            return None

        try:
            # Convert to 0-based indexing
            page_index = pagenum - 1
            if page_index < 0 or page_index >= self.totalpages:
                print(f"Page {pagenum} out of range (1-{self.totalpages})")
                return None

            # Load specific page only when needed
            self._tiff_img.seek(page_index)
            page = self._tiff_img.copy()  # Make a copy to avoid iterator issues
            
            # Cache the page
            self.cache.put(pagenum, page)
            
            return page

        except Exception as e:
            print(f"Error getting page {pagenum}: {e}")
            return None

    def close(self):
        """Close and cleanup"""
        if self._tiff_img:
            self._tiff_img.close()
            self._tiff_img = None
        self.cache.clear()

    def get_cache_stats(self) -> dict:
        """Get cache statistics for debugging"""
        return {
            'cached_pages': len(self.cache.cache),
            'memory_usage_mb': self.cache.current_memory / (1024 * 1024),
            'max_memory_mb': self.cache.max_memory_bytes / (1024 * 1024)
        }

    def get_page_info(self, pagenum: int) -> Optional[dict]:
        """Get information about a specific page"""
        if not self._tiff_img:
            return None

        try:
            page_index = pagenum - 1
            if page_index < 0 or page_index >= self.totalpages:
                return None

            current_page = self._tiff_img.tell()
            self._tiff_img.seek(page_index)
            
            info = {
                'width': self._tiff_img.width,
                'height': self._tiff_img.height,
                'mode': self._tiff_img.mode,
                'format': self._tiff_img.format
            }
            
            # Restore original page
            self._tiff_img.seek(current_page)
            return info

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
