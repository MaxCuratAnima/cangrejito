# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Hoja de contacto con todas las poses, para revisar el dibujo sin abrir la mascota.

Uso: python dev/galeria.py <salida.png> [escala]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

import sprites as S
from sprites import Pose

POSES = [
    ('reposo', Pose()),
    ('parpadeo', Pose(ojos='cerrados')),
    ('mira arriba-izq', Pose(mirar=(-1, -1))),
    ('camina 0', Pose(patas='caminar', fase=0)),
    ('camina 2', Pose(patas='caminar', fase=2, cuerpo_y=1)),
    ('chasquea', Pose(brazos=('chasquear', 'chasquear'), fase_brazos=1)),
    ('saluda', Pose(brazos=('reposo', 'saludo'), ojos='feliz', boca=2)),
    ('teclea', Pose(brazos=('teclado', 'teclado'), fase_brazos=1, mirar=(0, 1), accesorios={'netbook': 1})),
    ('terminal', Pose(brazos=('teclado', 'teclado'), mirar=(1, 0), accesorios={'netbook': 1, 'terminal': 1}, t=1.3)),
    ('piensa+netbook', Pose(mirar=(1, -1), accesorios={'netbook': 1, 'pensar': 1}, t=1.3)),
    ('escucha', Pose(brazos=('reposo', 'oreja'), brillo=True, cejas='arriba', accesorios={'ondas': 1}, t=1.1)),
    ('baila', Pose(y=-1, brazos=('baile', 'reposo'), fase_brazos=1, ojos='feliz', boca_forma='sonrisa')),
    ('silba', Pose(boca_forma='o', mirar=(1, -1))),
    ('guiño', Pose(ojos='guino', boca_forma='sonrisa')),
    ('enamorado', Pose(ojos='corazon', rubor=True, boca_forma='sonrisa')),
    ('orgulloso', Pose(ojos='estrella', cejas='arriba', boca_forma='sonrisa', brazos=('festejo', 'festejo'))),
    ('frustrado', Pose(cejas='enojado', boca_forma='ondulada')),
    ('preocupado', Pose(cejas='preocupado', boca_forma='triste', ojos='grandes')),
    ('triste', Pose(ojos='llorar', cejas='preocupado', boca_forma='triste', t=0.3)),
    ('sueño', Pose(ojos='medio', boca_forma='o')),
    ('aburrido', Pose(brazos=('mirar_garra', 'reposo'), mirar=(-1, -1), ojos='medio')),
    ('curioso', Pose(cejas='arriba', brillo=True, boca_forma='o')),
    ('lee', Pose(brazos=('sostener', 'sostener'), mirar=(0, 1), accesorios={'libro': 1})),
    ('busca', Pose(brazos=('reposo', 'nada'), accesorios={'lupa': 1}, t=0.4)),
    ('web', Pose(brazos=('reposo', 'arriba'), mirar=(1, -1), accesorios={'mundo': 1}, t=0.7)),
    ('piensa', Pose(mirar=(1, -1), accesorios={'pensar': 1}, t=1.3)),
    ('ayudante', Pose(accesorios={'ayudante': 1, 'teclado': 1}, brazos=('teclado', 'teclado'), mirar=(0, 1))),
    ('llama !', Pose(brazos=('saludo', 'saludo'), fase_brazos=2, ojos='grandes', accesorios={'exclamacion': 1})),
    ('pregunta ?', Pose(brazos=('reposo', 'arriba'), ojos='grandes', accesorios={'pregunta': 1})),
    ('error', Pose(ojos='sorpresa', brazos=('reposo', 'rascar'), accesorios={'sudor': 1})),
    ('festeja', Pose(y=-3, aplastar=-1, brazos=('festejo', 'festejo'), ojos='feliz', boca=2, patas='abiertas')),
    ('mimo', Pose(ojos='feliz', rubor=True)),
    ('silencio', Pose(brazos=('boca', 'reposo'), ojos='cerrados')),
    ('bostezo', Pose(brazos=('estirar', 'estirar'), ojos='cerrados', boca=3)),
    ('duerme', Pose(patas='sentado', cuerpo_y=3, ojos='cerrados', brazos=('reposo', 'reposo'))),
    ('agarrado', Pose(patas='patalear', fase=1, brazos=('colgando', 'colgando'), ojos='grandes')),
    ('mareado', Pose(ojos='mareado', patas='patalear', brazos=('colgando', 'colgando'))),
    ('cae', Pose(patas='abiertas', brazos=('arriba', 'arriba'), ojos='grandes', aplastar=-1)),
    ('aterriza', Pose(aplastar=1)),
    ('habla', Pose(boca=2, brillo=True)),
    ('joystick', Pose(patas='sentado', cuerpo_y=2, brazos=('sostener', 'sostener'), mirar=(1, 0),
                      cejas='arriba', accesorios={'joystick': 1}, t=0.1)),
    ('pochoclos', Pose(patas='sentado', cuerpo_y=2, brazos=('sostener', 'reposo'), mirar=(1, 0),
                       boca_forma='o', accesorios={'pochoclos': 1})),
    ('come pochoclo', Pose(patas='sentado', cuerpo_y=2, brazos=('sostener', 'acercar'), mirar=(1, 0),
                           accesorios={'pochoclos': 1})),
    ('mate sorbo', Pose(brazos=('reposo', 'acercar'), ojos='feliz', rubor=True, accesorios={'mate_boca': 1})),
    ('mate', Pose(brazos=('reposo', 'sostener'), boca_forma='sonrisa', accesorios={'mate': 1})),
    ('hinchada', Pose(y=-1, patas='abiertas', brazos=('festejo', 'arriba'), ojos='feliz', boca_forma='sonrisa',
                      brillo=True, accesorios={'bandera': 1}, t=0.3)),
    ('guitarra gaucho', Pose(patas='sentado', cuerpo_y=2, brazos=('sostener', 'teclado'), fase_brazos=1,
                             ojos='cerrados', boca_forma='o', accesorios={'guitarra': 1, 'gaucho': 1})),
    ('baila gaucho', Pose(y=-1, brazos=('baile', 'reposo'), fase_brazos=1, ojos='feliz', boca_forma='sonrisa',
                          accesorios={'gaucho': 1})),
    ('camaro funk', Pose(y=-5, patas='sentado', cuerpo_y=3, brazos=('reposo', 'festejo'), boca_forma='sonrisa',
                         mirar=(1, 0), accesorios={'auto': 1, 'lentes': 1}, t=0.2)),
    ('derrape', Pose(y=-6, patas='sentado', cuerpo_y=3, dir=-1, brazos=('arriba', 'arriba'), boca_forma='o',
                     mirar=(-1, 0), accesorios={'auto': 1, 'lentes': 1}, t=0.5)),
    ('escucha en auto', Pose(y=-5, patas='sentado', cuerpo_y=3, brazos=('reposo', 'oreja'), cejas='arriba',
                             brillo=True, accesorios={'auto': 1, 'lentes': 1, 'ondas': 1}, t=1.1)),
    ('salta del auto', Pose(y=-11, patas='abiertas', brazos=('festejo', 'festejo'), ojos='grandes',
                            boca_forma='o', accesorios={'auto': 1})),
    ('el auto se va', Pose(brazos=('reposo', 'saludo'), ojos='feliz', auto_x=14, auto_atras=True,
                           accesorios={'auto': 1})),
    ('ceba mate', Pose(brazos=('teclado', 'servir'), mirar=(1, 1),
                       accesorios={'netbook': 1, 'termo_sirve': 1, 'mate_piso': 1}, t=0.1)),
    ('sorbo laburando', Pose(brazos=('teclado', 'acercar'), ojos='feliz', rubor=True, aplastar=-1,
                             accesorios={'netbook': 1, 'termo': 1, 'mate_boca': 1})),
    ('teclea con mate', Pose(brazos=('teclado', 'sostener'), mirar=(0, 1),
                             accesorios={'netbook': 1, 'termo': 1, 'mate_mano': 1})),
    ('mate dejado', Pose(brazos=('teclado', 'teclado'), fase_brazos=1, mirar=(0, 1),
                         accesorios={'netbook': 1, 'termo': 1, 'mate_piso': 1})),
]


def main():
    salida = sys.argv[1]
    esc = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    app = QGuiApplication(sys.argv)
    cols = 7
    cw, ch = S.W * esc, S.H * esc + 22
    filas = (len(POSES) + cols - 1) // cols
    hoja = QImage(cols * cw, filas * ch * 2, QImage.Format.Format_ARGB32)
    hoja.fill(QColor('#ffffff'))
    p = QPainter(hoja)
    p.setFont(QFont('Segoe UI', 10))
    for fondo_i, fondo in enumerate(('#e9eef3', '#23262d')):
        for i, (nombre, pose) in enumerate(POSES):
            x = (i % cols) * cw
            y = fondo_i * filas * ch + (i // cols) * ch
            p.fillRect(x, y, cw, ch, QColor(fondo))
            p.drawImage(QRect(x, y, S.W * esc, S.H * esc), S.dibujar(pose))
            p.setPen(QColor('#888888'))
            p.drawText(QRect(x, y + S.H * esc, cw, 22), Qt.AlignmentFlag.AlignCenter, nombre)
    p.end()
    hoja.save(salida)
    print(salida)


if __name__ == '__main__':
    main()
