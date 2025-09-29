"""
Constants and default configuration for DynamicAI
"""

try:
    from PIL import Image
    RESAMPLEFILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLEFILTER = Image.LANCZOS

DEFAULT_CONFIG = {
    'window_settings': {
        'geometry': '1400x800+100+50',
        'state': 'normal'
    },
    'panel_settings': {
        'left_center_position': 400,
        'center_right_position': 1100
    },
    'default_input_folder': '',
    'default_output_folder': '',
    'document_counter_digits': 4,
    'document_font_name': 'Arial',
    'document_font_size': 10,
    'document_font_bold': True,
    'export_format': 'JPEG',
    'jpeg_quality': 95,
    'file_handling_mode': 'auto_rename',
    'create_backup_on_overwrite': False,
    'auto_save_changes': True,
    'save_window_layout': True,
    'auto_fit_images': True,
    'show_debug_info': False,
    'thumbnail_width': 80,
    'thumbnail_height': 100,
    'last_folder': '',
    'csv_delimiter': ';',  # NUOVO: delimitatore CSV
    'application_info': {
        'name': 'DynamicAI Editor',
        'version': '3.4',  # AGGIORNATO
        'created': '2025'
    }
}