# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Globo de diálogo pixelado que sigue al cangrejito (se ve aunque la voz esté silenciada)."""
from __future__ import annotations

import sys
import time

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter
from PySide6.QtWidgets import QWidget

RELLENO = QColor('#FFF9F2')
BORDE = QColor('#2B1A14')
TEXTO = QColor('#2B1A14')
SUB = QColor('#B4573A')
ANCHO_MAX = 290
MARGEN = 10
COLA = 8          # alto de la colita
FUENTES = ['Segoe UI', 'Noto Sans', 'DejaVu Sans', 'Liberation Sans']   # la primera que haya (Windows, Linux)
WINDOWS = sys.platform == 'win32'


def banderas_flotante(*extra):
    """Ventana flotante sin marco y siempre encima (la del cangrejito y la del globo).
    En Windows es una ventana «herramienta» (no aparece en la barra de tareas). En Linux va sin
    administrador de ventanas: las «herramienta» dependen de una ventana invisible de Qt y WSLg no
    las muestra; así se ven en WSL, X11 y XWayland. Arriba de todo la mantiene Mascota.subir()."""
    b = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.NoDropShadowWindowHint
    b |= Qt.WindowType.Tool if WINDOWS else Qt.WindowType.X11BypassWindowManagerHint
    for e in extra:
        b |= e
    return b


class Globo(QWidget):
    def __init__(self):
        super().__init__(None, banderas_flotante(Qt.WindowType.WindowDoesNotAcceptFocus,
                                                 Qt.WindowType.WindowTransparentForInput))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.fuente = QFont()
        self.fuente.setFamilies(FUENTES)
        self.fuente.setPointSize(10)
        self.fuente.setWeight(QFont.Weight.DemiBold)
        self.fuente_sub = QFont()
        self.fuente_sub.setFamilies(FUENTES)
        self.fuente_sub.setPointSize(8)
        self.fuente_sub.setWeight(QFont.Weight.Bold)
        self.texto = ''
        self.sub = ''
        self.fin = 0.0
        self.alfa = 0.0
        self.cola_x = 20
        self.cola_abajo = True
        self._caja = QRect()

    # ------------------------------------------------------------ API
    def mostrar(self, texto: str, sub: str | None = None, dur: float | None = None):
        self.texto = texto
        self.sub = (sub or '').upper()
        if dur is None:
            dur = max(2.8, 1.2 + len(texto) * 0.07)
        self.fin = time.monotonic() + dur
        fm = QFontMetrics(self.fuente)
        caja = fm.boundingRect(QRect(0, 0, ANCHO_MAX, 2000), Qt.TextFlag.TextWordWrap, texto)
        alto_sub = QFontMetrics(self.fuente_sub).height() + 2 if self.sub else 0
        ancho = max(caja.width(), QFontMetrics(self.fuente_sub).horizontalAdvance(self.sub) if self.sub else 0)
        w = min(ANCHO_MAX, ancho) + MARGEN * 2 + 2
        h = caja.height() + alto_sub + MARGEN * 2
        self._alto_sub = alto_sub
        self._caja = QRect(0, 0, w, h)
        self.setFixedSize(w, h + COLA)
        self.update()

    def extender(self, segundos: float):
        self.fin = max(self.fin, time.monotonic() + segundos)

    def cerrar(self):
        self.fin = 0

    def seguir(self, punta_x: int, punta_y: int, pantalla: QRect, abajo_y: int):
        """Ubica el globo con la colita apuntando a (punta_x, punta_y); si no entra arriba, va abajo."""
        w, h = self.width(), self.height()
        x = max(pantalla.left() + 4, min(punta_x - w // 2, pantalla.right() - 4 - w))
        y = punta_y - h
        abajo = y < pantalla.top() + 2
        if abajo:
            y = abajo_y
        cola_x = max(14, min(punta_x - x, w - 14))
        if self.cola_abajo == abajo or cola_x != self.cola_x:
            self.cola_abajo = not abajo
            self.cola_x = cola_x
            self.update()
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)

    def tick(self, dt: float) -> bool:
        """Fundido de entrada y salida. Devuelve True mientras está visible."""
        objetivo = 1.0 if time.monotonic() < self.fin else 0.0
        if objetivo and not self.isVisible():
            self.alfa = 0.0
            self.setWindowOpacity(0.0)
            self.show()
        paso = dt / (0.15 if objetivo else 0.35)
        self.alfa = min(objetivo, self.alfa + paso) if objetivo > self.alfa else max(objetivo, self.alfa - paso)
        if self.isVisible():
            self.setWindowOpacity(self.alfa)
            if self.alfa <= 0.0:
                self.hide()
        return self.isVisible()

    # ------------------------------------------------------------ dibujo
    def paintEvent(self, _):
        p = QPainter(self)
        u = 2
        caja = QRect(self._caja)
        if not self.cola_abajo:
            caja.translate(0, COLA)
        self._escalonado(p, caja, BORDE, u)
        self._escalonado(p, caja.adjusted(u, u, -u, -u), RELLENO, u)
        # colita escalonada
        cx = self.cola_x
        borde_y = caja.bottom() + 1 - u if self.cola_abajo else caja.top()
        p.fillRect(cx - 3 * u, borde_y, 6 * u, u, RELLENO)          # abre el borde donde nace la cola
        for i in range(4):
            y = caja.bottom() + 1 + i * u if self.cola_abajo else caja.top() - (i + 1) * u
            ancho = (4 - i) * 2 * u
            p.fillRect(cx - ancho // 2, y, ancho, u, BORDE)
            if ancho > 2 * u:
                p.fillRect(cx - ancho // 2 + u, y, ancho - 2 * u, u, RELLENO)
        # texto
        interior = caja.adjusted(MARGEN + 1, MARGEN, -MARGEN, -MARGEN)
        if self.sub:
            p.setFont(self.fuente_sub)
            p.setPen(SUB)
            p.drawText(interior, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self.sub)
            interior.setTop(interior.top() + self._alto_sub)
        p.setFont(self.fuente)
        p.setPen(TEXTO)
        p.drawText(interior, Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, self.texto)
        p.end()

    @staticmethod
    def _escalonado(p: QPainter, r: QRect, color: QColor, u: int):
        p.fillRect(r.adjusted(2 * u, 0, -2 * u, 0), color)
        p.fillRect(r.adjusted(u, u, -u, -u), color)
        p.fillRect(r.adjusted(0, 2 * u, 0, -2 * u), color)
