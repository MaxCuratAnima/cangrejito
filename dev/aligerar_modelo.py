"""Achica el modelo XTTS argentino para que cargue rápido.

El model.pth publicado (5,3 GB) es un checkpoint de entrenamiento: además de los pesos trae
el estado del optimizador. Para hablar solo hacen falta los pesos, y guardados en float16
ocupan ~0,9 GB. Se guarda en %USERPROFILE%\\CangrejoVoz (conviene un disco rápido).
Al cargar, PyTorch los vuelve a pasar a float32 solo.
El original se lee de <base>\\xtts-modelo; la base es CANGREJITO_XTTS_DIR
(por defecto %USERPROFILE%\\CangrejitoXTTS).
"""
import os
import shutil
import time
from pathlib import Path

import torch

ORIGEN = Path(os.environ.get('CANGREJITO_XTTS_DIR') or Path.home() / 'CangrejitoXTTS') / 'xtts-modelo'
DESTINO = Path.home() / 'CangrejoVoz'
DESTINO.mkdir(exist_ok=True)

t = time.time()
ck = torch.load(ORIGEN / 'model.pth', map_location='cpu', weights_only=False)
print(f'leído en {time.time() - t:.0f} s; claves: {list(ck)[:8]}')
pesos = ck['model'] if isinstance(ck, dict) and 'model' in ck else ck
chico = {k: (v.half() if torch.is_tensor(v) and v.is_floating_point() else v) for k, v in pesos.items()}
torch.save({'model': chico}, DESTINO / 'model.pth')
for f in ('config.json', 'vocab.json', 'LICENSE'):
    shutil.copy2(ORIGEN / f, DESTINO / f)
print(f'listo: {(DESTINO / "model.pth").stat().st_size / 2**20:.0f} MB en {DESTINO}')
