
import os
from pathlib import Path
import streamlit as st
import shutil

def serve_static_files():
    """Serve static files for PWA functionality"""
    # Get Streamlit's static directory
    streamlit_static = Path(st.__path__[0]) / 'static'
    
    # Ensure static directory exists
    static_dir = Path('static')
    static_dir.mkdir(exist_ok=True)
    
    # Copy PWA files
    shutil.copy2('manifest.json', streamlit_static / 'manifest.json')
    shutil.copy2(static_dir / 'sw.js', streamlit_static / 'sw.js')
    
    # Copy icon
    icon_path = Path('generated-icon.png')
    if icon_path.exists():
        shutil.copy2(icon_path, streamlit_static / 'generated-icon.png')
    else:
        st.error('Icon file missing - PWA installation will not work')
