from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json

@dataclass
class Batch:
    """Rappresenta un Batch (documento PDF+JSON) all'interno di un Job"""
    id: Optional[int] = None
    job_id: int = 0
    name: str = ""
    pdf_path: str = ""
    json_path: str = ""
    status: str = "pending"  # pending, validated, exported, error
    page_count: int = 0
    validated: bool = False
    exported: bool = False
    created_at: Optional[datetime] = None
    metadata: dict = None  # Metadati estratti dal JSON
    
    def to_dict(self) -> dict:
        """Converte in dizionario per DB"""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'name': self.name,
            'pdf_path': self.pdf_path,
            'json_path': self.json_path,
            'status': self.status,
            'page_count': self.page_count,
            'validated': 1 if self.validated else 0,
            'exported': 1 if self.exported else 0,
            'metadata': json.dumps(self.metadata or {})
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Batch':
        """Crea Batch da dizionario DB"""
        metadata = {}
        if data.get('metadata'):
            try:
                metadata = json.loads(data['metadata'])
            except:
                pass
        
        return cls(
            id=data.get('id'),
            job_id=data.get('job_id'),
            name=data.get('name', ''),
            pdf_path=data.get('pdf_path', ''),
            json_path=data.get('json_path', ''),
            status=data.get('status', 'pending'),
            page_count=data.get('page_count', 0),
            validated=bool(data.get('validated', 0)),
            exported=bool(data.get('exported', 0)),
            created_at=data.get('created_at'),
            metadata=metadata
        )
    
    def is_complete(self) -> bool:
        """Controlla se batch è completato"""
        return self.validated and self.exported
    
    def get_status_icon(self) -> str:
        """Ottieni icona stato"""
        if self.status == 'error':
            return '❌'
        elif self.exported:
            return '✅'
        elif self.validated:
            return '🔍'
        else:
            return '⏸️'