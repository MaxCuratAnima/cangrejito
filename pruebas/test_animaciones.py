# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Las animaciones se dibujan sin errores y las secuencias hacen lo que tienen que hacer."""
import time

import mascota as M
import sprites as S
from galeria import POSES


def test_todas_las_poses_se_dibujan(app):
    for nombre, pose in POSES:
        img = S.dibujar(pose)
        assert (img.width(), img.height()) == (S.W, S.H), nombre


def test_paseos_libres_se_dibujan(mascota):
    for paseo in ('joystick', 'pochoclos', 'hinchada', 'mate', 'celular', 'auriculares', 'guitarra', 'auto',
                  'bandoneon', 'cuarteto', 'cumbia', 'rock', 'trap', 'noquis', 'izar', 'saludo_bandera',
                  'chacarera', 'robot', 'disco', 'reggae', 'metal', 'director',
                  'malabares', 'burbujas', 'sentadillas', 'estornudo', 'mosca', 'estirarse'):
        mascota.paseo = paseo
        for t in (0.1, 2.5, 6.5, 19.0):
            mascota.t0 = time.monotonic() - t
            S.dibujar(mascota._pose(time.monotonic()))


def test_cosquillas_y_mirada_larga(mascota):
    visto = []
    mascota.cosquillas.connect(lambda: visto.append('cosquillas'))
    mascota.observado.connect(lambda: visto.append('observado'))
    ahora = time.monotonic()
    for k in range(3):
        mascota._mimar(ahora + k)
    assert mascota.mom == 'mimo' and not visto
    mascota._mimar(ahora + 3)
    assert mascota.mom == 'cosquillas' and visto == ['cosquillas']
    assert mascota.mimos == []
    for t in (0.2, 1.0, 2.0):                                  # la risa se dibuja
        mascota.mom_ini = time.monotonic() - t
        S.dibujar(mascota._pose(time.monotonic()))
    mascota.mom = None
    mascota.hover_desde = time.monotonic() - 15
    mascota._tick()
    mascota._tick()
    assert visto.count('observado') == 1, 'avisa una sola vez por mirada'


def test_mate_mientras_labura(mascota):
    mascota.actividad('teclear')
    ahora = time.monotonic()
    mascota.trabajando_desde, mascota.prox_mate = ahora - 60, ahora - 1
    mascota._reloj_mate(ahora)
    assert mascota.mate_ini is not None
    fases = {u: M._fase_mate(u) for u in (0.5, 3.5, 6, 10.5, 19.5)}
    assert fases == {0.5: 'cebar', 3.5: 'sorbo', 6: 'mano', 10.5: 'sorbo', 19.5: 'dejado'}
    mascota.mate_ini = ahora - 3.5
    assert mascota._pose(ahora).brazos[1] == 'acercar'
    mascota.base, mascota.paseo, mascota.paseo_x = 'libre', 'caminar', mascota.px + 100
    mascota._reloj_mate(ahora)
    assert mascota.mate_ini is None, 'al caminar, el mate desaparece'


def test_camaro_maneja_derrapa_y_se_baja(mascota, app):
    mascota.musica, mascota.genero = True, 'funk'
    mascota.paseo, mascota.paseo_fin = 'auto', time.monotonic() + 999
    ag = app.primaryScreen().availableGeometry()
    izq, der = ag.left() - S.OX * mascota.E, ag.right() + 1 - (S.OX + 34) * mascota.E
    t0, derrapes, dir0 = time.monotonic(), 0, mascota.dir
    for i in range(900):
        mascota._fisica(1 / 30, t0 + i / 30)
        if mascota.dir != dir0:
            derrapes, dir0 = derrapes + 1, mascota.dir
        assert izq <= mascota.px <= der, 'el auto no se sale de la pantalla'
    assert derrapes >= 2
    assert any(q['spr'] in (S.HUMO, S.HUMO_CLARO) for q in mascota.particulas), 'echa humo'
    mascota.actividad('teclear')
    assert mascota.paseo == 'quieto' and mascota.bajando_auto is not None, 'se baja para laburar'


def test_con_juego_en_otro_monitor_hace_cosas_de_compañero(mascota):
    mascota.tapados = {'JUEGO'}
    mascota._hacia_juego = lambda: (1, 0)
    vistos = set()
    for _ in range(300):
        mascota.mom, mascota.paseo, mascota.paseo_fin, mascota.paseo_x = None, 'quieto', 0.0, None
        mascota._paseos(time.monotonic())
        vistos.add(mascota.paseo)
    assert {'joystick', 'pochoclos', 'hinchada'} <= vistos
