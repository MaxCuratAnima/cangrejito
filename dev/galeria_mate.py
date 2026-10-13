"""Las fases del mate (parado y laburando con la netbook) → docs/mate.png.  Uso: python dev/galeria_mate.py"""
import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

import config
import mascota as M
import sprites as S

app = QApplication([])


class Voz:
    hablando, estado, al_terminar = False, 'lista', None
    def nivel(self): return 0.0
    def decir(self, *a, **k): pass
    def callar(self): pass


cfg = type('C', (dict,), {'guardar': lambda self: None})(dict(config.POR_DEFECTO, silencio=True))
m = M.Mascota(cfg, Voz())
ag = app.primaryScreen().availableGeometry()
m.modo = 'suelo'
m.px, m.py = ag.center().x(), m._piso(ag)
filas = []

# 1) parado con el mate: sostiene y da sorbos
m.base, m.paseo, m.mate_ini = 'libre', 'mate', None
fila = []
for t in (0.5, 1.5, 2.5, 3.5, 5.0, 7.5, 8.5, 9.8):
    m.t0 = time.monotonic() - t
    m.alfas = {}
    for _ in range(8):
        pose = m._pose(m.t0 + t)
    fila.append(S.dibujar(pose))
filas.append(fila)

# 2) laburando: cebar, sorbo, mano, sorbo, mano, dejado
for bebida in ('mate', 'cafe'):
    m.cfg['bebida'] = bebida
    m.base, m.paseo = 'teclear', 'quieto'
    fila = []
    for u in (1.0, 2.5, 4.0, 6.0, 11.0, 14.0, 17.5, 21.0):
        ahora = time.monotonic()
        m.t0 = ahora - 20
        m.mate_ini = ahora - u
        m.alfas = {}
        for _ in range(8):
            pose = m._pose(ahora)
        fila.append(S.dibujar(pose))
    filas.append(fila)

esc = 3
ancho, alto = S.W * esc, S.H * esc
out = QImage(8 * (ancho + 6) + 6, len(filas) * (alto + 6) + 6, QImage.Format.Format_ARGB32)
out.fill(QColor('#2B2D31'))
p = QPainter(out)
for j, fila in enumerate(filas):
    for i, img in enumerate(fila):
        p.drawImage(6 + i * (ancho + 6), 6 + j * (alto + 6), img.scaled(ancho, alto))
p.end()
out.save(os.path.join(os.path.dirname(__file__), '..', 'docs', 'mate.png'))
print('ok')
