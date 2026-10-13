# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""¿Quién está grabando del micrófono ahora mismo? (sesiones de captura de audio de Windows).

Se usa para saber si le estás dictando a Claude (su dictado, Wispr Flow o el de Windows).
El registro de privacidad de Windows no anota el dictado de Claude, por eso se pregunta directo
al sistema de audio: cada programa que graba abre una «sesión» activa en el micrófono.
"""
from __future__ import annotations

import psutil
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioSessionControl2, IAudioSessionManager2

import rutas

CAPTURA = 1          # eCapture
ACTIVOS = 1          # DEVICE_STATE_ACTIVE
SESION_ACTIVA = 1    # AudioSessionStateActive


def procesos_grabando() -> set[str]:
    """Nombres (en minúscula) de los programas que están grabando de algún micrófono."""
    nombres = set()
    enum = AudioUtilities.GetDeviceEnumerator()
    dispositivos = enum.EnumAudioEndpoints(CAPTURA, ACTIVOS)
    for i in range(dispositivos.GetCount()):
        try:
            disp = dispositivos.Item(i)
            # QueryInterface y no ctypes.cast: el cast dejaba mal la cuenta de referencias COM
            # y el proceso se caía (0xc0000005) cuando había alguien grabando
            gestor = disp.Activate(IAudioSessionManager2._iid_, CLSCTX_ALL, None)
            gestor = gestor.QueryInterface(IAudioSessionManager2)
            sesiones = gestor.GetSessionEnumerator()
            for j in range(sesiones.GetCount()):
                ctl = sesiones.GetSession(j)
                if ctl.GetState() != SESION_ACTIVA:
                    continue
                pid = ctl.QueryInterface(IAudioSessionControl2).GetProcessId()
                try:
                    nombres.add(f'{psutil.Process(pid).name().lower()}|{psutil.Process(pid).exe().lower()}')
                except (psutil.Error, OSError):
                    pass
        except Exception:
            continue
    return nombres


def dictando(nombres: set[str]) -> bool:
    """Claude (la app, no Claude Code), Wispr Flow o el dictado de Windows están grabando."""
    for n in nombres:
        nombre, ruta = n.split('|', 1)
        if nombre == 'claude.exe' and rutas.es_app_claude(ruta):
            return True
        if 'wispr' in nombre or 'wispr' in ruta:
            return True
        if nombre in ('textinputhost.exe', 'voiceaccess.exe'):
            return True
    return False


def servir():
    """Modo proceso aparte: escribe 1 (dictando) o 0 cada 0,7 s. Si algo de COM se rompe,
    se cae este proceso y no el cangrejito."""
    import sys
    import time
    import os
    padre = os.getppid()
    ultimo = None
    salida = sys.stdout
    if salida is None:
        # como .exe sin consola, Python no arma sys.stdout aunque el cangrejito le pase un caño: lo abro a mano
        import ctypes
        import msvcrt
        manija = ctypes.windll.kernel32.GetStdHandle(-11)          # STD_OUTPUT_HANDLE
        salida = open(msvcrt.open_osfhandle(manija, os.O_WRONLY), 'w', buffering=1)
    sys.stdout = salida
    while True:
        if not psutil.pid_exists(padre):          # el cangrejito se cerró: me voy con él
            return
        try:
            estado = '1' if dictando(procesos_grabando()) else '0'
        except Exception:
            estado = '0'
        if estado != ultimo:
            sys.stdout.write(estado + '\n')
            sys.stdout.flush()
            ultimo = estado
        time.sleep(0.7)


if __name__ == '__main__':
    import sys
    import time
    if '--servir' in sys.argv:
        servir()
    for _ in range(20):
        g = procesos_grabando()
        print(time.strftime('%H:%M:%S'), 'dictando' if dictando(g) else '-', sorted(x.split('|')[0] for x in g))
        time.sleep(1)
