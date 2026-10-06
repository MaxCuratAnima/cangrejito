"""Reenviador de hooks de Claude Code → cangrejito.

Claude Code lo corre en cada evento (en segundo plano, con `async: true`) y le pasa
el JSON del evento por la entrada estándar. Lo mandamos al cangrejito por HTTP local.
Solo librería estándar y siempre sale con 0: si el cangrejito está cerrado, Claude
ni se entera.
"""
import http.client
import sys

PUERTO = 47833


def _leer_entrada() -> bytes:
    if sys.stdin is not None:
        return sys.stdin.buffer.read()
    # como .exe sin consola, Python no arma sys.stdin aunque Claude le pase el evento por un caño
    import ctypes
    import msvcrt
    import os
    manija = ctypes.windll.kernel32.GetStdHandle(-10)              # STD_INPUT_HANDLE
    if not manija or manija == -1:
        return b''
    with open(msvcrt.open_osfhandle(manija, os.O_RDONLY), 'rb') as f:
        return f.read()


def main():
    try:
        entrada = _leer_entrada()
        if not entrada:
            return
        c = http.client.HTTPConnection('127.0.0.1', PUERTO, timeout=0.5)
        c.request('POST', '/evento', body=entrada, headers={'Content-Type': 'application/json'})
        c.getresponse().read()
        c.close()
    except Exception:
        pass


if __name__ == '__main__':
    main()
    sys.exit(0)
