# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Cómo salió una tarea, según lo que escribió Claude al final: 'ok', 'casi' (bastante bien, no perfecto),
'regular' (a medias) o 'mal' (falló). Solo mira el texto y si lo último que hizo fue un error: si no hay
pistas claras, es 'ok' (mejor festejar de más que sacarle el gusto a algo que salió bien)."""
import re

_NO = r'(?:no|nunca|tampoco)\s+(?:\w+\s+){0,2}?'
MAL = re.compile(
    _NO + r'(?:pude|logr[eéó]|consegu[ií]|funcion[óo]|anduvo|sali[óo]|se pudo|fue posible|termin[eé]|resolv[ií])\b'
    r'|(?<!que )\bfall[óo]\b|\bfallaron\b|\bfallido\b|\bsigue(?:n)? (?:fallando|sin funcionar|roto)\b'
    r'|\bno (?:funciona|anda|compila|arranca)\b|\bimposible\b|\bme (?:trab[eé]|rend[ií]|qued[eé] sin)\b'
    r'|\bno hay forma\b|\bbloquead[oa]\b|\bno cumpl', re.I)
REGULAR = re.compile(
    r'\ba medias\b|\bparcialmente\b|\bresultado parcial\b|\b(?:es|fue|qued[óo]) parcial\b|\bno del todo\b|\bsin terminar\b|\bme falt[óo]\b|\bfalt[óo]\b'
    r'|\bsolo (?:pude|logr[eé]|se pudo|funcion[óo])\b|\bqued(?:a|an|ó|aron) (?:pendiente|sin|por hacer)s?\b'
    r'|\bno llegu[eé]\b|\bquedó a mitad\b|\bpor la mitad\b', re.I)
CASI = re.compile(
    r'\bsalvo\b|\bexcepto\b|\bdetalles? (?:menor|chic|menores|chicos)\w*\b|\bpeque[ñn]os? (?:detalles?|problemas?|errores?)\b'
    r'|\bno es perfecto\b|\bcasi (?:todo|listo|perfecto)\b|\bmayormente\b|\ben su mayor[ií]a\b|\bla mayor[ií]a\b'
    r'|\badvertencias?\b|\bwarnings?\b|\bquedan? (?:algunos|unos|un par)\b|\bsolo (?:queda|falta)n? (?:un|una|algunos|unos)\b'
    r'|\bsalvo que\b|\bcon (?:algunos|un par de) (?:detalles|errores|pendientes)\b', re.I)
EXITO = re.compile(r'\b(?:listo|termin[eé]|terminado|hecho|funciona(?:ndo)?|anda|pas[óo]|pasan|sin errores|todo ok|qued[óo] (?:bien|perfecto|impecable))\b', re.I)


# lo que no cuenta: «si algo no funciona, avisame», «sin warnings», «no faltó nada»
CONDICIONAL = re.compile(r'^\s*[¿"«(]*(?:si|por si|en caso de|cuando|ante cualquier)\b', re.I)
NEGADO = re.compile(r'\bsin\s+(?:\w+\s+)?(?:warnings?|advertencias?|errores|problemas|fallos?)\b|\bno falt[óo] nada\b'
                    r'|\bno hubo (?:\w+\s+)?(?:errores|problemas|fallos?)\b', re.I)


def _util(texto: str) -> str:
    """El texto sin las oraciones condicionales ni las frases negadas que parecen malas noticias y no lo son."""
    oraciones = re.split(r'(?<=[.!?])\s+|\n+', texto)
    return NEGADO.sub(' ', ' '.join(o for o in oraciones if not CONDICIONAL.match(o)))


def clasificar(texto: str, ultimo_fallo: bool = False) -> str:
    """'mal', 'regular', 'casi' u 'ok'. «ultimo_fallo»: lo último que hizo antes de parar fue una herramienta que falló."""
    t = _util((texto or '').strip())
    if MAL.search(t):
        return 'mal'
    if REGULAR.search(t):
        return 'regular'
    if CASI.search(t):
        return 'casi'
    if ultimo_fallo and not EXITO.search(t):
        return 'regular'
    return 'ok'
