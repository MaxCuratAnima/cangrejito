# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Arma voces de referencia para XTTS con el dataset argentino abierto (Google, OpenSLR 61, CC BY-SA 4.0).

Junta varias frases de un mismo hablante hasta ~12 s y las guarda en <base>\\voces.
Corre con el Python de XTTS (tiene pyarrow y soundfile):
  <python de xtts> dev\\voces_dataset.py [cuantas_por_genero]
La carpeta base es CANGREJITO_XTTS_DIR (por defecto %USERPROFILE%\\CangrejitoXTTS), con las
subcarpetas dataset, voces y xtts-modelo.
"""
import io
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import soundfile as sf

BASE = Path(os.environ.get('CANGREJITO_XTTS_DIR') or Path.home() / 'CangrejitoXTTS')
DATASET = BASE / 'dataset'
SALIDA = BASE / 'voces'
SALIDA.mkdir(parents=True, exist_ok=True)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4

for genero, archivo in (('mujer', 'female0.parquet'), ('hombre', 'male0.parquet')):
    tabla = pq.read_table(DATASET / archivo).to_pylist()
    por_hablante = defaultdict(list)
    for fila in tabla:
        por_hablante[fila['speaker_id']].append(fila)
    # los que más frases tienen suelen ser los más prolijos
    hablantes = sorted(por_hablante, key=lambda k: -len(por_hablante[k]))[:N]
    for sid in hablantes:
        partes, total, sr = [], 0.0, None
        for fila in por_hablante[sid]:
            audio, sr_f = sf.read(io.BytesIO(fila['audio']['bytes']), dtype='float32')
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            sr = sr or sr_f
            if sr_f != sr:
                continue
            # recorta silencios del principio y del final
            voz = np.nonzero(np.abs(audio) > 0.02)[0]
            if len(voz) == 0:
                continue
            audio = audio[max(0, voz[0] - int(0.05 * sr)): voz[-1] + int(0.1 * sr)]
            partes += [audio, np.zeros(int(0.25 * sr), np.float32)]
            total += len(audio) / sr
            if total >= 12:
                break
        ruta = SALIDA / f'{genero}_{sid}.wav'
        sf.write(ruta, np.concatenate(partes), sr)
        print(ruta.name, f'{total:.1f} s', f'{len(por_hablante[sid])} frases')
