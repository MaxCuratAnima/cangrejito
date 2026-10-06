"""La voz del cangrejito.

Dos motores, los dos locales y de la comunidad:
  xtts     XTTS-v2 afinado para español argentino (UNRN), con la voz de una grabación del
           dataset argentino abierto. Corre en la placa de video, en un proceso aparte
           (voz_xtts.py) que se cierra mientras jugás para liberar la placa.
  daniela  Piper es_AR (Daniela), en el procesador. Es el respaldo: se usa mientras XTTS
           carga, si falla, o mientras hay un juego en pantalla completa.

El tono se sube reproduciendo el audio a una frecuencia de muestreo mayor y se compensa
sintetizando más lento, así la velocidad queda natural. Todo corre en un hilo propio.
"""
from __future__ import annotations

import collections
import http.client
import io
import json
import logging
import os
import queue
import re
import subprocess
import threading
import time
import wave
from pathlib import Path

import numpy as np

log = logging.getLogger('cangrejito.voz')
AQUI = Path(__file__).resolve().parent
XTTS_PUERTO = 47834
# voz de Daniela (Piper, es_AR): se baja la primera vez del repositorio oficial de voces de Piper.
# Licencia CC BY-SA 4.0 (dataset OpenSLR 61, entrenada por larcanio).
DANIELA_URL = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_AR/daniela/high/'
DANIELA_SHA256 = '7ceb1fc0dab349418c5b54a639ae9ee595212d7c9ea422220d8419163d5cc985'

# Palabras que se leen mal (solo para la voz; el globo muestra el texto original).
DICCION = [
    (r'\bClaude Code\b', 'Clod Coud'), (r'\bClaude\b', 'Clod'), (r'\bClawd\b', 'Clod'),
    (r'\bUnity\b', 'Iúniti'), (r'\bVRChat\b', 'V R chat'),
    (r'\bPhysBones?\b', 'fis bouns'), (r'\bprefab(s?)\b', r'prífab\1'), (r'\bshader(s?)\b', r'shéider\1'),
    (r'\bcommit(s?)\b', r'cómit\1'), (r'\bhook(s?)\b', r'juk\1'),
    (r'\bscript(s?)\b', r'escript\1'), (r'\bsoftware\b', 'sóftuer'), (r'\bhardware\b', 'járduer'),
    (r'\bWindows\b', 'Uíndous'), (r'\bPowerShell\b', 'Páuer Shel'), (r'\bPython\b', 'Páiton'),
    (r'\bJavaScript\b', 'Yava escript'), (r'\bGitHub\b', 'Guit Jab'), (r'\bgit\b', 'guit'),
    (r'\bweb\b', 'ueb'), (r'\bbackup(s?)\b', r'bécap\1'), (r'\bdriver(s?)\b', r'dráiver\1'),
    (r'\bmouse\b', 'maus'), (r'\bmother\b', 'máder'), (r'\btester\b', 'téster'), (r'\bOK\b', 'oquéi'),
    (r'\bAFK\b', 'A F K'), (r'\bPC\b', 'pe ce'), (r'\bUSB\b', 'U S B'), (r'\bBIOS\b', 'bíos'),
    (r'\bAPI\b', 'A P I'), (r'\bHTML\b', 'hache te eme ele'), (r'\bJSON\b', 'yéison'), (r'\bCSS\b', 'ce ese ese'),
    (r'\bGPU\b', 'ge pe u'), (r'\bCPU\b', 'ce pe u'), (r'\bRAM\b', 'ram'), (r'\bMB\b', 'megas'), (r'\bGB\b', 'gigas'),
    (r'\.py\b', ' punto pai'), (r'\.js\b', ' punto yota ese'), (r'\.json\b', ' punto yéison'),
    (r'\.md\b', ' punto eme de'), (r'\.cs\b', ' punto ce ese'), (r'\.ps1\b', ' punto pe ese uno'),
    (r'\.bat\b', ' punto bat'), (r'\.html\b', ' punto hache te eme ele'), (r'\.txt\b', ' punto te equis te'),
    (r'_', ' '), (r'«|»|"', ''), (r'…', '.'),
]
DICCION = [(re.compile(a), b) for a, b in DICCION]


def pronunciar(texto: str) -> str:
    for patron, reemplazo in DICCION:
        texto = patron.sub(reemplazo, texto)
    return texto


class Voz:
    def __init__(self, cfg):
        self.cfg = cfg
        self.modelo = Path(cfg['modelo'])
        self.estado = 'cargando'           # el de Daniela, que siempre está
        self.voz = None
        self.sr = 22050
        self._cache: collections.OrderedDict[str, tuple] = collections.OrderedDict()
        self._cola: queue.Queue = queue.Queue()
        self._gen = 0                      # sube cada vez que hay que cortar lo que suena
        self._hablando = False
        self._inicio = 0.0
        self._envolvente = np.zeros(1, np.float32)
        self._ultimo_uso = 0.0
        self.al_terminar = None            # callback (desde el hilo de la voz)
        self._precalentar: list[str] = []
        # XTTS
        self._xtts_proc = None
        self._xtts_lista = False
        self._xtts_revisado = 0.0
        self.pausar_xtts = False           # hay un juego: nada de placa de video
        threading.Thread(target=self._trabajar, daemon=True, name='voz').start()
        if self.motor == 'xtts':
            self.iniciar_xtts()

    @property
    def volumen(self) -> float:
        return float(self.cfg['volumen'])

    @property
    def motor(self) -> str:
        return self.cfg.get('motor', 'daniela')

    # ------------------------------------------------------------ API
    @property
    def hablando(self) -> bool:
        return self._hablando or not self._cola.empty()

    def decir(self, texto: str, cortar: bool = False):
        if cortar:
            self.callar()
        self._cola.put((texto, self._gen))

    def callar(self):
        self._gen += 1
        while not self._cola.empty():
            try:
                self._cola.get_nowait()
            except queue.Empty:
                break
        if self._hablando:
            try:
                import sounddevice as sd
                sd.stop()
            except Exception:
                pass

    def nivel(self) -> float:
        """0..1: qué tan abierta va la boca ahora."""
        if not self._hablando:
            return 0.0
        i = int((time.monotonic() - self._inicio) / 0.03)
        if 0 <= i < len(self._envolvente):
            return float(self._envolvente[i])
        return 0.0

    def precalentar(self, frases):
        """Sintetiza de antemano las frases fijas, de a una y solo cuando no hay nada que decir."""
        self._precalentar = list(frases)

    # ------------------------------------------------------------ XTTS (proceso aparte)
    def iniciar_xtts(self):
        if self._xtts_proc and self._xtts_proc.poll() is None:
            return
        ref = self.cfg.get('voz_referencia')
        python = Path(self.cfg.get('xtts_python') or '')
        if not (self.cfg.get('xtts_python') and python.exists() and ref and Path(ref).exists()):
            log.warning('XTTS no disponible (falta el entorno o la voz de referencia)')
            return
        self._xtts_lista = False
        args = [str(python), str(AQUI / 'voz_xtts.py'), ref, '--padre', str(os.getpid())]
        if self.cfg.get('xtts_modelo'):
            args += ['--modelo', str(self.cfg['xtts_modelo'])]
        self._xtts_proc = subprocess.Popen(args, cwd=str(AQUI), creationflags=subprocess.CREATE_NO_WINDOW)
        log.info('arranca el servidor XTTS')

    def apagar_xtts(self):
        """Libera la placa de video (se llama cuando hay un juego en pantalla completa)."""
        self._xtts_lista = False
        try:
            c = http.client.HTTPConnection('127.0.0.1', XTTS_PUERTO, timeout=1)
            c.request('POST', '/salir')
            c.getresponse()
        except Exception:
            pass
        if self._xtts_proc:
            try:
                self._xtts_proc.kill()
            except Exception:
                pass
            self._xtts_proc = None
        log.info('servidor XTTS apagado')

    def _xtts_listo(self) -> bool:
        if self.pausar_xtts or self.motor != 'xtts':
            return False
        if self._xtts_lista:
            return True
        if time.monotonic() - self._xtts_revisado < 3:
            return False
        self._xtts_revisado = time.monotonic()
        try:
            c = http.client.HTTPConnection('127.0.0.1', XTTS_PUERTO, timeout=0.5)
            c.request('GET', '/estado')
            self._xtts_lista = json.loads(c.getresponse().read()).get('estado') == 'lista'
        except Exception:
            self._xtts_lista = False
        return self._xtts_lista

    def _xtts(self, texto: str, tono: float):
        c = http.client.HTTPConnection('127.0.0.1', XTTS_PUERTO, timeout=25)
        cuerpo = json.dumps({'texto': pronunciar(texto), 'velocidad': self.cfg['velocidad'] / tono,
                             'temperatura': self.cfg.get('temperatura', 0.7)})
        c.request('POST', '/hablar', body=cuerpo.encode(), headers={'Content-Type': 'application/json'})
        r = c.getresponse()
        if r.status != 200:
            raise RuntimeError(f'XTTS respondió {r.status}')
        with wave.open(io.BytesIO(r.read())) as w:
            sr = w.getframerate()
            audio = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32767
        return np.concatenate([audio, np.zeros(int(sr * 0.08), np.float32)]), sr

    # ------------------------------------------------------------ Daniela (Piper)
    def _bajar_daniela(self):
        """Primera vez: baja la voz (unos 110 MB) y comprueba que sea la original antes de usarla."""
        import hashlib
        import urllib.request
        self.estado = 'bajando'
        self.modelo.parent.mkdir(parents=True, exist_ok=True)
        log.info('bajo la voz de Daniela a %s', self.modelo.parent)
        for nombre, sha in ((self.modelo.name, DANIELA_SHA256), (self.modelo.name + '.json', None)):
            destino = self.modelo.parent / nombre
            parcial = destino.with_name(destino.name + '.parcial')
            h = hashlib.sha256()
            with urllib.request.urlopen(DANIELA_URL + nombre, timeout=60) as r, parcial.open('wb') as f:
                while bloque := r.read(1 << 20):
                    f.write(bloque)
                    h.update(bloque)
            if sha and h.hexdigest() != sha:
                parcial.unlink(missing_ok=True)
                raise RuntimeError('la voz bajada no coincide con la original')
            parcial.replace(destino)
        log.info('voz de Daniela bajada')

    def _cargar(self):
        try:
            if not (self.modelo.exists() and Path(f'{self.modelo}.json').exists()):
                self._bajar_daniela()
            import onnxruntime
            from piper import PiperVoice
            from piper.config import PiperConfig
            # 4 hilos como mucho: con todos los núcleos la voz calienta la PC al pedo
            opciones = onnxruntime.SessionOptions()
            opciones.intra_op_num_threads = 4
            opciones.inter_op_num_threads = 1
            config = json.loads(Path(f'{self.modelo}.json').read_text(encoding='utf-8'))
            self.voz = PiperVoice(config=PiperConfig.from_dict(config),
                                  session=onnxruntime.InferenceSession(str(self.modelo), sess_options=opciones,
                                                                       providers=['CPUExecutionProvider']))
            self.sr = self.voz.config.sample_rate
            self._daniela('Hola.', 1.0)
            self.estado = 'lista'
            log.info('voz de Daniela lista (%s Hz)', self.sr)
        except Exception as e:
            self.estado = 'no'
            log.exception('no pude cargar la voz: %s', e)

    def _daniela(self, texto: str, tono: float):
        from piper import SynthesisConfig
        cfg = SynthesisConfig(length_scale=tono / self.cfg['velocidad'])
        pausa = np.zeros(int(self.sr * 0.18), np.float32)
        partes = []
        for trozo in self.voz.synthesize(pronunciar(texto), syn_config=cfg):
            if partes:
                partes.append(pausa)
            partes.append(trozo.audio_float_array)
        partes.append(np.zeros(int(self.sr * 0.08), np.float32))
        return np.concatenate(partes).astype(np.float32), self.sr

    # ------------------------------------------------------------ síntesis con caché
    def _sintetizar(self, texto: str, solo_cache_xtts: bool = False):
        """(audio, frecuencia, tono) con el mejor motor disponible."""
        usar_xtts = self._xtts_listo()
        tono = float(self.cfg['tono_xtts'] if usar_xtts else self.cfg['tono'])
        motor = 'xtts' if usar_xtts else 'daniela'
        clave = f'{motor}|{self.cfg.get("voz_referencia")}|{tono:.2f}|{self.cfg["velocidad"]:.2f}|{texto}'
        hit = self._cache.get(clave)
        if hit is not None:
            self._cache.move_to_end(clave)
            return hit
        if solo_cache_xtts and not usar_xtts:
            return None
        audio, sr = self._xtts(texto, tono) if usar_xtts else self._daniela(texto, tono)
        hit = (audio, sr, tono)
        self._cache[clave] = hit
        while len(self._cache) > 300:
            self._cache.popitem(last=False)
        return hit

    def _trabajar(self):
        self._cargar()
        import sounddevice as sd
        while True:
            try:
                texto, gen = self._cola.get(timeout=0.5)
            except queue.Empty:
                if self._precalentar and self.voz is not None and (self.motor != 'xtts' or self._xtts_listo()):
                    try:
                        self._sintetizar(self._precalentar.pop(0))
                    except Exception:
                        pass
                    time.sleep(0.4)          # de a poco, sin acaparar nada
                continue
            if gen != self._gen or self.voz is None:
                continue
            try:
                audio, sr, tono = self._sintetizar(texto)
            except Exception:
                log.exception('falló la síntesis; pruebo con Daniela')
                self._xtts_lista = False
                try:
                    audio, sr = self._daniela(texto, float(self.cfg['tono']))
                    tono = float(self.cfg['tono'])
                except Exception:
                    log.exception('tampoco Daniela')
                    continue
            if gen != self._gen:
                continue
            sr_salida = int(sr * tono)
            # envolvente para la boca: energía cada 30 ms del tiempo real de reproducción
            paso = max(1, int(sr_salida * 0.03))
            n = len(audio) // paso
            if n:
                bloques = np.abs(audio[: n * paso]).reshape(n, paso).mean(axis=1)
                env = np.clip(bloques / (bloques.max() + 1e-6) * 1.4, 0, 1)
            else:
                env = np.zeros(1, np.float32)
            dur = len(audio) / sr_salida
            try:
                if time.monotonic() - self._ultimo_uso > 30:
                    # por si cambió la salida de audio (auriculares inalámbricos que se apagan)
                    sd._terminate()
                    sd._initialize()
                sd.play(np.clip(audio * self.volumen, -1, 1), samplerate=sr_salida, blocking=False)
            except Exception:
                log.exception('no pude reproducir; reintento con los dispositivos refrescados')
                try:
                    sd._terminate()
                    sd._initialize()
                    sd.play(np.clip(audio * self.volumen, -1, 1), samplerate=sr_salida, blocking=False)
                except Exception:
                    log.exception('sin audio')
                    continue
            self._envolvente = env
            self._inicio = time.monotonic()
            self._hablando = True
            fin = self._inicio + dur + 0.05
            while time.monotonic() < fin and gen == self._gen:
                time.sleep(0.02)
            if gen != self._gen:
                try:
                    sd.stop()
                except Exception:
                    pass
            self._hablando = False
            self._ultimo_uso = time.monotonic()
            if self.al_terminar:
                try:
                    self.al_terminar()
                except Exception:
                    log.exception('al_terminar')
