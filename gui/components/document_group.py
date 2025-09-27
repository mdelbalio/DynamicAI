"""
Document group component for DynamicAI
"""

import tkinter as tk
from PIL import Image
from typing import TYPE_CHECKING, List, Optional
from .thumbnail import PageThumbnail

if TYPE_CHECKING:
    from gui.main_window import AIDOXAApp

class DocumentGroup:
    """Represents a group of pages belonging to the same document category"""
    
    def __init__(self, parent: tk.Widget, categoryname: str, mainapp: 'AIDOXAApp', document_counter: int):
        self.parent = parent  # <-- QUESTO ERA MANCANTE
        self.mainapp = mainapp
        self.categoryname = categoryname
        self.document_counter = document_counter
        self.isselected = False
        self.thumbnails: List[PageThumbnail] = []
        self.pages: List[int] = []
        
        # Create UI elements
        self.create_widgets()
        self.bind_events()

    def create_widgets(self):
        """Create the document group UI widgets"""
        # Main frame with colored background
        self.frame = tk.Frame(self.parent, bd=2, relief="ridge", bg="#f0f0f0")
        
        # Create header with document counter and category name
        self.create_header()
        
        # Container for thumbnails without wrapping (original layout)
        self.pages_frame = tk.Frame(self.frame, bg="white")
        self.pages_frame.pack(fill="x", padx=5, pady=5)

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
            # Add at end
            thumbnail.pack(side="left", padx=3, pady=3)
            self.thumbnails.append(thumbnail)
            if pagenum not in self.pages:
                self.pages.append(pagenum)
        else:
            # Insert at specific position
            self.thumbnails.insert(position, thumbnail)
            if pagenum not in self.pages:
                self.pages.insert(position, pagenum)
            self.repack_thumbnails()
        
        return thumbnail

    def remove_thumbnail(self, thumbnail: PageThumbnail) -> int:
        """Remove a thumbnail from this group"""
        if thumbnail in self.thumbnails:
            index = self.thumbnails.index(thumbnail)
            self.thumbnails.remove(thumbnail)
            thumbnail.pack_forget()
            if thumbnail.pagenum in self.pages:
                self.pages.remove(thumbnail.pagenum)
            return index
        return -1

    def repack_thumbnails(self):
        """Repack all thumbnails in the correct order"""
        for thumb in self.thumbnails:
            thumb.pack_forget()
        for thumb in self.thumbnails:
            thumb.pack(side="left", padx=3, pady=3)

    def get_drop_position(self, x_root: int) -> int:
        """Determine where to insert based on x coordinate"""
        if not self.thumbnails:
            return 0
            
        frame_x = self.pages_frame.winfo_rootx()
        relative_x = x_root - frame_x
        
        for i, thumb in enumerate(self.thumbnails):
            try:
                thumb_x = thumb.frame.winfo_x() + thumb.frame.winfo_width() // 2
                if relative_x < thumb_x:
                    return i
            except tk.TclError:
                continue
        
        return len(self.thumbnails)

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
        """Refresh all thumbnail sizes from config"""
        thumb_width = self.mainapp.config_manager.get('thumbnail_width', 80)
        thumb_height = self.mainapp.config_manager.get('thumbnail_height', 100)
        
        for thumbnail in self.thumbnails:
            thumbnail.update_thumbnail_size(thumb_width, thumb_height)

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
            'empty': self.is_empty()
        }