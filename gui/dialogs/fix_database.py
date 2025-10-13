import sqlite3
import os
from config import DB_FILE

def fix_database():
    """Fix existing database to support new dynamic categories"""
    print(f"Fixing database: {DB_FILE}")
    
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            
            # Check existing table structure
            cursor.execute("PRAGMA table_info(categories)")
            columns = [row[1] for row in cursor.fetchall()]
            print(f"Existing columns: {columns}")
            
            # Add missing columns if they don't exist
            missing_columns = [
                ('source', "TEXT NOT NULL DEFAULT 'manual'"),
                ('json_document', 'TEXT DEFAULT NULL'),
                ('usage_count', 'INTEGER DEFAULT 0'),
                ('is_protected', 'BOOLEAN DEFAULT 0')
            ]
            
            for col_name, col_def in missing_columns:
                if col_name not in columns:
                    print(f"Adding missing column: {col_name}")
                    cursor.execute(f"ALTER TABLE categories ADD COLUMN {col_name} {col_def}")
            
            # Update existing categories to have proper source
            cursor.execute("UPDATE categories SET source = 'manual' WHERE source IS NULL")
            cursor.execute("UPDATE categories SET usage_count = 1 WHERE usage_count IS NULL OR usage_count = 0")
            
            conn.commit()
            print("✅ Database fixed successfully!")
            
            # Show current categories
            cursor.execute("""
                SELECT name, source, usage_count, is_protected 
                FROM categories 
                ORDER BY name
            """)
            
            print("\nCurrent categories:")
            for row in cursor.fetchall():
                print(f"  - {row[0]} (source: {row[1]}, usage: {row[2]}, protected: {row[3]})")
            
    except Exception as e:
        print(f"Error fixing database: {e}")

if __name__ == "__main__":
    fix_database()
