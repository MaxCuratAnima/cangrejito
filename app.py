# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Entrada del Cangrejito.exe (PyInstaller): un solo programa con varios modos.

  Cangrejito.exe                  la mascota
  Cangrejito.exe --lanzador       arranca con Windows y abre la mascota cuando abrís Claude
  Cangrejito.exe --avisar         lo llaman los hooks de Claude Code (reenvía el evento)
  Cangrejito.exe --microfono      proceso aparte que mira si le estás dictando a Claude
  Cangrejito.exe --instalar-hooks [--narracion] [--siempre-visible]
  Cangrejito.exe --quitar-hooks

Los modos livianos se resuelven antes de importar PySide6, así arrancan rápido.
"""
import sys


def main():
    args = sys.argv[1:]
    if '--avisar' in args:
        import avisar
        avisar.main()
        sys.exit(0)
    if '--lanzador' in args:
        import lanzador
        lanzador.main()
        return
    if '--microfono' in args:
        import microfono
        microfono.servir()
        return
    if '--instalar-hooks' in args or '--quitar-hooks' in args:
        import instalar_claude
        sys.exit(instalar_claude.desde_consola(args))
    from cangrejito_app import main as mascota
    mascota()


if __name__ == '__main__':
    main()
