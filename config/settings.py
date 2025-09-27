"""
Configuration management for DynamicAI
"""

import os
import sys
import json
from .constants import DEFAULT_CONFIG

def get_config_file_path():
    """Get the path to the configuration file"""
    if getattr(sys, 'frozen', False):
        # Se il programma è compilato (exe)
        app_dir = os.path.dirname(sys.executable)
    else:
        # Se eseguito da script Python
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(app_dir, "DynamicAI_config.json")

def get_db_file_path():
    """Get the path to the database file"""
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(app_dir, "DynamicAI_categories.db")

CONFIG_FILE = get_config_file_path()
DB_FILE = get_db_file_path()

class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self):
        self.config_data = self.load_config()
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # Merge with default config to ensure all keys exist
                merged_config = DEFAULT_CONFIG.copy()
                for key, value in config.items():
                    if key in merged_config and isinstance(value, dict) and isinstance(merged_config[key], dict):
                        merged_config[key].update(value)
                    else:
                        merged_config[key] = value
                return merged_config
            else:
                self.save_config_data(DEFAULT_CONFIG)
                return DEFAULT_CONFIG.copy()
        except Exception as e:
            print(f"Error loading config: {e}")
            return DEFAULT_CONFIG.copy()
    
    def save_config_data(self, config_data):
        """Save configuration data to JSON file"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            print(f"Configuration saved to: {CONFIG_FILE}")
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def save_config(self):
        """Save current configuration to JSON file"""
        self.save_config_data(self.config_data)
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config_data.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.config_data[key] = value
    
    def update(self, updates):
        """Update multiple configuration values"""
        self.config_data.update(updates)
