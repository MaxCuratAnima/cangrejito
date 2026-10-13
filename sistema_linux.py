# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Lo que el vigilante necesita saber del sistema, versión Linux (X11; en Wayland corre por XWayland).

Misma interfaz que sistema_windows.py. Usa herramientas comunes si están instaladas y, si no, esa
parte se apaga sola (nunca rompe):
  xprop, xwininfo  pantalla completa (paquete x11-utils)
  xprintidle       tiempo sin tocar el teclado ni el mouse (para dormirse)
  playerctl        qué suena en Spotify
En Linux no hay app de escritorio de Claude: «Claude abierto» es que haya Claude Code corriendo.
"""
from __future__ import annotations

import re
import shutil
import subprocess

import psutil

_TIENE = {}
JUEGOS_PESADOS = {'vrchat.exe', 'vrserver', 'vrmonitor', 'vrcompositor'}   # VR: la placa va al 100 %
_pesado = [False]


def _hay(programa: str) -> bool:
    if programa not in _TIENE:
        _TIENE[programa] = shutil.which(programa) is not None
    return _TIENE[programa]


def _correr(*args: str, timeout: float = 1.0) -> str:
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def segundos_inactivo() -> float:
    if not _hay('xprintidle'):
        return 0.0                                   # sin xprintidle no se duerme solo
    salida = _correr('xprintidle').strip()
    return int(salida) / 1000.0 if salida.isdigit() else 0.0


def ventanas():
    return None                                      # en Linux se pregunta directo por la ventana activa


def monitores_en_pantalla_completa(propias: set[int], ventanas_=None) -> dict[tuple, str]:
    """{(izq, arriba, der, abajo): proceso} si la ventana activa está en pantalla completa."""
    if not (_hay('xprop') and _hay('xwininfo')):
        return {}
    m = re.search(r'window id # (0x[0-9a-f]+)', _correr('xprop', '-root', '_NET_ACTIVE_WINDOW'))
    if not m or int(m.group(1), 16) in propias or int(m.group(1), 16) == 0:
        return {}
    wid = m.group(1)
    estado = _correr('xprop', '-id', wid, '_NET_WM_STATE', '_NET_WM_PID')
    if '_NET_WM_STATE_FULLSCREEN' not in estado:
        return {}
    info = _correr('xwininfo', '-id', wid)
    numeros = {k: int(v) for k, v in re.findall(r'(Absolute upper-left [XY]|Width|Height):\s+(-?\d+)', info)}
    if len(numeros) < 4:
        return {}
    x, y = numeros['Absolute upper-left X'], numeros['Absolute upper-left Y']
    pid = re.search(r'_NET_WM_PID\(CARDINAL\) = (\d+)', estado)
    try:
        proc = psutil.Process(int(pid.group(1))).name().lower() if pid else ''
    except psutil.Error:
        proc = ''
    return {(x, y, x + numeros['Width'] - 1, y + numeros['Height'] - 1): proc}


def pids_app_claude() -> set[int]:
    """Procesos de Claude Code (en Linux no hay app de escritorio). De paso anota si hay VR."""
    pids, pesado = set(), False
    for p in psutil.process_iter(['name']):
        nombre = (p.info['name'] or '').lower()
        if nombre in JUEGOS_PESADOS:
            pesado = True
        if nombre == 'claude':
            pids.add(p.pid)
    _pesado[0] = pesado
    return pids


def app_claude_abierta(ventanas_, pids: set[int]) -> bool:
    return bool(pids)


def hay_vr() -> bool:
    return _pesado[0]


def spotify_tema(ventanas_=None) -> str:
    """«Artista - Tema» si Spotify está sonando (por MPRIS, con playerctl)."""
    if not _hay('playerctl') or _correr('playerctl', '-p', 'spotify', 'status').strip() != 'Playing':
        return ''
    return _correr('playerctl', '-p', 'spotify', 'metadata', '--format', '{{artist}} - {{title}}').strip()


def poner_encima(ventana: int):
    pass                                             # alcanza con la bandera «siempre encima» de Qt


def enganchar_cambio_ventana(al_cambiar):
    return None


def olvidar_nombres():
    pass
