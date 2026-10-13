# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Dónde vive cada cosa. Solo librería estándar (lo usa también el lanzador, que corre sin librerías).

  CODIGO  la carpeta del programa (instalado puede ser de solo lectura)
  DATOS   lo de cada usuario: config.json, registro, temas_auto.json y la voz
          (Windows: %APPDATA%\\Cangrejito · Linux: ~/.local/share/cangrejito)
"""
import os
import shutil
import sys
from pathlib import Path

WINDOWS = sys.platform == 'win32'
CONGELADO = getattr(sys, 'frozen', False)                  # corre como .exe (PyInstaller)
CODIGO = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))


def _datos_por_defecto() -> Path:
    if WINDOWS:
        return Path(os.environ.get('APPDATA') or Path.home() / 'AppData' / 'Roaming') / 'Cangrejito'
    return Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local' / 'share') / 'cangrejito'


# para pruebas: CANGREJITO_DATOS cambia la carpeta de datos
DATOS = Path(os.environ.get('CANGREJITO_DATOS') or _datos_por_defecto())
VOZ = DATOS / 'voz'


def preparar():
    """Crea la carpeta de datos y, la primera vez, trae lo que había al lado del código (instalaciones viejas)."""
    DATOS.mkdir(parents=True, exist_ok=True)
    viejo = Path(__file__).resolve().parent
    for nombre in ('config.json', 'temas_auto.json'):
        destino = DATOS / nombre
        if not destino.exists() and (viejo / nombre).exists():
            shutil.copy2(viejo / nombre, destino)
    if not (DATOS / 'temas_auto.json').exists() and (CODIGO / 'temas_auto.ejemplo.json').exists():
        shutil.copy2(CODIGO / 'temas_auto.ejemplo.json', DATOS / 'temas_auto.json')


def es_claude_code_suelto(ruta: str) -> bool:
    """Claude Code corriendo en una terminal: un claude.exe que no es la app de escritorio ni el Claude Code
    que la app trae adentro (%APPDATA%\\Claude\\claude-code\\…, que se cierra con ella)."""
    r = (ruta or '').lower()
    return r.endswith('\\claude.exe') and not es_app_claude(r) and '\\claude\\claude-code\\' not in r


def es_app_claude(ruta: str) -> bool:
    """El claude.exe de la app de escritorio (Microsoft Store o instalador clásico), no el de Claude Code."""
    r = (ruta or '').lower()
    return r.endswith('\\claude.exe') and ('\\windowsapps\\claude_' in r or '\\anthropicclaude\\' in r)
