"""
Helper functions and utilities for DynamicAI
"""

import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable

def create_progress_dialog(parent: tk.Widget, title: str = "Elaborazione in corso...") -> tuple:
    """Create a progress dialog window
    
    Args:
        parent: Parent widget
        title: Dialog title
        
    Returns:
        Tuple of (window, label_var, info_label)
    """
    progress_window = tk.Toplevel(parent)
    progress_window.title(title)
    progress_window.geometry("450x150")
    progress_window.transient(parent)
    progress_window.grab_set()
    
    # Center the dialog
    progress_window.geometry("+%d+%d" % (parent.winfo_rootx() + 100, parent.winfo_rooty() + 100))
    
    progress_label = tk.Label(progress_window, text=title)
    progress_label.pack(pady=20)
    
    progress_var = tk.StringVar()
    progress_info = tk.Label(progress_window, textvariable=progress_var)
    progress_info.pack(pady=10)
    
    return progress_window, progress_var, progress_info

def show_help_dialog(parent: tk.Widget):
    """Show comprehensive help dialog - MODIFICATO"""
    help_text = """ISTRUZIONI OPERATIVE DynamicAI v3.4:

CARICAMENTO DOCUMENTI:
- Configura cartelle input/output nelle Preferenze
- Usa "Aggiorna Lista (Preview)" per caricare automaticamente
- I documenti vengono caricati dalla cartella input configurata

METADATI (NUOVO v3.4):
- I metadati vengono letti automaticamente dall'header del file JSON
- Campi disponibili: NumeroProgetto, Intestatario, IndirizzoImmobile, 
  LavoroEseguito, EstremiCatastali
- Tutti i campi sono editabili nel pannello destro
- Le modifiche vengono automaticamente incluse nell'export CSV

CONFIGURAZIONE DOCUMENTI:
- Contatore documenti con numero di cifre personalizzabile
- Font e dimensione personalizzabili per le intestazioni
- Formato intestazione: [NNNN] Categoria (es: 0001 Documentazione)
- Allineamento testo a sinistra
- Hover su intestazione per evidenziazione

SELEZIONE:
- Click su miniatura: seleziona pagina e documento
- Click su intestazione documento: seleziona intero documento
- Hover con mouse: evidenziazione automatica
- Elementi selezionati sono evidenziati in blu/oro

DRAG & DROP:
- Trascina miniature per spostarle tra documenti
- Trascina per riordinare dentro stesso documento
- Il sistema distingue automaticamente tra click e drag
- L'anteprima gialla segue il mouse durante il trascinamento

ZOOM IMMAGINE:
- Zoom +/- : Ingrandisce/rimpicciolisce l'immagine
- Fit: Adatta immagine alla finestra centrale
- Click singolo su immagine: torna al fit automatico
- Zoom Area: Seleziona rettangolo con il mouse per zoom
- Hover su immagine: sfondo più scuro per feedback

PANNELLI INDIPENDENTI:
- Trascina il separatore sinistro per ridimensionare pannello sinistra/centro
- Trascina il separatore destro per ridimensionare pannello centro/destra
- I due separatori sono completamente indipendenti
- Impostazioni salvate automaticamente

GESTIONE DOCUMENTI:
- Tasto destro su intestazione: menu contestuale
- Crea nuovo documento: popup con categorie esistenti + nuove
- Database categorie: salva categorie personali tra sessioni
- Elimina documenti vuoti (senza pagine)
- Rinumerazione automatica della sequenza

GESTIONE CATEGORIE:
- Database SQLite locale per categorie personali
- Colori diversi: verde (da JSON), blu (da database)
- Ricerca categorie nel popup di selezione
- Combobox modificabile nel pannello destro
- Salvataggio automatico di nuove categorie

CAMBIO CATEGORIA:
- Seleziona documento (intestazione o miniatura)
- Combobox modificabile: categorie esistenti + crea nuove
- Salvataggio automatico nel database

GESTIONE FILE ESISTENTI:
- Rinomina automatica: file.pdf → file(1).pdf → file(2).pdf
- Chiedi conferma: popup prima di sovrascrivere
- Sovrascrivi sempre: backup opzionale
- Sistema numerazione Windows-style

EXPORT MIGLIORATO (v3.4):
- JPEG: file singoli per ogni pagina
- PDF Singolo: file PDF per ogni pagina
- PDF Multi-pagina: un PDF per ogni documento
- TIFF Singolo: file TIFF per ogni pagina
- TIFF Multi-pagina: un TIFF per ogni documento
- Qualità JPEG configurabile
- Gestione intelligente file esistenti
- NUOVO: Export automatico CSV con metadati

EXPORT CSV (NUOVO v3.4):
- Nome file CSV = nome cartella input
- Contiene tutti i metadati per ogni documento/file
- Delimitatore configurabile (default: punto e virgola)
- Formato: Nome File; Categoria; NumeroProgetto; Intestatario; 
  IndirizzoImmobile; LavoroEseguito; EstremiCatastali

SCORCIATOIE:
- Ctrl+R: Aggiorna Lista
- Ctrl+E: Completa Sequenza / Export
- Ctrl+Q: Esci"""
    
    help_window = tk.Toplevel(parent)
    help_window.title("Aiuto DynamicAI v3.4")
    help_window.geometry("750x950")
    help_window.transient(parent)
    
    text_widget = tk.Text(help_window, wrap=tk.WORD, padx=20, pady=20)
    text_widget.insert("1.0", help_text)
    text_widget.config(state=tk.DISABLED)
    text_widget.pack(fill="both", expand=True)
    
    tk.Button(help_window, text="Chiudi", command=help_window.destroy, 
             bg="lightblue").pack(pady=10)

def show_about_dialog(parent: tk.Widget):
    """Show about dialog with application information - MODIFICATO"""
    from config.settings import CONFIG_FILE, DB_FILE
    
    about_text = (f"DynamicAI - Editor Lineare Avanzato\n\n"
                 f"File di configurazione:\n{CONFIG_FILE}\n\n"
                 f"Database categorie:\n{DB_FILE}\n\n"
                 f"Versione: 3.4\n"
                 f"Sviluppato con Python e Tkinter\n\n"
                 f"Nuove Funzionalità v3.4:\n"
                 f"• Gestione completa metadati da JSON\n"
                 f"• Campi metadati editabili nell'interfaccia\n"
                 f"• Export automatico CSV con metadati\n"
                 f"• Nome CSV basato su cartella input\n"
                 f"• Delimitatore CSV configurabile\n"
                 f"• Integrazione metadati in export\n\n"
                 f"Funzionalità v3.3:\n"
                 f"• Gestione intelligente file esistenti\n"
                 f"• Rinominazione automatica stile Windows\n"
                 f"• Modalità backup migliorata\n"
                 f"• Architettura modulare")
    
    messagebox.showinfo("Informazioni", about_text)

def center_window(window: tk.Toplevel, parent: tk.Widget):
    """Center a window relative to its parent
    
    Args:
        window: Window to center
        parent: Parent widget
    """
    window.update_idletasks()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (window.winfo_width() // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (window.winfo_height() // 2)
    window.geometry(f"+{x}+{y}")

def validate_folder_path(path: str) -> bool:
    """Validate if a folder path exists and is accessible
    
    Args:
        path: Folder path to validate
        
    Returns:
        True if valid and accessible
    """
    import os
    return os.path.exists(path) and os.path.isdir(path)

def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase
    
    Args:
        filename: Filename to process
        
    Returns:
        File extension without dot
    """
    return filename.lower().split('.')[-1] if '.' in filename else ''

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "unnamed"
        
    import re
    # Remove invalid characters for Windows/Unix filenames
    sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Replace multiple spaces with underscore
    sanitized = re.sub(r'\s+', '_', sanitized.strip())
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    return sanitized or "unnamed"


def generate_numbered_filename(base_name: str, counter: int, config_manager, is_multi_document=False, category_name=""):
    """
    Genera nome file con numerazione personalizzabile
    
    Args:
        base_name: Nome base del documento (senza estensione)
        counter: Numero progressivo 
        config_manager: Gestore configurazione
        is_multi_document: Se True, include nome base nel contatore
        category_name: Nome categoria (per modalità split)
    
    Returns:
        str: Nome file numerato (senza estensione)
        
    Esempio:
        base_name='contratto', counter=1, prefix='Doc_', suffix='_v1'
        -> 'Doc_0001_contratto_v1' (se is_multi_document=True)
        -> 'Doc_0001_v1' (se is_multi_document=False)
    """
    # Carica configurazione numerazione
    numbering_config = config_manager.config_data.get('document_numbering', {})
    
    prefix = numbering_config.get('prefix', '')
    suffix = numbering_config.get('suffix', '') 
    counter_digits = numbering_config.get('counter_digits', 4)
    use_base_name = numbering_config.get('use_base_name', True)
    numbering_mode = numbering_config.get('numbering_mode', 'per_category')
    
    # Formatta contatore con zeri iniziali
    formatted_counter = str(counter).zfill(counter_digits)
    
    # Costruisci parti del nome
    parts = []
    
    # Prefisso
    if prefix:
        parts.append(prefix.rstrip('_'))  # Remove trailing underscore if present
    
    # Contatore
    parts.append(formatted_counter)
    
    # Nome base (se abilitato e modalità multi-documento)
    if use_base_name and is_multi_document and base_name:
        safe_base = sanitize_filename(base_name)
        if safe_base and safe_base != "unnamed":
            parts.append(safe_base)
    
    # Categoria (sempre per modalità per_category, mai per globale)
    if numbering_mode == 'per_category' and category_name and category_name != "Pagina vuota":
        safe_category = sanitize_filename(category_name)
        if safe_category and safe_category != "unnamed":
            parts.append(safe_category)
    
    # Suffisso  
    if suffix:
        parts.append(suffix.lstrip('_'))  # Remove leading underscore if present
    
    # Unisci con underscore, rimuovi underscore doppi/tripli
    filename = '_'.join(part for part in parts if part)
    
    # Cleanup multiple underscores
    import re
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_')
    
    return filename or f"doc_{formatted_counter}"  # Fallback se vuoto

def get_document_counter_manager(config_manager, numbering_mode='per_category'):
    """
    Gestisce i contatori per la numerazione documenti
    
    Args:
        config_manager: Gestore configurazione
        numbering_mode: 'global' o 'per_category'
        
    Returns:
        dict: Dizionario contatori per categoria
    """
    start_number = config_manager.config_data.get('document_numbering', {}).get('start_number', 1)
    
    if numbering_mode == 'global':
        # Contatore globale unico
        return {'_global': start_number}
    else:
        # Contatori separati per categoria
        return {}  # Si inizializza dinamicamente

def generate_numbered_filename(base_name, counter, config_manager, is_multi_document=False, category_name=""):
    """
    Genera nome file con numerazione personalizzabile
    
    Args:
        base_name: Nome base del documento
        counter: Numero progressivo 
        config_manager: Gestore configurazione
        is_multi_document: Se True, include nome base nel contatore
        category_name: Nome categoria (per modalità split)
    
    Returns:
        str: Nome file numerato (senza estensione)
        
    Esempio:
        base_name='contratto', counter=1, prefix='Doc_', suffix='_v1'
        -> 'Doc_0001_contratto_v1' (se is_multi_document=True)
        -> 'Doc_0001_v1' (se is_multi_document=False)
    """
    # Carica configurazione numerazione
    numbering_config = config_manager.config_data.get('document_numbering', {})
    
    prefix = numbering_config.get('prefix', '')
    suffix = numbering_config.get('suffix', '') 
    counter_digits = numbering_config.get('counter_digits', 4)
    use_base_name = numbering_config.get('use_base_name', True)
    
    # Formatta contatore con zeri iniziali
    formatted_counter = str(counter).zfill(counter_digits)
    
    # Costruisci parti del nome
    parts = []
    
    # Prefisso
    if prefix:
        parts.append(prefix)
    
    # Contatore
    parts.append(formatted_counter)
    
    # Nome base (se abilitato e modalità multi-documento)
    if use_base_name and is_multi_document and base_name:
        # Sanitizza nome base
        safe_base = sanitize_filename(base_name)
        parts.append(safe_base)
    
    # Categoria (per modalità split)
    if category_name and category_name != "Pagina vuota":
        safe_category = sanitize_filename(category_name)
        parts.append(safe_category)
    
    # Suffisso  
    if suffix:
        parts.append(suffix)
    
    # Unisci con underscore, rimuovi underscore doppi/tripli
    filename = '_'.join(part for part in parts if part)
    filename = '_'.join(filter(None, filename.split('_')))  # Remove empty parts
    
    return filename or f"doc_{formatted_counter}"  # Fallback se vuoto


def sanitize_filename(filename):
    """
    Sanitizza nome file rimuovendo caratteri non validi
    
    Args:
        filename: Nome file da sanitizzare
        
    Returns:
        str: Nome file sanitizzato
    """
    if not filename:
        return ""
        
    # Caratteri non validi Windows/Linux
    invalid_chars = r'<>:"/\|?*'
    sanitized = filename
    
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '')
    
    # Rimuovi spazi multipli e sostituisci con underscore
    sanitized = '_'.join(sanitized.split())
    
    # Rimuovi punti iniziali/finali e spazi
    sanitized = sanitized.strip('. ')
    
    return sanitized or "unnamed"