from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import json

@dataclass
class Job:
    """Rappresenta un Job di elaborazione"""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    input_folder: str = ""
    output_folder: str = ""
    status: str = "pending"  # pending, in_progress, completed, error
    progress: float = 0.0
    total_images: int = 0
    completed_images: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: dict = None
    maintain_structure: bool = True  # 🔥 NUOVO CAMPO per gestire struttura directory

    def __post_init__(self):
        """Initialize metadata dict if None"""
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict:
        """Converte in dizionario per DB"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'input_folder': self.input_folder,
            'output_folder': self.output_folder,
            'status': self.status,
            'progress': self.progress,
            'total_images': self.total_images,
            'completed_images': self.completed_images,
            'maintain_structure': int(self.maintain_structure),  # 🔥 AGGIUNTO
            'metadata': json.dumps(self.metadata or {})
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Job':
        """Crea Job da dizionario DB"""
        metadata = {}
        if data.get('metadata'):
            try:
                metadata = json.loads(data['metadata'])
            except:
                pass

        return cls(
            id=data.get('id'),
            name=data.get('name', ''),
            description=data.get('description', ''),
            input_folder=data.get('input_folder', ''),
            output_folder=data.get('output_folder', ''),
            status=data.get('status', 'pending'),
            progress=data.get('progress', 0.0),
            total_images=data.get('total_images', 0),
            completed_images=data.get('completed_images', 0),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            maintain_structure=bool(data.get('maintain_structure', 1)),  # 🔥 AGGIUNTO
            metadata=metadata
        )

    @property
    def workflow_type(self):
        """Compatibilità con codice esistente"""
        return self.metadata.get('workflow_type', 'split_categorie')
    
    @workflow_type.setter
    def workflow_type(self, value):
        """Compatibilità con codice esistente"""
        if self.metadata is None:
            self.metadata = {}
        self.metadata['workflow_type'] = value

    def __str__(self):
        """Rappresentazione stringa del Job"""
        return f"Job(id={self.id}, name='{self.name}', status='{self.status}')"

    def __repr__(self):
        """Rappresentazione debug del Job"""
        return (f"Job(id={self.id}, name='{self.name}', "
                f"input_folder='{self.input_folder}', "
                f"output_folder='{self.output_folder}', "
                f"status='{self.status}', progress={self.progress}, "
                f"maintain_structure={self.maintain_structure})")
