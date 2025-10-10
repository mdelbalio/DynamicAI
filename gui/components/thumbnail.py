"""
Page thumbnail component for DynamicAI with grid layout support
"""

import tkinter as tk
from PIL import Image, ImageTk
from config.constants import RESAMPLEFILTER
from typing import TYPE_CHECKING, Tuple, Optional

if TYPE_CHECKING:
    from gui.main_window import AIDOXAApp
    from gui.components.document_group import DocumentGroup

class PageThumbnail:
    """Represents a page thumbnail with drag and drop capabilities and grid layout support"""
    
    def __init__(self, parent: tk.Widget, pagenum: int, image: Image.Image, 
                 categoryname: str, mainapp: 'AIDOXAApp', document_group: 'DocumentGroup'):
        self.parent = parent
        self.pagenum = pagenum
        self.image = image  # Può essere None per lazy loading
        self.categoryname = categoryname
        self.mainapp = mainapp
        self.document_group = document_group
        self.isselected = False

        # ⭐ NUOVO: Lazy loading support
        self.document_loader = None  # Riferimento al loader per lazy loading
        self.image_loaded = False  # Flag per sapere se immagine è caricata
    
        # Variables for managing drag vs click
        self.is_dragging = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None

        # Get thumbnail size from config
        thumb_width = mainapp.config_manager.get('thumbnail_width', 80)
        thumb_height = mainapp.config_manager.get('thumbnail_height', 100)

        # ⭐ NUOVO: Crea thumbnail o placeholder
        if image is None:
            # Lazy loading: crea placeholder
            self.thumbnail_imgtk = self.create_placeholder_thumbnail((thumb_width, thumb_height))
        else:
            # Caricamento normale
            self.thumbnail_imgtk = self.create_thumbnail(image, (thumb_width, thumb_height))
            self.image_loaded = True

        # Store current thumbnail size for updates
        self.current_thumb_size = (thumb_width, thumb_height)
        
        # Create UI elements
        self.create_widgets()
        self.bind_events()

    def create_widgets(self):
        """Create the thumbnail UI widgets"""
        # Main frame with enhanced selection styling
        self.frame = tk.Frame(self.parent, bd=2, relief="solid", bg="white")
        
        # Image Label
        self.img_label = tk.Label(self.frame, image=self.thumbnail_imgtk, bg="white", cursor="hand2")
        self.img_label.pack(padx=2, pady=2)
        
        # Page label
        self.text_label = tk.Label(self.frame, text=f"Pagina {self.pagenum}", 
                                  font=("Arial", 8, "bold"), bg="white")
        self.text_label.pack(pady=(0, 2))

    def bind_events(self):
        """Bind mouse events for drag and drop and selection"""
        widgets = [self.frame, self.img_label, self.text_label]
        
        for widget in widgets:
            # Mouse events for drag and drop
            widget.bind("<Button-1>", self.on_button_press)
            widget.bind("<B1-Motion>", self.on_drag_motion)
            widget.bind("<ButtonRelease-1>", self.on_button_release)
            
            # Hover events for visual feedback
            widget.bind("<Enter>", self.on_enter)
            widget.bind("<Leave>", self.on_leave)

    def create_thumbnail(self, image: Image.Image, size: Tuple[int, int] = (80, 100)) -> ImageTk.PhotoImage:
        """Create a thumbnail version of the image"""
        img_copy = image.copy()
        img_copy.thumbnail(size, RESAMPLEFILTER)
        return ImageTk.PhotoImage(img_copy)

    # ⭐⭐⭐ AGGIUNGI QUESTI METODI QUI ⭐⭐⭐

    def create_placeholder_thumbnail(self, size: Tuple[int, int] = (80, 100)) -> ImageTk.PhotoImage:
        """Crea thumbnail placeholder veloce per lazy loading"""
        from PIL import ImageDraw, ImageFont
        
        # Crea immagine grigia con numero pagina
        placeholder = Image.new('RGB', size, color='#CCCCCC')
        draw = ImageDraw.Draw(placeholder)
        
        # Disegna numero pagina
        text = str(self.pagenum)
        try:
            # Prova font TrueType
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            # Fallback font default
            font = ImageFont.load_default()
        
        # Centra il testo
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except:
            # Fallback per versioni vecchie di Pillow
            text_width = len(text) * 10
            text_height = 14
        
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        draw.text((x, y), text, fill='#666666', font=font)
        
        return ImageTk.PhotoImage(placeholder)

    def set_image(self, image: Image.Image):
        """Imposta immagine reale (chiamato da lazy loading)"""
        self.image = image
        
        # Ricrea thumbnail con immagine reale
        thumb_width = self.mainapp.config_manager.get('thumbnail_width', 80)
        thumb_height = self.mainapp.config_manager.get('thumbnail_height', 100)
        self.thumbnail_imgtk = self.create_thumbnail(image, (thumb_width, thumb_height))
        
        # Aggiorna label
        self.img_label.configure(image=self.thumbnail_imgtk)
        
        self.image_loaded = True
        self.mainapp.debug_print(f"Image loaded for page {self.pagenum}")

    def on_enter(self, event):
        """Handle mouse enter - show hover effect"""
        if not self.isselected:
            self.frame.configure(bg="#E0E0E0")
            self.img_label.configure(bg="#E0E0E0")
            self.text_label.configure(bg="#E0E0E0")

    def on_leave(self, event):
        """Handle mouse leave - remove hover effect"""
        if not self.isselected:
            self.frame.configure(bg="white")
            self.img_label.configure(bg="white")
            self.text_label.configure(bg="white")

    def on_button_press(self, event):
        """Handle button press - start potential drag"""
        # ⭐ NUOVO: Carica immagine reale se non ancora caricata (lazy loading)
        if not self.image_loaded and self.document_loader:
            try:
                self.mainapp.debug_print(f"Loading image on demand for page {self.pagenum}")
                img = self.document_loader.get_page(self.pagenum)
                if img:
                    self.set_image(img)
            except Exception as e:
                self.mainapp.debug_print(f"Error loading image on demand: {e}")
        
        self.drag_start_pos = (event.x_root, event.y_root)
        self.is_dragging = False
        self.mainapp.debug_print(f"Button press on page {self.pagenum}")

    def on_drag_motion(self, event):
        """Handle drag motion - determine if it's drag or click"""
        if self.drag_start_pos:
            dx = event.x_root - self.drag_start_pos[0]
            dy = event.y_root - self.drag_start_pos[1]
            distance = (dx**2 + dy**2)**0.5
            
            # If moves more than 5 pixels, start drag
            if distance > 5 and not self.is_dragging:
                self.is_dragging = True
                self.mainapp.debug_print(f"Starting drag for page {self.pagenum}")
                self.start_drag()
                
            if self.is_dragging:
                self.continue_drag(event)

    def on_button_release(self, event):
        """Handle button release - execute click or end drag"""
        if self.is_dragging:
            # Was a drag, end it
            self.mainapp.debug_print(f"Ending drag for page {self.pagenum}")
            self.end_drag(event)
        else:
            # Was a simple click, select the thumbnail
            self.mainapp.debug_print(f"Click detected on page {self.pagenum}")
            self.mainapp.select_thumbnail(self)
        
        # Reset state
        self.is_dragging = False
        self.drag_start_pos = None

    def start_drag(self):
        """Start drag operation"""
        self.mainapp.dragging = True
        self.mainapp.drag_item = self

    def continue_drag(self, event):
        """Continue drag operation"""
        if self.mainapp.drag_preview is None:
            self.mainapp.create_drag_preview(self)
        self.mainapp.move_drag_preview(event.x_root + 20, event.y_root + 20)

    def end_drag(self, event):
        """End drag operation"""
        self.mainapp.stop_drag(event.x_root, event.y_root)

    def select(self):
        """Select this thumbnail"""
        self.isselected = True
        self.frame.configure(bg="#87CEEB", relief="raised", bd=3)
        self.img_label.configure(bg="#87CEEB")
        self.text_label.configure(bg="#87CEEB")

    def deselect(self):
        """Deselect this thumbnail"""
        self.isselected = False
        self.frame.configure(bg="white", relief="solid", bd=2)
        self.img_label.configure(bg="white")
        self.text_label.configure(bg="white")

    def update_category(self, new_category: str):
        """Update the category name for this thumbnail"""
        self.categoryname = new_category
        # The page number display doesn't change, only internal category

    def update_thumbnail_size(self, width: int, height: int):
        """Update thumbnail size with new dimensions"""
        if (width, height) != self.current_thumb_size:
            self.current_thumb_size = (width, height)
            self.thumbnail_imgtk = self.create_thumbnail(self.image, (width, height))
            self.img_label.configure(image=self.thumbnail_imgtk)

    # Grid layout methods
    def grid(self, **kwargs):
        """Place the thumbnail using grid geometry manager"""
        self.frame.grid(**kwargs)

    def grid_forget(self):
        """Remove the thumbnail from grid display"""
        self.frame.grid_forget()

    def grid_info(self):
        """Get grid information for this thumbnail"""
        return self.frame.grid_info()

    # Legacy pack methods for backward compatibility
    def pack(self, **kwargs):
        """Place the thumbnail using pack geometry manager (legacy)"""
        self.frame.pack(**kwargs)

    def pack_forget(self):
        """Remove the thumbnail from pack display (legacy)"""
        self.frame.pack_forget()

    def destroy(self):
        """Destroy the thumbnail widget"""
        try:
            self.frame.destroy()
        except tk.TclError:
            # Widget already destroyed
            pass

    def get_info(self) -> dict:
        """Get thumbnail information"""
        grid_info = {}
        try:
            grid_info = self.grid_info()
        except tk.TclError:
            grid_info = {}
            
        return {
            'pagenum': self.pagenum,
            'category': self.categoryname,
            'selected': self.isselected,
            'image_size': self.image.size if self.image else None,
            'thumbnail_size': self.current_thumb_size,
            'grid_position': {
                'row': grid_info.get('row', -1),
                'column': grid_info.get('column', -1)
            }
        }