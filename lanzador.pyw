# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Atajo del lanzador para correrlo con «pythonw -S lanzador.pyw» (el código está en lanzador.py)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lanzador import main

if __name__ == '__main__':
    main()
