"""
Batch Scanner - Scansione ricorsiva directory con rilevamento workflow automatico
"""

import os
import json
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class DocumentPair:
    """Rappresenta una coppia documento+JSON rilevata"""
    id: Optional[int] = None
    doc_path: str = ""
    json_path: str = ""
    relative_path: str = ""
    workflow_type: str = ""  # 'split_categorie' | 'metadati_semplici'
    json_data: dict = None
    status: str = "pending"  # pending, processing, completed, error
    error_message: Optional[str] = None
    
    def get_doc_basename(self) -> str:
        """Ritorna nome file documento senza path"""
        return os.path.basename(self.doc_path)
    
    def get_json_basename(self) -> str:
        """Ritorna nome file JSON senza path"""
        return os.path.basename(self.json_path)


class BatchScanner:
    """Gestisce scansione ricorsiva directory e rilevamento workflow"""
    
    def __init__(self, supported_extensions=None):
        """
        Inizializza scanner
        
        Args:
            supported_extensions: Lista estensioni supportate (default: PDF, TIFF, TIF)
        """
        self.supported_extensions = supported_extensions or ['.pdf', '.tiff', '.tif']
        self.scan_stats = {
            'total_dirs': 0,
            'documents_found': 0,
            'json_found': 0,
            'pairs_matched': 0,
            'split_categorie': 0,
            'metadati_semplici': 0
        }
    
    def scan_directory(self, root_path: str, max_depth: int = -1) -> List[DocumentPair]:
        """
        Scansiona ricorsivamente directory alla ricerca di coppie PDF+JSON
        
        Args:
            root_path: Percorso root da scansionare
            max_depth: Profondità massima (-1 = illimitato)
            
        Returns:
            Lista di DocumentPair con metadati completi
            
        Raises:
            ValueError: Se root_path non esiste
        """
        if not os.path.exists(root_path):
            raise ValueError(f"Percorso non esistente: {root_path}")
        
        if not os.path.isdir(root_path):
            raise ValueError(f"Il percorso non è una directory: {root_path}")
        
        # Reset statistiche
        self.scan_stats = {k: 0 for k in self.scan_stats}
        
        found_pairs = []
        
        for dirpath, dirnames, filenames in os.walk(root_path):
            self.scan_stats['total_dirs'] += 1
            
            # Calcola profondità corrente
            depth = dirpath[len(root_path):].count(os.sep)
            
            # Limita profondità se specificato
            if max_depth != -1 and depth >= max_depth:
                dirnames[:] = []  # Ferma discesa in sottodirectory
                continue
            
            # Trova documenti supportati
            docs = [f for f in filenames 
                   if os.path.splitext(f.lower())[1] in self.supported_extensions]
            jsons = [f for f in filenames if f.lower().endswith('.json')]
            
            self.scan_stats['documents_found'] += len(docs)
            self.scan_stats['json_found'] += len(jsons)
            
            # Match PDF + JSON
            for doc in docs:
                basename = os.path.splitext(doc)[0]
                json_name = f"{basename}.json"
                
                if json_name in jsons:
                    try:
                        doc_pair = self._create_document_pair(
                            dirpath, doc, json_name, root_path
                        )
                        found_pairs.append(doc_pair)
                        self.scan_stats['pairs_matched'] += 1
                        
                        # Statistiche workflow
                        if doc_pair.workflow_type == 'split_categorie':
                            self.scan_stats['split_categorie'] += 1
                        else:
                            self.scan_stats['metadati_semplici'] += 1
                            
                    except Exception as e:
                        print(f"[WARNING] Errore processing {doc}: {e}")
                        continue
        
        return found_pairs
    
    def _create_document_pair(self, dirpath: str, doc: str, json_name: str, 
                             root_path: str) -> DocumentPair:
        """
        Crea DocumentPair con rilevamento workflow automatico
        
        Args:
            dirpath: Directory contenente i file
            doc: Nome file documento
            json_name: Nome file JSON
            root_path: Path root per calcolo path relativo
            
        Returns:
            DocumentPair configurato
        """
        doc_path = os.path.join(dirpath, doc)
        json_path = os.path.join(dirpath, json_name)
        
        # Carica JSON e rileva workflow
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
        except Exception as e:
            raise ValueError(f"Errore lettura JSON {json_name}: {e}")
        
        workflow_type = self._detect_workflow(json_data)
        
        # Calcola path relativo
        if dirpath == root_path:
            relative_path = "."
        else:
            relative_path = os.path.relpath(dirpath, root_path)
        
        return DocumentPair(
            doc_path=doc_path,
            json_path=json_path,
            relative_path=relative_path,
            workflow_type=workflow_type,
            json_data=json_data,
            status='pending'
        )
    
    def _detect_workflow(self, json_data: dict) -> str:
        """
        Rileva tipo workflow dal contenuto JSON
        
        Args:
            json_data: Contenuto JSON caricato
            
        Returns:
            'split_categorie' se JSON contiene array 'categories'
            'metadati_semplici' altrimenti
        """
        # Controlla presenza array categories
        if 'categories' in json_data:
            categories = json_data['categories']
            if isinstance(categories, list) and len(categories) > 0:
                # Valida struttura categories
                first_cat = categories[0]
                if isinstance(first_cat, dict) and 'categoria' in first_cat:
                    return 'split_categorie'
        
        # Default: metadati semplici
        return 'metadati_semplici'
    
    def get_scan_summary(self) -> str:
        """
        Genera riepilogo scansione
        
        Returns:
            Stringa formattata con statistiche
        """
        return f"""SCANSIONE COMPLETATA:
        
Directory analizzate: {self.scan_stats['total_dirs']}
Documenti trovati: {self.scan_stats['documents_found']}
File JSON trovati: {self.scan_stats['json_found']}
Coppie complete: {self.scan_stats['pairs_matched']}

WORKFLOW RILEVATI:
  Split Categorie: {self.scan_stats['split_categorie']}
  Metadati Semplici: {self.scan_stats['metadati_semplici']}
"""
    
    def get_stats(self) -> Dict:
        """Ritorna dizionario con statistiche scansione"""
        return self.scan_stats.copy()


# Funzioni helper per uso esterno

def quick_scan(root_path: str, max_depth: int = -1) -> List[DocumentPair]:
    """
    Funzione helper per scansione rapida
    
    Args:
        root_path: Directory da scansionare
        max_depth: Profondità massima (-1 = illimitato)
        
    Returns:
        Lista DocumentPair trovati
    """
    scanner = BatchScanner()
    return scanner.scan_directory(root_path, max_depth)


def scan_with_stats(root_path: str, max_depth: int = -1) -> tuple:
    """
    Scansione con ritorno statistiche
    
    Returns:
        Tuple (documents, stats_dict)
    """
    scanner = BatchScanner()
    documents = scanner.scan_directory(root_path, max_depth)
    stats = scanner.get_stats()
    return documents, stats