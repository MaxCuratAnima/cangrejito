# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Ventana de Configuración: el nombre, cuánto habla, cómo comenta, su personalidad y la voz.

La primera vez aparece como bienvenida; después se abre desde el menú (clic derecho → Configuración).
Los cambios se aplican al toque: el narrador y la mascota leen la config en cada momento.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QVBoxLayout)

import sprites as S
import version

HABLA = [('poco', 'Poco: solo lo importante (permisos, preguntas y cuando termina)'),
         ('normal', 'Normal: cada paso de Claude'),
         ('mucho', 'Mucho: cada paso, y algún comentario suelto cuando no hay nada')]
DETALLE = [('corto', 'Cortos: una frase'),
           ('detallado', 'Detallados: lo que encontró y qué va a probar')]
# los mismos valores, para el menú del clic derecho (más cortos)
HABLA_MENU = [('poco', 'Poco (solo lo importante)'), ('normal', 'Normal (cada paso)'),
              ('mucho', 'Mucho (y comentarios sueltos)')]
DETALLE_MENU = [('corto', 'Cortos'), ('detallado', 'Detallados')]
VOLUMEN = [(0.25, '25 %'), (0.5, '50 %'), (0.75, '75 %'), (1.0, '100 %')]
# velocidad de la voz: 100 % es la normal (1,05 para Piper)
VELOCIDAD = [(0.84, '80 %'), (0.945, '90 %'), (1.05, '100 % (normal)'), (1.155, '110 %'), (1.31, '125 %')]


def _combo(opciones, actual) -> QComboBox:
    c = QComboBox()
    for valor, texto in opciones:
        c.addItem(texto, valor)
    i = next((k for k, (v, _) in enumerate(opciones) if v == actual), 1)
    c.setCurrentIndex(i)
    return c


class Configuracion(QDialog):
    def __init__(self, cfg, probar_voz=None, bienvenida: bool = False):
        super().__init__(None, Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.cfg = cfg
        self.probar_voz = probar_voz
        self.setWindowTitle('Cangrejito: ¡hola!' if bienvenida else 'Configuración del Cangrejito')
        self.setMinimumWidth(520)

        caja = QVBoxLayout(self)
        arriba = QHBoxLayout()
        dibujo = QLabel()
        img = S.dibujar(S.Pose(brazos=('reposo', 'saludo'), fase_brazos=1, ojos='feliz', boca_forma='sonrisa'))
        img = img.copy(S.OX - 1, S.OY + 6, 36, 24)
        dibujo.setPixmap(QPixmap.fromImage(img.scaled(img.width() * 3, img.height() * 3,
                                                       Qt.AspectRatioMode.KeepAspectRatio,
                                                       Qt.TransformationMode.FastTransformation)))
        arriba.addWidget(dibujo)
        titulo = QLabel('<b>¡Hola! Soy tu cangrejito.</b><br>Te voy a contar en voz alta lo que hace Claude Code.'
                        '<br>Contame cómo querés que sea:' if bienvenida else
                        '<b>Configuración</b><br>Los cambios se aplican al toque.')
        titulo.setWordWrap(True)
        arriba.addWidget(titulo, 1)
        caja.addLayout(arriba)

        # ── vos
        g1 = QGroupBox('Vos')
        f1 = QFormLayout(g1)
        self.nombre = QLineEdit(cfg.get('nombre') or '')
        self.nombre.setPlaceholderText('Tu nombre o apodo')
        self.nombre.setMaxLength(30)
        f1.addRow('¿Cómo te llamo?', self.nombre)
        caja.addWidget(g1)

        # ── cómo habla
        g2 = QGroupBox('Cómo habla')
        f2 = QFormLayout(g2)
        self.habla = _combo(HABLA, cfg.get('habla', 'normal'))
        f2.addRow('¿Cuánto habla?', self.habla)
        self.detalle = _combo(DETALLE, cfg.get('detalle', 'detallado'))
        f2.addRow('Comentarios', self.detalle)
        caja.addWidget(g2)

        # ── personalidad
        g3 = QGroupBox('Personalidad')
        v3 = QVBoxLayout(g3)
        self.groserias = QCheckBox('Puede decir alguna mala palabra suave («¡la puta madre, otra vez no!»)')
        self.groserias.setChecked(bool(cfg.get('groserias', True)))
        self.quejas = QCheckBox('Se queja un poquito cuando un proyecto viene largo (del proyecto, nunca de vos)')
        self.quejas.setChecked(bool(cfg.get('quejas', True)))
        self.musica = QCheckBox('Comenta de vez en cuando el tema que suena en Spotify')
        self.musica.setChecked(bool(cfg.get('comentar_musica', True)))
        self.animaciones = QCheckBox('Se pone a bailar con la música (y guitarra con folklore, Camaro con phonk)')
        self.animaciones.setChecked(bool(cfg.get('animaciones_musica', True)))
        for c in (self.groserias, self.quejas, self.musica, self.animaciones):
            v3.addWidget(c)
        caja.addWidget(g3)

        # ── voz
        g4 = QGroupBox('Voz')
        f4 = QFormLayout(g4)
        self.volumen = QSlider(Qt.Orientation.Horizontal)
        self.volumen.setRange(0, 100)
        self.volumen.setValue(round(float(cfg.get('volumen', 0.5)) * 100))
        f4.addRow('Volumen', self.volumen)
        self.velocidad = _combo(VELOCIDAD, min((v for v, _ in VELOCIDAD),
                                               key=lambda v: abs(v - float(cfg.get('velocidad', 1.05)))))
        fila = QHBoxLayout()
        fila.addWidget(self.velocidad, 1)
        probar = QPushButton('Probar la voz')
        probar.clicked.connect(self._probar)
        fila.addWidget(probar)
        f4.addRow('Velocidad', fila)
        self.silencio = QCheckBox('Sin voz (solo el globo de texto)')
        self.silencio.setChecked(bool(cfg.get('silencio', False)))
        f4.addRow('', self.silencio)
        caja.addWidget(g4)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.button(QDialogButtonBox.StandardButton.Ok).setText('¡Listo!' if bienvenida else 'Guardar')
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)
        caja.addWidget(botones)

        firma = QLabel(f'{version.NOMBRE} {version.VERSION} · Hecho por {version.AUTOR}')
        f = QFont()
        f.setPointSize(8)
        firma.setFont(f)
        firma.setStyleSheet('color: gray')
        firma.setAlignment(Qt.AlignmentFlag.AlignRight)
        caja.addWidget(firma)

    def _aplicar(self):
        c = self.cfg
        c['nombre'] = self.nombre.text().strip()[:30] or c.get('nombre') or 'compa'
        c['habla'] = self.habla.currentData()
        c['detalle'] = self.detalle.currentData()
        c['groserias'] = self.groserias.isChecked()
        c['quejas'] = self.quejas.isChecked()
        c['comentar_musica'] = self.musica.isChecked()
        c['animaciones_musica'] = self.animaciones.isChecked()
        c['volumen'] = self.volumen.value() / 100
        c['velocidad'] = float(self.velocidad.currentData())
        c['silencio'] = self.silencio.isChecked()

    def _probar(self):
        self._aplicar()
        if self.probar_voz:
            self.probar_voz()

    def _guardar(self):
        self._aplicar()
        self.cfg.guardar()
        self.accept()


def abrir(cfg, probar_voz=None, bienvenida: bool = False) -> bool:
    """Muestra la ventana; devuelve True si guardaron. Si cancelan la bienvenida, queda «compa»."""
    copia = dict(cfg)
    v = Configuracion(cfg, probar_voz, bienvenida)
    ok = v.exec() == QDialog.DialogCode.Accepted
    if not ok:
        cfg.clear()
        cfg.update(copia)                      # «Cancelar» deshace lo que se probó
        if bienvenida and not cfg.get('nombre'):
            cfg['nombre'] = 'compa'
        cfg.guardar()
    return ok
