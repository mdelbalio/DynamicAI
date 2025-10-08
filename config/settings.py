r"""
Configuration management for DynamicAI (patched, bbox-aware friendly)
- Percorsi config/db in cartella utente quando possibile (Windows: %APPDATA%\DynamicAI)
- Merge con DEFAULT_CONFIG (shallow + dict nested)
- Salvataggio atomico
"""

import os
import sys
import json
from tempfile import NamedTemporaryFile
from .constants import DEFAULT_CONFIG

APP_NAME = "DynamicAI"

def _user_config_dir() -> str:
    """Restituisce la cartella di configurazione utente.
    Windows: %APPDATA%\\DynamicAI
    Linux/macOS: ~/.config/DynamicAI
    Se non disponibile, fallback alla root progetto.
    """
    try:
        if os.name == "nt":
            base = os.getenv("APPDATA") or os.path.expanduser("~")
            path = os.path.join(base, APP_NAME)
        else:
            base = os.path.join(os.path.expanduser("~"), ".config")
            path = os.path.join(base, APP_NAME)
        os.makedirs(path, exist_ok=True)
        return path
    except Exception:
        # fallback root progetto
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_config_file_path():
    """Path del file di configurazione JSON."""
    return os.path.join(_user_config_dir(), f"{APP_NAME}_config.json")

def get_db_file_path():
    """Path del file database SQLite (se usato)."""
    return os.path.join(_user_config_dir(), f"{APP_NAME}_categories.db")

def get_batch_db_file_path():
    """Path del file database batch SQLite."""
    return os.path.join(_user_config_dir(), f"{APP_NAME}_batch_state.db")

CONFIG_FILE = get_config_file_path()
DB_FILE = get_db_file_path()
BATCH_DB_FILE = get_batch_db_file_path()

class ConfigManager:
    """Gestisce la configurazione dell'applicazione."""
    def __init__(self):
        self.config_data = self.load_config()

    # ----------------
    # Load / Save
    # ----------------
    def load_config(self):
        """Carica la configurazione dal file JSON, fondendola con DEFAULT_CONFIG."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # merge: copia defaults e poi overlay config con nested dict-merge
                merged = DEFAULT_CONFIG.copy()
                for key, value in config.items():
                    if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                        merged[key] = {**merged[key], **value}
                    else:
                        merged[key] = value
                
                # ⭐ NUOVO: Imposta dinamicamente batch database path se None
                if merged.get('batch_database_path') is None:
                    merged['batch_database_path'] = BATCH_DB_FILE
                
                return merged
            else:
                defaults = DEFAULT_CONFIG.copy()
                # ⭐ NUOVO: Imposta dinamicamente batch database path se None
                if defaults.get('batch_database_path') is None:
                    defaults['batch_database_path'] = BATCH_DB_FILE
                self.save_config_data(defaults)
                return defaults
        except Exception as e:
            print(f"Error loading config: {e}")
            defaults = DEFAULT_CONFIG.copy()
            if defaults.get('batch_database_path') is None:
                defaults['batch_database_path'] = BATCH_DB_FILE
            return defaults

    def save_config_data(self, config_data):
        """Salva il JSON in modo atomico per evitare corruzione file."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with NamedTemporaryFile('w', delete=False, encoding='utf-8', dir=os.path.dirname(CONFIG_FILE), prefix='._tmp_', suffix='.json') as tmp:
                json.dump(config_data, tmp, indent=4, ensure_ascii=False)
                temp_name = tmp.name
            # atomic replace
            if os.name == "nt":
                # su Windows, os.replace è atomic entro lo stesso volume
                os.replace(temp_name, CONFIG_FILE)
            else:
                os.replace(temp_name, CONFIG_FILE)
            print(f"Configuration saved to: {CONFIG_FILE}")
        except Exception as e:
            print(f"Error saving config: {e}")

    def save_config(self):
        self.save_config_data(self.config_data)

    # ----------------
    # Helpers
    # ----------------
    def get(self, key, default=None):
        return self.config_data.get(key, default)

    def set(self, key, value):
        self.config_data[key] = value

    def update(self, updates: dict):
        if not isinstance(updates, dict):
            return
        for k, v in updates.items():
            if isinstance(v, dict) and isinstance(self.config_data.get(k), dict):
                self.config_data[k].update(v)
            else:
                self.config_data[k] = v