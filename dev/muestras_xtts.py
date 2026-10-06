"""Genera la misma frase con cada voz de <base>\\voces para elegir de oído.

  <python de xtts> dev\\muestras_xtts.py
La carpeta base es CANGREJITO_XTTS_DIR (por defecto %USERPROFILE%\\CangrejitoXTTS).
"""
import os
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import voz_xtts  # noqa: E402

VOCES = Path(os.environ.get('CANGREJITO_XTTS_DIR') or Path.home() / 'CangrejitoXTTS') / 'voces'
SALIDA = VOCES / 'muestras'
SALIDA.mkdir(exist_ok=True)
FRASE = '¡Hola! Soy tu cangrejito. Ya terminé de arreglar el servidor, ¿lo probamos?'

t = time.time()
m = voz_xtts.preparar_modelo()
print(f'modelo cargado en {time.time() - t:.1f} s, VRAM {torch.cuda.memory_allocated() / 2**30:.2f} GB')
for i, ref in enumerate(sorted(VOCES.glob('*.wav')), 1):
    gpt, emb = m.get_conditioning_latents(audio_path=[str(ref)])
    t = time.time()
    with torch.inference_mode():
        out = m.inference(FRASE, 'es', gpt, emb, temperature=0.7, enable_text_splitting=True)
    audio = np.asarray(out['wav'], dtype=np.float32)
    sf.write(SALIDA / f'{i}-{ref.stem}.wav', audio, 24000)
    print(f'{i}: {ref.stem}: {len(audio) / 24000:.1f} s de audio en {time.time() - t:.1f} s')
print(f'VRAM máxima {torch.cuda.max_memory_allocated() / 2**30:.2f} GB')
