# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Servidor de voz XTTS-v2 en español argentino (modelo de la UNRN, afinado con grabaciones argentinas).

Es opcional: corre aparte, con su propio Python (un entorno con coqui-tts y PyTorch, el de
«xtts_python» en config.json), porque PyTorch es pesado y así el cangrejito puede cerrarlo
para liberar la placa de video mientras jugás.

  POST http://127.0.0.1:47834/hablar  {"texto": "...", "velocidad": 1.0}  → WAV 24 kHz
  GET  http://127.0.0.1:47834/estado  → {"estado": "cargando" | "lista" | "error"}

Uso: pythonw voz_xtts.py <voz_de_referencia.wav> [--padre PID] [--modelo CARPETA]
(sin --modelo usa %USERPROFILE%\\CangrejoVoz, donde deja el modelo dev/aligerar_modelo.py)
"""
import ctypes
import io
import json
import logging
import sys
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import rutas  # noqa: E402

# la carpeta del modelo: --modelo, o el modelo achicado de dev/aligerar_modelo.py
MODELO = (Path(sys.argv[sys.argv.index('--modelo') + 1]) if '--modelo' in sys.argv
          else Path.home() / 'CangrejoVoz')
PUERTO = 47834
HOSTS_OK = {f'127.0.0.1:{PUERTO}', f'localhost:{PUERTO}'}

rutas.DATOS.mkdir(parents=True, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s xtts %(levelname)s %(message)s',
                    handlers=[RotatingFileHandler(rutas.DATOS / 'registro-xtts.txt', maxBytes=200_000,
                                                  backupCount=1, encoding='utf-8')])
log = logging.getLogger('xtts')

estado = {'estado': 'cargando'}
lock = threading.Lock()
modelo = None
latentes = None


def _cargar_audio(ruta, sampling_rate):
    """Reemplazo de load_audio de coqui: lee con soundfile (sin depender de FFmpeg)."""
    import soundfile as sf
    import torch
    import torchaudio
    audio, sr = sf.read(str(ruta), dtype='float32', always_2d=True)
    audio = torch.from_numpy(audio.mean(axis=1)).unsqueeze(0)
    if sr != sampling_rate:
        audio = torchaudio.functional.resample(audio, sr, sampling_rate)
    return audio.clamp_(-1, 1)


def preparar_modelo():
    import torch
    import TTS.tts.models.xtts as mx
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    mx.load_audio = _cargar_audio
    cfg = XttsConfig()
    cfg.load_json(str(MODELO / 'config.json'))
    m = Xtts.init_from_config(cfg)
    m.load_checkpoint(cfg, checkpoint_path=str(MODELO / 'model.pth'), vocab_path=str(MODELO / 'vocab.json'),
                      use_deepspeed=False)
    m.to('cuda' if torch.cuda.is_available() else 'cpu')
    m.eval()
    return m


def cargar(referencia: Path):
    global modelo, latentes
    try:
        import torch
        t = time.time()
        m = preparar_modelo()
        dispositivo = 'cuda' if torch.cuda.is_available() else 'cpu'
        gpt, emb = m.get_conditioning_latents(audio_path=[str(referencia)])
        modelo, latentes = m, (gpt, emb)
        sintetizar('Hola.', 1.0)              # la primera es la más lenta
        estado['estado'] = 'lista'
        log.info('lista en %s (%.1f s), voz %s', dispositivo, time.time() - t, referencia.name)
    except Exception as e:
        estado['estado'] = 'error'
        estado['error'] = str(e)
        log.exception('no pude cargar XTTS')


def sintetizar(texto: str, velocidad: float, temperatura: float = 0.7) -> bytes:
    import numpy as np
    import torch
    with lock, torch.inference_mode():
        gpt, emb = latentes
        out = modelo.inference(texto, 'es', gpt, emb, temperature=temperatura, speed=velocidad,
                               enable_text_splitting=True)
    audio = np.asarray(out['wav'], dtype=np.float32)
    pcm = (np.clip(audio, -1, 1) * 32767 * 0.95).astype('<i2').tobytes()
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    return buf.getvalue()


class Manejador(BaseHTTPRequestHandler):
    def _ok(self) -> bool:
        if self.headers.get('Origin') or self.headers.get('Host') not in HOSTS_OK:
            self.send_response(403)
            self.end_headers()
            return False
        return True

    def do_GET(self):
        if not self._ok():
            return
        datos = json.dumps(estado).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_POST(self):
        if not self._ok():
            return
        if self.path == '/salir':
            self.send_response(204)
            self.end_headers()
            log.info('me piden salir (libero la placa de video)')
            import os
            os._exit(0)
        if estado['estado'] != 'lista':
            self.send_response(503)
            self.end_headers()
            return
        try:
            d = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
            wav = sintetizar(str(d.get('texto', ''))[:600], float(d.get('velocidad', 1.0)),
                             float(d.get('temperatura', 0.7)))
        except Exception:
            log.exception('falló la síntesis')
            self.send_response(500)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', 'audio/wav')
        self.send_header('Content-Length', str(len(wav)))
        self.end_headers()
        self.wfile.write(wav)

    def log_message(self, *a):
        pass


def vigilar_padre(pid: int):
    """Si el cangrejito se cierra, este servidor se va con él."""
    import os
    if sys.platform == 'win32':
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x00100000, False, pid)        # SYNCHRONIZE
        if h:
            k.WaitForSingleObject(h, 0xFFFFFFFF)
    else:
        while True:                                       # en Linux: se fija cada 2 s si sigue vivo
            try:
                os.kill(pid, 0)
            except OSError:
                break
            time.sleep(2)
    log.info('el cangrejito se cerró: salgo')
    os._exit(0)


def main():
    referencia = Path(sys.argv[1])
    if '--padre' in sys.argv:
        threading.Thread(target=vigilar_padre, args=(int(sys.argv[sys.argv.index('--padre') + 1]),),
                         daemon=True).start()
    try:
        srv = ThreadingHTTPServer(('127.0.0.1', PUERTO), Manejador)
    except OSError:
        log.info('ya hay otro servidor XTTS')
        return
    threading.Thread(target=cargar, args=(referencia,), daemon=True).start()
    srv.serve_forever()


if __name__ == '__main__':
    main()
