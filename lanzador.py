"""Lanzador del cangrejito: arranca con Windows, pesa unos pocos MB y cada 3 segundos se fija si
abriste la app de Claude. Cuando la abrís, abre el cangrejito; cuando la cerrás, el cangrejito
se despide y se cierra solo (con su voz y todo), así no ocupa memoria mientras no usás Claude.

Si lo cerrás con «Salir» desde su menú, no vuelve hasta la próxima vez que abras Claude.

Corre con el Python base y sin librerías (pythonw -S), para que sea liviano.
"""
import ctypes
import ctypes.wintypes as wt
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rutas  # noqa: E402

APAGADO = rutas.DATOS / 'apagado.txt'   # lo escribe el cangrejito al elegir «Salir»
PUERTO = 47833


def comando_cangrejo() -> list:
    """Instalado: el mismo .exe. Desde el código: el Python de «python» en config.json (con PySide6 y
    compañía), o si no, el pythonw que está al lado del que corre el lanzador."""
    if rutas.CONGELADO:
        return [sys.executable]
    try:
        python = json.loads((rutas.DATOS / 'config.json').read_text(encoding='utf-8-sig')).get('python')
    except (OSError, ValueError):
        python = None
    return [python or str(Path(sys.executable).with_name('pythonw.exe')), str(AQUI / 'cangrejito.pyw')]

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
ENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
kernel32.OpenProcess.restype = wt.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wt.HANDLE, wt.DWORD, wt.LPWSTR, ctypes.POINTER(wt.DWORD)]


def _ruta(pid: int) -> str:
    h = kernel32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ''
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wt.DWORD(1024)
        return buf.value if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)) else ''
    finally:
        kernel32.CloseHandle(h)


def pids_app_claude() -> set:
    """Procesos de la app de Claude que tienen una ventana visible (no los de Claude Code)."""
    vistos, pids = set(), set()

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            pid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value not in vistos:
                vistos.add(pid.value)
                if rutas.es_app_claude(_ruta(pid.value)):
                    pids.add(pid.value)
        return True

    user32.EnumWindows(ENUM(cb), 0)
    return pids


def cangrejo_andando() -> bool:
    try:
        with socket.create_connection(('127.0.0.1', PUERTO), timeout=0.3):
            return True
    except OSError:
        return False


def apagado_por_vos(pids_app: set) -> bool:
    """«Salir» vale hasta que cierres esa app de Claude."""
    try:
        guardados = {int(x) for x in APAGADO.read_text().split()}
    except (OSError, ValueError):
        return False
    if guardados & pids_app:
        return True
    APAGADO.unlink(missing_ok=True)
    return False


def main():
    kernel32.CreateMutexW(None, False, 'Local\\cangrejito-lanzador')
    if kernel32.GetLastError() == 183:                     # ERROR_ALREADY_EXISTS
        return
    try:
        rutas.preparar()           # trae la config de una instalación vieja (ahí puede estar «python»)
    except OSError:
        pass
    ultimo = 0.0
    while True:
        try:
            pids = pids_app_claude()
            if pids and not apagado_por_vos(pids) and time.monotonic() - ultimo > 20 and not cangrejo_andando():
                ultimo = time.monotonic()
                subprocess.Popen(comando_cangrejo(), cwd=str(AQUI),
                                 creationflags=0x08000000 | 0x00000008)              # sin ventana, suelto
        except Exception:
            pass
        time.sleep(3)


if __name__ == '__main__':
    main()
