# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Dibujo del cangrejito: pixel-art propio al estilo de Clawd, hecho en código.

Todo se pinta en una grilla chica (1 unidad = 1 píxel de un QImage de W×H) y la
ventana la agranda sin suavizar. Las coordenadas «del cangrejo» (34×29) se corren
(OX, OY) dentro del lienzo para dejar lugar arriba a los accesorios.

Mapa del cangrejo (coordenadas del cangrejo):
  cuerpo 16×10 en (9, 16) · ojos 2×3 en (12, 19) y (20, 19) · patas en x 10, 13, 20, 23
  (filas 26 a 28) · hombros en y 20 · piso = y 29.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter

W, H = 40, 45          # lienzo, en unidades
OX, OY = 3, 14         # dónde cae el cangrejo dentro del lienzo
PIES = OY + 29         # borde de abajo de las patas (unidades del lienzo)
CABEZA = (OX + 17, OY + 16)   # arriba al medio del cuerpo


def _c(hexa: str, a: int = 255) -> QColor:
    c = QColor(hexa)
    c.setAlpha(a)
    return c


PALETA = {
    'o': _c('#D97757'),   # naranja Claude
    'O': _c('#B4573A'),   # naranja oscuro (patas, sombra de abajo)
    'h': _c('#E6906F'),   # naranja claro (brillo de arriba)
    'k': _c('#1E1310'),   # ojos
    'w': _c('#FFFFFF'),
    'g': _c('#B9B9C4'),   # gris claro (teclas)
    'G': _c('#4A4A55'),   # gris oscuro
    'K': _c('#15151A'),   # pantalla
    'b': _c('#BFE3FF', 110),  # vidrio de la lupa
    'B': _c('#3D7BD9'),   # agua del mundo
    'n': _c('#4CC06A'),   # verde
    'y': _c('#FFD447'),   # amarillo
    'r': _c('#FF5C7A'),   # corazón
    'R': _c('#FF7F9A', 150),  # rubor
    'p': _c('#FFF4E0'),   # papel
    'm': _c('#8A5A3C'),   # marrón
    'c': _c('#7FD4FF'),   # gota de sudor
    'x': _c('#E0364B'),   # rojo de la X
    'C': _c('#74ACDF'),   # celeste de la bandera
    'M': _c('#C98B4F'),   # madera clara (guitarra)
    'a': _c('#FF9F1C'),   # naranja (bandera del orgullo)
    'v': _c('#9B5DE5'),   # violeta
    'P': _c('#8E1B2E'),   # bordó (poncho salteño)
    'Y': _c('#E8B33A'),   # dorado (cadena, sol)
    'f': _c('#FF8FB1'),   # rosa (flor)
    'e': _c('#2E8B57'),   # verde oscuro (ruda)
    's': _c('#D8D8E0'),   # plateado (plato, micrófono)
    'L': _c('#5B3A29'),   # café
    't': _c('#C77B30'),   # té
    'q': _c('#F2D68A'),   # ñoquis
    'Z': _c('#C8352E'),   # salsa de tomate
    'u': _c('#1F3A93'),   # azul oscuro (gorrita, moño)
}
CONTORNO = _c('#1E1310', 95)

# ---------------------------------------------------------------- grillas
GARRAS = {
    'arriba':  ['o..o', 'o..o', 'oooo', '.oo.'],
    'abajo':   ['.oo.', 'oooo', 'o..o', 'o..o'],
    'izq':     ['ooo.', '..oo', '..oo', 'ooo.'],
    'der':     ['.ooo', 'oo..', 'oo..', '.ooo'],
    'cerrada': ['.oo.', 'oooo', 'oooo', '.oo.'],
}
ESPEJO_GARRA = {'izq': 'der', 'der': 'izq'}
# cuando la pinza pasa por delante del cuerpo va más oscura, si no se pierde
GARRAS_DELANTE = {k: [f.replace('o', 'O') for f in v] for k, v in GARRAS.items()}

LIBRO = [
    '.pppppmmppppp.',
    'pGGGGpmmpGGGGp',
    'ppppppmmpppppp',
    'pGGGppmmpGGGpp',
    'ppppppmmpppppp',
    'mmmmmmmmmmmmmm',
]
LUPA = [
    '...GGGG..',
    '..GbbbbG.',
    '.GbwbbbbG',
    '.GbbbbbbG',
    '.GbbbbbbG',
    '..GbbbbG.',
    '.m.GGGG..',
    'mm.......',
]
MUNDO_MASCARA = ['..###..', '.#####.', '#######', '#######', '#######', '.#####.', '..###..']
MUNDO_TEXTURA = [
    'BBBnnBBBBBBnBB',
    'BnnnnnBBBBnnnB',
    'BBnnnBBBBnnnnB',
    'BBBnBBBBBBnnBB',
    'BBBBnnBBBBBnBB',
    'BBBnnnBBBBBBBB',
    'BBBBnBBBBBBBBB',
]
EXCLAMACION = ['yy', 'yy', 'yy', 'yy', 'yy', '..', 'yy']
PREGUNTA = ['.yyy.', 'y...y', '....y', '..yy.', '..y..', '.....', '..y..']
SUDOR = ['.c', 'cc', 'cc']
MINI = [  # el logo de Claude Code, tal cual (18×5)
    '...oooooooooooo...',
    '...ookoooooooko...',
    '.oooooooooooooooo.',
    '...oooooooooooo...',
    '....O.O....O.O....',
]
NETBOOK = [   # vista de atrás: tapa con el logo de Claude y la base
    '..GGGGGGGGGGGGGG..',
    '..GGGGGGGoGGGGGG..',
    '..GGGGGGoooGGGGG..',
    '..GGGGGGGoGGGGGG..',
    '..GGGGGGGGGGGGGG..',
    'gggggggggggggggggg',
    'GGGGGGGGGGGGGGGGGG',
]
CEJAS = {   # ceja izquierda, 3×2 (la derecha es el espejo)
    'enojado':    ['#..', '.##'],
    'preocupado': ['..#', '##.'],
    'arriba':     ['###', '...'],
}
OJO_CORAZON = ['r.r', 'rrr', '.r.']
OJO_ESTRELLA = ['.y.', 'yyy', '.y.']
BOCAS = {
    'sonrisa':  ['k..k', '.kk.'],
    'o':        ['.kk.', '.kk.'],
    'triste':   ['.kk.', 'k..k'],
    'ondulada': ['k.k.', '.k.k'],
}
JOYSTICK = [   # joystick de consola: cruceta a la izquierda, botones de colores a la derecha
    '.GGGGGGGGGG.',
    'GGgGGGGGGyGG',
    'GgggGGGGrGnG',
    'GGgGGGGGGBGG',
    '.GG......GG.',
]
POCHOCLOS = [  # balde a rayas con pochoclos asomando
    '.ywpy..',
    'wpywpwy',
    'rwrwrwr',
    'rwrwrwr',
    '.rwrwr.',
    '.rwrwr.',
]
MATE = ['..g..', 'mnnnm', 'mmmmm', 'mmmmm', '.mmm.']   # bombilla, yerba y calabaza
TERMO = ['.G.', 'GgG', 'ggg', 'gGg', 'ggg', 'ggg', 'ggg', 'gGg', '.g.']   # parado en el piso
TERMO_SIRVE = ['....Gg', '...ggg', '..ggg.', '.ggG..', 'Gg....']        # inclinado, el pico abajo a la izq
AUTO = [   # Camaro blanco descapotable, de costado, mirando a la derecha (34×9 con las ruedas, que van aparte)
    '......................bK..........',     # parabrisas
    '.....................bbK..........',
    '...wwwwwwwwwwwwwwwwwwwwwwwwwwwww..',     # borde de las puertas: el cangrejito va sentado adentro
    '.Gwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwyy',
    'xwkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkww',
    'Gwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwg',
    '.GGG.......GGGGGGGGGGGG.......GGG.',
]
RUEDAS_X = (7, 26)        # centro de las ruedas (mirando a la derecha)
AUTO_Y = OY + 21          # fila del lienzo donde arranca el auto
HUMO = ['.gg.', 'gggg', 'gggg', '.gg.']
HUMO_CLARO = ['.ww.', 'wwww', 'wwgw', '.ww.']
GUITARRA = [   # criolla: clavijas, mástil y caja con la boca (por debajo de la boca, para que se lo vea cantar)
    '...........mmmm.',
    '..........mMMMMm',
    'GGpmmmmmmmMMkkMm',
    'GGpmmmmmmmMMkkMm',
    '..........mMMMMm',
    '...........mmmm.',
]
ELECTRICA = [  # guitarra eléctrica roja (rock nacional)
    '..........xx....',
    '...........xxx..',
    'GGMMMMMMMMxxxxx.',
    'GGmmmmmmmmxxwwx.',
    '..........xxxxx.',
    '.........xx.....',
]
TECLADO = [    # teclado colgado, como el de la cumbia (keytar)
    '..........xxxx',
    'GGGGGGGGGGGG..',
    'GwkwwkwkwwkG..',
    'GGGGGGGGGGGG..',
]
MICROFONO = ['ss', 'ss', '.K', '.K', '.K']
TAZA = {   # café y té (para quien no toma mate), y el vasito de caña con ruda de la Pachamama
    'cafe': ['wLLLw.', 'wwwwwg', 'wwwwwg', '.www..'],
    'te':   ['wtttw.', 'wwwwwg', 'wywwwg', '.www..'],
    'ruda': ['.e.e.', 'seees', 'swwws', 'sssss'],
}
NOQUIS = [     # plato de ñoquis con tuco, y el billete asomando abajo
    '...qZqZq...',
    '..qqZqqZqq.',
    'sssssssssss',
    'nnsssssssnn',
]
TENEDOR = ['s.s', 'sss', '.s.', '.s.']
ESCARAPELA = ['.CCC.', 'CwwwC', 'CwCwC', 'CwwwC', '.CCC.']
FLOR = ['.f.', 'fyf', '.f.']
# banderas de 8×6 (la de la hinchada y la del mástil); se elige en la configuración
BANDERAS = {
    'argentina': ['CCCCCCCC', 'CCCCCCCC', 'wwwyywww', 'wwwyywww', 'CCCCCCCC', 'CCCCCCCC'],
    'uruguay':   ['yywwwwww', 'yyBBBBBB', 'wwwwwwww', 'BBBBBBBB', 'wwwwwwww', 'BBBBBBBB'],
    'chile':     ['BBBwwwww', 'BwBwwwww', 'BBBwwwww', 'xxxxxxxx', 'xxxxxxxx', 'xxxxxxxx'],
    'paraguay':  ['xxxxxxxx', 'xxxxxxxx', 'wwwyywww', 'wwwwwwww', 'BBBBBBBB', 'BBBBBBBB'],
    'bolivia':   ['xxxxxxxx', 'xxxxxxxx', 'yyyyyyyy', 'yyyyyyyy', 'nnnnnnnn', 'nnnnnnnn'],
    'peru':      ['xxxwwxxx'] * 6,
    'colombia':  ['yyyyyyyy', 'yyyyyyyy', 'yyyyyyyy', 'BBBBBBBB', 'xxxxxxxx', 'xxxxxxxx'],
    'venezuela': ['yyyyyyyy', 'yyyyyyyy', 'BwBBBBwB', 'BBwwwwBB', 'xxxxxxxx', 'xxxxxxxx'],
    'mexico':    ['nnwwwwxx', 'nnwwwwxx', 'nnwmmwxx', 'nnwmmwxx', 'nnwwwwxx', 'nnwwwwxx'],
    'espana':    ['xxxxxxxx', 'yyyyyyyy', 'yyyyyyyy', 'yyyyyyyy', 'yyyyyyyy', 'xxxxxxxx'],
    'brasil':    ['nnnyynnn', 'nnyyyynn', 'nyyBByyn', 'nyyBByyn', 'nnyyyynn', 'nnnyynnn'],
    'orgullo':   ['xxxxxxxx', 'aaaaaaaa', 'yyyyyyyy', 'nnnnnnnn', 'BBBBBBBB', 'vvvvvvvv'],
}
NOMBRES_BANDERAS = [('argentina', 'Argentina'), ('uruguay', 'Uruguay'), ('chile', 'Chile'),
                    ('paraguay', 'Paraguay'), ('bolivia', 'Bolivia'), ('peru', 'Perú'), ('colombia', 'Colombia'),
                    ('venezuela', 'Venezuela'), ('mexico', 'México'), ('espana', 'España'), ('brasil', 'Brasil'),
                    ('orgullo', 'Orgullo (arcoíris)')]
# partículas (se dibujan fuera de la grilla, con posición libre)
NOTA = ['..yy', '..y.', '..y.', 'yyy.', 'yy..']
BURBUJA = ['.cc.', 'c..c', 'c..c', '.cc.']                       # pompa de jabón
PELOTAS = (['.x.', 'xxx', '.x.'], ['.y.', 'yyy', '.y.'], ['.C.', 'CCC', '.C.'])   # para los malabares
MOSCA = ['w.w', '.k.', '.k.']
GOTA = ['c']
Z_GRANDE = ['yyyy', '..y.', '.y..', 'yyyy']
Z_CHICA = ['yyy', '.y.', 'yyy']
CORAZON = ['.r.r.', 'rrrrr', 'rrrrr', '.rrr.', '..r..']
ESTRELLA = ['.y.', 'yyy', '.y.']
PARLANTE_MUDO = ['...G....', '..GG.x.x', 'GGGG..x.', 'GGGG.x.x', '..GG....', '...G....']
PARLANTE = ['...G.....', '..GG..G..', 'GGGG.G.G.', 'GGGG.G.G.', '..GG..G..', '...G.....']


_cache: dict[tuple, QImage] = {}


def sprite(filas, espejo: bool = False) -> QImage:
    """Grilla de texto → QImage de 1 unidad por píxel (cacheada)."""
    clave = (tuple(filas), espejo)
    img = _cache.get(clave)
    if img is None:
        h, w = len(filas), max(len(f) for f in filas)
        img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        p = QPainter(img)
        for j, fila in enumerate(filas):
            for i, ch in enumerate(fila):
                if ch in '. #':
                    continue
                p.fillRect(w - 1 - i if espejo else i, j, 1, 1, PALETA[ch])
        p.end()
        _cache[clave] = img
    return img


# ---------------------------------------------------------------- pose
@dataclass
class Pose:
    y: int = 0                 # todo el cangrejo (negativo = arriba)
    cuerpo_y: int = 0          # solo cuerpo, cara y brazos (respirar, sentarse)
    aplastar: int = 0          # +1 aplastado, -1 estirado
    patas: str = 'quietas'     # quietas, caminar, patalear, abiertas, sentado
    fase: int = 0              # cuadro de las patas
    dir: int = 1               # hacia dónde camina (para las patas)
    brazos: tuple = ('reposo', 'reposo')   # izquierdo, derecho
    fase_brazos: int = 0
    ojos: str = 'normal'       # normal, cerrados, feliz, sorpresa, mareado, grandes
    mirar: tuple = (0, 0)      # -1..1 en x e y
    boca: int = 0              # 0 cerrada, 1-2 hablando, 3 bostezo
    boca_forma: str = ''       # sin hablar: sonrisa, o, triste, ondulada
    cejas: str = ''            # enojado, preocupado, arriba
    rubor: bool = False
    brillo: bool = False
    accesorios: dict = field(default_factory=dict)   # nombre -> opacidad 0..1
    t: float = 0.0             # reloj, para animar accesorios
    auto_x: int = 0            # el auto corrido (cuando se va solo)
    auto_atras: bool = False   # el auto detrás del cangrejo (ya se bajó)
    bebida: str = 'mate'       # mate, cafe, te o ruda (qué toma mientras labura)
    bandera: str = 'argentina'  # la de la hinchada
    fuelle: int = 4            # cuánto está abierto el bandoneón
    escala_x: float = 1.0      # <1: de canto, achatado (la vueltita de la chacarera)


def _brazo(nombre: str, f: int, lado: int):
    """Brazo izquierdo en coordenadas del cangrejo: (rectángulos, (x, y, garra)) o None."""
    if nombre == 'reposo':
        return [(7, 20, 2, 2)], (3, 19, 'izq')
    if nombre == 'chasquear':
        return [(7, 20, 2, 2)], (3, 19, 'izq' if f % 2 == 0 else 'cerrada')
    if nombre == 'arriba':
        return [(7, 15, 2, 7)], (6, 11, 'arriba')
    if nombre == 'festejo':
        return [(7, 15, 2, 7)], (6, 11 - (f % 2), 'arriba' if f % 2 == 0 else 'cerrada')
    if nombre == 'saludo':
        dx = (-1, 0, 1, 0)[f % 4]
        return [(7, 15, 2, 7)], (6 + dx, 11, 'arriba' if f % 4 < 2 else 'cerrada')
    if nombre == 'estirar':
        return [(7, 13, 2, 9)], (6, 9, 'arriba')
    if nombre == 'teclado':
        alto = 3 - (1 if (f + (lado > 0)) % 2 else 0)
        return [(7, 20, 2, alto)], (7, 20 + alto, 'abajo')
    if nombre == 'colgando':
        dx = (0, 1, 0, -1)[f % 4]
        return [(7, 20, 2, 3)], (6 + dx, 23, 'abajo')
    if nombre == 'sostener':
        return [(7, 20, 2, 2)], (7, 22, 'der')
    if nombre == 'boca':
        return [], (14, 22, 'arriba')
    if nombre == 'rascar':
        return [(7, 15, 2, 7)], (8 + (f % 2), 12, 'der')
    if nombre == 'oreja':          # pinza en la «oreja»: te está escuchando
        return [(7, 15, 2, 6)], (5, 12 + (f % 2), 'der')
    if nombre == 'baile':
        return ([(7, 15, 2, 7)], (6, 11, 'arriba')) if f % 2 else ([(7, 20, 2, 2)], (3, 21, 'izq'))
    if nombre == 'servir':         # brazo estirado hacia afuera, sosteniendo el termo
        return [(4, 19, 4, 2)], (1, 16, 'arriba')
    if nombre == 'acercar':        # pinza al costado de la boca (sostiene el mate, come algo)
        return [(7, 20, 2, 2), (9, 22, 2, 2)], (11, 23, 'der')
    if nombre == 'mirar_garra':    # brazo levantado, la garra afuera del cuerpo (se la mira aburrido)
        return [(7, 16, 2, 5)], (4, 12, 'der')
    if nombre == 'nada':
        return None
    return [(7, 20, 2, 2)], (3, 19, 'izq')


def _espejar(rects, garra):
    rects = [(34 - x - w, y, w, h) for (x, y, w, h) in rects]
    gx, gy, tipo = garra
    return rects, (34 - gx - 4, gy, ESPEJO_GARRA.get(tipo, tipo))


def _patas(pose: Pose):
    """Rectángulos de las 4 patas en coordenadas del cangrejo."""
    xs = [10, 13, 20, 23]
    f = pose.fase
    if pose.patas == 'caminar':
        paso = f % 4
        out = []
        for i, x in enumerate(xs):
            grupo = i % 2              # 0: patas 1 y 3; 1: patas 2 y 4
            levantada = (paso == 0 and grupo == 0) or (paso == 2 and grupo == 1)
            dx = pose.dir if levantada else 0
            out.append((x + dx, 26, 1, 2 if levantada else 3))
        return out
    if pose.patas == 'patalear':
        movs = ((0, 3), (1, 4), (0, 3), (-1, 4))
        return [(x + movs[(f + i) % 4][0], 26, 1, movs[(f + i) % 4][1]) for i, x in enumerate(xs)]
    if pose.patas == 'abiertas':
        return [(9, 26, 1, 3), (12, 26, 1, 3), (21, 26, 1, 3), (24, 26, 1, 3)]
    if pose.patas == 'sentado':
        return [(7, 28, 2, 1), (25, 28, 2, 1)]
    return [(x, 26, 1, 3) for x in xs]


def dibujar(pose: Pose) -> QImage:
    """La pose entera en un QImage de W×H unidades (con contorno suave)."""
    cang = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    cang.fill(0)
    p = QPainter(cang)
    acc = pose.accesorios
    # --- el auto no se mueve con el cangrejo: va delante (sentado adentro) o detrás (cuando ya se bajó)
    a_auto = acc.get('auto', 0)
    if a_auto > 0.01 and pose.auto_atras:
        _dibujar_auto(p, pose, a_auto)
    p.translate(OX, OY + pose.y)

    def r(x, y, w, h, col):
        p.fillRect(x, y, w, h, PALETA[col] if isinstance(col, str) else col)

    def spr(filas, x, y, alfa=1.0, espejo=False):
        if alfa <= 0.01:
            return
        p.setOpacity(alfa)
        p.drawImage(x, y, sprite(filas, espejo))
        p.setOpacity(1.0)

    # --- patas (no se mueven con el cuerpo)
    for (x, y, w, h) in _patas(pose):
        r(x, y, w, h, 'O')

    # --- cuerpo
    cy = pose.cuerpo_y
    if pose.aplastar > 0:
        bx, by, bw, bh = 8, 18, 18, 8
    elif pose.aplastar < 0:
        bx, by, bw, bh = 10, 14, 14, 12
    else:
        bx, by, bw, bh = 9, 16, 16, 10
    by += cy
    dt = by - 16                    # cuánto se corrió la parte de arriba
    r(bx, by, bw, bh, 'o')
    r(bx + 1, by, bw - 2, 1, 'h')
    r(bx, by + bh - 1, bw, 1, 'O')

    # --- pañuelo de gaucho (rojo) o de tanguero (blanco): abajo del cuerpo, con el nudo entre las patas
    medio = bx + bw // 2
    for nombre, col in (('gaucho', 'x'), ('panuelo_blanco', 'w')):
        a = acc.get(nombre, 0)
        if a > 0.01:
            p.setOpacity(a)
            r(bx + 2, by + bh - 1, bw - 4, 1, col)
            r(medio - 1, by + bh, 2, 1, col)
            r(medio - 1, by + bh + 1, 1, 1, col)
            p.setOpacity(1.0)
    _ropa_cuerpo(p, acc, bx, by, bw, bh, pose.t)
    a = acc.get('escarapela', 0)
    if a > 0.01:
        spr(ESCARAPELA, 9, 21 + dt, a)

    # --- mini cangrejo ayudante arriba de la cabeza
    a = acc.get('ayudante', 0)
    if a > 0.01:
        rebote = int(pose.t * 3.3) % 2
        spr(MINI, 8, 11 + dt - rebote, a)

    # --- brillo de la pantalla de la netbook en la cara
    a = acc.get('netbook', 0)
    if a > 0.5:
        r(bx + 1, 19 + dt, bw - 2, 3, _c('#9FD8FF', 38))

    # --- cejas (Clawd no tiene; aparecen solo para expresar algo)
    if pose.cejas:
        dibujo = CEJAS[pose.cejas]
        for ex, espejo in ((12, False), (20, True)):
            for j, fila in enumerate(dibujo):
                for i, ch in enumerate(fila):
                    if ch == '#':
                        ii = 2 - i if espejo else i
                        r(ex - 1 + ii, 17 + dt + j, 1, 1, 'k')

    # --- ojos
    lx, ly = pose.mirar
    for ex in (12, 20):
        x, y = ex + lx, 19 + dt + ly
        o = pose.ojos
        if o == 'guino':
            o = 'cerrados' if ex > 16 else 'normal'
        if o == 'cerrados':
            r(x, y + 2, 2, 1, 'k')
        elif o == 'medio':
            r(x, y + 1, 2, 2, 'k')
            r(x, y + 1, 2, 1, 'O')
        elif o == 'corazon':
            spr(OJO_CORAZON, x - (1 if ex < 16 else 0), y, 1.0)
        elif o == 'estrella':
            spr(OJO_ESTRELLA, x - (1 if ex < 16 else 0), y, 1.0)
        elif o == 'llorar':
            r(x, y, 2, 3, 'k')
            caida = int(pose.t * 4) % 4
            r(x + (0 if ex < 16 else 1), y + 3 + caida, 1, 1, 'c')
        elif o == 'feliz':
            r(x, y, 2, 1, 'k')
            r(x - 1, y + 1, 1, 1, 'k')
            r(x + 2, y + 1, 1, 1, 'k')
        elif o == 'sorpresa':
            r(x - 1, y, 4, 4, 'k')
            r(x, y + 1, 2, 2, 'o')
        elif o == 'mareado':
            for (i, j) in ((0, 0), (2, 0), (1, 1), (0, 2), (2, 2)):
                r(x - 1 + i + (1 if ex > 16 else 0), y + j, 1, 1, 'k')
        elif o == 'grandes':
            r(x, y - 1, 2, 4, 'k')
            r(x, y - 1, 1, 1, 'w')
        else:
            r(x, y, 2, 3, 'k')
            if pose.brillo:
                r(x, y, 1, 1, 'w')

    # --- lentes de sol
    a = acc.get('lentes', 0)
    if a > 0.01:
        p.setOpacity(a)
        y = 19 + dt
        r(11, y, 4, 3, 'k')
        r(19, y, 4, 3, 'k')
        r(15, y, 4, 1, 'k')
        r(12, y, 1, 1, 'w')
        r(20, y, 1, 1, 'w')
        p.setOpacity(1.0)

    # --- rubor y boca
    if pose.rubor:
        r(10, 23 + dt, 2, 1, 'R')
        r(22, 23 + dt, 2, 1, 'R')
    if pose.boca >= 3:
        r(15, 22 + dt, 4, 3, 'k')
    elif pose.boca > 0:
        r(16, 23 + dt, 2, pose.boca, 'k')
    elif pose.boca_forma:
        spr(BOCAS[pose.boca_forma], 15, 23 + dt)

    # --- casco de robot (Daft Punk): tapa la cara, visor negro con luces
    for nombre, col in (('casco_plata', 's'), ('casco_oro', 'Y')):
        a = acc.get(nombre, 0)
        if a > 0.01:
            _casco(p, bx, by, bw, dt, pose.t, a, col)

    # --- cosas delante del cuerpo
    a = acc.get('libro', 0)
    if a > 0.01:
        spr(LIBRO, 10, 22 + dt, a)
    a = acc.get('celular', 0)
    if a > 0.01:
        _celular(p, 11, 23 + dt, pose.t, a)
        if a > 0.5:
            r(bx + 1, 19 + dt, bw - 2, 3, _c('#9FD8FF', 30))
    a = acc.get('joystick', 0)
    if a > 0.01:
        _joystick(p, 11, 23 + dt, pose.t, a)
    a = acc.get('pochoclos', 0)
    if a > 0.01:
        spr(POCHOCLOS, 8, 22 + dt, a)
    vaso = MATE if pose.bebida == 'mate' else TAZA.get(pose.bebida, TAZA['cafe'])
    a = acc.get('mate', 0)
    if a > 0.01:
        spr(vaso, 26, 22 + dt, a)          # en la pinza, al costado (el sorbo es «mate_boca», más abajo)
    a = acc.get('bandera', 0)
    if a > 0.01:
        _bandera(p, 25, 4 + dt, pose.t, a, pose.bandera)
    a = acc.get('guitarra', 0)
    if a > 0.01:
        spr(GUITARRA, 8, 23 + dt, a)
    a = acc.get('electrica', 0)
    if a > 0.01:
        spr(ELECTRICA, 8, 23 + dt, a)
    a = acc.get('teclado_musical', 0)
    if a > 0.01:
        spr(TECLADO, 9, 24 + dt, a)
    a = acc.get('bandoneon', 0)
    if a > 0.01:
        _bandoneon(p, 17, 22 + dt, pose.fuelle, a)
    a = acc.get('noquis', 0)
    if a > 0.01:
        spr(NOQUIS, 12, 25, a)              # en el piso, adelante
    # mate de trabajo: el termo y el mate en el piso a la derecha de la netbook, o en la mano
    a = acc.get('termo', 0)
    if a > 0.01:
        spr(TERMO, 33, 20, a)
    a = acc.get('mate_piso', 0)
    if a > 0.01:
        spr(vaso, 27, 29 - len(vaso), a)
    a = acc.get('mate_mano', 0)
    if a > 0.01:
        spr(vaso, 27, 21 + dt, a)

    # --- brazos
    for lado, nombre in ((-1, pose.brazos[0]), (1, pose.brazos[1])):
        b = _brazo(nombre, pose.fase_brazos, lado)
        if b is None:
            continue
        rects, garra = b
        if lado > 0:
            rects, garra = _espejar(rects, garra)
        cuerpo = QRect(bx, by, bw, bh)
        for (x, y, w, h) in rects:
            r(x, y + dt, w, h, 'O' if cuerpo.intersects(QRect(x, y + dt, w, h)) else 'o')
        gx, gy, tipo = garra
        delante = cuerpo.intersected(QRect(gx, gy + dt, 4, 4))
        spr((GARRAS_DELANTE if delante.width() * delante.height() >= 4 else GARRAS)[tipo], gx, gy + dt)

    # --- el termo cebando va delante de la pinza que lo sostiene
    a = acc.get('termo_sirve', 0)
    if a > 0.01:
        spr(TERMO_SIRVE, 28, 16 + dt, a)
        if a > 0.5:
            r(28, 21 + dt + int(pose.t * 8) % 3, 1, 1, 'c')        # el chorrito de agua

    # --- auriculares (vincha arriba del cuerpo y dos almohadillas a los costados)
    a = acc.get('auriculares', 0)
    if a > 0.01:
        p.setOpacity(a)
        r(bx + 2, by - 2, bw - 4, 1, 'G')
        r(bx + 1, by - 1, 1, 1, 'G')
        r(bx + bw - 2, by - 1, 1, 1, 'G')
        for x in (bx - 1, bx + bw - 1):
            r(x, by + 1, 2, 4, 'G')
            r(x + (0 if x < bx else 1), by + 2, 1, 2, 'r')
        p.setOpacity(1.0)

    # --- sombreros (uno solo a la vez: el más visible)
    _sombrero(p, acc, bx, by, bw)

    # --- netbook delante (tapa las pinzas que teclean detrás de la pantalla)
    a = acc.get('netbook', 0)
    if a > 0.01:
        spr(NETBOOK, 8, 22 + max(0, dt), a)

    # --- el sorbo de mate: la bombilla a la boca, delante de todo (también de la netbook)
    a = acc.get('mate_boca', 0)
    if a > 0.01:
        spr(vaso, 15, 23 + dt, a)
    a = acc.get('tenedor', 0)
    if a > 0.01:
        spr(TENEDOR, 16, 22 + dt, a)
    a = acc.get('microfono', 0)
    if a > 0.01:
        spr(MICROFONO, 20, 20 + dt, a)

    # --- accesorios de la cabeza
    a = acc.get('ondas', 0)
    if a > 0.01:
        n = int(pose.t * 3) % 4
        p.setOpacity(a)
        for i in range(min(n, 3)):
            x0, y0, h = 28 + 2 * i, 15 - i + dt, 4 + 2 * i
            r(x0, y0, 1, 1, 'w')
            r(x0 + 1, y0 + 1, 1, h - 2, 'w')
            r(x0, y0 + h - 1, 1, 1, 'w')
        p.setOpacity(1.0)
    a = acc.get('lupa', 0)
    if a > 0.01:
        vaiven = round(math.sin(pose.t * 2.2) * 4)
        lx0 = 14 + vaiven
        spr(LUPA, lx0, 15 + dt, a)
        p.setOpacity(a)
        p.drawImage(lx0 - 3, 20 + dt, sprite(GARRAS_DELANTE['arriba']))
        p.setOpacity(1.0)
    a = acc.get('mundo', 0)
    if a > 0.01:
        _mundo(p, 27, 6 + dt, pose.t, a)
    a = acc.get('terminal', 0)
    if a > 0.01:
        _terminal(p, 24, 4 + dt, pose.t, a)
    a = acc.get('pensar', 0)
    if a > 0.01:
        n = int(pose.t * 2.5) % 4
        p.setOpacity(a)
        for i, (x, y, s) in enumerate(((24, 13, 1), (26, 10, 2), (29, 6, 3))):
            if i < n:
                r(x, y + dt, s, s, 'w')
        p.setOpacity(1.0)
    a = acc.get('exclamacion', 0)
    if a > 0.01:
        spr(EXCLAMACION, 16, 5 + dt - int(pose.t * 6) % 2, a)
    a = acc.get('pregunta', 0)
    if a > 0.01:
        spr(PREGUNTA, 15, 5 + dt - int(pose.t * 4) % 2, a)
    a = acc.get('sudor', 0)
    if a > 0.01:
        spr(SUDOR, 25, 14 + dt + int(pose.t * 3) % 3, a)
    a = acc.get('panuelo_baile', 0)
    if a > 0.01:
        _panuelo(p, 26, 6 + dt, pose.t, a)
    a = acc.get('bola_disco', 0)
    if a > 0.01:
        _bola_disco(p, bx + bw // 2 - 3, by - 13, pose.t, a)
    if a_auto > 0.01 and not pose.auto_atras:
        p.resetTransform()
        _dibujar_auto(p, pose, a_auto)
    p.end()
    if pose.escala_x < 0.99:
        ancho = max(2, round(W * pose.escala_x))
        fino = cang.scaled(ancho, H, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        cang = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
        cang.fill(0)
        q = QPainter(cang)
        q.drawImage((W - ancho) // 2, 0, fino)
        q.end()
    return _con_contorno(cang)


def _casco(p: QPainter, bx: int, by: int, bw: int, dt: int, t: float, a: float, col: str):
    """Casco de robot: carcasa metálica, visor negro con tiras de luces que cambian y rejilla abajo."""
    p.setOpacity(a)

    def r(x, y, w, h, c):
        p.fillRect(x, y, w, h, PALETA[c])
    for k, ins in enumerate((2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1)):      # carcasa redondeada
        r(bx - 1 + ins, 15 + dt + k, bw + 2 - 2 * ins, 1, col)
    r(bx + 2, 15 + dt, bw - 4, 1, 'w')               # brillo de arriba
    r(bx, 25 + dt, bw, 1, 'G')                       # sombra de abajo
    for k, ins in enumerate((1, 0, 0, 0, 1)):        # visor
        r(bx + 1 + ins, 17 + dt + k, bw - 2 - 2 * ins, 1, 'K')
    luces = 'rynCv'
    for i in range(2):                               # tiras de luces que corren
        r(bx + 2, 18 + dt + i * 2, bw - 4, 1, luces[(int(t * 5) + i * 2) % 5])
    for k in range(3):                               # rejilla de la boca
        r(bx + 4 + k * 3, 23 + dt, 2, 2, 'G')
    r(bx - 2, 18 + dt, 1, 4, 'G')                    # orejeras
    r(bx + bw + 1, 18 + dt, 1, 4, 'G')
    p.setOpacity(1.0)


def _panuelo(p: QPainter, x0: int, y0: int, t: float, a: float):
    """Pañuelo celeste y blanco que flamea (la vueltita de chacarera): ocho columnas con ondas."""
    p.setOpacity(a)
    for i in range(8):
        dy = round(math.sin(t * 12 - i * 0.9) * (1 + i * 0.25))
        for j, col in enumerate('CCwwCC'):
            p.fillRect(x0 + i, y0 + j + dy + i // 3, 1, 1, PALETA[col])
    p.setOpacity(1.0)


def _bola_disco(p: QPainter, x0: int, y0: int, t: float, a: float):
    """Bola de espejos colgada arriba de la cabeza, con reflejos de colores que giran."""
    p.setOpacity(a)
    p.fillRect(x0 + 2, y0 - 4, 1, 4, PALETA['G'])    # el hilo
    forma = ((1, 0, 4), (0, 1, 6), (0, 2, 6), (0, 3, 6), (0, 4, 6), (1, 5, 4))
    g = int(t * 6)
    for fila, (dx, y, n) in enumerate(forma):
        for i in range(n):
            p.fillRect(x0 + dx + i, y0 + y, 1, 1, PALETA['wsgw'[(i + fila + g) % 4]])
    for k in range(5):                               # destellos alrededor
        ang = t * 2.5 + k * 1.256
        x, y = x0 + 3 + round(math.cos(ang) * 8), y0 + 3 + round(math.sin(ang) * 6)
        p.fillRect(x, y, 1, 1, PALETA['yfCvr'[k]])
    p.setOpacity(1.0)


def _dibujar_auto(p: QPainter, pose: Pose, a: float):
    p.setOpacity(a)
    p.drawImage(OX + pose.auto_x, AUTO_Y, _auto(int(pose.t * 14) % 4, pose.dir < 0))
    p.setOpacity(1.0)


def _celular(p: QPainter, x0: int, y0: int, t: float, a: float):
    """Celular acostado con un jueguito: el amarillo salta los obstáculos verdes que vienen."""
    p.setOpacity(a)
    p.fillRect(x0, y0, 12, 5, PALETA['G'])
    p.fillRect(x0 + 1, y0 + 1, 10, 3, PALETA['K'])
    obst = x0 + 10 - int(t * 7) % 10
    p.fillRect(obst, y0 + 3, 1, 1, PALETA['n'])
    salta = x0 + 1 <= obst <= x0 + 4
    p.fillRect(x0 + 3, y0 + (1 if salta else 3), 1, 1, PALETA['y'])
    p.setOpacity(1.0)


def _auto(fase: int, espejo: bool) -> QImage:
    """El Camaro con las ruedas girando (cacheado por cuadro y lado)."""
    clave = ('auto', fase, espejo)
    img = _cache.get(clave)
    if img is None:
        img = QImage(34, 9, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        q = QPainter(img)
        q.drawImage(0, 0, sprite(AUTO))
        for cx in RUEDAS_X:
            q.fillRect(cx - 1, 5, 3, 1, PALETA['K'])
            q.fillRect(cx - 2, 6, 5, 2, PALETA['K'])
            q.fillRect(cx - 1, 8, 3, 1, PALETA['K'])
            q.fillRect(cx, 6, 1, 2, PALETA['G'])                            # maza
            rx, ry = ((-1, 6), (1, 6), (1, 7), (-1, 7))[fase]               # rayo que gira
            q.fillRect(cx + rx, ry, 1, 1, PALETA['g'])
        q.end()
        if espejo:
            img = img.flipped(Qt.Orientation.Horizontal)
        _cache[clave] = img
    return img


def mate_sorbo(t: float) -> bool:
    """¿Está chupando la bombilla? (lo usan el dibujo y la cara)."""
    return t % 7 < 2.2


def _joystick(p: QPainter, x0: int, y0: int, t: float, a: float):
    """Joystick con un botón que se aprieta a cada rato (titila en blanco)."""
    p.setOpacity(a)
    p.drawImage(x0, y0, sprite(JOYSTICK))
    botones = ((9, 1), (8, 2), (10, 2), (9, 3), (2, 1), (1, 2), (3, 2))
    bx, by = botones[(int(t * 7) * 5) % len(botones)]
    if int(t * 14) % 2 == 0:
        p.fillRect(x0 + bx, y0 + by, 1, 1, PALETA['w'])
    p.setOpacity(1.0)


def _bandera(p: QPainter, x0: int, y0: int, t: float, a: float, pais: str = 'argentina'):
    """Bandera flameando en un palito (el palito pasa por la pinza)."""
    filas = BANDERAS.get(pais, BANDERAS['argentina'])
    p.setOpacity(a)
    p.fillRect(x0, y0 - 1, 1, 10, PALETA['m'])
    for i in range(8):
        dy = round(math.sin(t * 9 - i * 0.9)) if i > 0 else 0
        for j, fila in enumerate(filas):
            p.fillRect(x0 + 1 + i, y0 + dy + j - 1, 1, 1, PALETA[fila[i]])
    p.setOpacity(1.0)


def _bandoneon(p: QPainter, cx: int, y0: int, fuelle: int, a: float):
    """Bandoneón: las dos tapas negras con botones y el fuelle en zigzag, que se abre y se cierra."""
    n = max(2, min(9, fuelle))
    x0 = cx - (6 + n) // 2
    p.setOpacity(a)
    for x in (x0, x0 + 3 + n):
        p.fillRect(x, y0, 3, 6, PALETA['K'])
        for j in (1, 3):
            p.fillRect(x + 1, y0 + j, 1, 1, PALETA['w'])
    for i in range(n):
        for j in range(6):
            p.fillRect(x0 + 3 + i, y0 + j, 1, 1, PALETA['G' if (i + j) % 2 else 'g'])
    p.setOpacity(1.0)


SOMBREROS = ('gaucho', 'galera', 'bicornio', 'funyi', 'gorrita', 'gorra', 'gorro_navidad',
             'gorro_rasta', 'peluca', 'melena')


def _sombrero(p: QPainter, acc: dict, bx: int, by: int, bw: int):
    """Un solo sombrero: el más visible (si se cruzan dos, el que se va se apaga). Sin sombrero, la flor."""
    puestos = [(acc.get(k, 0), k) for k in SOMBREROS if acc.get(k, 0) > 0.01]
    if not puestos:
        flor = acc.get('flor', 0)
        if flor > 0.01:
            p.setOpacity(flor)
            p.drawImage(bx + bw - 5, by - 2, sprite(FLOR))
            p.setOpacity(1.0)
        return
    a, k = max(puestos)
    p.setOpacity(a)

    def r(x, y, w, h, col):
        p.fillRect(x, y, w, h, PALETA[col])
    medio = bx + bw // 2
    if k == 'gaucho':                       # ala ancha, copa y cinta roja
        r(bx + 4, by - 4, bw - 8, 2, 'K')
        r(bx + 4, by - 2, bw - 8, 1, 'x')
        r(bx - 1, by - 1, bw + 2, 1, 'K')
    elif k == 'galera':                     # galera colonial, alta, con cinta celeste
        r(bx + 4, by - 8, bw - 8, 7, 'K')
        r(bx + 4, by - 3, bw - 8, 1, 'C')
        r(bx + 1, by - 1, bw - 2, 1, 'K')
    elif k == 'bicornio':                   # el de San Martín, de costado, con escarapela y penacho
        r(bx, by - 1, bw, 1, 'K')
        r(bx + 2, by - 3, bw - 4, 2, 'K')
        r(bx + 5, by - 5, bw - 10, 2, 'K')
        r(medio - 1, by - 4, 2, 2, 'C')
        r(medio - 1, by - 7, 1, 2, 'x')
    elif k == 'funyi':                      # sombrero de tanguero
        r(bx + 4, by - 4, bw - 8, 3, 'G')
        r(medio - 1, by - 4, 2, 1, 'K')     # la hendidura de la copa
        r(bx + 4, by - 2, bw - 8, 1, 'K')
        r(bx + 1, by - 1, bw - 2, 1, 'G')
    elif k == 'gorrita':                    # gorrita de cumbiero, con la visera de costado
        r(bx + 4, by - 3, bw - 8, 3, 'u')
        r(medio - 1, by - 4, 2, 1, 'u')
        r(bx + bw - 4, by - 1, 6, 1, 'u')
    elif k == 'gorra':                      # gorra de trapero, visera derecha y logo dorado
        r(bx + 4, by - 3, bw - 8, 3, 'K')
        r(bx + 3, by - 1, bw - 6, 1, 'K')
        r(medio - 1, by - 2, 2, 1, 'Y')
    elif k == 'gorro_rasta':                # gorro tejido rojo-amarillo-verde con rastas a los costados
        for i, col in enumerate('nyx'):
            r(bx + 2, by - 6 + i * 2, bw - 4, 2, col)
        r(bx + 1, by - 1, bw - 2, 1, 'K')
        for lado in (bx - 1, bx + bw - 1):
            r(lado, by, 2, 7, 'm')
            r(lado, by + 2, 2, 1, 'L')
            r(lado, by + 5, 2, 1, 'L')
    elif k == 'peluca':                     # peluca blanca de director de orquesta, con rulos
        r(bx + 1, by - 3, bw - 2, 3, 'w')
        for lado in (bx - 1, bx + bw - 2):
            r(lado, by - 1, 3, 5, 'w')
            r(lado + 1, by + 1, 1, 1, 'g')
            r(lado + 1, by + 3, 1, 1, 'g')
        r(bx + 3, by - 2, 1, 1, 'g')
        r(bx + bw - 4, by - 2, 1, 1, 'g')
    elif k == 'melena':                     # pelo largo de metalero, cae por los costados
        r(bx + 1, by - 3, bw - 2, 3, 'K')
        r(bx - 1, by - 1, 3, 10, 'K')
        r(bx + bw - 2, by - 1, 3, 10, 'K')
        r(bx, by + 4, 1, 1, 'G')
    elif k == 'gorro_navidad':              # gorro de Papá Noel con pompón
        r(bx + 2, by - 1, bw - 4, 1, 'w')
        r(bx + 4, by - 3, bw - 8, 2, 'x')
        r(bx + 6, by - 5, 5, 2, 'x')
        r(bx + 10, by - 6, 3, 1, 'x')
        r(bx + 13, by - 7, 2, 2, 'w')
    p.setOpacity(1.0)


def _ropa_cuerpo(p: QPainter, acc: dict, bx: int, by: int, bw: int, bh: int, t: float):
    """Lo que se pone en el cuerpo (de la boca para abajo, así no tapa la cara)."""
    def r(x, y, w, h, col):
        p.fillRect(x, y, w, h, PALETA[col])
    medio = bx + bw // 2
    abajo = by + 6
    alto = by + bh - abajo
    for k in ('poncho', 'guardapolvo', 'campera', 'camiseta', 'lentejuelas', 'cadena'):
        a = acc.get(k, 0)
        if a <= 0.01:
            continue
        p.setOpacity(a)
        if k == 'poncho':                   # poncho salteño: bordó con guarda negra
            r(bx, abajo, bw, alto, 'P')
            r(bx, abajo, bw, 1, 'K')
            r(bx, by + bh - 2, bw, 1, 'K')
        elif k == 'guardapolvo':            # guardapolvo blanco con moño azul
            r(bx, abajo, bw, alto, 'w')
            r(medio - 2, abajo, 4, 1, 'u')
            r(medio, abajo + 2, 1, 1, 'g')
        elif k == 'campera':                # campera de cuero negra, abierta adelante, con solapas
            r(bx, abajo + 1, 5, alto - 1, 'K')
            r(bx + bw - 5, abajo + 1, 5, alto - 1, 'K')
            r(bx + 4, abajo + 1, 1, 2, 'G')
            r(bx + bw - 5, abajo + 1, 1, 2, 'G')
            r(bx + 1, abajo + 3, 1, 1, 'g')     # el cierre de un bolsillo
        elif k == 'camiseta':               # la albiceleste, a rayas
            for x in range(bx, bx + bw):
                r(x, abajo, 1, alto, 'C' if (x - bx) // 2 % 2 == 0 else 'w')
        elif k == 'lentejuelas':            # camisa brillante de cuartetero: brillitos que titilan
            for i, (x, y) in enumerate(((1, 7), (4, 8), (7, 7), (10, 8), (13, 7), (2, 9), (6, 9),
                                        (9, 9), (12, 9), (14, 9))):
                r(bx + x, by + y, 1, 1, 'YwfC'[(i + int(t * 6)) % 4])
        elif k == 'cadena':                 # cadena dorada en V con dije
            for i in range(4):
                r(bx + 3 + i, abajo - 1 + i // 2, 1, 1, 'Y')
                r(bx + bw - 4 - i, abajo - 1 + i // 2, 1, 1, 'Y')
            r(medio - 1, abajo + 1, 2, 2, 'Y')
        p.setOpacity(1.0)


def _teclado(p: QPainter, pose: Pose, a: float):
    p.setOpacity(a)
    p.fillRect(5, 26, 24, 3, PALETA['G'])
    semilla = int(pose.t * 9)
    for fila in (26, 27):
        for x in range(6, 28, 2):
            prendida = (x * 7 + fila * 3 + semilla * 5) % 23 == 0
            p.fillRect(x, fila, 1, 1, PALETA['h' if prendida else 'g'])
    p.fillRect(12, 28, 10, 1, PALETA['g'])
    p.setOpacity(1.0)


def _mundo(p: QPainter, x0: int, y0: int, t: float, a: float):
    p.setOpacity(a)
    giro = int(t * 5)
    for j, fila in enumerate(MUNDO_MASCARA):
        for i, ch in enumerate(fila):
            if ch == '#':
                tex = MUNDO_TEXTURA[j]
                p.fillRect(x0 + i, y0 + j, 1, 1, PALETA[tex[(i + giro) % len(tex)]])
    p.setOpacity(1.0)


def _terminal(p: QPainter, x0: int, y0: int, t: float, a: float):
    p.setOpacity(a)
    p.fillRect(x0, y0, 11, 8, PALETA['G'])
    p.fillRect(x0 + 1, y0 + 1, 9, 6, PALETA['K'])
    paso = int(t * 3)
    largos = (5, 7, 3, 8, 4, 6, 2, 7)
    for i in range(3):
        n = largos[(paso + i) % len(largos)]
        p.fillRect(x0 + 2, y0 + 2 + i * 2 - 1 + 1, min(n, 7), 1, PALETA['n'])
    if int(t * 4) % 2 == 0:
        p.fillRect(x0 + 8, y0 + 5, 1, 1, PALETA['w'])
    p.setOpacity(1.0)


_CONTORNO_BGRA = np.array([CONTORNO.blue(), CONTORNO.green(), CONTORNO.red(), 255], np.float32) \
    * (CONTORNO.alpha() / 255)


def _con_contorno(img: QImage) -> QImage:
    """Suma un borde oscuro semitransparente de 1 unidad para que se vea en cualquier fondo."""
    W, H = img.width(), img.height()
    bpl = img.bytesPerLine()
    arr = np.frombuffer(img.constBits(), np.uint8).reshape(H, bpl // 4, 4)[:, :W].copy()
    lleno = arr[..., 3] > 0
    borde = np.zeros_like(lleno)
    borde[1:] |= lleno[:-1]
    borde[:-1] |= lleno[1:]
    borde[:, 1:] |= lleno[:, :-1]
    borde[:, :-1] |= lleno[:, 1:]
    borde &= ~lleno
    arr[borde] = _CONTORNO_BGRA.astype(np.uint8)
    arr = np.ascontiguousarray(arr)
    return QImage(arr.data, W, H, W * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()


def fila_superior(img: QImage) -> int:
    """Primera fila del lienzo con algo dibujado (para que el globo no tape nada)."""
    bpl = img.bytesPerLine()
    alfa = np.frombuffer(img.constBits(), np.uint8).reshape(H, bpl)[:, 3:W * 4:4]
    filas = np.nonzero(alfa.any(axis=1))[0]
    return int(filas[0]) if len(filas) else OY + 16


def recorte_cangrejo() -> QRect:
    """Zona del lienzo donde está el cangrejo en reposo (para el ícono)."""
    return QRect(OX + 2, OY + 14, 31, 16)


# ---------------------------------------------------------------- el mástil del Día de la Bandera
MW, MH = 16, 44          # lienzo del mástil (un poco más alto que el cangrejito)


def dibujar_mastil(t: float, izada: float = 1.0, pais: str = 'argentina') -> QImage:
    """Mástil con la bandera flameando. «izada» va de 0 (abajo de todo) a 1 (arriba)."""
    img = QImage(MW, MH, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    filas = BANDERAS.get(pais, BANDERAS['argentina'])
    p.fillRect(1, 0, 3, 2, PALETA['Y'])                 # la punta dorada
    p.fillRect(2, 2, 1, MH - 6, PALETA['g'])            # el palo
    p.fillRect(0, MH - 4, 6, 4, PALETA['m'])            # la base
    p.fillRect(1, MH - 4, 4, 1, PALETA['M'])
    arriba = 3 + round((1 - izada) * (MH - 18))
    for i in range(12):
        # flamea más lejos del palo; mientras sube va quieta
        dy = round(math.sin(t * 7 - i * 0.7) * min(1.0, i / 3)) if izada > 0.95 else 0
        for j in range(8):
            p.fillRect(3 + i, arriba + j + dy, 1, 1, PALETA[filas[j * 6 // 8][i * 8 // 12]])
    p.end()
    return _con_contorno(img)
