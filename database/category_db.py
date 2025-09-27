"""
Category database management for DynamicAI
"""

import sqlite3
from typing import List, Optional

class CategoryDatabase:
    """Manages category storage in SQLite database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for categories"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    def add_category(self, category_name: str) -> bool:
        """Add a new category or update last_used if exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO categories (name, last_used) 
                    VALUES (?, CURRENT_TIMESTAMP)
                """, (category_name,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding category: {e}")
            return False
    
    def get_all_categories(self) -> List[str]:
        """Get all categories ordered by last_used desc"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM categories ORDER BY last_used DESC")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    def remove_category(self, category_name: str) -> bool:
        """Remove a category from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM categories WHERE name = ?", (category_name,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error removing category: {e}")
            return False
    
    def category_exists(self, category_name: str) -> bool:
        """Check if category exists in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM categories WHERE name = ?", (category_name,))
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"Error checking category: {e}")
            return False
    
    def get_category_stats(self) -> dict:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM categories")
                total_categories = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT name, last_used 
                    FROM categories 
                    ORDER BY last_used DESC 
                    LIMIT 1
                """)
                most_recent = cursor.fetchone()
                
                return {
                    'total_categories': total_categories,
                    'most_recent': most_recent[0] if most_recent else None,
                    'most_recent_date': most_recent[1] if most_recent else None
                }
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {'total_categories': 0, 'most_recent': None, 'most_recent_date': None}
