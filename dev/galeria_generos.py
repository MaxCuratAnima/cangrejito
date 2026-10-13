"""Cuadros de cada baile por género (el paseo de cada uno, en varios instantes) → docs/generos.png.
Uso: python dev/galeria_generos.py [paseo ...]   (sin argumentos: los nuevos)"""
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
m.modo, m.base = 'suelo', 'libre'
m.px, m.py = ag.center().x(), m._piso(ag)
PASEOS = sys.argv[1:] or ['chacarera', 'robot', 'disco', 'reggae', 'metal', 'director']
GEN = {p: g for g, ps in M.GENERO_PASEO.items() for p in ps}
TIEMPOS = ((0.3, 1.0, 2.0, 3.0, 3.2, 3.4, 4.5, 6.5) if set(PASEOS) & set(M.GRACIAS)
           else (0.2, 0.6, 1.0, 1.4, 1.8, 2.6, 3.4, 4.2))
filas = []
for paseo in PASEOS:
    m.paseo, m.musica, m.genero = paseo, True, GEN.get(paseo, '')
    m.alfas = {}
    m.prox_nota = 1e18
    fila = []
    for t in TIEMPOS:
        m.t0 = time.monotonic() - t
        m.paseo_fin = m.t0 + M.GRACIAS.get(paseo, 99.0)
        for _ in range(8):                      # deja que los accesorios aparezcan (fundido)
            pose = m._pose(m.t0 + t)
        fila.append(S.dibujar(pose))
    filas.append(fila)
esc = 3
ancho, alto = S.W * esc, S.H * esc
out = QImage(len(TIEMPOS) * (ancho + 6) + 6, len(filas) * (alto + 6) + 6, QImage.Format.Format_ARGB32)
out.fill(QColor('#2B2D31'))
p = QPainter(out)
for j, fila in enumerate(filas):
    for i, img in enumerate(fila):
        p.drawImage(6 + i * (ancho + 6), 6 + j * (alto + 6), img.scaled(ancho, alto))
p.end()
destino = os.path.join(os.path.dirname(__file__), '..', 'docs', 'generos.png')
out.save(destino)
print('ok', out.width(), out.height())
