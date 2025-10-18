"""
Workflow Manager for DynamicAI
Manages different operational modes and interface states
"""

from enum import Enum
from typing import Optional, Dict, Any
import tkinter as tk

class WorkflowMode(Enum):
    """Different workflow modes for the application"""
    IDLE = "idle"                    # Applicazione appena avviata
    SINGLE_FILE = "single_file"      # Caricamento file singolo
    BATCH_PROCESSING = "batch_processing"  # Elaborazione batch
    SPLIT_MODE = "split_mode"        # Modalità divisione documenti
    METADATA_ONLY = "metadata_only"  # Solo visualizzazione metadati

class InterfaceState(Enum):
    """Interface display states"""
    EMPTY = "empty"                  # Interfaccia vuota
    THUMBNAILS_ONLY = "thumbnails_only"  # Solo anteprime
    METADATA_ONLY = "metadata_only"  # Solo metadati
    FULL_MODE = "full_mode"         # Anteprime + metadati

class WorkflowManager:
    """Manages workflow states and interface adaptation"""
    
    def __init__(self, main_app):
        self.main_app = main_app
        self.current_workflow = WorkflowMode.IDLE
        self.current_interface = InterfaceState.EMPTY
        self.batch_context = False
        self.document_loaded = False
        self.categories_present = False
        
        # Track what's currently loaded
        self.loaded_document_path = None
        self.loaded_categories = None
        self.loaded_metadata = None
        
    def set_mode(self, workflow: WorkflowMode, interface: InterfaceState = None, **kwargs):
        """Set workflow mode and adapt interface"""
        self.debug_print(f"[WORKFLOW] Changing mode: {self.current_workflow.value} → {workflow.value}")
        
        # Update states
        previous_workflow = self.current_workflow
        self.current_workflow = workflow
        
        if interface:
            self.current_interface = interface
        
        # Update context flags
        self.batch_context = (workflow == WorkflowMode.BATCH_PROCESSING)
        self.document_loaded = kwargs.get('document_loaded', self.document_loaded)
        self.categories_present = kwargs.get('categories_present', self.categories_present)
        
        # Adapt interface only if workflow actually changed
        if previous_workflow != workflow or interface:
            self._adapt_interface()
        
        self.debug_print(f"[WORKFLOW] Mode set: {workflow.value} | Interface: {self.current_interface.value} | Batch: {self.batch_context}")
    
    def determine_interface_mode(self, has_categories: bool, has_metadata: bool) -> InterfaceState:
        """Determine appropriate interface mode based on available data"""
        if has_categories and has_metadata:
            return InterfaceState.FULL_MODE
        elif has_categories:
            return InterfaceState.THUMBNAILS_ONLY
        elif has_metadata:
            return InterfaceState.METADATA_ONLY
        else:
            return InterfaceState.EMPTY
    
    def _adapt_interface(self):
        """Adapt interface elements based on current state"""
        try:
            self.debug_print(f"[WORKFLOW] Adapting interface to: {self.current_interface.value}")
            
            if self.current_interface == InterfaceState.METADATA_ONLY:
                self._show_metadata_only()
            elif self.current_interface == InterfaceState.THUMBNAILS_ONLY:
                self._show_thumbnails_only()
            elif self.current_interface == InterfaceState.FULL_MODE:
                self._show_full_interface()
            else:
                self._show_empty_interface()
                
        except Exception as e:
            self.debug_print(f"[WORKFLOW] Error adapting interface: {e}")
    
    def _show_metadata_only(self):
        """Show only metadata fields"""
        try:
            # Hide thumbnail areas
            if hasattr(self.main_app, 'content_frame'):
                self.main_app.content_frame.pack_forget()
            
            # Ensure metadata panel is visible
            if hasattr(self.main_app, 'right_panel'):
                self.main_app.right_panel.pack(side='right', fill='y', padx=5)
                
            self.debug_print("[WORKFLOW] Interface adapted to metadata only")
            
        except Exception as e:
            self.debug_print(f"[WORKFLOW] Error showing metadata only: {e}")
    
    def _show_thumbnails_only(self):
        """Show only thumbnail interface"""
        try:
            # Show thumbnail areas
            if hasattr(self.main_app, 'content_frame'):
                self.main_app.content_frame.pack(side='left', fill='both', expand=True)
            
            # Hide metadata panel
            if hasattr(self.main_app, 'right_panel'):
                self.main_app.right_panel.pack_forget()
                
            self.debug_print("[WORKFLOW] Interface adapted to thumbnails only")
            
        except Exception as e:
            self.debug_print(f"[WORKFLOW] Error showing thumbnails only: {e}")
    
    def _show_full_interface(self):
        """Show complete interface"""
        try:
            # Show all panels
            if hasattr(self.main_app, 'content_frame'):
                self.main_app.content_frame.pack(side='left', fill='both', expand=True)
            if hasattr(self.main_app, 'right_panel'):
                self.main_app.right_panel.pack(side='right', fill='y', padx=5)
                
            self.debug_print("[WORKFLOW] Interface adapted to full mode")
            
        except Exception as e:
            self.debug_print(f"[WORKFLOW] Error showing full interface: {e}")
    
    def _show_empty_interface(self):
        """Show empty interface"""
        try:
            # Hide all content panels
            if hasattr(self.main_app, 'content_frame'):
                self.main_app.content_frame.pack_forget()
            if hasattr(self.main_app, 'right_panel'):
                self.main_app.right_panel.pack_forget()
                
            self.debug_print("[WORKFLOW] Interface adapted to empty mode")
            
        except Exception as e:
            self.debug_print(f"[WORKFLOW] Error showing empty interface: {e}")
    
    def can_load_metadata(self) -> bool:
        """Check if metadata can be loaded in current state"""
        return self.current_interface in [InterfaceState.METADATA_ONLY, InterfaceState.FULL_MODE]
    
    def can_load_thumbnails(self) -> bool:
        """Check if thumbnails can be loaded in current state"""
        return self.current_interface in [InterfaceState.THUMBNAILS_ONLY, InterfaceState.FULL_MODE]
    
    def is_batch_mode(self) -> bool:
        """Check if in batch processing mode"""
        return self.batch_context
    
    def is_split_mode(self) -> bool:
        """Check if in split mode (categories present)"""
        return self.categories_present and self.can_load_thumbnails()
    
    def reset_to_idle(self):
        """Reset workflow to idle state"""
        self.set_mode(WorkflowMode.IDLE, InterfaceState.EMPTY)
        self.document_loaded = False
        self.categories_present = False
        self.loaded_document_path = None
        self.loaded_categories = None
        self.loaded_metadata = None
    
    def prepare_for_document_load(self, has_categories: bool, has_metadata: bool, is_batch: bool = False):
        """Prepare workflow for document loading"""
        # Determine workflow mode
        if is_batch:
            workflow = WorkflowMode.BATCH_PROCESSING
        else:
            workflow = WorkflowMode.SINGLE_FILE
            
        # Determine interface mode
        interface = self.determine_interface_mode(has_categories, has_metadata)
        
        # Set mode
        self.set_mode(
            workflow, 
            interface, 
            document_loaded=True, 
            categories_present=has_categories
        )
        
        return workflow, interface
    
    def debug_print(self, message: str):
        """Debug logging"""
        if hasattr(self.main_app, 'debug_print'):
            self.main_app.debug_print(message)
        else:
            print(message)
