#!/usr/bin/env python3
"""
DynamicAI - Editor Lineare Avanzato
Main application entry point
"""

import sys
import os

def main():
    """Main application entry point"""
    try:
        # Add the current directory to Python path to ensure imports work
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
            
        # Import here to ensure path is set up first
        from gui.main_window import AIDOXAApp
        
        app = AIDOXAApp()
        app.mainloop()
        
    except ImportError as e:
        print(f"Errore di import: {e}")
        print("\nVerifica che tutti i file siano presenti:")
        print("- gui/__init__.py")
        print("- gui/main_window.py")
        print("- config/__init__.py")
        print("- database/__init__.py")
        print("- export/__init__.py")
        print("- loaders/__init__.py")
        print("- utils/__init__.py")
        print("\nE che gui/main_window.py contenga la classe AIDOXAApp")
        sys.exit(1)
        
    except Exception as e:
        print(f"Errore nell'avvio dell'applicazione: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
