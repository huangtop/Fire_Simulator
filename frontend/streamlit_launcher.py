"""Launcher (entry) for Streamlit front-end.

This launcher avoids Python import name collisions by explicitly loading
the top-level `fire_streamlit.py` file from the repository root using
importlib when available. That prevents accidentally importing
`frontend/fire_streamlit.py` (which would cause circular import).
"""

import os
import streamlit as st
import importlib.util


def load_root_fire_streamlit():
    """Load the repo-root fire_streamlit.py by path and return the module.

    Returns the loaded module or None if not available.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    candidate = os.path.join(repo_root, 'fire_streamlit.py')
    if not os.path.exists(candidate):
        return None

    spec = importlib.util.spec_from_file_location('fire_streamlit_root', candidate)
    if spec is None or spec.loader is None:
        return None

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def import_streamlit_tool():
    """Import and return StreamlitFIREPlanningTool class.

    Tries to load the repo-root `fire_streamlit.py` first, then falls back
    to a normal import if that fails.
    """
    mod = load_root_fire_streamlit()
    if mod is not None and hasattr(mod, 'StreamlitFIREPlanningTool'):
        return getattr(mod, 'StreamlitFIREPlanningTool')

    # Final fallback: regular import (may raise)
    from fire_streamlit import StreamlitFIREPlanningTool  # type: ignore
    return StreamlitFIREPlanningTool


def main():
    try:
        StreamlitFIREPlanningTool = import_streamlit_tool()
    except Exception as e:
        st.set_page_config(page_title="💰 FIRE理財規劃工具", page_icon="💰", layout="wide")
        st.error(f"無法載入 fire_streamlit.py: {e}")
        st.stop()

    tool = StreamlitFIREPlanningTool()
    tool.main()


if __name__ == '__main__':
    main()
