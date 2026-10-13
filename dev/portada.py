# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Imagen de las poses para el README (docs/poses.png): una selección sobre fondo oscuro.

Uso: python dev/portada.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'dev'))

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

import sprites as S
from galeria import POSES

ELEGIDAS = ['saluda', 'teclea', 'terminal', 'escucha', 'baila', 'lee', 'busca',
            'festeja', 'duerme', 'joystick', 'mate sorbo', 'guitarra gaucho', 'camaro funk', 'hinchada']
ESC, COLS = 4, 7


def main():
    app = QGuiApplication(sys.argv)  # noqa: F841
    poses = dict(POSES)
    cw, ch = S.W * ESC, S.H * ESC + 26
    filas = (len(ELEGIDAS) + COLS - 1) // COLS
    hoja = QImage(COLS * cw, filas * ch, QImage.Format.Format_ARGB32)
    hoja.fill(QColor('#1d1f24'))
    p = QPainter(hoja)
    p.setFont(QFont('Segoe UI', 10))
    for i, nombre in enumerate(ELEGIDAS):
        x, y = (i % COLS) * cw, (i // COLS) * ch
        p.drawImage(QRect(x, y, S.W * ESC, S.H * ESC), S.dibujar(poses[nombre]))
        p.setPen(QColor('#9aa0aa'))
        p.drawText(QRect(x, y + S.H * ESC, cw, 22), Qt.AlignmentFlag.AlignCenter, nombre)
    p.end()
    salida = RAIZ / 'docs' / 'poses.png'
    salida.parent.mkdir(exist_ok=True)
    hoja.save(str(salida))
    print(salida)


if __name__ == '__main__':
    main()
