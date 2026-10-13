"""Simula a los ayudantes (reloj falso) y arma docs/ayudantes.png con varios cuadros de la animación."""
import os
import random
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

import ayudantes as A
import sprites as S

app = QApplication([])
random.seed(7)
reloj = [1000.0]
A.time.monotonic = lambda: reloj[0]


class Voz:
    hablando = False


class Mascota:
    voz, atencion = Voz(), None
    def isVisible(self): return True
    def geometry(self): return QRect(0, 0, S.W * 5, S.H * 5)
    def subir(self): pass


def armar(cuantos, listos):
    A.time.monotonic = lambda: reloj[0]
    a = A.Ayudantes({'escala': 5}, Mascota())
    a.m.atencion = None
    for i in range(cuantos):
        a.nuevo(f'a{i}', 's')
    return a


def cuadro(a, habla=False):
    a.m.voz.hablando = habla
    marg = a.marg
    img = QImage(S.W + 2 * marg, S.H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor('#2B2D31'))
    q = QPainter(img)
    q.drawImage(marg, 0, S.dibujar(S.Pose(t=reloj[0] % 100)))
    ahora = reloj[0]
    for v in sorted(a.agentes.values(), key=lambda v: v['y']):
        e = a._estado(v, ahora - a.t0, ahora, habla)
        A._mini(q, v['x'], v['y'], e, ahora - a.t0, v['alfa'])
    q.end()
    return img.scaled(img.width() * 4, img.height() * 4)


def avanzar(a, seg):
    for _ in range(int(seg / 0.1)):
        reloj[0] += 0.1
        a._ult = reloj[0] - 0.1
        a._tick()


filas = []
# cuadros de un recorrido: caen, miran el celular, caminan, saludan, hablan, terminan
a = armar(5, 0)
for seg, habla in ((0.25, False), (0.5, False), (3, False), (3, False), (3, True), (3, False)):
    avanzar(a, seg)
    filas.append(cuadro(a, habla))
for k in (0, 1, 2):
    a.listo(f'a{k}')
for seg in (0.4, 1.0, 3.0):
    avanzar(a, seg)
    filas.append(cuadro(a))
ancho = max(i.width() for i in filas)
cols = 3
out = QImage(cols * (ancho + 16) + 16, ((len(filas) + cols - 1) // cols) * (filas[0].height() + 16) + 16,
             QImage.Format.Format_ARGB32)
out.fill(QColor('#1B1C1F'))
p = QPainter(out)
for n, im in enumerate(filas):
    p.drawImage(16 + (n % cols) * (ancho + 16), 16 + (n // cols) * (im.height() + 16), im)
p.end()
os.makedirs('docs', exist_ok=True)
out.save('docs/ayudantes.png')
print('ok', out.width(), out.height(), len(filas))
