# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Servidor HTTP local que recibe los eventos de Claude Code (vía avisar.py)."""
from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6.QtCore import QObject, Signal

log = logging.getLogger('cangrejito.eventos')
PUERTO = 47833
HOSTS_OK = {f'127.0.0.1:{PUERTO}', f'localhost:{PUERTO}'}


class Receptor(QObject):
    evento = Signal(dict)


def arrancar(receptor: Receptor) -> ThreadingHTTPServer | None:
    """Levanta el servidor en un hilo. Devuelve None si el puerto está ocupado (ya hay otro cangrejito)."""

    class Manejador(BaseHTTPRequestHandler):
        def do_POST(self):
            # Solo avisar.py: nada de páginas web (traen Origin) ni otros nombres de host.
            if self.headers.get('Origin') or self.headers.get('Host') not in HOSTS_OK or self.path != '/evento':
                self.send_response(403)
                self.end_headers()
                return
            try:
                largo = int(self.headers.get('Content-Length') or 0)
                datos = json.loads(self.rfile.read(min(largo, 8_000_000)) or b'{}')
                if isinstance(datos, dict):
                    receptor.evento.emit(datos)
            except Exception:
                log.exception('evento ilegible')
            self.send_response(204)
            self.end_headers()

        def log_message(self, *a):
            pass

    try:
        srv = ThreadingHTTPServer(('127.0.0.1', PUERTO), Manejador)
    except OSError:
        return None
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True, name='eventos').start()
    log.info('escuchando en 127.0.0.1:%s', PUERTO)
    return srv
