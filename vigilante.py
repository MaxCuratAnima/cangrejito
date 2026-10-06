"""Mira la PC cada 2 segundos: si la app de Claude está abierta, si estás AFK, qué monitores
tienen algo en pantalla completa (un juego o un video), si le estás dictando a Claude,
si suena Spotify y qué sesiones de Claude Code están activas."""
from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import json
import logging
import os
import sys
import time
from pathlib import Path

import psutil
from PySide6.QtCore import QObject, QTimer, Signal

import rutas

log = logging.getLogger('cangrejito.vigilante')
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi
SESIONES = Path.home() / '.claude' / 'sessions'
CLASES_ESCRITORIO = {'Progman', 'WorkerW', 'Shell_TrayWnd', 'Shell_SecondaryTrayWnd'}
# procesos cuyas ventanas grandes no son «pantalla completa» (paneles, overlays)
NO_CUENTAN = {'explorer.exe', 'modogamer.exe', 'nvidia overlay.exe', 'nvidia share.exe', 'textinputhost.exe',
              'shellexperiencehost.exe', 'searchhost.exe', 'startmenuexperiencehost.exe', 'lockapp.exe',
              'gamebar.exe', 'wallpaper32.exe', 'wallpaper64.exe', 'lively.exe'}
HWND_TOPMOST = -1
SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x1, 0x2, 0x10
GWL_STYLE, GWL_EXSTYLE = -16, -20
WS_EX_TOOLWINDOW, WS_EX_TRANSPARENT, WS_EX_NOACTIVATE = 0x80, 0x20, 0x08000000
DWMWA_CLOAKED = 14


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', wt.UINT), ('dwTime', wt.DWORD)]


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [('cbSize', wt.DWORD), ('rcMonitor', wt.RECT), ('rcWork', wt.RECT), ('dwFlags', wt.DWORD),
                ('szDevice', wt.WCHAR * 32)]


user32.GetForegroundWindow.restype = wt.HWND
user32.MonitorFromWindow.restype = wt.HMONITOR
user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
user32.GetMonitorInfoW.argtypes = [wt.HMONITOR, ctypes.POINTER(MONITORINFOEX)]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsIconic.argtypes = [wt.HWND]
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wt.UINT]
dwmapi.DwmGetWindowAttribute.argtypes = [wt.HWND, wt.DWORD, ctypes.c_void_p, wt.DWORD]
ENUM = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)


def segundos_inactivo() -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(lii)
    user32.GetLastInputInfo(ctypes.byref(lii))
    return ((kernel32.GetTickCount() - lii.dwTime) & 0xFFFFFFFF) / 1000.0


def _ventanas():
    """Ventanas de primer nivel visibles: (hwnd, pid)."""
    out = []

    def cb(hwnd, _):
        if user32.IsWindowVisible(hwnd):
            pid = wt.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            out.append((hwnd, pid.value))
        return True

    user32.EnumWindows(ENUM(cb), 0)
    return out


def _monitor(hwnd):
    mi = MONITORINFOEX()
    mi.cbSize = ctypes.sizeof(mi)
    if not user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(mi)):
        return None
    return mi


_nombres: dict[int, str] = {}


def _proceso(pid: int) -> str:
    n = _nombres.get(pid)
    if n is None:
        try:
            n = psutil.Process(pid).name().lower()
        except psutil.Error:
            n = ''
        _nombres[pid] = n
    return n


def monitores_en_pantalla_completa(propias: set[int], ventanas=None) -> dict[tuple, str]:
    """{(izq, arriba, der, abajo) del monitor: proceso} tapados por una ventana a pantalla completa."""
    tapados = {}
    for hwnd, pid in (ventanas if ventanas is not None else _ventanas()):
        h = int(hwnd)
        if h in propias or user32.IsIconic(hwnd):
            continue
        ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE) & 0xFFFFFFFF
        if ex & (WS_EX_TOOLWINDOW | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE):
            continue
        oculta = wt.DWORD()
        if dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED, ctypes.byref(oculta), 4) == 0 and oculta.value:
            continue
        r = wt.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            continue
        mi = _monitor(hwnd)
        if mi is None:
            continue
        m = mi.rcMonitor
        proc = _proceso(pid)
        # VRChat tapa su monitor aunque esté en ventana (en VR casi nunca va a pantalla completa)
        if proc != 'vrchat.exe' and not (r.left <= m.left and r.top <= m.top
                                         and r.right >= m.right and r.bottom >= m.bottom):
            continue
        clase = ctypes.create_unicode_buffer(64)
        user32.GetClassNameW(hwnd, clase, 64)
        if clase.value in CLASES_ESCRITORIO:
            continue
        if proc in NO_CUENTAN:
            continue
        tapados.setdefault((m.left, m.top, m.right, m.bottom), proc)
    return tapados


JUEGOS_PESADOS = {'vrchat.exe', 'vrserver.exe', 'vrmonitor.exe', 'vrcompositor.exe'}   # VR: la placa va al 100 %
_pesado = [False]


def pids_app_claude() -> set[int]:
    """Procesos de la app de escritorio de Claude (Store o instalador clásico), no los de Claude Code.
    De paso anota si hay VRChat o SteamVR abiertos (en _pesado)."""
    pids = set()
    pesado = False
    for p in psutil.process_iter(['name']):
        try:
            nombre = (p.info['name'] or '').lower()
            if nombre in JUEGOS_PESADOS:
                pesado = True
            if nombre == 'claude.exe' and rutas.es_app_claude(p.exe()):
                pids.add(p.pid)
        except (psutil.Error, OSError):
            continue
    _pesado[0] = pesado
    return pids


def _titulo(hwnd) -> str:
    n = user32.GetWindowTextLengthW(hwnd)
    if n <= 0:
        return ''
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(hwnd, buf, n + 1)
    return buf.value


def spotify_tema(ventanas) -> str:
    """«Artista - Tema» si Spotify está sonando ('' en pausa: ahí el título es «Spotify…»)."""
    for hwnd, pid in ventanas:
        if _proceso(pid) == 'spotify.exe':
            t = _titulo(hwnd)
            if ' - ' in t and not t.lower().startswith('spotify'):
                return t
    return ''


def poner_encima(hwnd: int):
    user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)


# folklore y guitarra criolla: con estos se sienta a tocar la guitarra vestido de gaucho
# (se suman más desde config.json, en «artistas_guitarra»)
ARTISTAS_GUITARRA = ['chaqueño', 'palavecino', 'los nocheros', 'abel pintos', 'soledad', 'jorge rojas',
                     'los tekis', 'luciano pereyra', 'los manseros', 'mercedes sosa', 'yupanqui',
                     'chalchaleros', 'fronterizos', 'los huayra', 'destino san javier', 'lucio rojas',
                     'galleguillo', 'carabajal', 'raly barrionuevo', 'facundo toro', 'los alonsitos',
                     'christian herrera', 'nahuel pennisi', 'larralde', 'horacio guarany', 'los cantores del alba',
                     'los kjarkas', 'cuti y roberto carabajal', 'los visconti', 'la callejera']
PALABRAS_GUITARRA = ['acústic', 'acoustic', 'unplugged', 'zamba', 'chacarera', 'folklore', 'folclore',
                     'guitarra', 'gato ', 'cueca', 'vidala', 'chamamé', 'chamame']


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


# cuando cambia la ventana de adelante, el cangrejito se vuelve a poner arriba enseguida
# (la app de Claude también es «siempre visible»: al tocarla, Windows la ponía encima de él)
WINEVENTPROC = ctypes.WINFUNCTYPE(None, wt.HANDLE, wt.DWORD, wt.HWND, wt.LONG, wt.LONG, wt.DWORD, wt.DWORD)
user32.SetWinEventHook.restype = wt.HANDLE
user32.SetWinEventHook.argtypes = [wt.DWORD, wt.DWORD, wt.HMODULE, WINEVENTPROC, wt.DWORD, wt.DWORD, wt.DWORD]
EVENT_SYSTEM_FOREGROUND = 0x0003


class Vigilante(QObject):
    app = Signal(bool)                # la app de Claude se abrió / cerró
    afk = Signal(bool)
    monitores_tapados = Signal(set)   # rectángulos de los monitores con algo en pantalla completa
    escuchando = Signal(bool)         # le estás dictando a Claude
    musica = Signal(bool)             # suena Spotify
    tema = Signal(str)                # empezó otro tema («Artista - Tema»)
    juego_pesado = Signal(bool)       # VRChat o SteamVR abiertos: nada de placa de video

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
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._mirar)
        self._rapido = QTimer(self)
        self._rapido.timeout.connect(self._mirar_micro)

    def arrancar(self):
        self._mirar()
        self._timer.start(2000)
        self._rapido.start(700)
        self._al_cambiar = WINEVENTPROC(lambda *_: QTimer.singleShot(120, self.encima))
        self._gancho = user32.SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_FOREGROUND, None,
                                              self._al_cambiar, 0, 0, 0)
        if not self._gancho:
            log.warning('no pude enganchar el cambio de ventana: queda solo el repaso cada 2 s')

    def encima(self):
        try:
            for h in self.propias_fn():
                poner_encima(int(h))
        except Exception:
            log.exception('encima')

    def _mirar_micro(self):
        """El micrófono se consulta en un proceso aparte (microfono.py --servir): si Windows
        se pone raro con el audio, se cae ese proceso y no el cangrejito."""
        from PySide6.QtCore import QProcess
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

    def _mirar(self):
        self._vueltas += 1
        try:
            ventanas = _ventanas()
            pids = pids_app_claude()          # siempre: de paso anota si hay VR abierto
            abierta = (self.forzar or self.cfg.get('siempre_visible', False)
                       or any(pid in pids and user32.GetWindowTextLengthW(h) > 0 for h, pid in ventanas))
            if abierta != self.app_abierta:
                self.app_abierta = abierta
                log.info('app de Claude %s', 'abierta' if abierta else 'cerrada')
                self.app.emit(abierta)

            afk = segundos_inactivo() >= self.cfg['afk_minutos'] * 60
            if afk != self.es_afk:
                self.es_afk = afk
                self.afk.emit(afk)

            propias = {int(h) for h in self.propias_fn()}
            tapados = monitores_en_pantalla_completa(propias, ventanas)
            if set(tapados) != self.tapados:
                self.tapados = set(tapados)
                log.info('pantalla completa: %s', tapados or 'ninguna')
                self.monitores_tapados.emit(set(tapados))

            vr = _pesado[0]
            if vr != self.vr:
                self.vr = vr
                log.info('VRChat/SteamVR abierto: %s', vr)
                self.juego_pesado.emit(vr)

            tema = spotify_tema(ventanas)
            sonando = bool(tema)
            if sonando != self.sonando:
                self.sonando = sonando
                self.musica.emit(sonando)
            if tema and tema != self.tema_actual:      # pausar y seguir con el mismo tema no cuenta
                self.tema_actual = tema
                self.tema.emit(tema)

            if self._vueltas % 2 == 0:
                self._leer_sesiones()
            for h in propias:                          # repaso por las dudas, además del aviso al toque
                poner_encima(h)
            if self._vueltas % 30 == 0:
                _nombres.clear()
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
        self.sesiones = nuevas
