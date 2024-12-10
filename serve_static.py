import os
from pathlib import Path
import streamlit as st
import shutil

def serve_static_files():
    """Serve static files for PWA functionality"""
    try:
        # Get Streamlit's static directory
        streamlit_static = Path(st.__path__[0]) / 'static'
        
        # Create static directory if it doesn't exist
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        
        # Generate icons first
        from generate_icons import generate_pwa_icon
        for size in [192, 512]:
            icon = generate_pwa_icon(size)
            icon_path = static_dir / f"icon-{size}.png"
            icon.save(icon_path)
        
        # Copy static files to Streamlit's static directory
        static_files = ["manifest.json", "sw.js", "icon-192.png", "icon-512.png"]
        for file in static_files:
            src = static_dir / file
            dst = streamlit_static / file
            if src.exists():
                shutil.copy2(src, dst)
            else:
                st.error(f"Error: Required PWA file missing: {file}")
    except Exception as e:
        st.error("Error setting up PWA functionality. Please try refreshing the page.")
