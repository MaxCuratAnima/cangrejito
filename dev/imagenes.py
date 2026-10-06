# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Imágenes fijas del proyecto, dibujadas con el mismo código del cangrejito:

  cangrejito.png                      ícono para Linux (menú y autoarranque)
  instalador/asistente-grande.bmp     el cangrejito saludando, a la izquierda del instalador de Windows
  instalador/asistente-chico.bmp      el cangrejito chiquito, arriba a la derecha en cada paso

Uso: python dev/imagenes.py
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter

import sprites as S

FONDO_ARRIBA, FONDO_ABAJO = QColor('#2b2f3a'), QColor('#1a1c22')
NARANJA = QColor('#D97757')


def _cangrejo(pose: S.Pose, escala: int) -> QImage:
    img = S.dibujar(pose)
    return img.scaled(img.width() * escala, img.height() * escala, Qt.AspectRatioMode.KeepAspectRatio,
                      Qt.TransformationMode.FastTransformation)


def icono():
    img = S.dibujar(S.Pose()).copy(S.recorte_cangrejo())
    lado = max(img.width(), img.height())
    cuadro = QImage(lado, lado, QImage.Format.Format_ARGB32)
    cuadro.fill(0)
    p = QPainter(cuadro)
    p.drawImage((lado - img.width()) // 2, (lado - img.height()) // 2, img)
    p.end()
    cuadro.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio,
                  Qt.TransformationMode.FastTransformation).save(str(RAIZ / 'cangrejito.png'))


def asistente_grande():
    """164×314 (el tamaño que pide Inno Setup a escala 100 %), hecho al doble para pantallas grandes."""
    w, h = 328, 628
    img = QImage(w, h, QImage.Format.Format_RGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, FONDO_ARRIBA)
    g.setColorAt(1, FONDO_ABAJO)
    p.fillRect(0, 0, w, h, g)
    # el cangrejito saludando, sobre una «barra de tareas»
    cang = _cangrejo(S.Pose(brazos=('reposo', 'saludo'), fase_brazos=1, ojos='feliz', boca_forma='sonrisa',
                            brillo=True), 7)
    piso = 430
    p.fillRect(0, piso, w, 6, QColor('#3a3f4c'))
    p.drawImage((w - cang.width()) // 2, piso - S.PIES * 7, cang)
    # nombre y autor
    p.setPen(NARANJA)
    f = QFont()
    f.setFamilies(['Segoe UI', 'Noto Sans', 'DejaVu Sans'])
    f.setPixelSize(44)
    f.setBold(True)
    p.setFont(f)
    p.drawText(QRect(0, 60, w, 60), Qt.AlignmentFlag.AlignCenter, 'Cangrejito')
    f.setPixelSize(20)
    f.setBold(False)
    p.setFont(f)
    p.setPen(QColor('#c9ccd4'))
    p.drawText(QRect(16, 120, w - 32, 60), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
               'tu compañero que narra\nlo que hace Claude Code')
    p.setPen(QColor('#9aa0aa'))
    f.setPixelSize(19)
    p.setFont(f)
    p.drawText(QRect(0, h - 70, w, 40), Qt.AlignmentFlag.AlignCenter, 'Hecho por MaxCurat')
    p.end()
    img.save(str(RAIZ / 'instalador' / 'asistente-grande.bmp'))


def asistente_chico():
    """55×55 (a escala 100 %), hecho al doble."""
    lado = 110
    img = QImage(lado, lado, QImage.Format.Format_RGB32)
    img.fill(QColor('#ffffff'))
    cang = S.dibujar(S.Pose(brazos=('reposo', 'saludo'), fase_brazos=1, ojos='feliz', boca_forma='sonrisa'))
    cang = cang.copy(QRect(S.OX - 1, S.OY + 8, 36, 22))
    cang = cang.scaled(lado - 8, lado - 8, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.FastTransformation)
    p = QPainter(img)
    p.drawImage((lado - cang.width()) // 2, (lado - cang.height()) // 2, cang)
    p.end()
    img.save(str(RAIZ / 'instalador' / 'asistente-chico.bmp'))


def banner():
    """docs/banner.png, 1280×640: cabecera del README y vista previa del repo al compartir el link."""
    w, h = 1280, 640
    img = QImage(w, h, QImage.Format.Format_RGB32)
    p = QPainter(img)
    g = QLinearGradient(0, 0, 0, h)
    g.setColorAt(0, FONDO_ARRIBA)
    g.setColorAt(1, FONDO_ABAJO)
    p.fillRect(0, 0, w, h, g)
    piso = 500
    p.fillRect(0, piso, w, h - piso, QColor('#15171c'))
    p.fillRect(0, piso, w, 2, QColor('#3a3f4c'))
    poses = [S.Pose(brazos=('teclado', 'teclado'), fase_brazos=1, mirar=(0, 1), accesorios={'netbook': 1}),
             S.Pose(brazos=('reposo', 'saludo'), fase_brazos=1, ojos='feliz', boca_forma='sonrisa', brillo=True),
             S.Pose(y=-5, patas='sentado', cuerpo_y=3, brazos=('reposo', 'festejo'), boca_forma='sonrisa',
                    mirar=(1, 0), accesorios={'auto': 1, 'lentes': 1}, t=0.2)]
    for x, pose, esc in ((150, poses[0], 6), (520, poses[1], 8), (900, poses[2], 6)):
        c = _cangrejo(pose, esc)
        p.drawImage(x - c.width() // 2 + 120, piso - S.PIES * esc, c)
    f = QFont()
    f.setFamilies(['Segoe UI', 'Noto Sans', 'DejaVu Sans'])
    f.setPixelSize(96)
    f.setBold(True)
    p.setFont(f)
    p.setPen(NARANJA)
    p.drawText(QRect(0, 50, w, 120), Qt.AlignmentFlag.AlignCenter, 'Cangrejito')
    f.setPixelSize(34)
    f.setBold(False)
    p.setFont(f)
    p.setPen(QColor('#d4d7de'))
    p.drawText(QRect(0, 165, w, 50), Qt.AlignmentFlag.AlignCenter,
               'la mascota de escritorio que narra lo que hace Claude Code')
    f.setPixelSize(24)
    p.setFont(f)
    p.setPen(QColor('#9aa0aa'))
    p.drawText(QRect(0, h - 90, w, 40), Qt.AlignmentFlag.AlignCenter, 'Hecho por MaxCurat · Windows y Linux')
    p.end()
    img.save(str(RAIZ / 'docs' / 'banner.png'))


if __name__ == '__main__':
    app = QGuiApplication(sys.argv)
    icono()
    asistente_grande()
    asistente_chico()
    banner()
    print('listo: cangrejito.png, instalador/asistente-*.bmp y docs/banner.png')
