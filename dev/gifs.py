# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""GIF animados para el README (docs/*.gif), grabados con el mismo código de la mascota.

Corre sin pantalla y con un reloj simulado, así cada escena sale fluida y siempre igual.
Uso: python dev/gifs.py          (necesita Pillow: pip install pillow)
"""
import os
import sys
import time as _time
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PIL import Image  # noqa: E402
from PySide6.QtCore import QRect  # noqa: E402
from PySide6.QtGui import QColor, QImage, QLinearGradient, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import config  # noqa: E402
import globo as G  # noqa: E402
import mascota as M  # noqa: E402

SALIDA = RAIZ / 'docs'
FPS = 12


class Reloj:
    """Reemplaza al módulo time en la mascota y el globo: el tiempo avanza solo cuando grabamos."""
    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t

    def localtime(self, *a):
        return _time.localtime(*a)


RELOJ = Reloj()
M.time = RELOJ
G.time = RELOJ


class VozMuda:
    hablando, estado, al_terminar = False, 'lista', None

    def nivel(self):
        return 0.0


def nueva(app) -> M.Mascota:
    cfg = type('C', (dict,), {'guardar': lambda self: None})(dict(config.POR_DEFECTO, silencio=True))
    m = M.Mascota(cfg, VozMuda())
    m.t0 = m._ult = RELOJ.t
    m.prox_parpadeo = RELOJ.t + 2
    m.prox_mate = RELOJ.t + 99999
    ag = app.primaryScreen().availableGeometry()
    m.modo, m.base = 'suelo', 'libre'
    m.px, m.py = ag.center().x() - M.S.W * m.E / 2, m._piso(ag)
    m.paseo, m.paseo_fin = 'quieto', RELOJ.t + 99999
    m.move(round(m.px), round(m.py))
    m.show()
    return m


def fondo(w: int, h: int, barra: int) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, QColor('#2b2f3a'))
    g.setColorAt(1, QColor('#1f2229'))
    p.fillRect(0, 0, w, h, g)
    p.fillRect(0, h - barra, w, barra, QColor('#15171c'))          # la barra de tareas
    p.fillRect(0, h - barra, w, 1, QColor('#3a3f4c'))
    p.end()
    return img


def grabar(nombre: str, m: M.Mascota, segundos: float, ancho: int, alto: int = 250, guion=None,
           velocidad: float = 1.0, centro_x=None):
    """Graba la escena: cada cuadro avanza el reloj, corre la mascota y pega ventana + globo."""
    ag = QApplication.primaryScreen().availableGeometry()
    barra = 34
    origen_y = ag.bottom() + 1 - (alto - barra)
    cx = centro_x if centro_x is not None else m.px + M.S.W * m.E / 2
    origen_x = round(cx - ancho / 2)
    cuadros, pasos = [], int(segundos * FPS)
    for i in range(pasos):
        RELOJ.t += velocidad / FPS
        if guion:
            guion(i / FPS * velocidad, m)
        m._tick()
        img = fondo(ancho, alto, barra)
        p = QPainter(img)
        p.drawPixmap(m.x() - origen_x, m.y() - origen_y, m.grab())
        if m.globo.isVisible() and m.globo.alfa > 0.01:
            p.setOpacity(m.globo.alfa)
            p.drawPixmap(m.globo.x() - origen_x, m.globo.y() - origen_y, m.globo.grab())
        p.end()
        cuadros.append(_a_pil(img))
    m.globo.hide()
    m.hide()
    destino = SALIDA / f'{nombre}.gif'
    cuadros[0].save(destino, save_all=True, append_images=cuadros[1:], duration=round(1000 / FPS), loop=0,
                    optimize=True, disposal=2)
    print(f'{destino.name}: {len(cuadros)} cuadros, {destino.stat().st_size // 1024} KB')


def _a_pil(img: QImage) -> Image.Image:
    img = img.convertToFormat(QImage.Format.Format_RGB888)
    pil = Image.frombytes('RGB', (img.width(), img.height()), bytes(img.constBits()), 'raw', 'RGB',
                          img.bytesPerLine())
    return pil.convert('P', palette=Image.Palette.ADAPTIVE, colors=128)


def _fuentes():
    """Sin pantalla, Qt no ve las fuentes del sistema: le cargo las del globo a mano."""
    from PySide6.QtGui import QFontDatabase
    carpetas = [Path(os.environ.get('WINDIR', 'C:/Windows')) / 'Fonts', Path('/usr/share/fonts')]
    for nombre in ('segoeui.ttf', 'seguisb.ttf', 'segoeuib.ttf', 'NotoSans-Regular.ttf', 'DejaVuSans.ttf'):
        for c in carpetas:
            for f in ([c / nombre] if (c / nombre).exists() else list(c.rglob(nombre)) if c.exists() else []):
                QFontDatabase.addApplicationFont(str(f))
                break


def main():
    app = QApplication(sys.argv)
    _fuentes()
    SALIDA.mkdir(exist_ok=True)

    # 1. trabajando: lo que narra mientras Claude labura
    m = nueva(app)
    textos = [(0.0, 'teclear', 'Edito sprites.py: le agrego humo a las ruedas'),
              (3.2, 'terminal', 'Corro las pruebas para ver que todo ande'),
              (6.4, 'buscar', 'Busco dónde se dibuja el auto')]

    def guion_trabajo(t, m):
        for ini, act, texto in textos:
            if abs(t - ini) < 0.5 / FPS:
                m.actividad(act)
                m.globo.mostrar(texto, 'Proyecto cangrejito', 2.8)
    grabar('trabajando', m, 9.5, 420, guion=guion_trabajo)

    # 2. el mate mientras labura (a velocidad doble)
    m = nueva(app)
    m.actividad('teclear')
    m.mate_ini = RELOJ.t + 0.3
    grabar('mate', m, 11, 300, velocidad=2.0)

    # 3. el Camaro con phonk: de punta a punta, derrapando
    m = nueva(app)
    m.musica, m.funk = True, True
    m.paseo, m.paseo_fin, m.dir = 'auto', RELOJ.t + 99999, 1
    ag = app.primaryScreen().availableGeometry()
    grabar('camaro', m, 9, ag.width(), centro_x=ag.center().x())

    # 4. folklore: guitarra criolla y ropa de gaucho
    m = nueva(app)
    m.musica, m.guitarra = True, True
    m.paseo = 'guitarra'
    grabar('guitarra', m, 4, 300)

    # 5. mientras jugás en el otro monitor
    m = nueva(app)
    m.tapados = {'JUEGO'}
    m._hacia_juego = lambda: (1, 0)
    escenas = [(0.0, 'joystick'), (3.0, 'pochoclos'), (6.0, 'hinchada')]

    def guion_juego(t, m):
        for ini, paseo in escenas:
            if abs(t - ini) < 0.5 / FPS:
                m.paseo, m.paseo_fin = paseo, RELOJ.t + 99999
    grabar('jugando', m, 8.5, 300, guion=guion_juego)

    # 6. bailando con Spotify
    m = nueva(app)
    m.musica = True
    m.momento('bailar', 30)
    grabar('baile', m, 4, 300)


if __name__ == '__main__':
    main()
