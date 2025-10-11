"""
Document group component for DynamicAI with multi-row grid layout
"""

import tkinter as tk
from PIL import Image
from typing import TYPE_CHECKING, List, Optional
import math
from .thumbnail import PageThumbnail

if TYPE_CHECKING:
    from gui.main_window import AIDOXAApp

class DocumentGroup:
    """Represents a group of pages belonging to the same document category with multi-row layout"""
    
    def __init__(self, parent: tk.Widget, categoryname: str, mainapp: 'AIDOXAApp', document_counter: int):
        self.parent = parent
        self.mainapp = mainapp
        self.categoryname = categoryname
        self.document_counter = document_counter
        self.isselected = False
        self.thumbnails: List[PageThumbnail] = []
        self.pages: List[int] = []
        
        # Grid layout settings
        self.thumbnails_per_row = 4  # Default thumbnails per row
        self.min_thumbnails_per_row = 2
        self.max_thumbnails_per_row = 6
        
        # Create UI elements
        self.create_widgets()
        self.bind_events()

    def create_widgets(self):
        """Create the document group UI widgets"""
        # Main frame with colored background
        self.frame = tk.Frame(self.parent, bd=2, relief="ridge", bg="#f0f0f0")
        
        # Create header with document counter and category name
        self.create_header()
        
        # Container for thumbnails with grid layout
        self.pages_frame = tk.Frame(self.frame, bg="white")
        self.pages_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Configure grid weights for responsive layout
        self.pages_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

    def create_header(self):
        """Create the document group header with counter and category"""
        # Get font settings from config
        font_name = self.mainapp.config_manager.get('document_font_name', 'Arial')
        font_size = self.mainapp.config_manager.get('document_font_size', 10)
        font_bold = self.mainapp.config_manager.get('document_font_bold', True)
        font_style = "bold" if font_bold else "normal"
        
        # Create header text with counter
        digits = self.mainapp.config_manager.get('document_counter_digits', 4)
        counter_text = f"{self.document_counter:0{digits}d}"
        header_text = f"{counter_text} {self.categoryname}"
        
        # Category label with hover effect
        self.label = tk.Label(self.frame, text=header_text, 
                             font=(font_name, font_size, font_style), 
                             bg="#d0d0d0", cursor="hand2", padx=5, pady=3,
                             anchor="w", justify="left")
        self.label.pack(fill="x", padx=2, pady=2)

    def bind_events(self):
        """Bind mouse events for group interaction"""
        # Bind click to category label for group selection
        self.label.bind("<Button-1>", self.on_group_click)
        # Bind right-click for context menu
        self.label.bind("<Button-3>", self.on_right_click)
        # Bind hover events for highlighting
        self.label.bind("<Enter>", self.on_header_enter)
        self.label.bind("<Leave>", self.on_header_leave)
        # Bind to frame resize for dynamic grid adjustment
        self.pages_frame.bind("<Configure>", self.on_frame_configure)

    def on_frame_configure(self, event):
        """Handle frame resize to adjust grid layout dynamically"""
        if event.widget == self.pages_frame and len(self.thumbnails) > 0:
            # Calculate optimal thumbnails per row based on frame width
            frame_width = event.width
            if frame_width > 1:
                # Get thumbnail width from config
                thumb_width = self.mainapp.config_manager.get('thumbnail_width', 80)
                padding_per_thumbnail = 6  # 3px padding on each side
                total_thumb_width = thumb_width + padding_per_thumbnail
                
                # Calculate how many thumbnails can fit
                optimal_per_row = max(self.min_thumbnails_per_row, 
                                    min(self.max_thumbnails_per_row, 
                                        frame_width // total_thumb_width))
                
                # Only repack if the number changed significantly
                if abs(optimal_per_row - self.thumbnails_per_row) > 0:
                    self.thumbnails_per_row = optimal_per_row
                    self.after_idle_repack()

    def after_idle_repack(self):
        """Repack thumbnails after idle to avoid recursive calls"""
        self.mainapp.after_idle(self.repack_thumbnails_grid)

    def on_header_enter(self, event):
        """Handle mouse enter on header"""
        if not self.isselected:
            self.label.configure(bg="#e0e0e0")

    def on_header_leave(self, event):
        """Handle mouse leave on header"""
        if not self.isselected:
            self.label.configure(bg="#d0d0d0")

    def on_group_click(self, event):
        """Handle click on group header"""
        self.mainapp.select_document_group(self)

    def on_right_click(self, event):
        """Handle right click on group header"""
        self.mainapp.show_document_context_menu(self, event)

    def select_group(self):
        """Highlight the group header when selected"""
        self.isselected = True
        self.label.configure(bg="#FFD700", relief="raised", bd=2)
        self.frame.configure(bg="#FFFACD")

    def deselect_group(self):
        """Remove highlight from group header"""
        self.isselected = False
        self.label.configure(bg="#d0d0d0", relief="flat", bd=1)
        self.frame.configure(bg="#f0f0f0")

    def add_page(self, pagenum: int, image: Image.Image, position: Optional[int] = None) -> PageThumbnail:
        """Add a page to this document group"""
        thumbnail = PageThumbnail(self.pages_frame, pagenum, image, self.categoryname, self.mainapp, self)
        
        if position is None:
            self.thumbnails.append(thumbnail)
            if pagenum not in self.pages:
                self.pages.append(pagenum)
        else:
            self.thumbnails.insert(position, thumbnail)
            if pagenum not in self.pages:
                self.pages.insert(position, pagenum)
        
        self.repack_thumbnails_grid()
        return thumbnail

    def add_page_lazy(self, pagenum: int, document_loader, position: Optional[int] = None) -> PageThumbnail:
        """Aggiungi pagina con lazy loading - carica immagine dopo creazione
        
        Args:
            pagenum: Numero pagina
            document_loader: Loader del documento per caricare immagine
            position: Posizione di inserimento (opzionale)
        
        Returns:
            PageThumbnail creato
        """
        # Crea thumbnail SENZA immagine (placeholder)
        thumbnail = PageThumbnail(
            self.pages_frame, pagenum, None,  # None = placeholder
            self.categoryname, self.mainapp, self  # ✅ CORRETTO: self.categoryname
        )
        
        # ⭐ IMPOSTA il document_loader SUBITO
        thumbnail.document_loader = document_loader
        
        # Aggiungi alla lista
        if position is None:
            self.thumbnails.append(thumbnail)
            if pagenum not in self.pages:
                self.pages.append(pagenum)
        else:
            self.thumbnails.insert(position, thumbnail)
            if pagenum not in self.pages:
                self.pages.insert(position, pagenum)
        
        # Repack grid
        self.repack_thumbnails_grid()
        
        # ⭐ CARICA IMMAGINE DOPO UN BREVE DELAY
        self.mainapp.after(50, lambda: self._load_thumbnail_image(thumbnail))
        
        return thumbnail

    def _load_thumbnail_image(self, thumbnail):
        """Helper per caricare immagine thumbnail in background"""
        try:
            if not thumbnail.image_loaded and thumbnail.document_loader:
                self.mainapp.debug_print(f"Loading image for page {thumbnail.pagenum}")
                img = thumbnail.document_loader.get_page(thumbnail.pagenum)
                if img:
                    thumbnail.set_image(img)
                    self.mainapp.debug_print(f"✅ Image loaded for page {thumbnail.pagenum}")
                else:
                    self.mainapp.debug_print(f"❌ Failed to load image for page {thumbnail.pagenum}")
        except Exception as e:
            self.mainapp.debug_print(f"Error loading thumbnail image: {e}")   

    def remove_thumbnail(self, thumbnail: PageThumbnail) -> int:
        """Remove a thumbnail from this group"""
        if thumbnail in self.thumbnails:
            index = self.thumbnails.index(thumbnail)
            self.thumbnails.remove(thumbnail)
            thumbnail.grid_forget()  # Changed from pack_forget to grid_forget
            if thumbnail.pagenum in self.pages:
                self.pages.remove(thumbnail.pagenum)
            # Repack remaining thumbnails
            self.repack_thumbnails_grid()
            return index
        return -1

    def repack_thumbnails_grid(self):
        """Repack all thumbnails in grid layout"""
        # Clear all current grid positions
        for thumb in self.thumbnails:
            thumb.grid_forget()
        
        # Calculate grid dimensions
        total_thumbnails = len(self.thumbnails)
        if total_thumbnails == 0:
            return
        
        # Adjust thumbnails per row based on count and frame width
        current_frame_width = self.pages_frame.winfo_width()
        if current_frame_width > 1:
            thumb_width = self.mainapp.config_manager.get('thumbnail_width', 80)
            padding_per_thumbnail = 6
            total_thumb_width = thumb_width + padding_per_thumbnail
            optimal_per_row = max(self.min_thumbnails_per_row, 
                                min(self.max_thumbnails_per_row, 
                                    current_frame_width // total_thumb_width))
            self.thumbnails_per_row = optimal_per_row
        
        # Grid layout
        for i, thumb in enumerate(self.thumbnails):
            row = i // self.thumbnails_per_row
            col = i % self.thumbnails_per_row
            thumb.grid(row=row, column=col, padx=3, pady=3, sticky="n")
        
        # Auto-resize the frame height based on number of rows
        num_rows = math.ceil(total_thumbnails / self.thumbnails_per_row)
        thumb_height = self.mainapp.config_manager.get('thumbnail_height', 100)
        label_height = 20  # Approximate height of page label
        total_thumb_height = thumb_height + label_height + 6  # 6px padding
        min_frame_height = num_rows * total_thumb_height + 10  # 10px extra padding
        
        # Update frame minimum height
        self.pages_frame.configure(height=min_frame_height)

    def repack_thumbnails(self):
        """Legacy method - redirects to grid layout"""
        self.repack_thumbnails_grid()

    def get_drop_position(self, x_root: int) -> int:
        """Determine where to insert based on x coordinate - adapted for grid"""
        if not self.thumbnails:
            return 0
            
        frame_x = self.pages_frame.winfo_rootx()
        frame_y = self.pages_frame.winfo_rooty()
        relative_x = x_root - frame_x
        
        # Find the closest thumbnail position in grid
        closest_distance = float('inf')
        closest_position = len(self.thumbnails)
        
        for i, thumb in enumerate(self.thumbnails):
            try:
                # Get thumbnail center position
                thumb_info = thumb.grid_info()
                if thumb_info:
                    row = thumb_info.get('row', 0)
                    col = thumb_info.get('column', 0)
                    
                    # Estimate position based on grid
                    thumb_width = self.mainapp.config_manager.get('thumbnail_width', 80)
                    thumb_x = col * (thumb_width + 6) + (thumb_width // 2)
                    
                    distance = abs(relative_x - thumb_x)
                    if distance < closest_distance:
                        closest_distance = distance
                        closest_position = i
                        
                        # If we're to the left of center, insert before
                        if relative_x < thumb_x:
                            closest_position = i
                        else:
                            closest_position = i + 1
                            
            except tk.TclError:
                continue
        
        return min(closest_position, len(self.thumbnails))

    def calculate_optimal_thumbnails_per_row(self) -> int:
        """Calculate optimal number of thumbnails per row based on current frame width"""
        frame_width = self.pages_frame.winfo_width()
        if frame_width <= 1:
            return self.thumbnails_per_row  # Return current if width not available
        
        thumb_width = self.mainapp.config_manager.get('thumbnail_width', 80)
        padding_per_thumbnail = 6  # 3px padding on each side
        total_thumb_width = thumb_width + padding_per_thumbnail
        
        optimal_per_row = max(self.min_thumbnails_per_row, 
                            min(self.max_thumbnails_per_row, 
                                frame_width // total_thumb_width))
        
        return optimal_per_row

    def update_category_name(self, new_name: str):
        """Update the category name display"""
        self.categoryname = new_name
        
        # Get font settings from config
        font_name = self.mainapp.config_manager.get('document_font_name', 'Arial')
        font_size = self.mainapp.config_manager.get('document_font_size', 10)
        font_bold = self.mainapp.config_manager.get('document_font_bold', True)
        font_style = "bold" if font_bold else "normal"
        
        # Update header text with counter
        digits = self.mainapp.config_manager.get('document_counter_digits', 4)
        counter_text = f"{self.document_counter:0{digits}d}"
        header_text = f"{counter_text} {new_name}"
        
        # Update with LEFT alignment
        self.label.configure(text=header_text, font=(font_name, font_size, font_style),
                           anchor="w", justify="left")
        
        # Update all thumbnails in this group
        for thumb in self.thumbnails:
            thumb.update_category(new_name)

    def update_document_counter(self, new_counter: int):
        """Update document counter"""
        self.document_counter = new_counter
        
        # Get font settings from config
        font_name = self.mainapp.config_manager.get('document_font_name', 'Arial')
        font_size = self.mainapp.config_manager.get('document_font_size', 10)
        font_bold = self.mainapp.config_manager.get('document_font_bold', True)
        font_style = "bold" if font_bold else "normal"
        
        # Update header text with new counter
        digits = self.mainapp.config_manager.get('document_counter_digits', 4)
        counter_text = f"{new_counter:0{digits}d}"
        header_text = f"{counter_text} {self.categoryname}"
        
        # Update with LEFT alignment
        self.label.configure(text=header_text, font=(font_name, font_size, font_style),
                           anchor="w", justify="left")

    def refresh_font_settings(self):
        """Refresh the header font settings from config"""
        font_name = self.mainapp.config_manager.get('document_font_name', 'Arial')
        font_size = self.mainapp.config_manager.get('document_font_size', 10)
        font_bold = self.mainapp.config_manager.get('document_font_bold', True)
        font_style = "bold" if font_bold else "normal"
        digits = self.mainapp.config_manager.get('document_counter_digits', 4)
        
        counter_text = f"{self.document_counter:0{digits}d}"
        header_text = f"{counter_text} {self.categoryname}"
        self.label.configure(text=header_text, font=(font_name, font_size, font_style),
                           anchor="w", justify="left")

    def refresh_thumbnail_sizes(self):
        """Refresh all thumbnail sizes from config and repack grid"""
        thumb_width = self.mainapp.config_manager.get('thumbnail_width', 80)
        thumb_height = self.mainapp.config_manager.get('thumbnail_height', 100)
        
        for thumbnail in self.thumbnails:
            thumbnail.update_thumbnail_size(thumb_width, thumb_height)
        
        # Recalculate grid layout with new sizes
        self.thumbnails_per_row = self.calculate_optimal_thumbnails_per_row()
        self.repack_thumbnails_grid()

    def is_empty(self) -> bool:
        """Check if document group has no thumbnails"""
        return len(self.thumbnails) == 0

    def get_page_count(self) -> int:
        """Get number of pages in this group"""
        return len(self.thumbnails)

    def pack(self, **kwargs):
        """Pack the document group frame"""
        self.frame.pack(**kwargs)

    def pack_forget(self):
        """Remove the document group from display"""
        self.frame.pack_forget()

    def destroy(self):
        """Destroy the document group and all its thumbnails"""
        for thumb in self.thumbnails:
            thumb.destroy()
        self.frame.destroy()

    def get_info(self) -> dict:
        """Get document group information"""
        return {
            'category': self.categoryname,
            'counter': self.document_counter,
            'page_count': len(self.thumbnails),
            'pages': self.pages.copy(),
            'selected': self.isselected,
            'empty': self.is_empty(),
            'thumbnails_per_row': self.thumbnails_per_row,
            'grid_rows': math.ceil(len(self.thumbnails) / self.thumbnails_per_row) if self.thumbnails else 0
        }