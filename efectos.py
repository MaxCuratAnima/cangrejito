# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Efectos de sonido hechos con código (sin archivos, sin licencias): el confeti cuando festeja.

  confeti   un «pop» de cotillón, la cornetita de cumpleaños y los papelitos cayendo
  fiesta    dos pops, dos cornetitas y más papelitos (cuando termina un laburo largo)
"""
from __future__ import annotations

import numpy as np

_cache: dict[tuple, np.ndarray] = {}


def _pop(sr: int, rng) -> np.ndarray:
    """El tapón del cotillón: un golpe grave cortito más un chasquido de ruido."""
    t = np.arange(int(sr * 0.09)) / sr
    golpe = np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.025)
    ruido = np.diff(rng.standard_normal(len(t) + 1)) * np.exp(-t / 0.006)
    return (0.7 * golpe + 0.45 * ruido).astype(np.float32)


def _corneta(sr: int, dur: float, f0: float, rng) -> np.ndarray:
    """La cornetita de cumpleaños (espantasuegras): un zumbido como de kazoo que sube al soplar,
    con el «prrr» del papel que se desenrolla y una caída al final."""
    t = np.arange(int(sr * dur)) / sr
    u = t / dur
    frec = f0 * (0.82 + 0.18 * np.minimum(1, u / 0.12)) * (1 - 0.12 * np.clip((u - 0.8) / 0.2, 0, 1))
    frec *= 1 + 0.015 * np.sin(2 * np.pi * 6 * t)                     # el temblor del soplido
    fase = 2 * np.pi * np.cumsum(frec) / sr
    onda = np.tanh(2.5 * np.sin(fase)) + 0.35 * np.sin(2 * fase) + 0.2 * np.sin(3 * fase)
    prrr = 0.75 + 0.25 * np.sin(2 * np.pi * 28 * t)                   # el papelito vibrando
    soplo = 0.12 * rng.standard_normal(len(t))
    env = np.minimum(1, t / 0.03) * np.minimum(1, (dur - t) / 0.08)
    return ((onda * prrr + soplo) * env * 0.5).astype(np.float32)


def _papelitos(sr: int, dur: float, cuantos: int, rng) -> np.ndarray:
    """Crujiditos de papel: muchos chasquidos chiquitos al azar, cada vez más espaciados y suaves,
    sobre un susurro de fondo."""
    n = int(sr * dur)
    out = np.zeros(n, np.float32)
    for _ in range(cuantos):
        u = rng.random() ** 1.7                       # más al principio, menos al final
        ini = int(u * (n - sr * 0.01))
        largo = int(sr * rng.uniform(0.002, 0.008))
        golpe = np.diff(rng.standard_normal(largo + 1)) * np.exp(-np.arange(largo) / (largo / 3))
        out[ini:ini + largo] += golpe * rng.uniform(0.08, 0.3) * (1 - u * 0.7)
    t = np.arange(n) / sr
    susurro = np.diff(rng.standard_normal(n + 1)) * 0.025 * np.exp(-t / (dur / 2.5))
    return out + susurro.astype(np.float32)


def generar(nombre: str, sr: int) -> np.ndarray:
    """El efecto como audio en float32 a esa frecuencia (cacheado)."""
    clave = (nombre, sr)
    if clave in _cache:
        return _cache[clave]
    rng = np.random.default_rng(1810)
    def sumar(audio, sonido, ini, fuerza=1.0):
        i = int(sr * ini)
        n = min(len(sonido), len(audio) - i)
        audio[i:i + n] += sonido[:n] * fuerza

    if nombre == 'fiesta':
        audio = _papelitos(sr, 1.8, 170, rng) * 1.4
        for ini in (0.0, 0.33):
            sumar(audio, _pop(sr, rng), ini)
        sumar(audio, _corneta(sr, 0.75, 420, rng), 0.05, 0.8)
        sumar(audio, _corneta(sr, 0.6, 560, rng), 0.45, 0.7)     # otra cornetita, más aguda
    else:
        audio = _papelitos(sr, 1.0, 90, rng) * 1.4
        sumar(audio, _pop(sr, rng), 0.0)
        sumar(audio, _corneta(sr, 0.6, 450, rng), 0.04, 0.8)
    audio = (audio / (np.abs(audio).max() + 1e-6) * 0.6).astype(np.float32)
    _cache[clave] = audio
    return audio


def mezclar(efecto: np.ndarray, voz: np.ndarray, sr: int, demora: float = 0.45) -> tuple[np.ndarray, int]:
    """El efecto arranca primero y la voz entra «demora» segundos después, mientras siguen cayendo los
    papelitos. Devuelve (audio mezclado, muestras de efecto solo al principio)."""
    i = int(sr * demora)
    total = np.zeros(max(len(efecto), i + len(voz)), np.float32)
    total[:len(efecto)] += efecto
    total[i:i + len(voz)] += voz
    return np.clip(total, -1, 1), i
