"""Configura Claude Code para que le avise al cangrejito (lo corre el instalador).

  instalar: suma los hooks a ~/.claude/settings.json (con copia de seguridad, sin tocar los otros hooks
            y sin duplicar si se reinstala) y, si se pide, las reglas de narración al CLAUDE.md global.
  quitar:   saca solo lo del cangrejito.

Para pruebas, CANGREJITO_CLAUDE_DIR cambia la carpeta .claude.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

EVENTOS = ['SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PostToolUseFailure',
           'Notification', 'Stop', 'SubagentStart', 'SubagentStop', 'SessionEnd']
INICIO, FIN = '<!-- cangrejito: inicio -->', '<!-- cangrejito: fin -->'
REGLAS = """# Para el cangrejito narrador
Hay una mascota de escritorio (el cangrejito) que lee en voz alta lo que hacés.
- Escribí el `description` de cada comando (Bash/PowerShell) en castellano, breve y diciendo el para qué,
  no solo el qué: «Compilo el proyecto para ver si hay errores», no «Compile files».
- En tareas de varios pasos, antes de cada tanda de herramientas escribí en el chat una o dos frases cortas
  en castellano: qué encontraste, qué vas a probar y por qué, o por qué tarda. El cangrejito lee esas dos
  primeras frases en voz alta; no repitas lo mismo ni narres pasos triviales.
- Las tareas de TodoWrite también en castellano (`content` y `activeForm`)."""


def carpeta_claude() -> Path:
    return Path(os.environ.get('CANGREJITO_CLAUDE_DIR') or Path.home() / '.claude')


def _es_nuestro(h) -> bool:
    return (isinstance(h, dict) and '--avisar' in (h.get('args') or [])
            and 'cangrejito' in str(h.get('command', '')).lower())


def _leer(ruta: Path) -> dict:
    if not ruta.exists():
        return {}
    datos = json.loads(ruta.read_text(encoding='utf-8-sig') or '{}')   # si está roto, no lo toco
    if not isinstance(datos, dict):
        raise ValueError(f'{ruta} no es un objeto JSON')
    return datos


def _escribir(ruta: Path, datos: dict):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + '.tmp')
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(ruta)


def _sacar_hooks(datos: dict):
    hooks = datos.get('hooks')
    if not isinstance(hooks, dict):
        return
    for evento in list(hooks):
        grupos = []
        for g in hooks[evento] if isinstance(hooks[evento], list) else []:
            if isinstance(g, dict) and isinstance(g.get('hooks'), list):
                g = dict(g, hooks=[h for h in g['hooks'] if not _es_nuestro(h)])
                if not g['hooks']:
                    continue
            grupos.append(g)
        if grupos:
            hooks[evento] = grupos
        else:
            del hooks[evento]
    if not hooks:
        del datos['hooks']


def _bloque_claude_md(poner: bool):
    ruta = carpeta_claude() / 'CLAUDE.md'
    texto = ruta.read_text(encoding='utf-8-sig') if ruta.exists() else ''
    if INICIO in texto and FIN in texto:
        antes, resto = texto.split(INICIO, 1)
        texto = antes.rstrip('\n') + resto.split(FIN, 1)[1]
    if poner:
        texto = (texto.rstrip('\n') + '\n\n' if texto.strip() else '') + f'{INICIO}\n{REGLAS}\n{FIN}\n'
    if texto.strip():
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(texto, encoding='utf-8')
    elif ruta.exists():
        ruta.unlink()                  # solo tenía lo del cangrejito: no deja un archivo vacío


def instalar(exe: str, narracion: bool = False):
    ruta = carpeta_claude() / 'settings.json'
    datos = _leer(ruta)
    copia = ruta.with_name('settings.antes-del-cangrejito.json')
    if ruta.exists() and not copia.exists():
        copia.write_bytes(ruta.read_bytes())
    _sacar_hooks(datos)
    hooks = datos.setdefault('hooks', {})
    for evento in EVENTOS:
        hooks.setdefault(evento, []).append(
            {'hooks': [{'type': 'command', 'command': exe, 'args': ['--avisar'], 'timeout': 5, 'async': True}]})
    _escribir(ruta, datos)
    _bloque_claude_md(narracion)


def quitar():
    ruta = carpeta_claude() / 'settings.json'
    if ruta.exists():
        datos = _leer(ruta)
        _sacar_hooks(datos)
        _escribir(ruta, datos)
    _bloque_claude_md(False)


def desde_consola(args: list) -> int:
    try:
        if '--quitar-hooks' in args:
            quitar()
            return 0
        exe = args[args.index('--exe') + 1] if '--exe' in args else sys.executable
        instalar(exe, narracion='--narracion' in args)
        if '--siempre-visible' in args:
            from config import Config
            cfg = Config()
            cfg['siempre_visible'] = True
            cfg.guardar()
        return 0
    except Exception as e:                       # el instalador avisa si sale distinto de 0
        try:
            import rutas
            rutas.DATOS.mkdir(parents=True, exist_ok=True)
            (rutas.DATOS / 'error-instalacion.txt').write_text(repr(e), encoding='utf-8')
        except Exception:
            pass
        return 1


if __name__ == '__main__':
    sys.exit(desde_consola(sys.argv[1:]))
