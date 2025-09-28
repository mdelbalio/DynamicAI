"""
Category selection dialog for DynamicAI
"""

import tkinter as tk
from tkinter import messagebox
from typing import List, Optional, Set

class CategorySelectionDialog:
    """Dialog for selecting or creating document categories"""
    
    def __init__(self, parent: tk.Widget, json_categories: List[str], 
                 db_categories: List[str], title: str = "Seleziona Categoria"):
        self.parent = parent
        self.json_categories: Set[str] = set(json_categories)
        self.db_categories: Set[str] = set(db_categories)
        self.all_categories = sorted(self.json_categories.union(self.db_categories))
        self.result: Optional[str] = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
        
        self.create_widgets()
        self.dialog.wait_window()

    def create_widgets(self):
        """Create dialog widgets"""
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title = tk.Label(main_frame, text="Seleziona o Crea Categoria", 
                        font=("Arial", 14, "bold"), fg="darkblue")
        title.pack(pady=(0, 20))
        
        # Search frame
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(search_frame, text="Cerca:", font=("Arial", 10)).pack(side="left")
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 10))
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        self.search_var.trace('w', self.on_search_changed)
        
        # Categories frame
        categories_frame = tk.LabelFrame(main_frame, text="Categorie Disponibili", 
                                        font=("Arial", 10, "bold"))
        categories_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Scrollable listbox
        list_frame = tk.Frame(categories_frame)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.categories_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, 
                                           font=("Arial", 10), height=15)
        self.categories_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.categories_listbox.yview)
        
        # Populate listbox
        self.populate_listbox()
        
        # Legend
        legend_frame = tk.Frame(categories_frame)
        legend_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        json_label = tk.Label(legend_frame, text="● Dal JSON corrente", 
                             fg="darkgreen", font=("Arial", 9))
        json_label.pack(anchor="w")
        
        db_label = tk.Label(legend_frame, text="● Dal database (usate precedentemente)", 
                           fg="darkblue", font=("Arial", 9))
        db_label.pack(anchor="w")
        
        # New category frame
        new_frame = tk.LabelFrame(main_frame, text="Crea Nuova Categoria", 
                                 font=("Arial", 10, "bold"))
        new_frame.pack(fill="x", pady=(0, 20))
        
        new_entry_frame = tk.Frame(new_frame)
        new_entry_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(new_entry_frame, text="Nome:", font=("Arial", 10)).pack(side="left")
        self.new_category_var = tk.StringVar()
        self.new_category_entry = tk.Entry(new_entry_frame, textvariable=self.new_category_var, 
                                          font=("Arial", 10))
        self.new_category_entry.pack(side="left", fill="x", expand=True, padx=(5, 10))
        
        tk.Button(new_entry_frame, text="Usa Nuova", command=self.use_new_category, 
                 bg="lightgreen", font=("Arial", 9)).pack(side="right")
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        tk.Button(button_frame, text="Usa Selezionata", command=self.use_selected_category, 
                 bg="lightblue", font=("Arial", 10, "bold"), width=15).pack(side="left")
        
        tk.Button(button_frame, text="Annulla", command=self.cancel, 
                 font=("Arial", 10), width=10).pack(side="right")
        
        # Bind double-click
        self.categories_listbox.bind("<Double-Button-1>", lambda e: self.use_selected_category())
        
        # Bind Enter key on new category entry
        self.new_category_entry.bind("<Return>", lambda e: self.use_new_category())
        
        # Focus on search
        self.search_entry.focus()

    def populate_listbox(self, filter_text: str = ""):
        """Populate listbox with categories"""
        self.categories_listbox.delete(0, tk.END)
        
        filtered_categories = []
        if filter_text:
            filtered_categories = [cat for cat in self.all_categories 
                                 if filter_text.lower() in cat.lower()]
        else:
            filtered_categories = self.all_categories
        
        for category in filtered_categories:
            self.categories_listbox.insert(tk.END, category)
            # Color code based on source
            index = self.categories_listbox.size() - 1
            if category in self.json_categories:
                self.categories_listbox.itemconfig(index, fg="darkgreen")
            else:
                self.categories_listbox.itemconfig(index, fg="darkblue")

    def on_search_changed(self, *args):
        """Handle search text change"""
        search_text = self.search_var.get()
        self.populate_listbox(search_text)

    def use_selected_category(self):
        """Use the selected category from list"""
        selection = self.categories_listbox.curselection()
        if selection:
            selected_category = self.categories_listbox.get(selection[0])
            self.result = selected_category
            self.dialog.destroy()
        else:
            messagebox.showwarning("Attenzione", "Seleziona una categoria dalla lista")

    def use_new_category(self):
        """Use the new category entered"""
        new_category = self.new_category_var.get().strip()
        if new_category:
            self.result = new_category
            self.dialog.destroy()
        else:
            messagebox.showwarning("Attenzione", "Inserisci il nome della nuova categoria")

    def cancel(self):
        """Cancel selection"""
        self.result = None
        self.dialog.destroy()
