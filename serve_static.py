
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
    shutil.copy2('sw.js', streamlit_static / 'sw.js')
    
    # Copy icons
    for size in [192, 512]:
        icon_path = Path(f'generated-icon-{size}.png')
        if icon_path.exists():
            shutil.copy2(icon_path, streamlit_static / f'generated-icon-{size}.png')
        else:
            st.error(f'Icon file missing - generated-icon-{size}.png')
