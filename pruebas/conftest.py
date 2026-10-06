# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Pruebas sin pantalla ni datos reales: Qt «offscreen» y carpetas temporales (se arma antes de importar)."""
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / 'dev'))
_TMP = Path(tempfile.mkdtemp(prefix='cangrejito-pruebas-'))
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
os.environ['CANGREJITO_DATOS'] = str(_TMP / 'datos')
os.environ['CANGREJITO_CLAUDE_DIR'] = str(_TMP / 'claude')

import pytest  # noqa: E402


@pytest.fixture(scope='session')
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication(sys.argv)


class VozFalsa:
    hablando, estado, al_terminar = False, 'lista', None

    def nivel(self):
        return 0.0

    def decir(self, *a, **k):
        pass

    def callar(self):
        pass


@pytest.fixture
def mascota(app):
    import config
    import mascota as M

    cfg = type('C', (dict,), {'guardar': lambda self: None})(dict(config.POR_DEFECTO, silencio=True))
    m = M.Mascota(cfg, VozFalsa())
    ag = app.primaryScreen().availableGeometry()
    m.modo, m.base = 'suelo', 'libre'
    m.px, m.py = ag.center().x(), m._piso(ag)
    return m
