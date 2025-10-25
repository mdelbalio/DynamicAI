import sqlite3
import os
import json
from typing import List, Optional
from models.job import Job
from models.batch import Batch

class JobManager:
    """Gestisce i Job nel database"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Inizializza database con tabelle"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 🔥 Crea tabella jobs con maintain_structure
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    input_folder TEXT NOT NULL,
                    output_folder TEXT,
                    status TEXT DEFAULT 'pending',
                    progress REAL DEFAULT 0.0,
                    total_images INTEGER DEFAULT 0,
                    completed_images INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    maintain_structure INTEGER DEFAULT 1,
                    metadata TEXT
                )
            """)
            
            # 🔥 Aggiungi colonna maintain_structure se non esiste (per database esistenti)
            try:
                cursor.execute('ALTER TABLE jobs ADD COLUMN maintain_structure INTEGER DEFAULT 1')
                print("[DB] Added maintain_structure column to jobs table")
            except sqlite3.OperationalError:
                # Colonna già esistente
                pass
            
            # Crea tabella batches
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    pdf_path TEXT NOT NULL,
                    json_path TEXT,
                    status TEXT DEFAULT 'pending',
                    page_count INTEGER DEFAULT 0,
                    validated BOOLEAN DEFAULT 0,
                    exported BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                )
            """)
            
            # Crea indici
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_batches_job_id ON batches(job_id)")
            
            conn.commit()
    
    def create_job(self, job: Job) -> int:
        """Crea nuovo Job"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            data = job.to_dict()
            
            # 🔥 AGGIUNTO maintain_structure nell'INSERT
            cursor.execute("""
                INSERT INTO jobs (name, description, input_folder, output_folder,
                                status, progress, total_images, completed_images, 
                                maintain_structure, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data['name'], data['description'], data['input_folder'],
                  data['output_folder'], data['status'], data['progress'],
                  data['total_images'], data['completed_images'], 
                  data['maintain_structure'], data['metadata']))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_all_jobs(self) -> List[Job]:
        """Ottieni tutti i Job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            return [Job.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def get_job_by_id(self, job_id: int) -> Optional[Job]:
        """Ottieni Job per ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM jobs WHERE id=?", (job_id,))
            row = cursor.fetchone()
            return Job.from_dict(dict(row)) if row else None
    
    def update_job(self, job: Job):
        """Aggiorna Job"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            data = job.to_dict()
            
            # 🔥 AGGIUNTO maintain_structure nell'UPDATE
            cursor.execute("""
                UPDATE jobs SET name=?, description=?, input_folder=?, output_folder=?,
                              status=?, progress=?, total_images=?, completed_images=?,
                              maintain_structure=?, metadata=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (data['name'], data['description'], data['input_folder'],
                  data['output_folder'], data['status'], data['progress'],
                  data['total_images'], data['completed_images'], 
                  data['maintain_structure'], data['metadata'], job.id))
            
            conn.commit()
    
    def delete_job(self, job_id: int):
        """Elimina Job (e batches associati per CASCADE)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM jobs WHERE id=?", (job_id,))
            conn.commit()
    
    def scan_folder_for_batches(self, job: Job) -> List[dict]:
        """Scansiona cartella input per trovare coppie PDF+JSON"""
        batches = []
        if not os.path.exists(job.input_folder):
            return batches
        
        for file in os.listdir(job.input_folder):
            if file.lower().endswith(('.pdf', '.tiff', '.tif')):
                pdf_path = os.path.join(job.input_folder, file)
                json_name = os.path.splitext(file)[0] + '.json'
                json_path = os.path.join(job.input_folder, json_name)
                
                if os.path.exists(json_path):
                    batches.append({
                        'name': os.path.splitext(file)[0],
                        'pdf_path': pdf_path,
                        'json_path': json_path
                    })
        
        return batches
    
    def create_batch(self, batch: Batch) -> int:
        """Crea nuovo Batch"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            data = batch.to_dict()
            
            cursor.execute("""
                INSERT INTO batches (job_id, name, pdf_path, json_path,
                                   status, page_count, validated, exported, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (data['job_id'], data['name'], data['pdf_path'], data['json_path'],
                  data['status'], data['page_count'], data['validated'],
                  data['exported'], data['metadata']))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_job_batches(self, job_id: int) -> List[Batch]:
        """Ottieni tutti i Batch di un Job"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM batches 
                WHERE job_id=? 
                ORDER BY name
            """, (job_id,))
            return [Batch.from_dict(dict(row)) for row in cursor.fetchall()]
    
    def update_batch(self, batch: Batch):
        """Aggiorna Batch"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            data = batch.to_dict()
            
            cursor.execute("""
                UPDATE batches SET name=?, pdf_path=?, json_path=?, status=?,
                                 page_count=?, validated=?, exported=?, metadata=?
                WHERE id=?
            """, (data['name'], data['pdf_path'], data['json_path'], data['status'],
                  data['page_count'], data['validated'], data['exported'],
                  data['metadata'], batch.id))
            
            conn.commit()
    
    def update_job_progress(self, job_id: int):
        """Ricalcola progresso Job basato sui Batch"""
        batches = self.get_job_batches(job_id)
        if not batches:
            return
        
        total = len(batches)
        completed = sum(1 for b in batches if b.exported)
        progress = (completed / total) * 100 if total > 0 else 0
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if completed == total:
                status = 'completed'
            elif completed > 0:
                status = 'in_progress'
            else:
                status = 'pending'
            
            cursor.execute("""
                UPDATE jobs SET progress=?, status=?, completed_images=?,
                              updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (progress, status, completed, job_id))
            
            conn.commit()
    
    def create_batches_from_folder(self, job: Job) -> int:
        """Scansiona cartella e crea automaticamente i Batch"""
        batch_data = self.scan_folder_for_batches(job)
        created = 0
        total_pages = 0
        
        for data in batch_data:
            page_count = 0
            metadata = {}
            
            try:
                with open(data['json_path'], 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                    
                    if 'categories' in json_data:
                        for cat in json_data['categories']:
                            start = cat.get('inizio', 1)
                            end = cat.get('fine', start)
                            page_count += (end - start + 1)
                    
                    metadata = json_data.get('header', {})
                    
            except Exception as e:
                print(f"Error reading JSON {data['json_path']}: {e}")
            
            batch = Batch(
                job_id=job.id,
                name=data['name'],
                pdf_path=data['pdf_path'],
                json_path=data['json_path'],
                page_count=page_count,
                metadata=metadata
            )
            
            self.create_batch(batch)
            created += 1
            total_pages += page_count
        
        # Aggiorna totale pagine del Job
        if created > 0:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE jobs SET total_images=? WHERE id=?
                """, (total_pages, job.id))
                conn.commit()
        
        return created
    
    # 🔥 NUOVI METODI UTILI
    
    def get_job_stats(self, job_id: int) -> dict:
        """Ottieni statistiche complete del Job"""
        job = self.get_job_by_id(job_id)
        if not job:
            return {}
        
        batches = self.get_job_batches(job_id)
        
        return {
            'job': job,
            'total_batches': len(batches),
            'validated_batches': sum(1 for b in batches if b.validated),
            'exported_batches': sum(1 for b in batches if b.exported),
            'total_pages': sum(b.page_count for b in batches),
            'progress_percent': job.progress
        }
    
    def search_jobs(self, query: str = "") -> List[Job]:
        """Cerca Job per nome o descrizione"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if query:
                cursor.execute("""
                    SELECT * FROM jobs 
                    WHERE name LIKE ? OR description LIKE ?
                    ORDER BY created_at DESC
                """, (f'%{query}%', f'%{query}%'))
            else:
                cursor.execute("SELECT * FROM jobs ORDER BY created_at DESC")
            
            return [Job.from_dict(dict(row)) for row in cursor.fetchall()]
