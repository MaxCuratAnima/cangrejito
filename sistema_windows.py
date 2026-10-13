# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Lo que el vigilante necesita saber del sistema, versión Windows (API de Win32 con ctypes).

La misma interfaz está en sistema_linux.py; vigilante.py usa la que corresponde.
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt

import psutil

import rutas

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi
CLASES_ESCRITORIO = {'Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd'}
# procesos cuyas ventanas grandes no son «pantalla completa» (paneles, overlays)
NO_CUENTAN = {'explorer.exe', 'modogamer.exe', 'nvidia overlay.exe', 'nvidia share.exe', 'textinputhost.exe',
              'shellexperiencehost.exe', 'searchhost.exe', 'startmenuexperiencehost.exe', 'lockapp.exe',
              'gamebar.exe', 'wallpaper32.exe', 'wallpaper64.exe', 'lively.exe'}
HWND_TOPMOST = -1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_EX_TOOLWINDOW, WS_EX_TRANSPARENT, WS_EX_NOACTIVATE = 0x80, 0x20, 0x08000000
DWMWA_CLOAKED = 14


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', wt.UINT), ('dwTime', wt.DWORD)]


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [('cbSize', wt.DWORD), ('rcMonitor', wt.RECT), ('rcWork', wt.RECT), ('dwFlags', wt.DWORD),
                ('szDevice', wt.WCHAR * 32)]


user32.GetForegroundWindow.restype = wt.HWND
user32.MonitorFromWindow.restype = wt.HMONITOR
user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
user32.GetMonitorInfoW.argtypes = [wt.HMONITOR, ctypes.POINTER(MONITORINFOEX)]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsIconic.argtypes = [wt.HWND]
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
dwmapi.DwmGetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
ENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def segundos_inactivo() -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(lii)
    user32.GetLastInputInfo(ctypes.byref(lii))
    return ((kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF) / 1000.0


def _ventanas():
    """Ventanas de primer nivel visibles: (hwnd, pid)."""
    out = []

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            pid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            out.append((hwnd, pid.value))
        return True

    user32.EnumWindows(ENUM(cb), 0)
    return out


def _monitor(hwnd):
    mi = MONITORINFOEX()
    mi.cbSize = ctypes.sizeof(mi)
    if not user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(mi)):
        return None
    return mi


_nombres: dict[int, str] = {}


def _proceso(pid: int) -> str:
    n = _nombres.get(pid)
    if n is None:
        try:
            n = psutil.Process(pid).name().lower()
        except psutil.Error:
            n = ''
        _nombres[pid] = n
    return n


def monitores_en_pantalla_completa(propias: set[int], ventanas=None) -> dict[tuple, str]:
    """{(izq, arriba, der, abajo) del monitor: proceso} tapados por una ventana a pantalla completa."""
    tapados = {}
    for hwnd, pid in (ventanas if ventanas is not None else _ventanas()):
        h = int(hwnd)
        if h in propias or user32.IsIconic(hwnd):
            continue
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF
        if ex & (WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE):
            continue
        oculta = wt.DWORD()
        if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(oculta), 4) == 0 and oculta.value:
            continue
        r = wt.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            continue
        mi = _monitor(hwnd)
        if mi is None:
            continue
        m = mi.rcMonitor
        proc = _proceso(pid)
        # VRChat tapa su monitor aunque esté en ventana (en VR casi nunca va a pantalla completa)
        if proc != 'vrchat.exe' and not (r.left <= m.left and r.top <= m.top
                                         and r.right >= m.right and r.bottom >= m.bottom):
            continue
        clase = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, clase, 64)
        if clase.value in CLASES_ESCRITORIO:
            continue
        if proc in NO_CUENTAN:
            continue
        tapados.setdefault((m.left, m.top, m.right, m.bottom), proc)
    return tapados


JUEGOS_PESADOS = {'vrchat.exe', 'vrserver.exe', 'vrmonitor.exe', 'vrcompositor.exe'}   # VR: la placa va al 100 %
_pesado = [False]
_cli = [False]


def pids_app_claude() -> set[int]:
    """Procesos de la app de escritorio de Claude (Store o instalador clásico). De paso anota si hay
    Claude Code corriendo en una terminal (en _cli) y si hay VRChat o SteamVR abiertos (en _pesado)."""
    pids = set()
    pesado = cli = False
    for p in psutil.process_iter(['name']):
        try:
            nombre = (p.info['name'] or '').lower()
            if nombre in JUEGOS_PESADOS:
                pesado = True
            if nombre == 'claude.exe':
                ruta = p.exe()
                if rutas.es_app_claude(ruta):
                    pids.add(p.pid)
                elif rutas.es_claude_code_suelto(ruta):
                    cli = True                      # Claude Code en la terminal
        except (psutil.Error, OSError):
            continue
    _pesado[0] = pesado
    _cli[0] = cli
    return pids


def _titulo(hwnd) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ''
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def spotify_tema(ventanas) -> str:
    """«Artista - Tema» si Spotify está sonando ('' en pausa: ahí el título es «Spotify…»)."""
    for hwnd, pid in ventanas:
        if _proceso(pid) == 'spotify.exe':
            t = _titulo(hwnd)
            if ' - ' in t and not t.lower().startswith('spotify'):
                return t
    return ''


def poner_encima(hwnd: int):
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)


# cuando cambia la ventana de adelante, el cangrejito se vuelve a poner arriba enseguida
# (la app de Claude también es «siempre visible»: al tocarla, Windows la ponía encima de él)
WINEVENTPROC = ctypes.WINFUNCTYPE(None, wt.HANDLE, wt.DWORD, wt.HWND, wt.LONG, wt.LONG, wt.DWORD, wt.DWORD)
user32.SetWinEventHook.restype = wt.HANDLE
user32.SetWinEventHook.argtypes = [wt.DWORD, wt.DWORD, wt.HMODULE, WINEVENTPROC, wt.DWORD, wt.DWORD, wt.DWORD]
EVENT_SYSTEM_FOREGROUND = 0x0003


def ventanas():
    """Ventanas de primer nivel visibles (lo que después reciben las otras funciones)."""
    return _ventanas()


def app_claude_abierta(ventanas_, pids: set[int]) -> bool:
    """Claude está abierto: la app tiene alguna ventana con título, o corre Claude Code en una terminal."""
    return _cli[0] or any(pid in pids and user32.GetWindowTextLengthW(h) > 0 for h, pid in ventanas_)


def hay_vr() -> bool:
    """VRChat o SteamVR abiertos (lo anota pids_app_claude)."""
    return _pesado[0]


def enganchar_cambio_ventana(al_cambiar):
    """Llama a al_cambiar() cada vez que cambia la ventana de adelante. Devuelve lo que hay que guardar
    (si se pierde la referencia, Windows llama a un puntero muerto) o None si no se pudo."""
    cb = WINEVENTPROC(lambda *_: al_cambiar())
    gancho = user32.SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND, None, cb, 0, 0, 0)
    return (cb, gancho) if gancho else None


def olvidar_nombres():
    _nombres.clear()
