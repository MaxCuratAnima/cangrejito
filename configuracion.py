# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Ventana de Configuración: quién sos, cómo habla, su música, las fechas argentinas y la voz.

La primera vez aparece como bienvenida; después se abre desde el menú (clic derecho → Configuración).
Los cambios se aplican al toque: el narrador y la mascota leen la config en cada momento.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider, QTabWidget, QVBoxLayout,
                               QWidget)

import sprites as S
import version

HABLA = [('poco', 'Poco: solo lo importante (permisos, preguntas y cuando termina)'),
         ('normal', 'Normal: cada paso de Claude'),
         ('mucho', 'Mucho: cada paso, y algún comentario suelto cuando no hay nada')]
DETALLE = [('corto', 'Cortos: una frase'),
           ('detallado', 'Detallados: lo que encontró y qué va a probar')]
TRATO = [('masculino', 'Masculino («compañero»)'), ('femenino', 'Femenino («compañera»)'),
         ('neutro', 'Neutro (sin frases con género)')]
BEBIDA = [('mate', 'Mate (con termo y todo)'), ('cafe', 'Café'), ('te', 'Té'), ('nada', 'Nada')]
BANDERA = S.NOMBRES_BANDERAS + [('ninguna', 'Ninguna (no alienta con bandera)')]
PAUSAS = [(0, 'Nunca'), (45, 'Cada 45 minutos'), (60, 'Cada hora'), (90, 'Cada hora y media'),
          (120, 'Cada 2 horas')]
# géneros: con cada uno se pone su ropa y toca su instrumento (vigilante.genero_musical)
GENEROS = [('folklore', 'Folklore: gaucho con la guitarra criolla'),
           ('tango', 'Tango: funyi, pañuelo blanco y bandoneón'),
           ('cuarteto', 'Cuarteto: camisa con brillos y a bailar'),
           ('cumbia', 'Cumbia: gorrita, camiseta albiceleste y teclado'),
           ('rock', 'Rock nacional: campera de cuero, lentes y eléctrica'),
           ('trap', 'Trap: gorra, cadena, lentes y micrófono'),
           ('funk', 'Funk y phonk: el Camaro blanco con lentes'),
           ('electronica', 'Electrónica (Daft Punk): casco de robot y baile a tirones'),
           ('disco', 'Disco: bola de espejos y pose de Travolta'),
           ('reggae', 'Reggae: gorro rasta y meneo relajado'),
           ('metal', 'Metal: melena larga y cabeceo'),
           ('clasica', 'Clásica: peluca blanca y dirige la orquesta')]
# los mismos valores, para el menú del clic derecho (más cortos)
HABLA_MENU = [('poco', 'Poco (solo lo importante)'), ('normal', 'Normal (cada paso)'),
              ('mucho', 'Mucho (y comentarios sueltos)')]
DETALLE_MENU = [('corto', 'Cortos'), ('detallado', 'Detallados')]
TRATO_MENU = [('masculino', 'Compañero'), ('femenino', 'Compañera'), ('neutro', 'Neutro')]
BEBIDA_MENU = [('mate', 'Mate'), ('cafe', 'Café'), ('te', 'Té'), ('nada', 'Nada')]
VOLUMEN = [(0.25, '25 %'), (0.5, '50 %'), (0.75, '75 %'), (1.0, '100 %')]
# velocidad de la voz: 100 % es la normal (1,05 para Piper)
VELOCIDAD = [(0.84, '80 %'), (0.945, '90 %'), (1.05, '100 % (normal)'), (1.155, '110 %'), (1.31, '125 %')]
# cuánto respira entre oraciones y entre una frase y la siguiente
RESPIRA = [(0.7, 'Poco (más de corrido)'), (1.0, 'Normal'), (1.4, 'Bastante (más pausado)')]


def _combo(opciones, actual) -> QComboBox:
    c = QComboBox()
    for valor, texto in opciones:
        c.addItem(texto, valor)
    i = next((k for k, (v, _) in enumerate(opciones) if v == actual), min(1, len(opciones) - 1))
    c.setCurrentIndex(i)
    return c


def _cercano(opciones, actual: float):
    return min((v for v, _ in opciones), key=lambda v: abs(v - float(actual)))


def _pestana(*grupos) -> QWidget:
    w = QWidget()
    v = QVBoxLayout(w)
    for g in grupos:
        v.addWidget(g)
    v.addStretch(1)
    return w


class Configuracion(QDialog):
    def __init__(self, cfg, probar_voz=None, bienvenida: bool = False):
        super().__init__(None, Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint)
        self.cfg = cfg
        self.probar_voz = probar_voz
        self.setWindowTitle('Cangrejito: ¡hola!' if bienvenida else 'Configuración del Cangrejito')
        self.setMinimumWidth(560)

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
                        '<br>Contame cómo querés que sea (después lo cambiás con clic derecho):' if bienvenida else
                        '<b>Configuración</b><br>Los cambios se aplican al toque.')
        titulo.setWordWrap(True)
        arriba.addWidget(titulo, 1)
        caja.addLayout(arriba)
        pestanas = QTabWidget()
        caja.addWidget(pestanas)

        # ── vos
        g = QGroupBox('Vos')
        f = QFormLayout(g)
        self.nombre = QLineEdit(cfg.get('nombre') or '')
        self.nombre.setPlaceholderText('Tu nombre o apodo')
        self.nombre.setMaxLength(30)
        f.addRow('¿Cómo te llamo?', self.nombre)
        self.trato = _combo(TRATO, cfg.get('trato', 'masculino'))
        f.addRow('¿Cómo te trato?', self.trato)
        self.bebida = _combo(BEBIDA, cfg.get('bebida', 'mate'))
        f.addRow('¿Qué tomamos mientras laburamos?', self.bebida)
        self.bandera = _combo(BANDERA, cfg.get('bandera', 'argentina'))
        f.addRow('Tu bandera (para alentarte)', self.bandera)
        pestanas.addTab(_pestana(g), 'Vos')

        # ── cómo habla y personalidad
        g1 = QGroupBox('Cómo habla')
        f1 = QFormLayout(g1)
        self.habla = _combo(HABLA, cfg.get('habla', 'normal'))
        f1.addRow('¿Cuánto habla?', self.habla)
        self.detalle = _combo(DETALLE, cfg.get('detalle', 'detallado'))
        f1.addRow('Comentarios', self.detalle)
        self.pausas = _combo(PAUSAS, int(cfg.get('pausas', 0) or 0))
        f1.addRow('Pausas activas (estirarse, agua)', self.pausas)
        g2 = QGroupBox('Personalidad')
        v2 = QVBoxLayout(g2)
        self.groserias = QCheckBox('Puede decir alguna mala palabra suave («¡la puta madre, otra vez no!»)')
        self.groserias.setChecked(bool(cfg.get('groserias', True)))
        self.quejas = QCheckBox('Se queja un poquito cuando un proyecto viene largo (del proyecto, nunca de vos)')
        self.quejas.setChecked(bool(cfg.get('quejas', True)))
        self.avisos = QCheckBox('Avisa del límite de 5 horas y de cuándo conviene compactar el chat')
        self.avisos.setChecked(bool(cfg.get('avisos_uso', True)))
        self.chats = QCheckBox('Comenta también los chats normales de Claude (no solo Claude Code)')
        self.chats.setChecked(bool(cfg.get('chats_normales', False)))
        self.juego = QCheckBox('Cuando jugás en el otro monitor, juega con vos, come pochoclos y te alienta')
        self.juego.setChecked(bool(cfg.get('actividades_juego', True)))
        self.chistes = QCheckBox('Cada tanto, en los ratos libres, tira un chiste (con «Cuánto habla: mucho»)')
        self.chistes.setChecked(bool(cfg.get('chistes', True)))
        for c in (self.groserias, self.quejas, self.chistes, self.chats, self.avisos, self.juego):
            v2.addWidget(c)
        pestanas.addTab(_pestana(g1, g2), 'Cómo habla')

        # ── música: un renglón por género, con su ropa, y artistas propios para sumar
        g3 = QGroupBox('Música (Spotify)')
        v3 = QVBoxLayout(g3)
        self.musica = QCheckBox('Comenta de vez en cuando el tema que suena')
        self.musica.setChecked(bool(cfg.get('comentar_musica', True)))
        self.animaciones = QCheckBox('Se pone a bailar y se viste según la música')
        self.animaciones.setChecked(bool(cfg.get('animaciones_musica', True)))
        v3.addWidget(self.musica)
        v3.addWidget(self.animaciones)
        g4 = QGroupBox('Géneros (y artistas tuyos para sumar, separados por coma)')
        f4 = QFormLayout(g4)
        apagados = set(cfg.get('generos_apagados') or ())
        extra = cfg.get('artistas_extra') or {}
        viejos = {'funk': cfg.get('artistas_funk') or [], 'folklore': cfg.get('artistas_guitarra') or []}
        self.generos = {}
        for clave, texto in GENEROS:
            si = QCheckBox(texto)
            si.setChecked(clave not in apagados)
            artistas = QLineEdit(', '.join(list(extra.get(clave) or []) or viejos.get(clave, [])))
            artistas.setPlaceholderText('Ej.: mi banda favorita, otro artista')
            f4.addRow(si)
            f4.addRow('    Artistas:', artistas)
            self.generos[clave] = (si, artistas)
        pestanas.addTab(_pestana(g3, g4), 'Música')

        # ── fechas argentinas
        g5 = QGroupBox('Fechas patrias y culturales')
        v5 = QVBoxLayout(g5)
        self.fechas = QCheckBox('Se viste para las fechas patrias (escarapela, galera, bicornio…), iza la bandera '
                                'el 20 de junio, come ñoquis el 29 y cuenta curiosidades de cada día')
        self.fechas.setChecked(bool(cfg.get('fechas_argentinas', True)))
        self.fechas.setStyleSheet('QCheckBox { spacing: 8px; }')
        explica = QLabel('Es un cangrejito hecho por argentinos. Los días de memoria (24 de marzo y '
                         '2 de abril) no festeja ni hace chistes.')
        explica.setWordWrap(True)
        v5.addWidget(self.fechas)
        v5.addWidget(explica)
        pestanas.addTab(_pestana(g5), 'Argentina')

        # ── voz
        g6 = QGroupBox('Voz')
        f6 = QFormLayout(g6)
        self.volumen = QSlider(Qt.Orientation.Horizontal)
        self.volumen.setRange(0, 100)
        self.volumen.setValue(round(float(cfg.get('volumen', 0.5)) * 100))
        f6.addRow('Volumen', self.volumen)
        self.velocidad = _combo(VELOCIDAD, _cercano(VELOCIDAD, cfg.get('velocidad', 1.05)))
        f6.addRow('Velocidad', self.velocidad)
        self.respira = _combo(RESPIRA, _cercano(RESPIRA, cfg.get('pausas_voz', 1.0)))
        f6.addRow('Pausas para respirar', self.respira)
        self.efectos = QCheckBox('Efectos de sonido (el confeti cuando festeja)')
        self.efectos.setChecked(bool(cfg.get('efectos', True)))
        f6.addRow('', self.efectos)
        fila = QHBoxLayout()
        self.silencio = QCheckBox('Sin voz (solo el globo de texto)')
        self.silencio.setChecked(bool(cfg.get('silencio', False)))
        fila.addWidget(self.silencio, 1)
        probar = QPushButton('Probar la voz')
        probar.clicked.connect(self._probar)
        fila.addWidget(probar)
        f6.addRow('', fila)
        pestanas.addTab(_pestana(g6), 'Voz')

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        botones.button(QDialogButtonBox.StandardButton.Ok).setText('¡Listo!' if bienvenida else 'Guardar')
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)
        caja.addWidget(botones)

        firma = QLabel(f'{version.NOMBRE} {version.VERSION} · Hecho por {version.AUTOR}')
        fuente = QFont()
        fuente.setPointSize(8)
        firma.setFont(fuente)
        firma.setStyleSheet('color: gray')
        firma.setAlignment(Qt.AlignmentFlag.AlignRight)
        caja.addWidget(firma)

    def _aplicar(self):
        c = self.cfg
        c['nombre'] = self.nombre.text().strip()[:30] or c.get('nombre') or 'compa'
        c['trato'] = self.trato.currentData()
        c['bebida'] = self.bebida.currentData()
        c['bandera'] = self.bandera.currentData()
        c['habla'] = self.habla.currentData()
        c['detalle'] = self.detalle.currentData()
        c['pausas'] = int(self.pausas.currentData())
        c['groserias'] = self.groserias.isChecked()
        c['quejas'] = self.quejas.isChecked()
        c['avisos_uso'] = self.avisos.isChecked()
        c['chats_normales'] = self.chats.isChecked()
        c['chistes'] = self.chistes.isChecked()
        c['actividades_juego'] = self.juego.isChecked()
        c['comentar_musica'] = self.musica.isChecked()
        c['animaciones_musica'] = self.animaciones.isChecked()
        c['generos_apagados'] = [k for k, (si, _) in self.generos.items() if not si.isChecked()]
        c['artistas_extra'] = {k: [a.strip() for a in campo.text().split(',') if a.strip()]
                               for k, (_, campo) in self.generos.items() if campo.text().strip()}
        c['artistas_funk'] = c['artistas_extra'].get('funk', [])          # los nombres viejos, por las dudas
        c['artistas_guitarra'] = c['artistas_extra'].get('folklore', [])
        c['fechas_argentinas'] = self.fechas.isChecked()
        c['volumen'] = self.volumen.value() / 100
        c['velocidad'] = float(self.velocidad.currentData())
        c['pausas_voz'] = float(self.respira.currentData())
        c['respiro'] = round(0.7 * float(self.respira.currentData()), 2)
        c['silencio'] = self.silencio.isChecked()
        c['efectos'] = self.efectos.isChecked()

    def _probar(self):
        self._aplicar()
        if self.probar_voz:
            self.probar_voz()

    def _guardar(self):
        self._aplicar()
        self.cfg.guardar()
        self.accept()

    def showEvent(self, e):
        super().showEvent(e)
        self.raise_()                          # arriba de todo, también del cangrejito
        self.activateWindow()


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
