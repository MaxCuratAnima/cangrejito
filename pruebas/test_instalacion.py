# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Instalar y quitar los hooks de Claude Code no rompe la configuración de nadie."""
import json

import instalar_claude as I


def test_instalar_y_quitar_deja_todo_como_estaba():
    carpeta = I.carpeta_claude()
    carpeta.mkdir(parents=True, exist_ok=True)
    original = {'model': 'opus', 'hooks': {'Stop': [{'hooks': [{'type': 'command', 'command': 'otra.exe'}]}]}}
    (carpeta / 'settings.json').write_text(json.dumps(original), encoding='utf-8')
    (carpeta / 'CLAUDE.md').write_text('# Mis reglas\n', encoding='utf-8')

    exe = '/opt/Cangrejito/Cangrejito'
    I.instalar(exe, narracion=True)
    I.instalar(exe, narracion=True)                       # reinstalar no duplica
    d = json.loads((carpeta / 'settings.json').read_text(encoding='utf-8'))
    assert set(d['hooks']) == set(I.EVENTOS)
    assert sum(1 for g in d['hooks']['PreToolUse'] for h in g['hooks'] if h['command'] == exe) == 1
    assert [h['command'] for g in d['hooks']['Stop'] for h in g['hooks']] == ['otra.exe', exe]
    assert (carpeta / 'CLAUDE.md').read_text(encoding='utf-8').count(I.INICIO) == 1
    assert (carpeta / 'settings.antes-del-cangrejito.json').exists()

    I.quitar()
    assert json.loads((carpeta / 'settings.json').read_text(encoding='utf-8')) == original
    assert (carpeta / 'CLAUDE.md').read_text(encoding='utf-8').strip() == '# Mis reglas'


def test_settings_roto_no_se_toca():
    carpeta = I.carpeta_claude()
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / 'settings.json').write_text('{esto no es json', encoding='utf-8')
    assert I.desde_consola(['--instalar-hooks', '--exe', 'x']) == 1
    assert (carpeta / 'settings.json').read_text(encoding='utf-8') == '{esto no es json'
