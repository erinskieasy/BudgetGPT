import os
from pathlib import Path
import streamlit as st
from streamlit.components.v1.components import CustomComponent
from streamlit.web.server.server import Server
import shutil

def serve_static_files():
    # Create static directory if it doesn't exist
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # Copy static files to Streamlit's static serving directory
    streamlit_static = Path(st.__path__[0]) / "static"
    if not (streamlit_static / "manifest.json").exists():
        shutil.copy2(static_dir / "manifest.json", streamlit_static)
        shutil.copy2(static_dir / "sw.js", streamlit_static)
        shutil.copy2(Path("generated-icon.png"), streamlit_static / "generated-icon.png")
