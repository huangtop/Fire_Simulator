#!/usr/bin/env python3
"""List available font family names from matplotlib's font manager."""
import matplotlib.font_manager as fm

names = sorted({f.name for f in fm.fontManager.ttflist})
for n in names:
    print(n)
