import os
from pathlib import Path
import streamlit as st
import shutil

def serve_static_files():
    """Serve static files for PWA functionality"""
    # Get Streamlit's static directory
    streamlit_static = Path(st.__path__[0]) / "static"
    
    # Create static directory if it doesn't exist
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # Always copy the files to ensure they're up to date
    shutil.copy2(static_dir / "manifest.json", streamlit_static / "manifest.json")
    shutil.copy2(static_dir / "sw.js", streamlit_static / "sw.js")
    
    # Copy the icon and ensure it exists
    icon_path = Path("generated-icon.png")
    if icon_path.exists():
        shutil.copy2(icon_path, streamlit_static / "generated-icon.png")
    else:
        st.error("Icon file not found. Please ensure generated-icon.png exists in the root directory.")
