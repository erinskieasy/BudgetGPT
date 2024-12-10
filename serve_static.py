import os
from pathlib import Path
import streamlit as st
import shutil

def serve_static_files():
    """Serve static files for PWA functionality"""
    try:
        # Get Streamlit's static directory
        streamlit_static = Path(st.__path__[0]) / 'static'
        st.write(f"Streamlit static path: {streamlit_static}")
        
        # Create static directory if it doesn't exist
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        st.write(f"Local static directory: {static_dir}")
        
        # Generate icons first
        from generate_icons import generate_pwa_icon
        for size in [192, 512]:
            icon = generate_pwa_icon(size)
            icon_path = static_dir / f"icon-{size}.png"
            icon.save(icon_path)
            st.write(f"Generated icon: {icon_path}")
        
        # List of files to copy
        static_files = ["manifest.json", "sw.js", "icon-192.png", "icon-512.png"]
        
        # Copy files to Streamlit's static directory
        for file in static_files:
            src = static_dir / file
            dst = streamlit_static / file
            
            if src.exists():
                shutil.copy2(src, dst)
                st.write(f"Copied {file} to {dst}")
            else:
                st.error(f"Static file not found: {file}")
                st.write(f"Looking for file at: {src}")
        
        st.write("Static file serving completed")
        
    except Exception as e:
        st.error(f"Error serving static files: {str(e)}")
        import traceback
        st.write("Detailed error:", traceback.format_exc())
