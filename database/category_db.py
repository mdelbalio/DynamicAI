"""
Category database management for DynamicAI with dynamic JSON tracking

Enhanced version with:
- Dynamic JSON category synchronization
- Protection system for active categories
- Usage tracking and statistics
- Cleanup utilities
- Bug fixes for cursor management
"""

import sqlite3
import json
from typing import List, Optional, Dict, Set
from datetime import datetime

class CategoryDatabase:
    """Manages category storage in SQLite database with dynamic JSON category tracking"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.current_json_categories: Set[str] = set()  # Categorie dal JSON corrente
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for categories with enhanced schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',  -- 'json' o 'manual'
                    json_document TEXT DEFAULT NULL,         -- Path documento JSON origine
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,          -- Contatore utilizzi
                    is_protected BOOLEAN DEFAULT 0          -- Protezione eliminazione
                )
                """)

                # Migrazione per database esistenti - aggiungi colonne se non esistono
                cursor.execute("PRAGMA table_info(categories)")
                columns = [row[1] for row in cursor.fetchall()]

                missing_columns = [
                    ('source', "TEXT NOT NULL DEFAULT 'manual'"),
                    ('json_document', 'TEXT DEFAULT NULL'),
                    ('usage_count', 'INTEGER DEFAULT 0'),
                    ('is_protected', 'BOOLEAN DEFAULT 0')
                ]

                for col_name, col_def in missing_columns:
                    if col_name not in columns:
                        cursor.execute(f"ALTER TABLE categories ADD COLUMN {col_name} {col_def}")

                conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")

    def sync_json_categories(self, json_categories: List[str], json_document_path: str = None):
        """
        Sincronizza categorie dal JSON corrente

        Args:
            json_categories: Lista categorie dal JSON
            json_document_path: Path del documento JSON (opzionale)
        """
        try:
            self.current_json_categories = set(json_categories)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # 1. Aggiorna flag is_protected: rimuovi protezione da categorie precedenti
                cursor.execute("UPDATE categories SET is_protected = 0 WHERE source = 'json'")

                # 2. Aggiungi/aggiorna categorie JSON correnti
                for category in json_categories:
                    cursor.execute("""
                    INSERT OR REPLACE INTO categories 
                    (name, source, json_document, last_used, is_protected, usage_count) 
                    VALUES (?, 'json', ?, CURRENT_TIMESTAMP, 1, 
                            COALESCE((SELECT usage_count FROM categories WHERE name = ?), 0))
                    """, (category, json_document_path, category))

                conn.commit()
                print(f"[DEBUG] Sincronizzate {len(json_categories)} categorie da JSON: {json_categories}")

        except Exception as e:
            print(f"Error syncing JSON categories: {e}")

    def add_category(self, category_name: str, source: str = 'manual') -> bool:
        """Add a new category or update last_used if exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR REPLACE INTO categories (name, source, last_used, usage_count)
                VALUES (?, ?, CURRENT_TIMESTAMP, 
                        COALESCE((SELECT usage_count FROM categories WHERE name = ?) + 1, 1))
                """, (category_name, source, category_name))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding category: {e}")
            return False

    def get_all_categories(self) -> List[str]:
        """Get all categories ordered by: JSON categories first, then by last usage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT name FROM categories 
                ORDER BY 
                    CASE WHEN is_protected = 1 THEN 0 ELSE 1 END,  -- JSON prima
                    usage_count DESC,                              -- Poi per utilizzo
                    last_used DESC                                 -- Poi per data
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []

    def get_json_categories(self) -> List[str]:
        """Get only JSON categories (protected)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT name FROM categories 
                WHERE is_protected = 1 AND source = 'json'
                ORDER BY usage_count DESC, last_used DESC
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting JSON categories: {e}")
            return []

    def get_manual_categories(self) -> List[str]:
        """Get only manual categories (user-added, deletable)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT name FROM categories 
                WHERE source = 'manual' AND is_protected = 0
                ORDER BY usage_count DESC, last_used DESC
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting manual categories: {e}")
            return []

    def can_delete_category(self, category_name: str) -> bool:
        """Check if category can be deleted (not protected and not from current JSON)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT is_protected, source FROM categories WHERE name = ?
                """, (category_name,))
                result = cursor.fetchone()

                if result:
                    is_protected, source = result
                    # Non può cancellare se protetta O se è nel JSON corrente
                    return not is_protected and category_name not in self.current_json_categories
                return False
        except Exception as e:
            print(f"Error checking category deletion: {e}")
            return False

    def delete_category(self, category_name: str) -> bool:
        """Delete category if allowed (fixes cursor bug)"""
        try:
            if not self.can_delete_category(category_name):
                print(f"Category '{category_name}' cannot be deleted (protected or from current JSON)")
                return False

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM categories WHERE name = ?", (category_name,))
                deleted = cursor.rowcount > 0
                conn.commit()

                if deleted:
                    print(f"[DEBUG] Category '{category_name}' deleted successfully")
                return deleted

        except Exception as e:
            print(f"Error deleting category: {e}")
            return False

    def remove_category(self, category_name: str) -> bool:
        """Alias for delete_category for backward compatibility"""
        return self.delete_category(category_name)

    def category_exists(self, category_name: str) -> bool:
        """Check if category exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM categories WHERE name = ?", (category_name,))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking category existence: {e}")
            return False

    def get_category_info(self, category_name: str) -> Optional[Dict]:
        """Get detailed category information"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT name, source, json_document, created_date, last_used, usage_count, is_protected 
                FROM categories WHERE name = ?
                """, (category_name,))
                result = cursor.fetchone()

                if result:
                    return {
                        'name': result[0],
                        'source': result[1],
                        'json_document': result[2],
                        'created_date': result[3],
                        'last_used': result[4],
                        'usage_count': result[5],
                        'is_protected': bool(result[6])
                    }
                return None
        except Exception as e:
            print(f"Error getting category info: {e}")
            return None

    def get_category_stats(self) -> Dict:
        """Get comprehensive category statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Statistiche generali
                cursor.execute("SELECT COUNT(*) FROM categories")
                total_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM categories WHERE source = 'json'")
                json_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM categories WHERE source = 'manual'")
                manual_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM categories WHERE is_protected = 1")
                protected_count = cursor.fetchone()[0]

                # Categoria più utilizzata
                cursor.execute("""
                SELECT name, usage_count FROM categories 
                ORDER BY usage_count DESC LIMIT 1
                """)
                most_used = cursor.fetchone()

                return {
                    'total_categories': total_count,
                    'json_categories': json_count,
                    'manual_categories': manual_count,
                    'protected_categories': protected_count,
                    'current_json_categories': len(self.current_json_categories),
                    'most_used_category': most_used[0] if most_used else None,
                    'most_used_count': most_used[1] if most_used else 0
                }

        except Exception as e:
            print(f"Error getting category stats: {e}")
            return {
                'total_categories': 0,
                'json_categories': 0,
                'manual_categories': 0,
                'protected_categories': 0,
                'current_json_categories': 0,
                'most_used_category': None,
                'most_used_count': 0
            }

    def cleanup_unused_categories(self, keep_days: int = 30) -> int:
        """Clean up unused manual categories older than specified days"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                DELETE FROM categories 
                WHERE source = 'manual' 
                  AND is_protected = 0 
                  AND usage_count = 0 
                  AND datetime(last_used) < datetime('now', '-{} days')
                """.format(keep_days))

                deleted_count = cursor.rowcount
                conn.commit()

                if deleted_count > 0:
                    print(f"[DEBUG] Cleaned up {deleted_count} unused categories older than {keep_days} days")

                return deleted_count

        except Exception as e:
            print(f"Error cleaning up categories: {e}")
            return 0
