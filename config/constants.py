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
    
    # ---- NUOVO: Percorsi input ----
    'default_input_folder': '',
    'default_output_folder': '',
    'json_input_path': '',  # Cartella JSON separata (opzionale)
    'use_input_folder_for_json': True,  # True = JSON nella stessa cartella dei documenti
    
    # ---- NUOVO: Batch Manager ----
    'batch_mode_enabled': True,
    'split_documents_by_category': True,  # NUOVO: Flag per dividere documenti per categoria

    'application_info': {
        'name': 'DynamicAI Editor',
        'version': '3.6',  # Incrementato per batch
        'created': '2025'
    }
}