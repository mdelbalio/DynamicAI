import os
import io
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
from tkinter.scrolledtext import ScrolledText
from PIL import Image, ImageTk, ImageSequence
import threading
import queue
from concurrent.futures import ThreadPoolExecutor
try:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.LANCZOS
import fitz

CONFIG_FILE = "config.json"

class OverwriteDialog:
    def __init__(self, parent, filename):
        self.top = tk.Toplevel(parent)
        self.top.title("File Esistente")
        self.top.geometry("500x200")
        self.top.resizable(False, False)
        self.top.grab_set()
        self.top.transient(parent)
        self.top.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
        self.result = 'cancel'
        self.top.protocol("WM_DELETE_WINDOW", self.cancel)
        
        main_frame = tk.Frame(self.top, bg='white')
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tk.Label(main_frame, text="Il file già esiste:", font=('Arial', 12, 'bold'), bg='white').pack()
        tk.Label(main_frame, text=f"'{filename}'", font=('Arial', 10), bg='white', fg='blue').pack(pady=(5,15))
        tk.Label(main_frame, text="Cosa vuoi fare?", font=('Arial', 11), bg='white').pack()
        
        btn_frame = tk.Frame(main_frame, bg='white')
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Sovrascrivi", width=12, command=self.yes, 
                 bg='lightgreen', font=('Arial', 9, 'bold')).grid(row=0, column=0, padx=3)
        tk.Button(btn_frame, text="Salta", width=12, command=self.no, 
                 bg='orange', font=('Arial', 9, 'bold')).grid(row=0, column=1, padx=3)
        tk.Button(btn_frame, text="Sovrascrivi Tutto", width=15, command=self.yes_all, 
                 bg='lightblue', font=('Arial', 9, 'bold')).grid(row=0, column=2, padx=3)
        tk.Button(btn_frame, text="Salta Tutto", width=12, command=self.no_all, 
                 bg='yellow', font=('Arial', 9, 'bold')).grid(row=0, column=3, padx=3)
        tk.Button(btn_frame, text="Annulla", width=12, command=self.cancel, 
                 bg='lightcoral', font=('Arial', 9, 'bold')).grid(row=0, column=4, padx=3)
        
        self.top.focus_set()
    
    def yes(self):
        self.result = 'yes'
        self.top.destroy()
    
    def no(self):
        self.result = 'no'
        self.top.destroy()
    
    def yes_all(self):
        self.result = 'yes_all'
        self.top.destroy()
    
    def no_all(self):
        self.result = 'no_all'
        self.top.destroy()
    
    def cancel(self):
        self.result = 'cancel'
        self.top.destroy()

class BatchOverwriteDialog:
    def __init__(self, parent, existing_files):
        self.top = tk.Toplevel(parent)
        self.top.title("File Multipli Esistenti")
        self.top.geometry("650x500")
        self.top.resizable(True, True)
        self.top.grab_set()
        self.top.transient(parent)
        self.top.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")
        self.result = 'cancel'
        self.individual_decisions = {}
        self.top.protocol("WM_DELETE_WINDOW", self.cancel)
        
        main_frame = tk.Frame(self.top, bg='white')
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        tk.Label(main_frame, text=f"Trovati {len(existing_files)} file già esistenti:", 
                font=('Arial', 12, 'bold'), bg='white').pack()
        
        list_frame = tk.Frame(main_frame, bg='white')
        list_frame.pack(fill='both', expand=True, pady=(15,20))
        
        list_scrollbar = tk.Scrollbar(list_frame)
        list_scrollbar.pack(side='right', fill='y')
        
        files_listbox = tk.Listbox(list_frame, yscrollcommand=list_scrollbar.set,
                                  font=('Consolas', 9), height=10)
        files_listbox.pack(side='left', fill='both', expand=True)
        list_scrollbar.config(command=files_listbox.yview)
        
        for filename in existing_files:
            files_listbox.insert(tk.END, filename)
        
        tk.Label(main_frame, text="Cosa vuoi fare?", font=('Arial', 11), bg='white').pack(pady=(0,15))
        
        btn_frame = tk.Frame(main_frame, bg='white')
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Sovrascrivi Tutto", width=18, command=self.overwrite_all, 
                 bg='lightgreen', font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Salta Tutto", width=15, command=self.skip_all, 
                 bg='orange', font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Annulla Export", width=15, command=self.cancel, 
                 bg='lightcoral', font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        
        self.top.focus_set()
    
    def overwrite_all(self):
        self.result = 'overwrite_all'
        self.top.destroy()
    
    def skip_all(self):
        self.result = 'skip_all'
        self.top.destroy()
    
    def cancel(self):
        self.result = 'cancel'
        self.top.destroy()

class PageThumbnail:
    def __init__(self, parent, page_num, image, category_name, main_app):
        self.parent = parent
        self.page_num = page_num
        self.original_image = image
        self.category_name = category_name
        self.main_app = main_app
        self.is_selected = False
        
        self.thumbnail = self.create_thumbnail(image)
        
        self.main_frame = tk.Frame(parent, bg='white', relief='solid', bd=1)
        
        self.image_frame = tk.Frame(self.main_frame, bg='white', cursor='hand2')
        self.image_frame.pack(fill='x', padx=2, pady=2)
        
        self.image_label = tk.Label(self.image_frame, image=self.thumbnail, bg='white')
        self.image_label.pack()
        
        self.info_frame = tk.Frame(self.main_frame, bg='lightgray')
        self.info_frame.pack(fill='x')
        
        self.page_label = tk.Label(self.info_frame, text=f"Pagina {page_num}", 
                                  font=('Arial', 8, 'bold'), bg='lightgray', fg='darkblue')
        self.page_label.pack()
        
        self.category_label = tk.Label(self.info_frame, text=category_name, 
                                      font=('Arial', 7), bg='lightgray', fg='darkgreen')
        self.category_label.pack()
        
        # Binding per selezione
        self.main_frame.bind('<Button-1>', self.on_click)
        self.image_frame.bind('<Button-1>', self.on_click)
        self.image_label.bind('<Button-1>', self.on_click)
        self.info_frame.bind('<Button-1>', self.on_click)
        self.page_label.bind('<Button-1>', self.on_click)
        self.category_label.bind('<Button-1>', self.on_click)
    
    def create_thumbnail(self, image):
        thumb_size = (80, 100)
        thumb_img = image.copy()
        thumb_img.thumbnail(thumb_size, RESAMPLE_FILTER)
        return ImageTk.PhotoImage(thumb_img)
    
    def on_click(self, event):
        self.main_app.deselect_all_thumbnails()
        self.select()
        self.main_app.show_page_in_viewer(self.page_num - 1)
        self.main_app.update_right_panel(self.page_num, self.category_name)
    
    def select(self):
        self.is_selected = True
        self.main_app.selected_thumbnail = self
        self.main_frame.configure(bg='lightblue', relief='raised', bd=3)
        self.image_frame.configure(bg='lightblue')
        self.info_frame.configure(bg='lightblue')
        self.page_label.configure(bg='lightblue')
        self.category_label.configure(bg='lightblue')
    
    def deselect(self):
        self.is_selected = False
        self.main_frame.configure(bg='white', relief='solid', bd=1)
        self.image_frame.configure(bg='white')
        self.info_frame.configure(bg='lightgray')
        self.page_label.configure(bg='lightgray')
        self.category_label.configure(bg='lightgray')
    
    def update_category(self, new_category):
        self.category_name = new_category
        self.category_label.configure(text=new_category)
    
    def pack(self, **kwargs):
        self.main_frame.pack(**kwargs)
    
    def destroy(self):
        self.main_frame.destroy()

class DocumentLoader:
    def __init__(self, doc_path, file_type):
        self.doc_path = doc_path
        self.file_type = file_type
        self._cache = {}
        self._doc_handle = None
        self._tiff_pages = None
        self.total_pages = 0
        
    def __enter__(self):
        if self.file_type == "pdf":
            self._doc_handle = fitz.open(self.doc_path)
            self.total_pages = len(self._doc_handle)
        elif self.file_type in ["tiff", "tif"]:
            img = Image.open(self.doc_path)
            self._tiff_pages = [page.copy() for page in ImageSequence.Iterator(img)]
            img.close()
            self.total_pages = len(self._tiff_pages)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._doc_handle:
            self._doc_handle.close()
        if self._tiff_pages:
            for page in self._tiff_pages:
                page.close()
            self._tiff_pages = None
    
    def get_page(self, page_num):
        if page_num in self._cache:
            return self._cache[page_num]
        
        actual_page_num = page_num - 1
        
        try:
            if self.file_type == "pdf" and self._doc_handle:
                if actual_page_num < len(self._doc_handle):
                    pix = self._doc_handle[actual_page_num].get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                else:
                    return None
                    
            elif self.file_type in ["tiff", "tif"] and self._tiff_pages:
                if actual_page_num < len(self._tiff_pages):
                    img = self._tiff_pages[actual_page_num].copy()
                else:
                    return None
            else:
                return None
            
            if len(self._cache) > 20:
                oldest_key = next(iter(self._cache))
                old_img = self._cache.pop(oldest_key)
                old_img.close()
                
            self._cache[page_num] = img
            return img
            
        except Exception as e:
            print(f"Errore nel caricamento pagina {page_num}: {e}")
            return None

class AIDOXAApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AIDOXA - Editor Lineare")
        self.configure(bg='white')
        
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar()
        self.overwrite_files = tk.BooleanVar(value=True)
        
        self.doc_file = ""
        self.json_file = ""
        self.page_thumbnails = []
        self.available_categories = []
        self.current_page_index = 0
        self.zoom_factor = 0
        self.current_photo = None
        self.document_loader = None
        self.selected_thumbnail = None
        
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.result_queue = queue.Queue()
        
        self.load_config()
        self.create_widgets()
        self.apply_saved_geometry()
        self.bind_geometry_events()
        self.check_async_results()
    
    def create_widgets(self):
        menubar = tk.Menu(self)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="Impostazioni", command=self.open_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="Nuova Categoria", command=self.create_new_category)
        menubar.add_cascade(label="Menu", menu=settings_menu)
        self.config(menu=menubar)
        
        self.main_paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        self.main_paned.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.left_frame = tk.Frame(self.main_paned, bg='lightgray', relief=tk.SUNKEN, bd=1)
        self.main_paned.add(self.left_frame, width=350, minsize=300)
        
        self.right_paned = tk.PanedWindow(self.main_paned, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=4)
        self.main_paned.add(self.right_paned, minsize=400)
        
        self.center_frame = tk.Frame(self.right_paned, bg='black', relief=tk.SUNKEN, bd=1)
        self.right_paned.add(self.center_frame, width=600, minsize=300)
        
        self.right_frame = tk.Frame(self.right_paned, bg='lightgray', relief=tk.SUNKEN, bd=1)
        self.right_paned.add(self.right_frame, width=320, minsize=250)
        
        self.after(100, self.set_initial_proportions)
        
        # Pannello sinistro
        header_frame = tk.Frame(self.left_frame, bg='lightgray')
        header_frame.pack(fill='x', pady=(5,5))
        
        tk.Label(header_frame, text="Editor Documenti", bg='lightgray', 
                font=("Arial", 12, "bold"), fg='darkblue').pack()
        
        btn_frame = tk.Frame(self.left_frame, bg='lightgray')
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        self.btn_scan = tk.Button(btn_frame, text="Carica", 
                                 command=self.scan_and_preview, bg='lightblue', 
                                 font=('Arial', 9, 'bold'), width=8)
        self.btn_scan.pack(side='left', padx=2)
        
        self.btn_export = tk.Button(btn_frame, text="Esporta", 
                                   command=self.export_documents, bg='lightgreen', 
                                   font=('Arial', 9, 'bold'), width=8)
        self.btn_export.pack(side='left', padx=2)
        
        tk.Button(btn_frame, text="Nuova Cat.", 
                 command=self.create_new_category, bg='lightyellow', 
                 font=('Arial', 9), width=10).pack(side='left', padx=2)
        
        self.progress_var = tk.StringVar(value="")
        self.progress_label = tk.Label(self.left_frame, textvariable=self.progress_var, 
                                     bg='lightgray', font=('Arial', 8), fg='darkgreen')
        self.progress_label.pack(fill='x', padx=5)
        
        main_scroll_frame = tk.Frame(self.left_frame, bg='lightgray')
        main_scroll_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.pages_canvas = tk.Canvas(main_scroll_frame, bg='white', highlightthickness=0)
        self.pages_scrollbar = tk.Scrollbar(main_scroll_frame, orient="vertical", command=self.pages_canvas.yview)
        self.pages_scrollable_frame = tk.Frame(self.pages_canvas, bg='white')
        
        self.pages_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.pages_canvas.configure(scrollregion=self.pages_canvas.bbox("all"))
        )
        
        self.pages_canvas.create_window((0, 0), window=self.pages_scrollable_frame, anchor="nw")
        self.pages_canvas.configure(yscrollcommand=self.pages_scrollbar.set)
        
        self.pages_canvas.pack(side="left", fill="both", expand=True)
        self.pages_scrollbar.pack(side="right", fill="y")
        
        self.pages_canvas.bind("<MouseWheel>", self.on_pages_scroll)
        
        # Pannello centrale
        self.setup_canvas()
        
        # Pannello destro
        tk.Label(self.right_frame, text="Dettagli Pagina", bg='lightgray', 
                font=("Arial", 12, "bold"), fg='darkblue').pack(pady=(10,5))
        
        detail_frame = tk.Frame(self.right_frame, bg='lightgray')
        detail_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        info_frame = tk.Frame(detail_frame, bg='white', relief='solid', bd=1)
        info_frame.pack(fill='x', pady=(0,10))
        
        page_info_frame = tk.Frame(info_frame, bg='white')
        page_info_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(page_info_frame, text="Pagina:", font=('Arial', 10, 'bold'), 
                bg='white').pack(side='left')
        self.selected_page_label = tk.Label(page_info_frame, text="Nessuna", 
                                           font=('Arial', 10), bg='white', fg='blue')
        self.selected_page_label.pack(side='left', padx=(10,0))
        
        category_frame = tk.Frame(info_frame, bg='white')
        category_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(category_frame, text="Categoria:", font=('Arial', 10, 'bold'), 
                bg='white').pack(anchor='w')
        
        self.category_var = tk.StringVar()
        self.category_dropdown = ttk.Combobox(category_frame, textvariable=self.category_var,
                                            state="readonly", font=('Arial', 9))
        self.category_dropdown.pack(fill='x', pady=(5,10))
        self.category_dropdown.bind('<<ComboboxSelected>>', self.on_category_changed)
        
        self.detail_text = ScrolledText(detail_frame, bg='white', wrap=tk.WORD, 
                                       font=('Arial', 9), relief=tk.SUNKEN, bd=2, height=15)
        self.detail_text.pack(fill='both', expand=True)
        
        self.status_bar = tk.Label(self, text="Pronto", bg='lightsteelblue', 
                                  anchor='w', font=('Arial', 9))
        self.status_bar.pack(fill='x', side='bottom')
    
    def setup_canvas(self):
        self.canvas_frame = tk.Frame(self.center_frame, bg='black')
        self.canvas_frame.pack(fill='both', expand=True, padx=2, pady=2)
        
        canvas_container = tk.Frame(self.canvas_frame, bg='black')
        canvas_container.pack(fill='both', expand=True)
        
        self.canvas = tk.Canvas(canvas_container, bg='black', cursor='cross')
        
        self.h_scroll = tk.Scrollbar(canvas_container, orient='horizontal', command=self.canvas.xview)
        self.v_scroll = tk.Scrollbar(canvas_container, orient='vertical', command=self.canvas.yview)
        
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)
        
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.h_scroll.grid(row=1, column=0, sticky='ew')
        self.v_scroll.grid(row=0, column=1, sticky='ns')
        
        canvas_container.grid_rowconfigure(0, weight=1)
        canvas_container.grid_columnconfigure(0, weight=1)
        
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_click)
        self.canvas.bind("<ButtonPress-3>", self.pan_start)
        self.canvas.bind("<B3-Motion>", self.pan_move)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)
        
        ctrl_frame = tk.Frame(self.center_frame, bg='darkgray', height=50)
        ctrl_frame.pack(fill='x', side='bottom')
        ctrl_frame.pack_propagate(False)
        
        btn_ctrl_frame = tk.Frame(ctrl_frame, bg='darkgray')
        btn_ctrl_frame.pack(expand=True)
        
        self.btn_zoom_out = tk.Button(btn_ctrl_frame, text="Zoom -", command=self.zoom_out, 
                                     bg='orange', font=('Arial', 9))
        self.btn_zoom_out.pack(side='left', padx=2, pady=5)
        
        self.btn_zoom_fit = tk.Button(btn_ctrl_frame, text="Adatta", command=self.zoom_fit, 
                                     bg='yellow', font=('Arial', 9))
        self.btn_zoom_fit.pack(side='left', padx=2, pady=5)
        
        self.btn_zoom_in = tk.Button(btn_ctrl_frame, text="Zoom +", command=self.zoom_in, 
                                    bg='orange', font=('Arial', 9))
        self.btn_zoom_in.pack(side='left', padx=2, pady=5)
        
        self.page_label = tk.Label(btn_ctrl_frame, text="Nessuna pagina", bg='darkgray', 
                                  fg='white', font=('Arial', 10, 'bold'))
        self.page_label.pack(side='right', padx=10)
    
    def on_pages_scroll(self, event):
        self.pages_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def deselect_all_thumbnails(self):
        for thumbnail in self.page_thumbnails:
            thumbnail.deselect()
        self.selected_thumbnail = None
    
    def update_right_panel(self, page_num, category_name):
        self.selected_page_label.config(text=str(page_num))
        self.category_var.set(category_name)
        
        self.detail_text.delete('1.0', tk.END)
        
        detail_lines = [
            f"Pagina selezionata: {page_num}",
            f"Categoria corrente: {category_name}",
            f"Totale pagine: {len(self.page_thumbnails)}",
            "",
            "Istruzioni:",
            "• Click singolo su miniatura = seleziona e visualizza",
            "• Usa dropdown per cambiare categoria",
            "",
            "Zoom:",
            "• Click sul canvas = zoom adattato",
            "• Ctrl + rotella mouse = zoom in/out",
            "• Tasto destro + trascina = panning",
        ]
        
        self.detail_text.insert(tk.END, '\n'.join(detail_lines))
    
    def on_category_changed(self, event=None):
        if self.selected_thumbnail:
            new_category = self.category_var.get()
            self.selected_thumbnail.update_category(new_category)
            self.status_set(f"Categoria cambiata in: {new_category}")
    
    def add_page_thumbnail(self, page_num, image, category_name):
        thumbnail = PageThumbnail(self.pages_scrollable_frame, page_num, image, category_name, self)
        self.page_thumbnails.append(thumbnail)
        thumbnail.pack(fill='x', pady=2, padx=2)
        
        self.pages_scrollable_frame.update_idletasks()
        self.pages_canvas.configure(scrollregion=self.pages_canvas.bbox("all"))
        
        return thumbnail
    
    def clear_thumbnails(self):
        for thumbnail in self.page_thumbnails:
            thumbnail.destroy()
        self.page_thumbnails.clear()
        self.selected_thumbnail = None
    
    def create_new_category(self):
        name = simpledialog.askstring("Nuova Categoria", "Nome della categoria:")
        if name and name.strip() and name.strip() not in self.available_categories:
            self.available_categories.append(name.strip())
            self.available_categories.sort()
            self.category_dropdown['values'] = self.available_categories
            self.status_set(f"Categoria '{name}' aggiunta")
        elif name and name.strip() in self.available_categories:
            messagebox.showinfo("Info", "Categoria già esistente")
    
    def show_page_in_viewer(self, page_index):
        if not self.document_loader:
            return
        
        self.current_page_index = page_index
        page_num = page_index + 1
        
        image = self.document_loader.get_page(page_num)
        if not image:
            self.clear_canvas()
            return
        
        if self.zoom_factor <= 0:
            self.zoom_factor = 1.0
        
        w, h = image.size
        zoomed_w = int(w * self.zoom_factor)
        zoomed_h = int(h * self.zoom_factor)
        
        try:
            img_resized = image.resize((zoomed_w, zoomed_h), RESAMPLE_FILTER)
            self.current_photo = ImageTk.PhotoImage(img_resized)
            
            self.canvas.delete('all')
            self.canvas.config(scrollregion=(0, 0, zoomed_w, zoomed_h))
            self.canvas.create_image(0, 0, anchor='nw', image=self.current_photo)
            
            self.page_label.config(text=f"Pagina {page_num} / {self.document_loader.total_pages}")
                
        except Exception as e:
            self.status_set(f"Errore nella visualizzazione: {e}")
    
    def scan_and_preview(self):
        folder = self.input_folder.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showwarning("Attenzione", "Cartella input non valida.\nUsa Menu → Impostazioni")
            return
        
        self.btn_scan.config(state='disabled', text="Carico...")
        self.progress_var.set("Scansione cartella...")
        
        future = self.executor.submit(self._scan_documents, folder)
    
    def _scan_documents(self, folder):
        try:
            files = os.listdir(folder)
            document_files = self._find_document_files(files)
            json_files = [f for f in files if f.lower().endswith('.json')]
            
            if not document_files:
                raise Exception("Nessun PDF o TIFF trovato")
            if not json_files:
                raise Exception("Nessun file JSON trovato")
            
            doc_file = document_files[0]
            json_file = json_files[0]
            
            with open(os.path.join(folder, json_file), 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            categories = data.get('categories', [])
            
            ext = os.path.splitext(doc_file)[1].lower()
            file_type = "pdf" if ext == ".pdf" else "tiff"
            full_doc_path = os.path.join(folder, doc_file)
            
            document_loader = DocumentLoader(full_doc_path, file_type)
            document_loader.__enter__()
            
            self.result_queue.put({
                'type': 'scan_complete',
                'data': {
                    'doc_file': doc_file,
                    'categories': categories,
                    'document_loader': document_loader
                }
            })
            
        except Exception as e:
            self.result_queue.put({
                'type': 'error',
                'data': {'message': str(e)}
            })
    
    def _find_document_files(self, files):
        pdfs = [f for f in files if f.lower().endswith('.pdf')]
        tiffs = [f for f in files if f.lower().endswith(('.tiff', '.tif'))]
        return pdfs + tiffs
    
    def check_async_results(self):
        try:
            while True:
                result = self.result_queue.get_nowait()
                if result['type'] == 'scan_complete':
                    self._handle_scan_complete(result['data'])
                elif result['type'] == 'export_progress':
                    self._handle_export_progress(result['data'])
                elif result['type'] == 'export_complete':
                    self._handle_export_complete(result['data'])
                elif result['type'] == 'error':
                    self._handle_error(result['data'])
        except queue.Empty:
            pass
        finally:
            self.after(100, self.check_async_results)
    
    def _handle_scan_complete(self, data):
        self.doc_file = data['doc_file']
        self.document_loader = data['document_loader']
        
        self.clear_thumbnails()
        
        self.available_categories = self._extract_all_categories(data['categories'])
        self.category_dropdown['values'] = self.available_categories
        
        self._create_linear_thumbnails(data['categories'])
        
        self.btn_scan.config(state='normal', text="Carica")
        self.progress_var.set("")
        
        self.status_set(f"Documento caricato: {len(self.page_thumbnails)} pagine")
        
        if self.page_thumbnails:
            self.page_thumbnails[0].on_click(None)
    
    def _extract_all_categories(self, categories_data):
        categories = set()
        for cat in categories_data:
            if cat['categoria'] != 'Pagina vuota':
                categories.add(cat['categoria'])
        
        standard_categories = [
            "Istanze", "Documentazione Amministrativa", "Atto di rilascio - Diniego",
            "Elaborati", "Allegati", "Comunicazioni", "Non Classificate"
        ]
        
        for std_cat in standard_categories:
            categories.add(std_cat)
        
        return sorted(list(categories))
    
    def _create_linear_thumbnails(self, categories_data):
        if not self.document_loader:
            return
        
        page_category_map = {}
        for cat in categories_data:
            category_name = cat['categoria']
            for page_num in range(cat['inizio'], cat['fine'] + 1):
                page_category_map[page_num] = category_name
        
        for page_num in range(1, self.document_loader.total_pages + 1):
            image = self.document_loader.get_page(page_num)
            if image:
                category_name = page_category_map.get(page_num, "Non Classificate")
                self.add_page_thumbnail(page_num, image, category_name)
    
    def export_documents(self):
        if not self.input_folder.get() or not self.output_folder.get():
            messagebox.showwarning("Attenzione", "Imposta cartelle nelle impostazioni")
            return
        
        if not self.page_thumbnails:
            messagebox.showwarning("Attenzione", "Nessun documento da esportare")
            return
        
        export_data = self._generate_export_structure_linear()
        
        result = messagebox.askyesno("Conferma Export", 
                                   f"Esportare {len(export_data)} documenti?")
        if not result:
            return
        
        overwrite_auto = self.overwrite_files.get()
        overwrite_decisions = {}
        
        if not overwrite_auto:
            existing_files = []
            for i, (category_name, pages) in enumerate(export_data):
                filename = f"{os.path.splitext(self.doc_file)[0]}_{i+1:03d}{os.path.splitext(self.doc_file)[1]}"
                save_path = os.path.join(self.output_folder.get(), filename)
                if os.path.exists(save_path):
                    existing_files.append(filename)
            
            if existing_files:
                if not self._handle_existing_files(existing_files, overwrite_decisions):
                    return
        
        self.btn_export.config(state='disabled', text="Export...")
        future = self.executor.submit(self._export_documents, self.output_folder.get(), export_data, overwrite_decisions, overwrite_auto)
    
    def _generate_export_structure_linear(self):
        export_data = []
        current_category = None
        current_pages = []
        
        for thumbnail in self.page_thumbnails:
            if thumbnail.category_name != current_category:
                if current_category and current_pages:
                    export_data.append((current_category, current_pages.copy()))
                
                current_category = thumbnail.category_name
                current_pages = [thumbnail.page_num]
            else:
                current_pages.append(thumbnail.page_num)
        
        if current_category and current_pages:
            export_data.append((current_category, current_pages))
        
        return export_data
    
    def _export_documents(self, output_folder, export_data, overwrite_decisions, overwrite_auto):
        try:
            if not self.document_loader:
                raise Exception("Nessun documento caricato")
            
            ext = os.path.splitext(self.doc_file)[1].lower()
            exported_count = 0
            total_docs = len(export_data)
            
            for idx, (category_name, page_numbers) in enumerate(export_data):
                progress_data = {
                    'current': idx + 1,
                    'total': total_docs,
                    'percentage': int(((idx + 1) / total_docs) * 100)
                }
                self.result_queue.put({
                    'type': 'export_progress',
                    'data': progress_data
                })
                
                filename = f"{os.path.splitext(self.doc_file)[0]}_{idx+1:03d}{ext}"
                save_path = os.path.join(output_folder, filename)
                
                if os.path.exists(save_path):
                    if overwrite_auto:
                        pass
                    else:
                        decision = overwrite_decisions.get(filename, 'skip')
                        if decision == 'skip':
                            save_path = self.get_unique_filename(output_folder, filename)
                
                try:
                    if ext == ".pdf":
                        self._save_pdf_pages(page_numbers, save_path)
                    else:
                        self._save_tiff_pages(page_numbers, save_path)
                    exported_count += 1
                except Exception as e:
                    print(f"Errore nel salvare {filename}: {e}")
                    continue
            
            self.result_queue.put({
                'type': 'export_complete',
                'data': {
                    'exported_count': exported_count,
                    'total_docs': total_docs,
                    'output_folder': output_folder
                }
            })
            
        except Exception as e:
            self.result_queue.put({
                'type': 'error',
                'data': {'message': f"Errore durante export: {e}"}
            })
    
    def _save_pdf_pages(self, page_numbers, path):
        doc = fitz.open()
        
        for page_num in page_numbers:
            img = self.document_loader.get_page(page_num)
            if img:
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
                
                width, height = img.size
                page = doc.new_page(width=width, height=height)
                page.insert_image(page.rect, stream=img_bytes)
        
        doc.save(path)
        doc.close()
    
    def _save_tiff_pages(self, page_numbers, path):
        images = []
        
        for page_num in page_numbers:
            img = self.document_loader.get_page(page_num)
            if img:
                images.append(img)
        
        if images:
            images[0].save(path, save_all=True, append_images=images[1:])
    
    def _handle_existing_files(self, existing_files, overwrite_decisions):
        if len(existing_files) == 1:
            filename = existing_files[0]
            dlg = OverwriteDialog(self, filename)
            self.wait_window(dlg.top)
            
            if dlg.result == 'cancel':
                return False
            elif dlg.result in ['yes', 'yes_all']:
                overwrite_decisions[filename] = 'overwrite'
            else:
                overwrite_decisions[filename] = 'skip'
        else:
            dlg = BatchOverwriteDialog(self, existing_files)
            self.wait_window(dlg.top)
            
            if dlg.result == 'cancel':
                return False
            
            for filename in existing_files:
                if dlg.result == 'overwrite_all':
                    overwrite_decisions[filename] = 'overwrite'
                elif dlg.result == 'skip_all':
                    overwrite_decisions[filename] = 'skip'
                else:
                    overwrite_decisions[filename] = dlg.individual_decisions.get(filename, 'skip')
        
        return True
    
    def get_unique_filename(self, folder, filename):
        base, ext = os.path.splitext(filename)
        candidate = filename
        count = 1
        
        while os.path.exists(os.path.join(folder, candidate)):
            candidate = f"{base} ({count}){ext}"
            count += 1
        
        return os.path.join(folder, candidate)
    
    def _handle_export_progress(self, data):
        progress_text = f"Export: {data['current']}/{data['total']} ({data['percentage']}%)"
        self.progress_var.set(progress_text)
    
    def _handle_export_complete(self, data):
        self.btn_export.config(state='normal', text="Esporta")
        self.progress_var.set("")
        
        exported_count = data['exported_count']
        total_docs = data['total_docs']
        output_folder = data['output_folder']
        
        self.status_set(f"Export completato: {exported_count}/{total_docs} file")
        messagebox.showinfo("Export Completato", 
                          f"Esportati {exported_count}/{total_docs} documenti")
    
    def _handle_error(self, data):
        self.btn_scan.config(state='normal', text="Carica")
        self.btn_export.config(state='normal', text="Esporta")
        self.progress_var.set("")
        
        messagebox.showerror("Errore", data['message'])
        self.status_set(f"Errore: {data['message']}")
    
    # Canvas methods
    def clear_canvas(self):
        self.canvas.delete('all')
        self.page_label.config(text="Nessuna pagina")
        self.current_photo = None
    
    def zoom_in(self):
        if self.current_photo:
            self.zoom_factor *= 1.25
            self.show_page_in_viewer(self.current_page_index)
    
    def zoom_out(self):
        if self.current_photo:
            self.zoom_factor = max(0.1, self.zoom_factor / 1.25)
            self.show_page_in_viewer(self.current_page_index)
    
    def zoom_fit(self):
        if not self.current_photo:
            return
        
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        
        if canvas_w <= 1 or canvas_h <= 1:
            self.after(100, self.zoom_fit)
            return
        
        if self.document_loader:
            page_num = self.current_page_index + 1
            img = self.document_loader.get_page(page_num)
            if img:
                w, h = img.size
                ratio_w = canvas_w / w
                ratio_h = canvas_h / h
                self.zoom_factor = min(ratio_w, ratio_h, 1.0) * 0.95
                self.show_page_in_viewer(self.current_page_index)
    
    def on_canvas_click(self, event):
        self.zoom_fit()
    
    def pan_start(self, event):
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor='fleur')
    
    def pan_move(self, event):
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def on_mousewheel(self, event):
        if self.current_photo:
            if event.state & 0x4:
                if event.delta > 0:
                    self.zoom_in()
                else:
                    self.zoom_out()
            else:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    # Configuration methods
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.input_folder.set(config.get('input_folder', ''))
                    self.output_folder.set(config.get('output_folder', ''))
                    self.overwrite_files.set(config.get('overwrite_files', True))
        except Exception as e:
            print(f"Errore caricamento config: {e}")
    
    def save_config(self):
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config.update({
                'input_folder': self.input_folder.get(),
                'output_folder': self.output_folder.get(),
                'overwrite_files': self.overwrite_files.get()
            })
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Errore salvataggio config: {e}")
    
    def open_settings(self):
        dlg = SettingsDialog(self, self.input_folder.get(), 
                           self.output_folder.get(), 
                           self.overwrite_files.get())
        self.wait_window(dlg.top)
        
        if dlg.saved:
            self.input_folder.set(dlg.input_folder)
            self.output_folder.set(dlg.output_folder)
            self.overwrite_files.set(dlg.overwrite_files)
            self.save_config()
            self.status_set("Configurazione salvata")
    
    def status_set(self, msg):
        self.status_bar.config(text=msg)
        self.update_idletasks()
    
    # Geometry management methods
    def bind_geometry_events(self):
        self.bind('<Configure>', self.on_main_window_configure)
        self.main_paned.bind('<ButtonRelease-1>', self.on_paned_configure)
        self.right_paned.bind('<ButtonRelease-1>', self.on_paned_configure)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def on_main_window_configure(self, event):
        if event.widget == self:
            self.after_idle(self.save_geometry)
    
    def on_paned_configure(self, event):
        self.after_idle(self.save_geometry)
    
    def save_geometry(self):
        try:
            geometry_data = {
                'window_geometry': self.geometry(),
                'window_state': self.state(),
                'left_pane_width': self.main_paned.sash_coord(0)[0] if len(self.main_paned.panes()) > 1 else 350,
                'center_pane_width': self.right_paned.sash_coord(0)[0] if len(self.right_paned.panes()) > 1 else 600
            }
            
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            config['geometry'] = geometry_data
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Errore salvataggio geometria: {e}")
    
    def apply_saved_geometry(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                geometry_data = config.get('geometry', {})
                window_geometry = geometry_data.get('window_geometry', '1400x900')
                window_state = geometry_data.get('window_state', 'zoomed')
                
                self.geometry(window_geometry)
                
                if window_state == 'zoomed':
                    self.state('zoomed')
                elif window_state == 'normal':
                    self.state('normal')
                
                left_width = geometry_data.get('left_pane_width', 350)
                center_width = geometry_data.get('center_pane_width', 600)
                
                self.after(200, lambda: self.restore_pane_positions(left_width, center_width))
            else:
                self.geometry("1400x900")
                self.state('zoomed')
        except Exception as e:
            print(f"Errore caricamento geometria: {e}")
            self.geometry("1400x900")
            self.state('zoomed')
    
    def restore_pane_positions(self, left_width, center_width):
        try:
            if len(self.main_paned.panes()) > 1:
                self.main_paned.sash_place(0, left_width, 0)
            
            if len(self.right_paned.panes()) > 1:
                self.right_paned.sash_place(0, center_width, 0)
        except Exception as e:
            print(f"Errore ripristino posizioni: {e}")
    
    def set_initial_proportions(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if 'geometry' in config:
                    return
            
            total_width = self.winfo_width()
            if total_width > 100:
                left_width = int(total_width * 0.25)
                center_width = int(total_width * 0.50)
                
                self.main_paned.paneconfigure(self.left_frame, width=left_width)
                self.right_paned.paneconfigure(self.center_frame, width=center_width)
        except:
            pass
    
    def on_closing(self):
        if self.document_loader:
            self.document_loader.__exit__(None, None, None)
        
        self.executor.shutdown(wait=False)
        self.save_geometry()
        self.save_config()
        self.destroy()


class SettingsDialog:
    def __init__(self, parent, input_folder, output_folder, overwrite_files):
        self.top = tk.Toplevel(parent)
        self.top.title("Impostazioni AIDOXA")
        self.top.geometry("700x250")
        self.top.resizable(True, True)
        self.top.grab_set()
        self.top.transient(parent)
        self.apply_saved_geometry(parent)
        self.top.bind('<Configure>', self.on_configure)
        self.top.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.saved = False
        
        main_frame = tk.Frame(self.top, bg='white')
        main_frame.pack(fill='both', expand=True, padx=15, pady=15)
        
        tk.Label(main_frame, text="Configurazione Cartelle", font=('Arial', 14, 'bold'), 
                bg='white', fg='darkblue').grid(row=0, column=0, columnspan=3, pady=(0,20))
        
        tk.Label(main_frame, text="Cartella Input:", font=('Arial', 11, 'bold'), 
                bg='white').grid(row=1, column=0, sticky="w", pady=10)
        
        self.input_var = tk.StringVar(value=input_folder)
        input_entry = tk.Entry(main_frame, textvariable=self.input_var, width=55, 
                              font=('Consolas', 10), relief=tk.SUNKEN, bd=2)
        input_entry.grid(row=1, column=1, padx=(10,5), pady=10, sticky='ew')
        
        tk.Button(main_frame, text="Sfoglia", command=self.browse_input, 
                 bg='lightblue', font=('Arial', 9, 'bold')).grid(row=1, column=2, padx=5, pady=10)
        
        tk.Label(main_frame, text="Cartella Output:", font=('Arial', 11, 'bold'), 
                bg='white').grid(row=2, column=0, sticky="w", pady=10)
        
        self.output_var = tk.StringVar(value=output_folder)
        output_entry = tk.Entry(main_frame, textvariable=self.output_var, width=55, 
                               font=('Consolas', 10), relief=tk.SUNKEN, bd=2)
        output_entry.grid(row=2, column=1, padx=(10,5), pady=10, sticky='ew')
        
        tk.Button(main_frame, text="Sfoglia", command=self.browse_output, 
                 bg='lightgreen', font=('Arial', 9, 'bold')).grid(row=2, column=2, padx=5, pady=10)
        
        options_frame = tk.LabelFrame(main_frame, text="Opzioni Export", font=('Arial', 11, 'bold'),
                                    bg='white', fg='darkgreen')
        options_frame.grid(row=3, column=0, columnspan=3, sticky='ew', pady=(20,10))
        
        self.overwrite_var = tk.BooleanVar(value=overwrite_files)
        tk.Checkbutton(options_frame, text="Sovrascrivi automaticamente i file esistenti", 
                      variable=self.overwrite_var, font=('Arial', 10), bg='white').pack(anchor='w', padx=10, pady=10)
        
        btn_frame = tk.Frame(main_frame, bg='white')
        btn_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        tk.Button(btn_frame, text="Salva Configurazione", command=self.save, 
                 bg='lightgreen', font=('Arial', 11, 'bold'), width=20).pack(side='left', padx=10)
        tk.Button(btn_frame, text="Annulla", command=self.cancel, 
                 bg='lightcoral', font=('Arial', 11, 'bold'), width=15).pack(side='left', padx=10)
        
        main_frame.grid_columnconfigure(1, weight=1)
        self.top.focus_set()
        input_entry.focus()
    
    def apply_saved_geometry(self, parent):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                settings_geometry = config.get('settings_geometry')
                if settings_geometry:
                    self.top.geometry(settings_geometry)
                    return
            
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            x = parent_x + 100
            y = parent_y + 100
            self.top.geometry(f"700x250+{x}+{y}")
        except Exception as e:
            print(f"Errore caricamento geometria impostazioni: {e}")
            self.top.geometry("700x250+100+100")
    
    def save_settings_geometry(self):
        try:
            config = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            config['settings_geometry'] = self.top.geometry()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Errore salvataggio geometria impostazioni: {e}")
    
    def on_configure(self, event):
        if event.widget == self.top:
            self.top.after_idle(self.save_settings_geometry)
    
    def on_closing(self):
        self.save_settings_geometry()
        self.top.destroy()
    
    def browse_input(self):
        folder = filedialog.askdirectory(parent=self.top, title="Seleziona Cartella Input")
        if folder:
            self.input_var.set(folder)
    
    def browse_output(self):
        folder = filedialog.askdirectory(parent=self.top, title="Seleziona Cartella Output")
        if folder:
            self.output_var.set(folder)
    
    def save(self):
        if not self.input_var.get().strip() or not self.output_var.get().strip():
            messagebox.showwarning("Attenzione", "Specifica entrambe le cartelle")
            return
        
        if not os.path.isdir(self.input_var.get()):
            messagebox.showwarning("Attenzione", "Cartella input non esiste")
            return
        
        if not os.path.isdir(self.output_var.get()):
            result = messagebox.askyesno("Cartella Output", "Cartella output non esiste.\nCrearla?")
            if result:
                try:
                    os.makedirs(self.output_var.get(), exist_ok=True)
                except Exception as e:
                    messagebox.showerror("Errore", f"Impossibile creare cartella: {e}")
                    return
            else:
                return
        
        self.saved = True
        self.on_closing()
    
    def cancel(self):
        self.on_closing()
    
    @property
    def input_folder(self):
        return self.input_var.get().strip()
    
    @property
    def output_folder(self):
        return self.output_var.get().strip()
    
    @property
    def overwrite_files(self):
        return self.overwrite_var.get()


if __name__ == "__main__":
    app = AIDOXAApp()
    app.mainloop()