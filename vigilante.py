# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Mira la PC cada 2 segundos: si la app de Claude está abierta, si estás AFK, qué monitores
tienen algo en pantalla completa (un juego o un video), si le estás dictando a Claude,
si suena Spotify y qué sesiones de Claude Code están activas."""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import threading
import time
from pathlib import Path

import psutil
from PySide6.QtCore import QObject, QTimer, Signal

import rutas

log = logging.getLogger('cangrejito.vigilante')
if sys.platform == 'win32':
    import sistema_windows as so
else:
    import sistema_linux as so
SESIONES = Path.home() / '.claude' / 'sessions'
pids_app_claude = so.pids_app_claude          # lo usa el «Salir» del menú

# folklore y guitarra criolla: con estos se sienta a tocar la guitarra vestido de gaucho
# (se suman más desde config.json, en «artistas_guitarra»)
ARTISTAS_GUITARRA = ['chaqueño', 'palavecino', 'los nocheros', 'abel pintos', 'soledad', 'jorge rojas',
                     'los tekis', 'luciano pereyra', 'los manseros', 'mercedes sosa', 'yupanqui',
                     'chalchaleros', 'fronterizos', 'los huayra', 'destino san javier', 'lucio rojas',
                     'galleguillo', 'carabajal', 'raly barrionuevo', 'facundo toro', 'los alonsitos',
                     'christian herrera', 'nahuel pennisi', 'larralde', 'horacio guarany', 'los cantores del alba',
                     'los kjarkas', 'cuti y roberto carabajal', 'los visconti', 'la callejera',
                     'juan falú', 'juan falu', 'eduardo falú', 'eduardo falu', 'ernesto méndez', 'ernesto mendez',
                     'carlos moscardini', 'quique sinesi', 'jorge jewsbury', 'josé luis merlín', 'jose luis merlin',
                     'roberto calvo', 'ariel ramírez', 'ariel ramirez', 'jaime torres', 'dino saluzzi', 'hugo díaz',
                     'los cuatro de córdoba', 'los de salta', 'peteco carabajal', 'rubén patagonia', 'los trovadores',
                     'los tucu tucu', 'los hermanos ábalos', 'los hermanos abalos', 'chango farías gómez',
                     'chango nieto', 'los carabajal', 'tomás lipán', 'víctor heredia', 'victor heredia',
                     'argentino luna', 'claudio ceccoli', 'bernardo baraj', 'pablo márquez', 'mauro lombardi',
                     'gustavo santaolalla', 'juan quintero', 'luna monti', 'liliana herrero', 'lilián saba',
                     'zamba quipildor', 'los nombradores', 'cafrune', 'los tres sudamericanos']
PALABRAS_GUITARRA = ['acústic', 'acoustic', 'unplugged', 'zamba', 'chacarera', 'folklore', 'folclore',
                     'guitarra', 'gato ', 'cueca', 'vidala', 'chamamé', 'chamame', 'guaraní', 'guarania', 'carnavalito', 'huayno',
                     'bagualero', 'baguala', 'milonga campera', 'camino de las', 'catedral de los']


def es_de_guitarra(tema: str, extra=()) -> bool:
    """«Artista - Tema» de folklore o guitarra criolla (por el artista o por palabras del título)."""
    t = tema.lower()
    artista = t.split(' - ', 1)[0]
    return (any(a in artista for a in list(ARTISTAS_GUITARRA) + [str(x).lower() for x in extra])
            or any(w in t for w in PALABRAS_GUITARRA))


# funk y phonk: con estos se sube al Camaro blanco (se suman más en «artistas_funk» de config.json)
ARTISTAS_FUNK = ['kordhell', 'dvrst', 'interworld', 'pharmacist', 'ghostface playa', 'moondeity', 'playaphonk',
                 'sadfriend', 'lxngvx', 'ncts', 'hensonn', 'kaito shoma', 'sxmpra', 'xantesha', 'mupp',
                 'dxrk', 'slowboy', 'narvent', 'vøj', 'phonkha', 'shadxwbxrn', 'kslv']
PALABRAS_FUNK = ['phonk', 'funk', 'montagem', 'automotivo', 'mtg ', 'brazilian']


# íconos de la música argentina, por género: con cada uno se pone su ropa y toca su instrumento.
# «=nombre» tiene que ser el artista justo (si no, «rodrigo» se confundiría con «Olivia Rodrigo»).
GENEROS = {
    'tango': (['carlos gardel', 'gardel', 'astor piazzolla', 'piazzolla', 'julio sosa', 'aníbal troilo', 'troilo',
               'osvaldo pugliese', 'pugliese', "juan d'arienzo", "d'arienzo", 'roberto goyeneche', 'goyeneche',
               'edmundo rivero', 'susana rinaldi', 'bajofondo', 'gotan project', 'tanghetto', 'adriana varela',
               'hugo del carril', 'francisco canaro', 'carlos di sarli', 'alberto castillo', 'rubén juárez',
               'tita merello', 'horacio salgán', 'orquesta típica'],
              ['tango', 'milonga', 'bandoneón']),
    'cuarteto': (['la mona jiménez', 'la mona jimenez', 'carlos la mona', '=rodrigo', 'ulises bueno', '=la barra',
                  'damián córdoba', 'damian cordoba', 'jean carlos', 'banda xxi', "q' lokura", 'q lokura',
                  "la k'onga", 'la konga', '=sabroso', '=chipote', 'walter olmos', 'trulalá', 'tru la la',
                  'el loco amato', 'luck ra', 'potro rodrigo', 'eugenia quevedo', 'ale ceberio', 'dale q va'],
                 ['cuarteto', 'cuartetazo']),
    'cumbia': (['damas gratis', 'pablo lescano', 'los palmeras', '=gilda', 'ráfaga', 'rafaga', 'antonio ríos',
                'antonio rios', 'la nueva luna', 'los wachiturros', 'yerba brava', 'mala fama', 'supermerk2',
                'ke personajes', 'el polaco', '=la liga', 'amar azul', 'los charros', 'la t y la m', 'l-gante',
                'l gante', 'nene malo', 'los del fuego', 'grupo green', 'uriel lozano', 'leo mattioli',
                'la delio valdez', 'los totora', 'flor de piedra', 'néstor en bloque', 'agapornis', 'los lamas',
                'pibes chorros', 'la base musical', 'el retutu', 'meta guacha', 'los mirlos', 'karina la princesita'],
               ['cumbia', 'cumbión', 'rkt', 'turreo']),
    'rock': (['soda stereo', 'gustavo cerati', '=cerati', 'charly garcía', 'charly garcia', 'luis alberto spinetta',
              'spinetta', 'fito páez', 'fito paez', 'patricio rey', 'redonditos de ricota', 'los redondos',
              'indio solari', 'divididos', 'la renga', 'fabulosos cadillacs', 'andrés calamaro', 'andres calamaro',
              'los rodríguez', 'babasónicos', 'babasonicos', 'callejeros', 'la bersuit', 'bersuit vergarabat',
              'ciro y los persas', 'los piojos', 'las pastillas del abuelo', '=sumo', '=virus',
              'los abuelos de la nada', 'serú girán', 'seru giran', 'almendra', 'pescado rabioso', 'vox dei',
              'el mató a un policía motorizado', 'attaque 77', 'ataque 77', 'los gardelitos', 'catupecu machu',
              '=airbag', 'ratones paranoicos', 'viejas locas', 'intoxicados', 'el bordo', 'las pelotas', '=skay',
              'los auténticos decadentes', 'los autenticos decadentes', 'enanitos verdes', 'david lebón',
              '=pappo', 'los violadores', '2 minutos', 'el otro yo',
              'bandalos chinos', 'conociendo rusia', 'usted señálemelo', 'el kuelgue', 'patricio rey',
              'los tipitos', 'guasones', 'el cuarteto de nos', 'no te va gustar', 'la vela puerca'],
             ['rock nacional']),
    'trap': (['=duki', 'bizarrap', '=bzrp', 'nicki nicole', '=tini', 'maría becerra', 'maria becerra',
              'paulo londra', '=trueno', '=khea', '=emilia', 'lit killah', '=wos', 'milo j', 'ysy a',
              'rusherking', 'tiago pzk', 'neo pistea', 'callejero fino', '=cazzu', '=ca7riel', 'paco amoroso',
              'nathy peluso', '=dillom', '=mesita', '=bhavi', 'seven kayne', 'lucho ssj', '=ecko', '=fmk',
              'big one', '=lali', 'zecca', 'six sex', 'acru', 'kaleb di masi', '=homer el mero mero'],
             ['bzrp', 'music sessions', 'freestyle', 'trap']),
}
GENEROS['folklore'] = (ARTISTAS_GUITARRA, PALABRAS_GUITARRA)
# en las palabras, una «|» al final exige que la palabra termine ahí («reggae|» no confunde «reggaeton»)
GENEROS['electronica'] = (
    ['daft punk', '=justice', '=deadmau5', '=skrillex', '=avicii', 'david guetta', 'calvin harris', 'martin garrix',
     '=tiësto', '=tiesto', '=zedd', 'swedish house mafia', '=kygo', '=alok', '=marshmello', '=diplo', 'kraftwerk',
     'chemical brothers', '=moby', 'fatboy slim', '=bonobo', 'the prodigy', 'eric prydz', '=afrojack',
     'steve aoki', '=flume', '=odesza', '=kaskade', '=alesso', '=hardwell', 'armin van buuren', 'paul van dyk',
     'carl cox', 'boris brejcha', 'charlotte de witte', 'amelie lens', 'nina kraviz', '=solomun', 'jamie xx',
     'cassius', '=air', '=zhu', 'rüfüs du sol', 'rufus du sol', 'lost frequencies'],
    ['techno|', 'dubstep|', 'trance|', 'edm|', 'electrónica|', 'electronica|', 'synthwave|'])
GENEROS['disco'] = (
    ['bee gees', '=abba', 'donna summer', 'gloria gaynor', 'village people', 'boney m', 'sister sledge',
     'the trammps', 'earth, wind', 'earth wind', 'kool & the gang', 'kool and the gang', 'kc and the sunshine',
     'thelma houston', '=sylvester', 'diana ross', '=anita ward', 'lipps inc', '=cerrone', 'nile rodgers',
     'the jacksons', 'george mccrae', '=odyssey', 'rose royce', 'hot chocolate', 'the weather girls'],
    ['disco|', 'disco inferno', 'disco fever', 'disco queen', 'stayin alive', "stayin' alive", 'funkytown'])
GENEROS['reggae'] = (
    ['bob marley', 'peter tosh', 'jimmy cliff', 'toots and the maytals', 'burning spear', 'steel pulse', '=ub40',
     'sean paul', '=shaggy', 'damian marley', 'ziggy marley', '=chronixx', '=protoje', '=koffee', 'buju banton',
     '=sizzla', '=capleton', 'beenie man', 'third world', 'black uhuru', 'the wailers', 'inner circle',
     '=gondwana', 'los cafres', 'dread mar i', 'dread mar-i', '=nonpalidece', 'los pericos', '=alika',
     'fidel nadal', 'rebelution', '=sublime'],
    ['reggae|', 'reggae roots', 'roots reggae', 'dancehall|'])
GENEROS['metal'] = (
    ['metallica', 'iron maiden', 'black sabbath', 'megadeth', '=slayer', '=pantera', 'judas priest', 'motörhead',
     'motorhead', 'ac/dc', 'ozzy osbourne', 'rammstein', 'slipknot', 'system of a down', '=korn', 'sepultura',
     '=anthrax', '=testament', 'avenged sevenfold', '=dragonforce', '=sabaton', 'lamb of god', '=gojira',
     '=mastodon', '=opeth', '=nightwish', '=helloween', 'blind guardian', '=manowar', '=scorpions',
     'deep purple', 'rata blanca', '=hermética', 'almafuerte', 'dream theater', 'children of bodom', 'bring me the horizon', '=disturbed'],
    ['heavy metal', 'death metal', 'black metal', 'thrash metal', 'power metal'])
GENEROS['clasica'] = (
    ['beethoven', 'mozart', '=bach', 'vivaldi', 'chopin', 'tchaikovsky', 'tchaikovski', 'tchaikowsky', 'brahms',
     'schubert', 'debussy', '=ravel', 'händel', 'handel', 'haendel', '=liszt', 'paganini', 'rachmaninoff',
     'rajmáninov', 'stravinsky', '=mahler', '=verdi', '=puccini', '=wagner', 'schumann', 'johann strauss',
     'richard strauss', 'dvořák', 'dvorak', '=grieg', 'saint-saëns', '=satie', '=elgar', 'mendelssohn',
     'orquesta sinfónica', 'filarmónica', 'filarmonica', 'philharmonic', 'symphony orchestra', 'yo-yo ma',
     'lang lang', 'ludovico einaudi', 'rossini', 'bizet', 'albéniz', 'albeniz', 'de falla'],
    ['sinfonía|', 'sinfonia|', 'symphony|', 'sonata|', 'concerto|', 'nocturne|', 'réquiem|', 'requiem|'])

def _artistas(tema: str) -> tuple[str, list[str]]:
    """(campo del artista, cada artista por separado) de un «Artista, Otro - Tema»."""
    artista = tema.lower().split(' - ', 1)[0].strip()
    return artista, [a.strip() for a in re.split(r',|&| feat\.?| ft\.?| x |;', artista) if a.strip()]


def _coincide(nombre: str, artista: str, cada: list[str]) -> bool:
    nombre = str(nombre).lower().strip()
    if not nombre:
        return False
    if nombre.startswith('='):
        return nombre[1:] in cada
    return re.search(r'(?<!\w)' + re.escape(nombre) + r'(?!\w)', artista) is not None


def genero_musical(tema: str, extra: dict | None = None, apagados=()) -> str:
    """El género del tema para vestir al cangrejito: funk, folklore, tango, cuarteto, cumbia, rock,
    trap, electronica, disco, reggae, metal, clasica, o '' si no es ninguno. «extra»: artistas que suma cada persona en la configuración;
    «apagados»: géneros que la persona no quiere."""
    extra = extra or {}
    if 'funk' not in apagados and 'funkytown' not in tema.lower() and es_funk(tema, extra.get('funk') or ()):
        return 'funk'
    artista, cada = _artistas(tema)
    t = tema.lower().split(' - ', 1)[-1]          # las palabras se buscan solo en el título
    # primero por el artista (más seguro), después por palabras del título
    for g, (nombres, _) in GENEROS.items():
        if g not in apagados and any(_coincide(a, artista, cada) for a in list(nombres) + list(extra.get(g) or ())):
            return g
    for g, (_, palabras) in GENEROS.items():
        if g not in apagados and any(re.search(r'(?<!\w)' + re.escape(w.strip().rstrip('|')) + (r'(?!\w)' if w.strip().endswith('|') else ''), t)
                                for w in palabras):
            return g
    return ''


TEMAS_AUTO = rutas.DATOS / 'temas_auto.json'   # temas propios para el Camaro (se edita a mano)
_auto_leido = {'mtime': None, 'datos': {}}


def _temas_auto() -> dict:
    """temas_auto.json, releído solo si cambió."""
    try:
        mtime = TEMAS_AUTO.stat().st_mtime
        if mtime != _auto_leido['mtime']:
            _auto_leido['datos'] = json.loads(TEMAS_AUTO.read_text(encoding='utf-8-sig'))
            _auto_leido['mtime'] = mtime
    except (OSError, ValueError):
        log.exception('no pude leer temas_auto.json')
        _auto_leido['mtime'] = None
    return _auto_leido['datos']


def es_funk(tema: str, extra=()) -> bool:
    """«Artista - Tema» de funk o phonk: por el artista, por «MC …», por palabras del título
    o porque está en la playlist de temas_auto.json (nombre del tema + alguno de sus artistas)."""
    t = tema.lower()
    artista = t.split(' - ', 1)[0]
    datos = _temas_auto()
    artistas = list(ARTISTAS_FUNK) + [str(x).lower() for x in list(extra) + list(datos.get('artistas') or [])]
    if any(a and a in artista for a in artistas) or artista.startswith('mc ') or any(w in t for w in PALABRAS_FUNK):
        return True
    for item in datos.get('temas') or []:
        nombre = str(item.get('tema') or '').lower()
        if nombre and nombre in t and any(str(a).lower() in t for a in item.get('artistas') or []):
            return True
    return False


class Vigilante(QObject):
    app = Signal(bool)                # la app de Claude se abrió / cerró
    afk = Signal(bool)
    monitores_tapados = Signal(set)   # rectángulos de los monitores con algo en pantalla completa
    escuchando = Signal(bool)         # le estás dictando a Claude
    musica = Signal(bool)             # suena Spotify
    tema = Signal(str)                # empezó otro tema («Artista - Tema»)
    juego_pesado = Signal(bool)       # VRChat o SteamVR abiertos: nada de placa de video
    _datos = Signal(object)           # lo que juntó el hilo, para aplicar en el hilo de la interfaz

    def __init__(self, cfg, propias_fn):
        super().__init__()
        self.cfg = cfg
        self.propias_fn = propias_fn      # () -> [hwnd de nuestras ventanas]
        self.forzar = False               # --ya: aparecer aunque la app esté cerrada
        self.app_abierta = None
        self.es_afk = False
        self.tapados: set[str] = set()
        self.dictando = False
        self.sonando = False
        self.tema_actual = ''
        self.vr = False
        self.sesiones: dict[str, dict] = {}
        self._micro_proc = None
        self._micro_inicio = -1e9
        self._vueltas = 0
        self._pids = None
        self._propias: set[int] = set()
        self._parar = threading.Event()
        self._datos.connect(self._aplicar)
        self._rapido = QTimer(self)
        self._rapido.timeout.connect(self._mirar_micro)

    def arrancar(self):
        self._mirar()
        threading.Thread(target=self._hilo_correr, name='vigilante', daemon=True).start()
        self._rapido.start(700)
        self._encima_t = QTimer(self)                 # un solo temporizador: un menú o una ventana nueva
        self._encima_t.setSingleShot(True)            # disparan varios avisos seguidos y no hace falta uno por cada uno
        self._encima_t.timeout.connect(self.encima)
        self._gancho = so.enganchar_cambio_ventana(lambda: self._encima_t.start(150))
        if self._gancho is None and sys.platform == 'win32':
            log.warning('no pude enganchar el cambio de ventana: queda solo el repaso cada 2 s')

    def encima(self):
        try:
            for h in self.propias_fn():
                so.poner_encima(int(h))
        except Exception:
            log.exception('encima')

    def _mirar_micro(self):
        """El micrófono se consulta en un proceso aparte (microfono.py --servir): si Windows
        se pone raro con el audio, se cae ese proceso y no el cangrejito."""
        from PySide6.QtCore import QProcess
        if sys.platform != 'win32':
            return                      # en Linux no se detecta el dictado (todavía)
        if self._micro_proc is None or self._micro_proc.state() == QProcess.ProcessState.NotRunning:
            if time.monotonic() - self._micro_inicio < 10:
                return
            self._micro_inicio = time.monotonic()
            self._micro_proc = QProcess(self)
            self._micro_proc.readyReadStandardOutput.connect(self._leer_micro)
            if rutas.CONGELADO:          # instalado: el mismo .exe en modo micrófono
                self._micro_proc.start(sys.executable, ['--microfono'])
            else:
                aqui = Path(__file__).resolve().parent
                self._micro_proc.start(str(Path(sys.executable).with_name('python.exe')),
                                       ['-u', str(aqui / 'microfono.py'), '--servir'])
            log.info('arranca el vigilante del micrófono')

    def _leer_micro(self):
        for linea in bytes(self._micro_proc.readAllStandardOutput()).decode(errors='ignore').split():
            dictando = bool(self.app_abierta) and linea.strip() == '1'
            if dictando != self.dictando:
                self.dictando = dictando
                log.info('dictado: %s', dictando)
                self.escuchando.emit(dictando)

    # --- el repaso de la PC (procesos, ventanas, Spotify…) se junta en un hilo aparte: recorrer todos
    # los procesos y ventanas de Windows tarda decenas de milisegundos y, en el hilo de la interfaz,
    # trababa el arrastre y el menú cada 2 segundos.
    def _juntar(self, propias: set[int], vuelta: int) -> dict:
        d = {}
        ventanas = so.ventanas()
        if vuelta % 3 == 0 or self._pids is None:         # los procesos cambian despacio: cada 6 s
            self._pids = so.pids_app_claude()             # de paso anota si hay VR abierto
        d['abierta'] = bool(self.forzar or self.cfg.get('siempre_visible', False)
                            or so.app_claude_abierta(ventanas, self._pids))
        d['afk'] = so.segundos_inactivo() >= self.cfg['afk_minutos'] * 60
        d['tapados'] = set(so.monitores_en_pantalla_completa(propias, ventanas))
        d['vr'] = so.hay_vr()
        d['tema'] = so.spotify_tema(ventanas)
        d['sesiones'] = self._leer_sesiones() if vuelta % 2 == 0 else None
        return d

    def _hilo_correr(self):
        vuelta = 1
        while not self._parar.wait(2.0):
            try:
                self._datos.emit(self._juntar(self._propias, vuelta))
            except Exception:
                log.exception('vigilante (hilo)')
            vuelta += 1

    def _mirar(self):
        """Un repaso completo ahora mismo (al arrancar y en las pruebas)."""
        self._propias = {int(h) for h in self.propias_fn()}
        try:
            self._aplicar(self._juntar(self._propias, 0))
        except Exception:
            log.exception('vigilante')

    def _aplicar(self, d: dict):
        self._vueltas += 1
        try:
            abierta = d['abierta']
            if abierta != self.app_abierta:
                self.app_abierta = abierta
                log.info('app de Claude %s', 'abierta' if abierta else 'cerrada')
                self.app.emit(abierta)
            if d['afk'] != self.es_afk:
                self.es_afk = d['afk']
                self.afk.emit(d['afk'])
            if d['tapados'] != self.tapados:
                self.tapados = set(d['tapados'])
                log.info('pantalla completa: %s', d['tapados'] or 'ninguna')
                self.monitores_tapados.emit(set(d['tapados']))
            if d['vr'] != self.vr:
                self.vr = d['vr']
                log.info('VRChat/SteamVR abierto: %s', d['vr'])
                self.juego_pesado.emit(d['vr'])
            tema = d['tema']
            sonando = bool(tema)
            if sonando != self.sonando:
                self.sonando = sonando
                self.musica.emit(sonando)
            if tema and tema != self.tema_actual:      # pausar y seguir con el mismo tema no cuenta
                self.tema_actual = tema
                self.tema.emit(tema)
            if d['sesiones'] is not None:
                self.sesiones = d['sesiones']
            self._propias = {int(h) for h in self.propias_fn()}
            if self._vueltas % 5 == 0:                 # repaso por las dudas (el aviso al toque es el gancho)
                self.encima()
            if self._vueltas % 30 == 0:
                so.olvidar_nombres()
        except Exception:
            log.exception('vigilante')

    def _leer_sesiones(self):
        nuevas = {}
        try:
            for f in SESIONES.glob('*.json'):
                try:
                    d = json.loads(f.read_text(encoding='utf-8'))
                    if d.get('sessionId') and psutil.pid_exists(int(d.get('pid', 0))):
                        nombre = d.get('name') or os.path.basename((d.get('cwd') or '').rstrip('\\/'))
                        nuevas[d['sessionId']] = {'name': nombre, 'status': d.get('status') or ''}
                except Exception:
                    continue
        except Exception:
            pass
        return nuevas
