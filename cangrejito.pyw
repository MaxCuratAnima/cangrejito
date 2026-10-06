# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Cangrejito: mascota de escritorio que comenta lo que hace Claude Code.

Arranca con Windows escondido; aparece cuando abrís la app de Claude.
  --ya        aparece enseguida aunque la app esté cerrada (para probar)
  --sin-voz   arranca silenciado
(El código está en cangrejito_app.py; este archivo es el atajo para correrlo con pythonw.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cangrejito_app import main

if __name__ == '__main__':
    main()
