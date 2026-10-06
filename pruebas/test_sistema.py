# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Lo que depende del sistema (Windows o Linux) responde sin romperse, y la detección de música anda."""
import sys

import lanzador
import rutas
import vigilante


def test_funciones_del_sistema(app):
    so = vigilante.so
    v = so.ventanas()
    assert isinstance(so.pids_app_claude(), set)
    assert isinstance(so.app_claude_abierta(v, set()), bool)
    assert so.segundos_inactivo() >= 0
    assert isinstance(so.monitores_en_pantalla_completa(set(), v), dict)
    assert isinstance(so.spotify_tema(v), str)
    assert isinstance(so.hay_vr(), bool)
    assert so.__name__ == ('sistema_windows' if sys.platform == 'win32' else 'sistema_linux')


def test_lanzador():
    assert isinstance(lanzador.pids_app_claude(), set)
    assert lanzador.comando_cangrejo()[-1].endswith('cangrejito.pyw')
    assert rutas.DATOS.name.lower() == 'datos'           # la carpeta de prueba, no la real


def test_vigilante_da_una_vuelta(app):
    import config
    v = vigilante.Vigilante(config.Config(), lambda: [])
    v._mirar()
    assert v.app_abierta in (True, False)


def test_reconoce_la_app_de_claude():
    assert rutas.es_app_claude(r'C:\Program Files\WindowsApps\Claude_2.1_x64__abc\app\Claude.exe')
    assert rutas.es_app_claude(r'C:\Users\x\AppData\Local\AnthropicClaude\app-1.0.0\claude.exe')
    assert not rutas.es_app_claude(r'C:\Users\x\.local\bin\claude.exe')


def test_musica():
    assert vigilante.es_funk('Kordhell - Murder In My Mind')
    assert vigilante.es_funk('MC Hariel - Ilusão')
    assert not vigilante.es_funk('Soda Stereo - Persiana Americana')
    assert vigilante.es_de_guitarra('Chaqueño Palavecino - Amor salvaje')
    assert vigilante.es_de_guitarra('Mercedes Sosa - Zamba para no morir')
    assert not vigilante.es_de_guitarra('Duki - Goteo')
