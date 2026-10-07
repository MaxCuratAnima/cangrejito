# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
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

# Palabras que se leen mal (solo para la voz; el globo muestra el texto original). Se revisaron pasando
# cada una por el fonetizador de la voz (espeak es-419): las que salían deletreadas, en inglés mal leído
# o salteadas están acá. Las siglas en mayúsculas (MCP, LLM, WSL…) espeak ya las deletrea bien.
EMOJIS = re.compile('[\U0001F000-\U0001FAFF☀-➿⬀-⯿️‍]')
DICCION = [
    # símbolos y abreviaturas (antes que nada, porque cambian la puntuación)
    (r'\b[vV](\d+(?:\.\d+)+)\b', r'versión \1'), (r'(\d+)\s*/\s*(\d+)', r'\1 de \2'),
    (r'(\d)\s*%', r'\1 por ciento'), (r'(\d)\s*ms\b', r'\1 milisegundos'), (r'(\d)\s*s\b', r'\1 segundos'),
    (r'(\d)\s*min\b', r'\1 minutos'), (r'(\d)\s*h\b', r'\1 horas'), (r'(\d)\s*°C', r'\1 grados'),
    (r'\bx(\d)\b', r'por \1'), (r'#(\d)', r'número \1'), (r'\bp\.\s?ej\.', 'por ejemplo'),
    (r'\bvs\.?(?=\s)', 'contra'), (r'\baprox\.', 'aproximadamente'), (r'\s&\s', ' y '),
    (r'\s*(→|->|=>)\s*', ', a '), (r'\s*(—|–)\s*', ', '), (r'[~*#|]', ' '), (r'\(([^)]*)\)', r', \1,'),
    (r'\b[MH]m+h?\b', 'Emm'),                      # «Mmm» y «Hmm»: si no, los deletrea
    (r'\bUps\b', 'Úps'), (r'\b[Gg]oogle(o|ar|ás|a)\b', r'gugle\1'),   # si no, «aps» y «gooo»
    # nombres y palabras en inglés que lee mal
    (r'\bClaude Code\b', 'Clod Coud'), (r'\bClaude\b', 'Clod'), (r'\bClawd\b', 'Clod'),
    (r'\bUnity\b', 'Iúniti'), (r'\bVRChat\b', 'V R chat'), (r'\bSteamVR\b', 'Estim V R'), (r'\bSteam\b', 'Estim'),
    (r'\bSpotify\b', 'Espótifai'), (r'\bHalloween\b', 'Jálouin'), (r'\bYouTube\b', 'Iutiub'), (r'\bOneDrive\b', 'Uan dráiv'),
    (r'\bHugging Face\b', 'Jáguin feis'), (r'\bPiper\b', 'Páiper'), (r'\bWhisper\b', 'Uísper'),
    (r'\bPyInstaller\b', 'Pai instóler'), (r'\bPySide(\d?)\b', r'Pai said \1'), (r'\bpytest\b', 'pai test'),
    (r'\bBluetooth\b', 'Blutuz'), (r'\bNVIDIA\b', 'Envidia'), (r'\bRyzen\b', 'Ráisen'), (r'\bREADME\b', 'Ridmi'),
    (r'\bSonnet\b', 'Sónet'), (r'\bBoulogne-sur-Mer\b', 'Bulóñ sur Mer'), (r'\bUI\b', 'U I'), (r'\bIA\b', 'I A'),
    (r'\bPhysBones?\b', 'fis bouns'), (r'\bprefab(s?)\b', r'prífab\1'), (r'\bshader(s?)\b', r'shéider\1'),
    (r'\bcommit(s?)\b', r'cómit\1'), (r'\bhook(s?)\b', r'juk\1'), (r'\bbug(s?)\b', r'bag\1'),
    (r'\bscript(s?)\b', r'escript\1'), (r'\bsoftware\b', 'sóftuer'), (r'\bhardware\b', 'járduer'),
    (r'\bplugin(s?)\b', r'plaguin\1'), (r'\bupdate(s?)\b', r'apdéit\1'), (r'\bfeedback\b', 'fidbak'),
    (r'\bonline\b', 'onláin'), (r'\boffline\b', 'ofláin'), (r'\bemail(s?)\b', r'imeil\1'), (r'\bmail\b', 'meil'),
    (r'\bstream(s?)\b', r'estrim\1'), (r'\bstreaming\b', 'estríming'), (r'\bplaylist(s?)\b', r'pléilist\1'),
    (r'\bsprite(s?)\b', r'espráit\1'), (r'\bframe(s?)\b', r'fréim\1'), (r'\bframework(s?)\b', r'fréimuork\1'),
    (r'\bsetup\b', 'sétap'), (r'\bInno Setup\b', 'Ino sétap'), (r'\bdeploy\b', 'diplói'), (r'\brelease(s?)\b', r'rilís\1'),
    (r'\bpull request(s?)\b', r'pul ricuést\1'), (r'\bupload\b', 'áploud'), (r'\bdownload\b', 'dáunloud'),
    (r'\bdefault\b', 'difólt'), (r'\bdebug\b', 'dibág'), (r'\btimeout\b', 'táimaut'), (r'\bwarning(s?)\b', r'uórning\1'),
    (r'\bslider\b', 'esláider'), (r'\bissue(s?)\b', r'íshu\1'), (r'\bmerge\b', 'merch'), (r'\bvenv\b', 've env'),
    (r'\bpath\b', 'paz'), (r'\bStore\b', 'Estor'), (r'\bCtrl\b', 'Control'), (r'\bM\.2\b', 'eme dos'),
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
    (r'\.exe\b', ' punto e equis e'), (r'\.sh\b', ' punto ese hache'),
    (r'_', ' '), (r'«|»|"', ''),
]
DICCION = [(re.compile(a), b) for a, b in DICCION]


def pronunciar(texto: str) -> str:
    texto = EMOJIS.sub(' ', texto)
    for patron, reemplazo in DICCION:
        texto = patron.sub(reemplazo, texto)
    texto = ' '.join(texto.split())
    texto = re.sub(r'\s+([,.;:!?])', r'\1', texto)          # sin espacio antes de la puntuación
    texto = re.sub(r',(\s*,)+', ',', texto)                  # sin comas dobles
    return re.sub(r',\s*([.;:!?])', r'\1', texto).strip(' ,')


# Respirar: pausa después de cada oración según cómo termina (segundos, a velocidad normal)
PAUSAS = {'.': 0.42, '!': 0.45, '?': 0.5, '…': 0.6, ':': 0.32, ';': 0.32}
# en una oración larga sin comas, respira antes de estas palabras (como haría una persona)
_RESPIRO_ANTES = re.compile(r'\s+(?=(pero|porque|aunque|así que|entonces|mientras|cuando|para que|'
                            r'y después|y ahora|o sea|sino|si no)\b)', re.I)
_PALABRAS_SIN_RESPIRO = 9


def _respirar(frase: str) -> str:
    """Pone una coma (pausa cortita) antes de un conector si van muchas palabras seguidas sin pausa."""
    out, desde = [], 0
    for m in _RESPIRO_ANTES.finditer(frase):
        antes = frase[desde:m.start()]
        tramo = re.split(r'[,;:]', antes)[-1]
        if len(tramo.split()) >= _PALABRAS_SIN_RESPIRO and not antes.rstrip().endswith(','):
            # «…los acentos y entonces…» → «…los acentos, y entonces…» (la coma antes de la «y»)
            m_y = re.search(r'\s(y|e|o|u|ni|que)$', antes.rstrip(), re.I)
            if m_y:
                antes = antes.rstrip()
                out.append(antes[:m_y.start()] + ',' + antes[m_y.start():])
            else:
                out.append(antes.rstrip() + ',')
        else:
            out.append(antes)
        desde = m.start()
    out.append(frase[desde:])
    return ''.join(out)


# Ánimo de la frase: Piper no tiene emociones, pero se le cambia el tono (agudo/grave), la rapidez, cuánto
# varía al hablar (expresión), la fuerza y las pausas. Así enojado suena apurado y fuerte, cansado lento
# y grave, contento más agudo y vivo.
#            tono  rapidez expresión fuerza pausas
ANIMOS = {
    # el tono casi no cambia (si no, deja de sonar a él): el ánimo va por la rapidez, las pausas y la fuerza
    '':         (1.00, 1.00, 1.05, 1.00, 1.00),
    'contento': (1.02, 1.05, 1.15, 1.00, 0.92),
    'enojado':  (1.00, 1.10, 1.20, 1.20, 0.80),
    'cansado':  (0.97, 0.86, 0.85, 0.85, 1.40),
    'triste':   (0.98, 0.90, 0.85, 0.85, 1.30),
    'sorpresa': (1.03, 1.03, 1.15, 1.05, 1.00),
}


def trozos(texto: str) -> list[tuple[str, float]]:
    """El texto en oraciones, cada una con la pausa que va después: así no sale todo de un tirón."""
    partes = [p.strip() for p in re.split(r'(?<=[.!?…:;])\s+', texto.strip()) if p.strip()]
    out = []
    for p in partes:
        fin = p[-1]
        out.append((_respirar(p.replace('…', '.')), PAUSAS.get(fin, 0.38)))
    return out


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

    def decir(self, texto: str, cortar: bool = False, animo: str = '', efecto: str = ''):
        """animo: '', contento, enojado, cansado, triste o sorpresa (ver ANIMOS).
        efecto: '', confeti o fiesta (suena primero y la voz entra encima; ver efectos.py)."""
        if cortar:
            self.callar()
        self._cola.put((texto, self._gen, animo if animo in ANIMOS else '', efecto))

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
        self._xtts_proc = subprocess.Popen(args, cwd=str(AQUI),
                                           creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
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

    def _daniela(self, texto: str, tono: float, animo: str = ''):
        """Oración por oración, con su pausa para respirar. Si el texto es largo, va un poquito más
        despacio (con mucha información, de corrido, parecía una metralleta). «tono» ya trae el del ánimo;
        acá se aplican la rapidez, la expresión, la fuerza y las pausas del ánimo."""
        from piper import SynthesisConfig
        _, rapidez, expresion, fuerza, pausas = ANIMOS.get(animo, ANIMOS[''])
        velocidad = float(self.cfg['velocidad'])
        inferencia = (self.voz.config.__dict__ if self.voz is not None else {})
        largo = len(texto)
        calma = 1.0 + min(0.08, max(0.0, (largo - 110) / 1500))    # hasta 8 % más lento en textos largos
        cfg = SynthesisConfig(length_scale=tono / (velocidad * rapidez) * calma,
                              noise_scale=float(inferencia.get('noise_scale') or 0.667) * expresion,
                              noise_w_scale=min(1.3, float(inferencia.get('noise_w_scale') or 0.8) * expresion))
        respiro = float(self.cfg.get('pausas_voz', 1.0)) * pausas / velocidad ** 0.5
        partes = []
        for frase, pausa in trozos(pronunciar(texto)):
            for trozo in self.voz.synthesize(frase, syn_config=cfg):
                if partes and partes[-1].any():
                    partes.append(np.zeros(int(self.sr * 0.22 * respiro), np.float32))  # piper la partió
                partes.append(trozo.audio_float_array)
            partes.append(np.zeros(int(self.sr * pausa * respiro), np.float32))
        if not partes:
            return np.zeros(int(self.sr * 0.1), np.float32), self.sr
        partes[-1] = np.zeros(int(self.sr * 0.08), np.float32)      # al final, sin pausa larga
        audio = np.concatenate(partes).astype(np.float32)
        if fuerza > 1:          # más fuerte sin saturar: comprime un poco (y suena más «apretado», enojado)
            audio = np.tanh(audio * fuerza * 1.2) / np.tanh(fuerza * 1.2)
        else:
            audio = audio * fuerza
        return audio.astype(np.float32), self.sr

    # ------------------------------------------------------------ síntesis con caché
    def _sintetizar(self, texto: str, solo_cache_xtts: bool = False, animo: str = ''):
        """(audio, frecuencia, tono) con el mejor motor disponible."""
        usar_xtts = self._xtts_listo()
        tono = float(self.cfg['tono_xtts'] if usar_xtts else self.cfg['tono']) * ANIMOS.get(animo, ANIMOS[''])[0]
        # para que no suene plano: cada frase con un tonito apenas distinto (fijo por frase, así sirve la caché)
        tono *= (0.995, 1.0, 1.005)[sum(map(ord, texto)) % 3]
        motor = 'xtts' if usar_xtts else 'daniela'
        clave = (f'{motor}|{self.cfg.get("voz_referencia")}|{tono:.3f}|{self.cfg["velocidad"]:.2f}|'
                 f'{self.cfg.get("pausas_voz", 1.0)}|{animo}|{texto}')
        hit = self._cache.get(clave)
        if hit is not None:
            self._cache.move_to_end(clave)
            return hit
        if solo_cache_xtts and not usar_xtts:
            return None
        audio, sr = self._xtts(texto, tono) if usar_xtts else self._daniela(texto, tono, animo)
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
                texto, gen, animo, efecto = self._cola.get(timeout=0.5)
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
                audio, sr, tono = self._sintetizar(texto, animo=animo)
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
            solo_efecto = 0
            if efecto and self.cfg.get('efectos', True):
                import efectos
                audio, solo_efecto = efectos.mezclar(efectos.generar(efecto, sr), audio, sr)
            sr_salida = int(sr * tono)
            # envolvente para la boca: energía cada 30 ms del tiempo real de reproducción
            paso = max(1, int(sr_salida * 0.03))
            n = len(audio) // paso
            if n:
                bloques = np.abs(audio[: n * paso]).reshape(n, paso).mean(axis=1)
                env = np.clip(bloques / (bloques.max() + 1e-6) * 1.4, 0, 1)
                env[:solo_efecto // paso] = 0          # el pop del confeti no le mueve la boca
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
