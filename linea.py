# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""statusLine de Claude Code: recibe el estado (límite de 5 horas, contexto) y se lo pasa al cangrejito.
Solo librería estándar; nunca falla."""
import json
import sys
import urllib.request

try:
    datos = json.loads(sys.stdin.buffer.read().decode('utf-8', 'replace') or '{}')
    datos['hook_event_name'] = 'StatusLine'
    urllib.request.urlopen(urllib.request.Request(
        'http://127.0.0.1:47833/evento', json.dumps(datos).encode(), {'Content-Type': 'application/json'}),
        timeout=0.5)
except Exception:
    pass
