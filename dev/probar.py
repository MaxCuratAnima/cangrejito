"""Pruebas a mano: manda eventos falsos al cangrejito como si fueran de Claude Code.

  python dev/probar.py <escena>     escenas: leer, editar, comando, buscar, web, pregunta, permiso,
                                    error, listo, pedido, ayudante, fin-ayudante, sesion
  python dev/probar.py ventana      dice dónde está la ventana y si la parte transparente deja pasar el clic
"""
import ctypes
import ctypes.wintypes as wt
import json
import subprocess
import sys
from pathlib import Path

AVISAR = Path(__file__).resolve().parent.parent / 'avisar.py'
BASE = {'session_id': 'prueba', 'transcript_path': '', 'cwd': 'C:/'}

ESCENAS = {
    'pedido': {'hook_event_name': 'UserPromptSubmit', 'prompt': 'hola'},
    'leer': {'hook_event_name': 'PreToolUse', 'tool_name': 'Read', 'tool_input': {'file_path': 'C:/x/servidor.py'}},
    'editar': {'hook_event_name': 'PreToolUse', 'tool_name': 'Edit', 'tool_input': {'file_path': 'C:/x/app.js'}},
    'comando': {'hook_event_name': 'PreToolUse', 'tool_name': 'PowerShell',
                'tool_input': {'command': 'dir', 'description': 'Lista los archivos de la carpeta del curso'}},
    'buscar': {'hook_event_name': 'PreToolUse', 'tool_name': 'Grep', 'tool_input': {'pattern': 'x'}},
    'web': {'hook_event_name': 'PreToolUse', 'tool_name': 'WebSearch', 'tool_input': {'query': 'x'}},
    'pregunta': {'hook_event_name': 'PreToolUse', 'tool_name': 'AskUserQuestion', 'tool_input': {}},
    'permiso': {'hook_event_name': 'Notification', 'notification_type': 'permission_prompt', 'message': 'x'},
    'error': {'hook_event_name': 'PostToolUseFailure', 'tool_name': 'Bash', 'error': 'exit code 1'},
    'listo': {'hook_event_name': 'Stop', 'last_assistant_message':
              'Listo: el cangrejito ya camina por la barra de tareas y habla con la voz de Daniela.\n\n'
              '**Detalles** en `C:\\proyectos\\cangrejito\\mascota.py`.'},
    'ayudante': {'hook_event_name': 'SubagentStart', 'agent_type': 'Explore'},
    'fin-ayudante': {'hook_event_name': 'SubagentStop', 'agent_type': 'Explore'},
    'sesion': {'hook_event_name': 'SessionStart', 'source': 'startup'},
}


def mandar(escena: str, n: int = 0):
    d = dict(BASE, **ESCENAS[escena])
    if d['hook_event_name'].startswith(('PreToolUse', 'PostToolUse')):
        d['tool_use_id'] = f'toolu_prueba_{escena}_{n}'
    subprocess.run([sys.executable, '-S', str(AVISAR)], input=json.dumps(d).encode(), check=False)


def ventana():
    import psutil
    u = ctypes.windll.user32
    pids = {p.pid for p in psutil.process_iter(['cmdline'])
            if any('cangrejito.pyw' in (c or '') for c in (p.info['cmdline'] or []))}
    ENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    halladas = []

    def cb(h, _):
        pid = wt.DWORD()
        u.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value in pids and u.IsWindowVisible(h):
            r = wt.RECT()
            u.GetWindowRect(h, ctypes.byref(r))
            halladas.append((h, (r.left, r.top, r.right, r.bottom)))
        return True

    u.EnumWindows(ENUM(cb), 0)
    u.WindowFromPoint.argtypes = [wt.POINT]
    u.WindowFromPoint.restype = wt.HWND
    u.GetAncestor.restype = wt.HWND
    for h, (l, t, r, b) in halladas:
        print('ventana', h, (l, t, r, b), f'{r - l}x{b - t}')
        for nombre, (x, y) in {'esquina transparente': (l + 3, t + 3),
                               'centro del cuerpo': ((l + r) // 2, t + (b - t) * 32 // 45)}.items():
            debajo = u.GetAncestor(u.WindowFromPoint(wt.POINT(x, y)), 2)
            print(f'  {nombre}: {"la toma el cangrejito" if debajo == h else "pasa de largo"}')


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'ventana'
    if arg == 'ventana':
        ventana()
    else:
        for i, e in enumerate(arg.split(',')):
            mandar(e, i)
