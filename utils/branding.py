from __future__ import annotations
import os, sys
import tkinter as tk

def resource_path(relative: str) -> str:
    """Return absolute path to resource, works for dev and PyInstaller bundle."""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath(os.path.dirname(__file__)))
    p1 = os.path.join(base_path, relative)
    p2 = os.path.join(os.path.dirname(base_path), relative)
    return p1 if os.path.exists(p1) else p2

def set_app_icon(root: tk.Tk, png_path: str = "assets/icons/documentai.png") -> None:
    """Set the window icon from a PNG (cross-platform). Falls back silently."""
    try:
        full = resource_path(png_path)
        if os.path.exists(full):
            img = tk.PhotoImage(file=full)
            root.iconphoto(True, img)
    except Exception:
        pass
