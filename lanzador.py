# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Lanzador del cangrejito: arranca con la sesión, pesa unos pocos MB y cada 3 segundos se fija si
abriste Claude. Cuando lo abrís, abre el cangrejito; cuando lo cerrás, el cangrejito se despide y se
cierra solo (con su voz y todo), así no ocupa memoria mientras no usás Claude.

«Claude abierto» es la app de escritorio en Windows, o Claude Code corriendo en Linux (donde no hay
app). Con «siempre_visible» en la config, abre el cangrejito aunque Claude esté cerrado.
Si lo cerrás con «Salir» desde su menú, no vuelve hasta la próxima vez que abras Claude.

Corre con el Python base y sin librerías (pythonw -S), para que sea liviano.
"""
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


def _config() -> dict:
    try:
        return json.loads((rutas.DATOS / 'config.json').read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}


def comando_cangrejo() -> list:
    """Instalado: el mismo programa. Desde el código: el Python de «python» en config.json (con PySide6
    y compañía), o si no, el que está al lado del que corre el lanzador."""
    if rutas.CONGELADO:
        return [sys.executable]
    python = _config().get('python')
    if not python:
        python = str(Path(sys.executable).with_name('pythonw.exe')) if rutas.WINDOWS else sys.executable
    return [python, str(AQUI / 'cangrejito.pyw')]


if rutas.WINDOWS:
    import ctypes
    import ctypes.wintypes as wt

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
        return pids or pids_claude_code()

    psapi = ctypes.windll.psapi

    def pids_claude_code() -> set:
        """Claude Code corriendo en una terminal (el claude.exe que no es la app de escritorio)."""
        lista = (wt.DWORD * 4096)()
        usados = wt.DWORD()
        if not psapi.EnumProcesses(lista, ctypes.sizeof(lista), ctypes.byref(usados)):
            return set()
        out = set()
        for pid in lista[:usados.value // 4]:
            if rutas.es_claude_code_suelto(_ruta(pid)):
                out.add(pid)
        return out

    def unica_instancia() -> bool:
        kernel32.CreateMutexW(None, False, 'Local\\cangrejito-lanzador')
        return kernel32.GetLastError() != 183                  # ERROR_ALREADY_EXISTS

    def lanzar(comando: list):
        subprocess.Popen(comando, cwd=str(AQUI), creationflags=0x08000000 | 0x00000008)  # sin ventana, suelto

else:
    def pids_app_claude() -> set:
        """Procesos de Claude Code (en Linux no hay app de escritorio): se leen de /proc."""
        pids = set()
        for d in Path('/proc').iterdir():
            if d.name.isdigit():
                try:
                    if (d / 'comm').read_text().strip() == 'claude':
                        pids.add(int(d.name))
                except OSError:
                    continue
        return pids

    _candado = []

    def unica_instancia() -> bool:
        import fcntl
        rutas.DATOS.mkdir(parents=True, exist_ok=True)
        f = open(rutas.DATOS / 'lanzador.lock', 'w')
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        _candado.append(f)                                      # mientras viva el proceso, queda tomado
        return True

    def lanzar(comando: list):
        subprocess.Popen(comando, cwd=str(AQUI), start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def cangrejo_andando() -> bool:
    try:
        with socket.create_connection(('127.0.0.1', PUERTO), timeout=0.3):
            return True
    except OSError:
        return False


def apagado_por_vos(pids_app: set) -> bool:
    """«Salir» vale hasta que cierres esa sesión de Claude."""
    try:
        guardados = {int(x) for x in APAGADO.read_text().split()}
    except (OSError, ValueError):
        return False
    if guardados & pids_app:
        return True
    APAGADO.unlink(missing_ok=True)
    return False


def main():
    if not unica_instancia():
        return
    try:
        rutas.preparar()           # trae la config de una instalación vieja (ahí puede estar «python»)
        APAGADO.unlink(missing_ok=True)     # sesión nueva: un «Salir» de antes ya no vale
    except OSError:
        pass
    ultimo = 0.0
    while True:
        try:
            pids = pids_app_claude()
            quiere = bool(pids) or bool(_config().get('siempre_visible'))
            if (quiere and not apagado_por_vos(pids or {0}) and time.monotonic() - ultimo > 20
                    and not cangrejo_andando()):
                ultimo = time.monotonic()
                lanzar(comando_cangrejo())
        except Exception:
            pass
        time.sleep(3)


if __name__ == '__main__':
    main()
