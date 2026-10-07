# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Ajustes del cangrejito en config.json (en %APPDATA%\\Cangrejito). Se puede editar a mano."""
from __future__ import annotations

import json
import logging

import rutas

log = logging.getLogger('cangrejito.config')
RUTA = rutas.DATOS / 'config.json'

POR_DEFECTO = {
    'nombre': '',            # cómo te llama (si está vacío, lo pregunta la primera vez)
    'trato': 'masculino',    # masculino («compañero»), femenino («compañera») o neutro (sin frases con género)
    'bebida': 'mate',        # qué toma mientras labura: mate, cafe, te o nada
    'bandera': 'argentina',  # la de la hinchada cuando jugás (o «ninguna»)
    'fechas_argentinas': True,   # ropa, escarapela y curiosidades en las fechas patrias y culturales
    'actividades_juego': True,   # cuando jugás en el otro monitor: joystick, pochoclos, hinchada
    'avisos_uso': True,      # avisa del límite de 5 horas y de la memoria del chat
    'pausas': 0,             # minutos entre pausas activas (estirarse, tomar agua); 0 = nunca
    'generos_apagados': [],  # géneros con los que no se cambia de ropa (folklore, tango, cuarteto, …)
    'artistas_extra': {},    # artistas que sumás a cada género: {"cumbia": ["Mi banda"], …}
    'respiro': 0.7,          # segundos de silencio entre una frase y la siguiente
    'efectos': True,
    'chistes': True,         # de vez en cuando, en los ratos libres, tira un chiste         # sonido del confeti cuando festeja
    'pausas_voz': 1.0,       # cuánto respira entre oraciones (1 = normal, más = más pausado)
    'silencio': False,
    'volumen': 0.5,
    'motor': 'daniela',      # xtts (placa de video, más natural) o daniela (procesador)
    'voz_referencia': None,  # grabación que XTTS imita
    'tono': 1.15,            # Daniela: >1 = más agudo (voz de cangrejito)
    'tono_xtts': 1.06,       # XTTS
    'temperatura': 0.7,      # XTTS: más alto = más expresivo y variable
    'velocidad': 1.05,
    'escala': 3,             # píxeles por unidad del dibujo
    'afk_minutos': 5,
    'charla': False,         # comentarios sueltos cada tanto (apagado: habla solo de lo que hace Claude)
    'habla': 'normal',       # poco (solo lo importante), normal o mucho (y comentarios sueltos)
    'detalle': 'detallado',  # corto (una frase) o detallado (lo que encontró y qué va a probar)
    'groserias': True,       # alguna mala palabra suave de vez en cuando
    'quejas': True,          # se queja un poquito cuando el proyecto viene largo
    'animaciones_musica': True,  # baila con la música (guitarra con folklore, Camaro con phonk)
    'resumen_final': True,   # al terminar, dice la primera frase de la respuesta
    'comentar_musica': True,  # de vez en cuando festeja el tema nuevo de Spotify
    'artistas_funk': [],      # artistas extra con los que se sube al Camaro (además de los de funk/phonk)
    'artistas_guitarra': [],  # artistas extra con los que toca la guitarra de gaucho (además de los de folklore)
    'siempre_visible': False,  # aparecer aunque la app de Claude esté cerrada
    'margen_abajo': None,    # px libres abajo si el sistema no avisa de su barra (None: automático; en WSL, 48)
    'modelo': str(rutas.VOZ / 'es_AR-daniela-high.onnx'),   # voz de Daniela (si no está, la baja)
    'python': '',            # solo corriendo desde el código: el pythonw.exe con PySide6 que usa el lanzador
    'xtts_python': '',       # opcional: pythonw.exe de un entorno con XTTS (coqui-tts); vacío = sin XTTS
    'xtts_modelo': '',       # opcional: carpeta del modelo XTTS (model.pth, config.json, vocab.json)
    'x': None,               # última posición (se guarda sola)
    'pantalla': None,
}


class Config(dict):
    def __init__(self):
        super().__init__(POR_DEFECTO)
        rutas.preparar()
        try:
            if RUTA.exists():
                self.update(json.loads(RUTA.read_text(encoding='utf-8-sig')))
        except Exception:
            log.exception('config.json ilegible: uso los valores por defecto')
        self.guardar()

    def guardar(self):
        try:
            tmp = RUTA.with_suffix('.tmp')
            tmp.write_text(json.dumps(self, ensure_ascii=False, indent=2), encoding='utf-8')
            tmp.replace(RUTA)
        except Exception:
            log.exception('no pude guardar config.json')
