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
                categoryname: str, mainapp: 'AIDOXAApp', document_group: 'DocumentGroup',
                width: Optional[int] = None, height: Optional[int] = None):
        """Initialize page thumbnail with configurable size
        
        Args:
            parent: Parent widget
            pagenum: Page number
            image: Page image (can be None for lazy loading)
            categoryname: Category name
            mainapp: Main application instance
            document_group: Parent document group
            width: Thumbnail width (optional, defaults to config)
            height: Thumbnail height (optional, defaults to config)
        """
        self.parent = parent
        self.pagenum = pagenum
        self.image = image  # Può essere None per lazy loading
        self.categoryname = categoryname
        self.mainapp = mainapp
        self.document_group = document_group
        self.is_selected = False
        
        # ⭐ NUOVO: Lazy loading support
        self.document_loader = None  # Riferimento al loader per lazy loading
        self.image_loaded = False    # Flag per sapere se immagine è caricata
        # ✅ NUOVO: Ottieni dimensioni da parametri o config
        if width is None:
            width = mainapp.config_manager.get('thumbnail_width', 80)
        if height is None:
            height = mainapp.config_manager.get('thumbnail_height', 100)

        # Store thumbnail size
        self.thumbnail_width = width
        self.thumbnail_height = height
        
        # Variables for managing drag vs click
        self.is_dragging = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        
        # ✅ Usa dimensioni già impostate sopra
        thumb_width = self.thumbnail_width
        thumb_height = self.thumbnail_height
        
        # ⭐ NUOVO: Crea thumbnail o placeholder
        if image is None:
            # Lazy loading - crea placeholder
            self.thumbnail_img_tk = self.create_placeholder_thumbnail((thumb_width, thumb_height))
        else:
            # Caricamento normale
            self.thumbnail_img_tk = self.create_thumbnail(image, (thumb_width, thumb_height))
            self.image_loaded = True
        
        # Store current thumbnail size for updates
        self.current_thumb_size = (thumb_width, thumb_height)
        
        # Create UI elements
        self.create_widgets()
        self.bind_events()
        
        # ⭐ NUOVO: Auto-load se c'è document_loader
        if image is None and hasattr(self, 'document_loader') and self.document_loader:
            self.mainapp.after(100, self.try_auto_load)

    def try_auto_load(self):
        """Prova a caricare automaticamente l'immagine dopo creazione"""
        if not self.image_loaded and self.document_loader:
            try:
                self.mainapp.debug_print(f"Auto-loading image for page {self.pagenum}")
                img = self.document_loader.get_page(self.pagenum)
                if img:
                    self.set_image(img)
            except Exception as e:
                self.mainapp.debug_print(f"Error in auto-load: {e}")

    def create_widgets(self):
        """Create the thumbnail UI widgets - RESPONSIVE"""
        # Main frame with enhanced selection styling
        self.frame = tk.Frame(self.parent, bd=2, relief="solid", bg="white")
        
        # ✅ NUOVO: Configura frame per centrare contenuto
        self.frame.grid_rowconfigure(0, weight=1)  # Image row si espande
        self.frame.grid_rowconfigure(1, weight=0)  # Label row fissa
        self.frame.grid_columnconfigure(0, weight=1)  # Colonna si espande
        
        # Image Label - centrata
        self.img_label = tk.Label(self.frame, image=self.thumbnail_img_tk, bg="white", cursor="hand2")
        self.img_label.grid(row=0, column=0, padx=2, pady=2, sticky="n")  # Allineata in alto
        
        # Page label - centrata in basso
        self.text_label = tk.Label(self.frame, text=f"Pagina {self.pagenum}", 
                                  font=("Arial", 8, "bold"), bg="white")
        self.text_label.grid(row=1, column=0, pady=(0, 2), sticky="ew")  # Si espande orizzontalmente

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
        
        thumb_w, thumb_h = size
        
        # Crea immagine placeholder con sfondo grigio chiaro
        placeholder = Image.new('RGB', size, color='#E0E0E0')
        draw = ImageDraw.Draw(placeholder)
        
        # Disegna bordo
        draw.rectangle([(2, 2), (thumb_w-3, thumb_h-3)], outline='#BDBDBD', width=2)
        
        # Disegna icona documento stilizzata
        icon_color = '#9E9E9E'
        center_x = thumb_w // 2
        center_y = thumb_h // 2 - 10
        
        # Rettangolo documento
        doc_w, doc_h = 30, 40
        draw.rectangle(
            [(center_x - doc_w//2, center_y - doc_h//2),
             (center_x + doc_w//2, center_y + doc_h//2)],
            outline=icon_color, width=2
        )
        
        # Linee orizzontali (testo simulato)
        for i in range(3):
            y = center_y - 10 + (i * 8)
            draw.line([(center_x - 12, y), (center_x + 12, y)], fill=icon_color, width=1)
        
        # Numero pagina
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()
        
        text = f"#{self.pagenum}"
        
        # Calcola dimensioni testo per centrarlo
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
        except:
            # Fallback per versioni vecchie di Pillow
            text_w = len(text) * 10
            text_h = 14
        
        text_x = (thumb_w - text_w) // 2
        text_y = thumb_h - 25
        
        draw.text((text_x, text_y), text, fill='#616161', font=font)
        
        # Label "Caricamento..."
        try:
            small_font = ImageFont.truetype("arial.ttf", 8)
        except:
            small_font = ImageFont.load_default()
        
        loading_text = "Caricamento..."
        try:
            bbox = draw.textbbox((0, 0), loading_text, font=small_font)
            text_w = bbox[2] - bbox[0]
        except:
            text_w = len(loading_text) * 6
        
        loading_x = (thumb_w - text_w) // 2
        
        draw.text((loading_x, thumb_h - 12), loading_text, fill='#9E9E9E', font=small_font)

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

    def set_document_loader(self, loader):
        """Imposta riferimento al document loader per lazy loading"""
        self.document_loader = loader
        self.mainapp.debug_print(f"Document loader set for page {self.pagenum}")

    def load_image_if_needed(self):
        """Carica immagine reale se necessario (per viewport loading)"""
        if not self.image_loaded and self.document_loader:
            try:
                self.mainapp.debug_print(f"Loading image for viewport - page {self.pagenum}")
                img = self.document_loader.get_page(self.pagenum)
                if img:
                    self.set_image(img)
                    return True
            except Exception as e:
                self.mainapp.debug_print(f"Error in viewport loading: {e}")
        return False

    def is_in_viewport(self, canvas_widget) -> bool:
        """Controlla se la thumbnail è visibile nel viewport"""
        try:
            # Ottieni posizione del frame rispetto al canvas
            frame_x = self.frame.winfo_x()
            frame_y = self.frame.winfo_y()
            frame_w = self.frame.winfo_width()
            frame_h = self.frame.winfo_height()
            
            # Ottieni dimensioni visibili del canvas
            canvas_width = canvas_widget.winfo_width()
            canvas_height = canvas_widget.winfo_height()
            
            # Controlla se interseca con il viewport
            visible = (frame_x < canvas_width and 
                    frame_x + frame_w > 0 and
                    frame_y < canvas_height and 
                    frame_y + frame_h > 0)
            
            return visible
            
        except Exception as e:
            # Se c'è un errore, assumiamo sia visibile per sicurezza
            return True

    def get_load_priority(self, scroll_top: int) -> int:
        """Ottieni priorità di caricamento basata su distanza da viewport"""
        try:
            frame_y = self.frame.winfo_y()
            distance = abs(frame_y - scroll_top)
            # Priorità inverse (0 = alta, 1000+ = bassa)  
            return min(9999, distance)
        except:
            return 5000  # Priorità media se errore

    def on_enter(self, event):
        """Handle mouse enter - show hover effect"""
        if not self.is_selected:
            self.frame.configure(bg="#E0E0E0")
            self.img_label.configure(bg="#E0E0E0")
            self.text_label.configure(bg="#E0E0E0")

    def on_leave(self, event):
        """Handle mouse leave - remove hover effect"""
        if not self.is_selected:
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
        self.is_selected = True
        self.frame.configure(bg="#87CEEB", relief="raised", bd=3)
        self.img_label.configure(bg="#87CEEB")
        self.text_label.configure(bg="#87CEEB")

    def deselect(self):
        self.is_selected = False
        try:
            self.frame.configure(bg="white", relief="solid", bd=2)
        except tk.TclError:
            # Widget già distrutto, ignora
            pass
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
            'selected': self.is_selected,
            'image_size': self.image.size if self.image else None,
            'thumbnail_size': self.current_thumb_size,
            'grid_position': {
                'row': grid_info.get('row', -1),
                'column': grid_info.get('column', -1)
            }
        }