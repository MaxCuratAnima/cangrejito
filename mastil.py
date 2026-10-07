# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""El mástil del Día de la Bandera: una ventanita aparte, plantada en el piso al lado del cangrejito.

Se queda quieto, pero lo podés agarrar con el mouse y llevarlo a otro lado (cae al piso, como el
cangrejito). El cangrejito iza la bandera, la saluda y va a buscarla si la movés.
"""
from __future__ import annotations

import time

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

import sprites as S
from globo import banderas_flotante

GRAVEDAD = 2600.0
IZAR_SEGUNDOS = 6.0


class Mastil(QWidget):
    movido = Signal()               # lo soltaste en otro lado

    def __init__(self, cfg, area_fn):
        super().__init__(None, banderas_flotante(Qt.WindowType.WindowDoesNotAcceptFocus))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.cfg = cfg
        self.area_fn = area_fn      # pantalla → rectángulo usable (el mismo que usa el cangrejito)
        self.E = int(cfg['escala'])
        self.setFixedSize(S.MW * self.E, S.MH * self.E)
        self.px, self.py, self.vy = 0.0, 0.0, 0.0
        self.cayendo = False
        self.izada = 0.0
        self.izando_desde = None
        self.plantado = False           # está puesto hoy (aunque se esconda un rato por un juego)
        self.presion = None
        self.agarre = QPointF()
        self.arrastrando = False
        self.t0 = time.monotonic()
        self._ult = self.t0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    # ------------------------------------------------------------ API
    def plantar(self, x_palo: float, pant):
        """Lo planta en el piso de esa pantalla, con el palo en «x_palo» y la bandera abajo (sin izar)."""
        ag = self.area_fn(pant)
        self.px = max(ag.left(), min(ag.right() - self.width(), x_palo - 2.5 * self.E))
        self.py = self._piso(ag)
        self.izada, self.izando_desde = 0.0, None
        self.plantado = True
        self.move(round(self.px), round(self.py))
        self.show()
        self._ult = time.monotonic()
        self._timer.start(50)

    def sacar(self):
        self.plantado = False
        self.esconder()

    def esconder(self):
        """Un juego tapa todo: se esconde sin perder dónde estaba ni si ya estaba izada."""
        self._timer.stop()
        self.hide()

    def mostrar(self):
        self.show()
        self._ult = time.monotonic()
        self._timer.start(50)

    def izar(self):
        if self.izada < 1.0 and self.izando_desde is None:
            self.izando_desde = time.monotonic() - self.izada * IZAR_SEGUNDOS

    def x_palo(self) -> float:
        """Dónde está el palo (en la pantalla), para que el cangrejito sepa a dónde ir."""
        return self.px + 2.5 * self.E

    def pantalla(self):
        c = QPoint(round(self.x_palo()), round(self.py + self.height() / 2))
        return QGuiApplication.screenAt(c) or QGuiApplication.primaryScreen()

    def quieto(self) -> bool:
        return self.isVisible() and not self.arrastrando and not self.cayendo

    # ------------------------------------------------------------ reloj
    def _piso(self, ag: QRect) -> float:
        return ag.bottom() + 1 - self.height()

    def _tick(self):
        ahora = time.monotonic()
        dt = min(0.08, ahora - self._ult)
        self._ult = ahora
        if self.izando_desde is not None:
            self.izada = min(1.0, (ahora - self.izando_desde) / IZAR_SEGUNDOS)
            if self.izada >= 1.0:
                self.izando_desde = None
        if self.cayendo:
            piso = self._piso(self.area_fn(self.pantalla()))
            self.vy += GRAVEDAD * dt
            self.py = min(piso, self.py + self.vy * dt)
            if self.py >= piso:
                self.cayendo, self.vy = False, 0.0
                self.movido.emit()
            self.move(round(self.px), round(self.py))
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        img = S.dibujar_mastil(time.monotonic() - self.t0, self.izada, self.cfg.get('bandera_mastil', 'argentina'))
        p.drawImage(QRect(0, 0, self.width(), self.height()), img)
        p.end()

    # ------------------------------------------------------------ mouse: se agarra y se suelta
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.presion = e.globalPosition()
            self.agarre = self.presion - QPointF(self.px, self.py)
            self.arrastrando, self.cayendo = False, False

    def mouseMoveEvent(self, e):
        if self.presion is None:
            return
        g = e.globalPosition()
        if not self.arrastrando and (g - self.presion).manhattanLength() < 5:
            return
        if not self.arrastrando:
            self.arrastrando = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self.px, self.py = g.x() - self.agarre.x(), g.y() - self.agarre.y()
        self.move(round(self.px), round(self.py))

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self.presion is None:
            return
        self.presion = None
        if self.arrastrando:
            self.arrastrando = False
            self.unsetCursor()
            self.cayendo, self.vy = True, 0.0
