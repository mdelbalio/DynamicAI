"""
Constants and default configuration for DynamicAI v3.6 (BATCH EDITION)
- Aggiunte chiavi batch: csv_mode, json_input_path, batch_mode_enabled
- Mantiene retrocompatibilità con v3.5
"""

try:
    from PIL import Image
    RESAMPLEFILTER = Image.Resampling.LANCZOS
except Exception:
    try:
        RESAMPLEFILTER = Image.LANCZOS
    except Exception:
        RESAMPLEFILTER = Image.BICUBIC

DEFAULT_CONFIG = {
    'window_settings': {
        'geometry': '1400x800+100+50',
        'state': 'normal'
    },
    'panel_settings': {
        'left_center_position': 300,
        'center_right_position': 1200
    },
    'ui': {
        'theme': 'light',
        'language': 'it'
    },
    'fonts': {
        'document_font_name': 'Arial',
        'document_font_size': 10,
        'document_font_bold': True
    },

    # ---- Export (retrocompatibile) ----
    'export_format': 'JPEG',
    'jpeg_quality': 95,
    'file_handling_mode': 'auto_rename',
    'create_backup_on_overwrite': False,

    # ---- Opzioni export avanzate ----
    'export': {
        'target_folder': '',
        'jpeg_optimize': True,
        'jpeg_progressive': False,
        'jpeg_subsampling': '4:2:0',
        'pdf_dpi': 300,
        'tiff_compression': 'tiff_lzw',
    },

    'auto_save_changes': True,
    'save_window_layout': True,
    'auto_fit_images': True,
    'show_debug_info': False,
    'thumbnail_width': 80,
    'thumbnail_height': 100,
    'thumbnail_keep_aspect_ratio': False,  # Mantieni rapporto d'aspetto
    'last_folder': '',
    
    # ---- NUOVO: Gestione CSV e JSON ----
    'csv_delimiter': ';',
    'csv_mode': 'incremental',  # incremental | per_file
    'csv_output_path': '',  # Se vuoto, usa output_folder
    'csv_use_document_name': False,  # Se True, usa nome documento invece di cartella
    'csv_custom_name': '',  # Nome personalizzato (se vuoto, usa auto)

    # ---- BATCH CSV Configuration ----
    'batch_csv_location': 'per_folder',  # 'per_folder' | 'root' | 'custom'
    'batch_csv_naming': 'auto',  # 'auto' | 'folder_name' | 'custom' | 'timestamp'
    'batch_csv_custom_prefix': 'metadata',  # Prefisso personalizzato
    'batch_csv_add_timestamp': False,  # Aggiungi timestamp al nome file
    'batch_csv_add_counter': False,  # Aggiungi contatore sequenziale
    
    # ---- NUOVO: Percorsi input ----
    'default_input_folder': '',
    'default_output_folder': '',
    'preserve_folder_structure': False,  # Mantieni struttura directory input nell'output
    'json_input_path': '',  # Cartella JSON separata (opzionale)
    'use_input_folder_for_json': True,  # True = JSON nella stessa cartella dei documenti
    
    # ---- NUOVO: Batch Manager ----
    'batch_mode_enabled': True,
    'split_documents_by_category': True,  # NUOVO: Flag per dividere documenti per categoria
    
    # ========================================
    # BATCH CONFIGURATION - AGGIUNTO v3.6
    # ========================================
    'batch_input_mode': 'recursive',  # 'flat' | 'recursive'
    'batch_scan_depth': -1,  # -1 = unlimited, N = max depth
    'batch_preserve_structure': True,  # Preserve directory structure in output
    'batch_csv_mode': 'per_folder',  # 'per_folder' | 'global'
    'batch_database_path': None,  # Verrà impostato dinamicamente

    # ---- NUOVA: Numerazione Documenti ----
    'document_numbering': {
        'prefix': '',  # Prefisso (es: 'Doc_', 'Pratica_')
        'suffix': '',  # Suffisso (es: '_v1', '_FINAL')
        'counter_digits': 4,  # 2,3,4,5 cifre (01, 001, 0001, 00001)
        'start_number': 1,  # Numero iniziale
        'use_base_name': True,  # Usa nome file base in modalità multi-documento
        'numbering_mode': 'per_category'  # 'global' o 'per_category'
    },
    
    'application_info': {
        'name': 'DynamicAI Editor',
        'version': '3.6',  # Incrementato per batch
        'created': '2025'
    }
}