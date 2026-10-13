# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Los chats normales de Claude (los que no son de Claude Code): no mandan avisos, así que el cangrejito
los lee de la ventana de la app con la accesibilidad de Windows (UI Automation), igual que un lector de
pantalla. Solo lee la última respuesta que se ve; no escribe, no hace clic y no manda nada a ningún lado.

  escribiendo   Claude empezó a escribir una respuesta
  respondio     terminó (el texto no cambió en unos segundos): el narrador la comenta

Solo mira mientras la app de Claude está abierta y a la vista, y deja pasar las sesiones de Claude Code
(esas ya las cuentan los hooks). Cuesta unos milisegundos cada 3 segundos; en Linux no hace nada.
"""
from __future__ import annotations

import ctypes
import logging
import sys
import threading
import time

from PySide6.QtCore import QObject, Signal

log = logging.getLogger('cangrejito.chats')

CADA = 3.0                  # segundos entre una mirada y otra (si Claude está al frente)
CADA_ATRAS = 9.0            # y si no está al frente
GRACIA = 6.0                # segundos tras cambiar de chat en que lo que aparece se da por ya leído
ESTABLE = 4.5               # segundos sin cambios para dar por terminada la respuesta
MARCAS = ('claude respondió', 'claude said', 'claude responded')     # lo que dice el lector de pantalla
USUARIO = ('tú dijiste', 'you said', 'usted dijo')
RUIDO = ('presiona tab', 'conectores:', 'memoria:', 'press tab', 'connectors:', 'memory:')
BOTONES = {'copiar', 'copy', 'reintentar', 'retry', 'compartir', 'share', 'editar', 'edit', 'regenerar',
           'buena respuesta', 'mala respuesta', 'good response', 'bad response', 'good', 'bad', 'más', 'more',
           'mostrar más', 'show more', 'ver más', 'ver menos', 'show less', 'pensando', 'thinking', 'claude'}
TEXTO, ITEM, DOCUMENTO = 50020, 50007, 50030


def nombre_del_chat(titulo: str) -> str:
    """El título de la página sin el «- Claude» del final; vacío si es el genérico (chat nuevo, inicio)."""
    t = (titulo or '').strip()
    for sufijo in (' - Claude', ' | Claude', ' – Claude', ' — Claude'):
        if t.lower().endswith(sufijo.lower()):
            t = t[:-len(sufijo)].strip()
    if t.lower() in ('', 'claude', 'new chat', 'nuevo chat', 'nueva conversación', 'inicio', 'home'):
        return ''
    return t[:60]                         # tipos de control de UI Automation


def _al_frente(hwnd: int) -> bool:
    return ctypes.windll.user32.GetForegroundWindow() == hwnd


def _ventana_claude() -> int:
    """La ventana principal de la app de Claude (visible y no minimizada), o 0."""
    u = ctypes.windll.user32
    hallada = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(h, _):
        if u.IsWindowVisible(h) and not u.IsIconic(h):
            n = u.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            c = ctypes.create_unicode_buffer(64)
            u.GetClassNameW(h, c, 64)
            if b.value == 'Claude' and c.value == 'Chrome_WidgetWin_1':
                hallada.append(h)
        return True

    u.EnumWindows(cb, 0)
    return hallada[0] if hallada else 0


class _Uia:
    def __init__(self):
        import comtypes.client
        comtypes.client.GetModule('UIAutomationCore.dll')
        from comtypes.gen import UIAutomationClient as U
        self.U = U
        self.uia = comtypes.client.CreateObject('{ff48dba4-60ef-4201-aa87-54103eef594e}',
                                                interface=U.IUIAutomation)

    def leer(self, hwnd: int):
        """(título de la página, texto de la última respuesta de Claude) o (título, '') si no hay."""
        raiz = self.uia.ElementFromHandle(hwnd)
        els = raiz.FindAll(self.U.TreeScope_Descendants, self.uia.CreateTrueCondition())
        n = els.Length
        titulo = ''
        for i in range(min(n, 60)):
            e = els.GetElement(i)
            if e.CurrentControlType == DOCUMENTO and e.CurrentName:
                titulo = e.CurrentName
                break
        # desde el final hasta la última marca «Claude respondió»
        marca = -1
        for i in range(n - 1, max(-1, n - 700), -1):
            nombre = (els.GetElement(i).CurrentName or '').strip().lower()
            if nombre.startswith(MARCAS):
                marca = i
                break
        if marca < 0:
            return titulo, ''
        partes, vistos = [], set()
        for i in range(marca + 1, min(n, marca + 80)):
            e = els.GetElement(i)
            nombre = (e.CurrentName or '').strip()
            bajo = nombre.lower()
            if bajo.startswith(USUARIO):
                break
            if len(nombre) < 3 or bajo in BOTONES or bajo.startswith(RUIDO) or any(r in bajo for r in RUIDO):
                continue
            if e.CurrentControlType in (TEXTO, ITEM) and nombre not in vistos:
                vistos.add(nombre)
                partes.append(nombre)
        return titulo, ' '.join(partes)[:2000]


class LectorChats(QObject):
    escribiendo = Signal(str)   # el nombre del chat
    respondio = Signal(str, str)  # el nombre del chat y lo que respondió Claude
    cancelado = Signal()        # dejó de escribir sin terminar (cambió de chat, se cerró la app…)

    def __init__(self, cfg, app_abierta_fn):
        super().__init__()
        self.cfg = cfg
        self.app_abierta = app_abierta_fn
        self._hilo = None

    def arrancar(self):
        if sys.platform != 'win32' or self._hilo is not None:
            return
        self._hilo = threading.Thread(target=self._correr, name='lector-chats', daemon=True)
        self._hilo.start()

    def _correr(self):
        try:
            import comtypes
            comtypes.CoInitialize()
            uia = _Uia()
        except Exception:
            log.exception('no pude armar la lectura de los chats')
            return
        titulo_ant, texto_ant, hablado = None, '', ''
        cambio, avisado, gracia = 0.0, False, 0.0
        pausa = CADA
        while True:
            time.sleep(pausa)
            pausa = CADA
            try:
                if not (self.cfg.get('chats_normales', False) and self.app_abierta()):
                    titulo_ant = None
                    if avisado:
                        avisado = False
                        self.cancelado.emit()
                    continue
                hwnd = _ventana_claude()
                if not hwnd:
                    if avisado:
                        avisado = False
                        self.cancelado.emit()
                    continue
                if not _al_frente(hwnd):
                    pausa = CADA_ATRAS                        # de fondo: mira poco (cada lectura despierta a la app)
                titulo, texto = uia.leer(hwnd)
                if 'claude code' in titulo.lower():          # las sesiones de Claude Code ya llegan por hooks
                    titulo_ant = None
                    if avisado:
                        avisado = False
                        self.cancelado.emit()
                    continue
                ahora = time.monotonic()
                if titulo != titulo_ant:                      # otro chat (o recién arranca): sin comentar lo viejo
                    if avisado:
                        self.cancelado.emit()
                    titulo_ant, texto_ant, hablado, avisado = titulo, texto, texto, False
                    gracia = ahora + GRACIA                   # el árbol se arma de a poco: lo que aparezca ya existía
                    continue
                if ahora < gracia:
                    texto_ant = hablado = texto
                    cambio = ahora
                    continue
                if texto != texto_ant:
                    texto_ant, cambio = texto, ahora
                    if texto and texto != hablado and not avisado:
                        avisado = True
                        self.escribiendo.emit(nombre_del_chat(titulo))
                elif texto and texto != hablado and ahora - cambio >= ESTABLE:
                    hablado, avisado = texto, False
                    log.info('chat: respondió Claude (%d caracteres)', len(texto))
                    self.respondio.emit(nombre_del_chat(titulo), texto)
            except Exception:
                log.debug('lectura de chat falló', exc_info=True)
                time.sleep(5)
