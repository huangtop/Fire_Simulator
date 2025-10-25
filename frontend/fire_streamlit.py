"""Minimal Streamlit launcher that runs the canonical implementation.

This file intentionally remains tiny: it imports and runs
StreamlitFIREPlanningTool from the repository implementation
`fire_streamlit.py` so that that file stays as the single
source of truth for the Streamlit UI.
"""

import streamlit as st
import os
import sys
import importlib.util

# Configure matplotlib for Chinese font support
try:
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm

    # Set Chinese font for matplotlib
    candidates = [
        'Noto Sans CJK TC', 'Noto Sans CJK JP', 'Noto Sans CJK SC', 'Noto Sans CJK KR',
        'PingFang TC', 'PingFang', 'AppleGothic', 'Heiti TC', 'Microsoft JhengHei',
        'SimHei', 'Arial Unicode MS', 'Source Han Sans TW', 'Source Han Sans CN',
        'DejaVu Sans'
    ]

    available = {f.name for f in fm.fontManager.ttflist}
    chosen = None
    for c in candidates:
        if c in available:
            chosen = c
            break

    if chosen:
        plt.rcParams['font.family'] = chosen
        plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display
    else:
        # Fallback to system default
        plt.rcParams['font.family'] = 'sans-serif'

except ImportError:
    # matplotlib not available, skip font configuration
    pass

# Robustly load the canonical implementation from core_private to avoid
# circular imports when this launcher is executed from the `frontend/` dir
StreamlitFIREPlanningTool = None
try:
    # Ensure core_private is in the path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)  # Go up one level to project root
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Try direct import first (simplest approach)
    from core_private.fire_streamlit import StreamlitFIREPlanningTool
except ImportError as e:
    # Show detailed error for debugging
    st.set_page_config(page_title="💰 FIRE理財規劃工具", page_icon="💰", layout="wide")
    st.error(f"直接 import 失敗: {e}")
    st.error("請檢查 core_private 模組是否正確安裝")
    st.stop()
def main():
    tool = StreamlitFIREPlanningTool()
    tool.main()


if __name__ == "__main__":
    main()
