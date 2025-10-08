"""
Batch Database - Gestione persistenza stato batch per recovery da crash
"""

import sqlite3
import os
from typing import List, Optional, Dict
from datetime import datetime
import json


class BatchDatabase:
    """Gestisce persistenza stato batch in SQLite"""
    
    def __init__(self, db_path: str = "data/batch_state.db"):
        """
        Inizializza database batch
        
        Args:
            db_path: Percorso file database SQLite (None = usa path da config)
        """
        # Se non specificato, usa path da config
        if db_path is None:
            from config import BATCH_DB_FILE
            db_path = BATCH_DB_FILE
        
        self.db_path = db_path
        
        # Crea directory se non esiste
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        self._init_database()
    
    def _init_database(self):
        """Crea tabelle se non esistono"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tabella sessioni batch
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_sessions (
                session_id TEXT PRIMARY KEY,
                root_path TEXT NOT NULL,
                output_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                completed BOOLEAN DEFAULT 0,
                total_documents INTEGER DEFAULT 0,
                processed_documents INTEGER DEFAULT 0
            )
        ''')
        
        # Tabella documenti batch
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                doc_path TEXT NOT NULL,
                json_path TEXT NOT NULL,
                relative_path TEXT,
                workflow_type TEXT,
                status TEXT DEFAULT 'pending',
                json_data TEXT,
                processed_at TIMESTAMP,
                error_message TEXT,
                exported_files TEXT,
                FOREIGN KEY (session_id) REFERENCES batch_sessions(session_id)
            )
        ''')
        
        # Indici per performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_status 
            ON batch_documents(session_id, status)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_workflow
            ON batch_documents(session_id, workflow_type)
        ''')
        
        conn.commit()
        conn.close()
    
    def create_session(self, root_path: str, output_path: str = None) -> str:
        """
        Crea nuova sessione batch
        
        Args:
            root_path: Percorso input scansionato
            output_path: Percorso output (opzionale)
            
        Returns:
            session_id generato
        """
        import uuid
        session_id = str(uuid.uuid4())
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO batch_sessions (session_id, root_path, output_path)
            VALUES (?, ?, ?)
        ''', (session_id, root_path, output_path))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def add_documents(self, session_id: str, documents: List):
        """
        Aggiunge documenti alla sessione
        
        Args:
            session_id: ID sessione
            documents: Lista DocumentPair da aggiungere
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for doc in documents:
            # Serializza json_data
            json_data_str = json.dumps(doc.json_data) if doc.json_data else None
            
            cursor.execute('''
                INSERT INTO batch_documents 
                (session_id, doc_path, json_path, relative_path, workflow_type, 
                 status, json_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (session_id, doc.doc_path, doc.json_path, doc.relative_path,
                  doc.workflow_type, doc.status, json_data_str))
        
        # Aggiorna contatore totale documenti
        cursor.execute('''
            UPDATE batch_sessions 
            SET total_documents = ?
            WHERE session_id = ?
        ''', (len(documents), session_id))
        
        conn.commit()
        conn.close()
    
    def update_document_status(self, doc_id: int, status: str, 
                               error: str = None, exported_files: List[str] = None):
        """
        Aggiorna stato documento
        
        Args:
            doc_id: ID documento
            status: Nuovo stato (pending, processing, completed, error)
            error: Messaggio errore (opzionale)
            exported_files: Lista file esportati (opzionale)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        exported_str = json.dumps(exported_files) if exported_files else None
        
        cursor.execute('''
            UPDATE batch_documents 
            SET status = ?, 
                processed_at = CURRENT_TIMESTAMP, 
                error_message = ?,
                exported_files = ?
            WHERE id = ?
        ''', (status, error, exported_str, doc_id))
        
        # Aggiorna contatore sessione se completato
        if status == 'completed':
            cursor.execute('''
                SELECT session_id FROM batch_documents WHERE id = ?
            ''', (doc_id,))
            session_id = cursor.fetchone()[0]
            
            cursor.execute('''
                UPDATE batch_sessions
                SET processed_documents = (
                    SELECT COUNT(*) FROM batch_documents
                    WHERE session_id = ? AND status = 'completed'
                )
                WHERE session_id = ?
            ''', (session_id, session_id))
        
        conn.commit()
        conn.close()
    
    def get_session_documents(self, session_id: str, status: str = None, 
                             workflow: str = None) -> List[Dict]:
        """
        Recupera documenti della sessione
        
        Args:
            session_id: ID sessione
            status: Filtra per stato (opzionale)
            workflow: Filtra per workflow type (opzionale)
            
        Returns:
            Lista dizionari con dati documenti
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = 'SELECT * FROM batch_documents WHERE session_id = ?'
        params = [session_id]
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if workflow:
            query += ' AND workflow_type = ?'
            params.append(workflow)
        
        query += ' ORDER BY id'
        
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            doc_dict = dict(zip(columns, row))
            
            # Deserializza json_data
            if doc_dict.get('json_data'):
                try:
                    doc_dict['json_data'] = json.loads(doc_dict['json_data'])
                except:
                    doc_dict['json_data'] = None
            
            # Deserializza exported_files
            if doc_dict.get('exported_files'):
                try:
                    doc_dict['exported_files'] = json.loads(doc_dict['exported_files'])
                except:
                    doc_dict['exported_files'] = []
            
            results.append(doc_dict)
        
        conn.close()
        return results
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """
        Recupera informazioni sessione
        
        Returns:
            Dizionario con dati sessione o None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM batch_sessions WHERE session_id = ?
        ''', (session_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    
    def get_incomplete_sessions(self) -> List[Dict]:
        """
        Trova sessioni non completate (per recovery da crash)
        
        Returns:
            Lista sessioni incomplete ordinate per data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM batch_sessions 
            WHERE completed = 0
            ORDER BY created_at DESC
        ''')
        
        columns = [desc[0] for desc in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return results
    
    def mark_session_completed(self, session_id: str):
        """Marca sessione come completata"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE batch_sessions
            SET completed = 1, completed_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (session_id,))
        
        conn.commit()
        conn.close()
    
    def delete_session(self, session_id: str):
        """
        Elimina sessione e documenti associati
        
        Args:
            session_id: ID sessione da eliminare
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Elimina documenti
        cursor.execute('DELETE FROM batch_documents WHERE session_id = ?', (session_id,))
        
        # Elimina sessione
        cursor.execute('DELETE FROM batch_sessions WHERE session_id = ?', (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_session_statistics(self, session_id: str) -> Dict:
        """
        Calcola statistiche sessione
        
        Returns:
            Dizionario con statistiche
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conta per stato
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM batch_documents
            WHERE session_id = ?
            GROUP BY status
        ''', (session_id,))
        
        status_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Conta per workflow
        cursor.execute('''
            SELECT workflow_type, COUNT(*) as count
            FROM batch_documents
            WHERE session_id = ?
            GROUP BY workflow_type
        ''', (session_id,))
        
        workflow_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Totali
        cursor.execute('''
            SELECT COUNT(*) FROM batch_documents WHERE session_id = ?
        ''', (session_id,))
        total = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total,
            'by_status': status_counts,
            'by_workflow': workflow_counts,
            'pending': status_counts.get('pending', 0),
            'processing': status_counts.get('processing', 0),
            'completed': status_counts.get('completed', 0),
            'error': status_counts.get('error', 0),
            'progress_percent': (status_counts.get('completed', 0) / total * 100) if total > 0 else 0
        }