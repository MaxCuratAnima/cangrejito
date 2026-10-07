# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Arma docs/outfits.png: la ropa de cada género musical argentino y de las fechas patrias y culturales.

    python dev/outfits.py [SALIDA.png]
"""
import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import sprites as S  # noqa: E402
from sprites import Pose  # noqa: E402

SONRIE = dict(ojos='feliz', boca_forma='sonrisa')
CUADROS = [
    ('Folklore', Pose(patas='sentado', cuerpo_y=2, brazos=('sostener', 'teclado'), ojos='cerrados',
                      boca_forma='o', accesorios={'gaucho': 1, 'guitarra': 1})),
    ('Tango', Pose(patas='sentado', brazos=('sostener', 'sostener'), fuelle=7, ojos='cerrados', cejas='preocupado',
                   accesorios={'funyi': 1, 'panuelo_blanco': 1, 'bandoneon': 1})),
    ('Cuarteto', Pose(brazos=('baile', 'festejo'), fase_brazos=1, patas='caminar', fase=1, t=0.3, brillo=True,
                      accesorios={'lentejuelas': 1}, **SONRIE)),
    ('Cumbia', Pose(brazos=('arriba', 'teclado'), boca_forma='o', ojos='feliz',
                    accesorios={'gorrita': 1, 'camiseta': 1, 'teclado_musical': 1})),
    ('Rock nacional', Pose(brazos=('sostener', 'teclado'), cuerpo_y=2, boca_forma='o',
                           accesorios={'campera': 1, 'lentes': 1, 'electrica': 1})),
    ('Trap', Pose(brazos=('baile', 'acercar'), fase_brazos=1, boca_forma='o',
                  accesorios={'gorra': 1, 'cadena': 1, 'lentes': 1, 'microfono': 1})),
    ('25 de Mayo y 9 de Julio', Pose(accesorios={'galera': 1, 'escarapela': 1}, **SONRIE)),
    ('17 de Agosto', Pose(brazos=('reposo', 'rascar'), brillo=True, accesorios={'bicornio': 1, 'escarapela': 1})),
    ('17 de Junio (Güemes)', Pose(accesorios={'poncho': 1, 'escarapela': 1}, **SONRIE)),
    ('Día del Maestro', Pose(accesorios={'guardapolvo': 1}, **SONRIE)),
    ('29: ñoquis', Pose(patas='sentado', cuerpo_y=2, brazos=('reposo', 'acercar'), mirar=(0, 1),
                        accesorios={'noquis': 1, 'tenedor': 1})),
    ('Navidad', Pose(accesorios={'gorro_navidad': 1}, **SONRIE)),
    ('Primavera', Pose(accesorios={'flor': 1}, rubor=True, **SONRIE)),
    ('Café en vez de mate', Pose(brazos=('reposo', 'acercar'), ojos='feliz', rubor=True, bebida='cafe',
                                 accesorios={'mate_boca': 1})),
    ('Hinchada', Pose(brazos=('festejo', 'arriba'), bandera='argentina', accesorios={'bandera': 1},
                                **SONRIE)),
]


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    for carpeta in (Path('C:/Windows/Fonts'), Path('/usr/share/fonts')):     # sin pantalla, Qt no las ve solo
        for nombre in ('segoeuib.ttf', 'segoeui.ttf', 'NotoSans-Bold.ttf', 'DejaVuSans-Bold.ttf'):
            for f in (carpeta.rglob(nombre) if carpeta.exists() else ()):
                QFontDatabase.addApplicationFont(str(f))
    salida = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / 'docs' / 'outfits.png'
    E, cols = 6, 5
    celda_w, celda_h = S.W * E, S.H * E + 40
    filas = (len(CUADROS) + cols - 1) // cols + 1
    img = QImage(cols * celda_w, filas * celda_h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor('#F6EFE6'))
    p = QPainter(img)
    fuente = QFont()
    fuente.setFamilies(['Segoe UI', 'Noto Sans', 'DejaVu Sans'])
    fuente.setPixelSize(19)
    fuente.setBold(True)
    p.setFont(fuente)
    p.setPen(QColor('#3A2A22'))
    for i, (titulo, pose) in enumerate(CUADROS):
        x, y = (i % cols) * celda_w, (i // cols) * celda_h
        dibujo = S.dibujar(pose)
        p.drawImage(QRect(x, y, S.W * E, S.H * E), dibujo)
        p.drawText(QRect(x, y + S.H * E, celda_w, 36), Qt.AlignmentFlag.AlignCenter, titulo)
    # el mástil del Día de la Bandera, con el cangrejito saludando al lado
    y = (filas - 1) * celda_h
    p.drawImage(QRect(40, y, S.W * E, S.H * E), S.dibujar(Pose(brazos=('reposo', 'rascar'), mirar=(1, -1),
                                                                brillo=True, accesorios={'escarapela': 1})))
    p.drawImage(QRect(40 + 30 * E, y + (S.H - S.MH) * E + 2 * E, S.MW * E, S.MH * E), S.dibujar_mastil(1.0))
    p.drawText(QRect(40 + 48 * E, y, 3 * celda_w, S.H * E), Qt.AlignmentFlag.AlignVCenter,
               '20 de Junio: iza la bandera y la saluda.\nEl mástil se agarra con el mouse y se lleva a otro lado.')
    p.end()
    salida.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(salida))
    print(salida)


if __name__ == '__main__':
    main()
