"""Fuerza cada escena entre los mini-cangrejos (reloj falso) y arma docs/escenas.png con cuadros de cada una."""
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
reloj = [1000.0]
A.time.monotonic = lambda: reloj[0]
original = random.choice
AGENTES = int(os.environ.get('AGENTES', 7))
PASOS = [float(x) for x in os.environ.get('PASOS', '0.1,2,2,2,2').split(',')]
ESCENAS = os.environ.get('ESCENAS', 'choque,torre,ola,saludo').split(',')
SALIDA = os.environ.get('SALIDA', 'escenas.png')


class Voz:
    hablando = False


class Mascota:
    voz, atencion, mom = Voz(), None, None
    momentos = []
    def isVisible(self): return True
    def geometry(self): return QRect(0, 0, S.W * 5, S.H * 5)
    def subir(self): pass
    def momento(self, nombre, dur): self.momentos.append(nombre)


def cuadro(a):
    marg = a.marg
    img = QImage(S.W + 2 * marg, S.H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(QColor('#2B2D31'))
    q = QPainter(img)
    q.drawImage(marg, 0, S.dibujar(S.Pose(t=reloj[0] % 100)))
    q.drawImage(0, 0, a._dibujar(reloj[0]))
    q.end()
    zoom = 8 if AGENTES <= 3 else 4
    return img.scaled(img.width() * zoom, img.height() * zoom)


def avanzar(a, seg):
    for _ in range(int(round(seg / 0.1))):
        reloj[0] += 0.1
        a._ult = reloj[0] - 0.1
        a._tick()


def escena(tipo, con_grande=None):
    random.seed(11)
    a = A.Ayudantes({'escala': 5}, Mascota())
    for i in range(AGENTES):
        a.nuevo(f'a{i}', 's')
    avanzar(a, 5)
    a.prox_saludo = 1e9
    marcas = []

    def elegir(seq):
        if tipo in seq:
            return tipo
        if con_grande and con_grande in seq:
            return con_grande
        return original(seq)
    A.random.choice = elegir
    a.prox_saludo = 0
    cuadros = []
    for seg in PASOS:
        avanzar(a, seg)
        a.prox_saludo = 1e9
        cuadros.append(cuadro(a))
    A.random.choice = original
    return cuadros


filas = []
for tipo in ESCENAS:
    filas += escena(tipo, 'choque' if tipo == 'saludo' else None)
cols = len(PASOS)
ancho = max(i.width() for i in filas)
alto = max(i.height() for i in filas)
out = QImage(cols * (ancho + 12) + 12, ((len(filas) + cols - 1) // cols) * (alto + 12) + 12, QImage.Format.Format_ARGB32)
out.fill(QColor('#1B1C1F'))
p = QPainter(out)
for n, im in enumerate(filas):
    p.drawImage(12 + (n % cols) * (ancho + 12), 12 + (n // cols) * (alto + 12), im)
p.end()
destino = os.path.join(os.path.dirname(__file__), '..', 'docs', SALIDA)
out.save(destino)
print('ok', out.width(), out.height(), len(filas))
