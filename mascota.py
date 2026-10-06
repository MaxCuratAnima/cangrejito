"""La ventana del cangrejito: animación, física tipo Shimeji, paseos y mouse.

Estados:
  base     — actividad duradera: libre, pensar, teclear, terminal, leer, buscar, web,
             llamar, preguntar, dormir.
  momento  — algo corto que se pone encima un rato: saludar, sorpresa, error, festejar,
             mimo, silencio, voz, bostezar, despertar, aterrizar, mareado.
  modo     — el cuerpo: suelo, cayendo, agarrado, entrando, saliendo, oculto.
"""
from __future__ import annotations

import math
import random
import time
from collections import deque

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QGuiApplication, QPainter
from PySide6.QtWidgets import QApplication, QWidget

import sprites as S
from globo import Globo
from sprites import Pose

TRABAJOS = {'pensar', 'teclear', 'terminal', 'leer', 'buscar', 'web', 'llamar', 'preguntar'}
ACCESORIOS = {
    'teclear': {'netbook'}, 'terminal': {'netbook', 'terminal'}, 'leer': {'libro'}, 'buscar': {'lupa'},
    'web': {'mundo'}, 'pensar': {'netbook', 'pensar'}, 'llamar': {'exclamacion'}, 'preguntar': {'pregunta'},
}
MATE_TRABAJOS = {'teclear', 'terminal', 'pensar', 'leer'}   # donde tiene una pinza libre para el mate


def _fase_mate(u: float) -> str:
    """Mate mientras labura: ceba, toma, teclea con una mano, toma de nuevo… y lo deja en el piso."""
    if u < 3:
        return 'cebar'
    if any(ini <= u < ini + 2 for ini in (3, 10, 17)):
        return 'sorbo'
    return 'mano' if u < 19 else 'dejado'


GRAVEDAD = 2600.0
VEL_PASEO = 42.0
COLORES_CONFETI = ['o', 'y', 'n', 'B', 'r', 'w', 'c']


class Mascota(QWidget):
    clic_silencio = Signal()
    mimado = Signal()
    menu_pedido = Signal(QPoint)
    se_fue = Signal()

    def __init__(self, cfg, voz):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool | Qt.WindowType.NoDropShadowWindowHint
                         | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.cfg = cfg
        self.voz = voz
        self.E = int(cfg['escala'])
        self.setFixedSize(S.W * self.E, S.H * self.E)
        self.globo = Globo()

        self.base = 'libre'
        self.mom, self.mom_ini, self.mom_fin = None, 0.0, 0.0
        self.modo = 'oculto'
        self.px, self.py = 0.0, 0.0
        self.vx, self.vy = 0.0, 0.0
        self.dir = 1
        self.paseo, self.paseo_fin, self.paseo_x = 'quieto', 0.0, None
        self.ayudantes = 0
        self.alfas: dict[str, float] = {}
        self.particulas: list[dict] = []
        self.prox_parpadeo, self.parpadeo_hasta = time.monotonic() + 3, 0.0
        self.prox_z = 0.0
        self.hover_desde = None
        self.imagen = None
        self.topes: deque = deque()
        self.pausado = False
        self.pendiente_mareo = False
        self.escuchando = False          # le estás dictando a Claude
        self.musica = False              # suena Spotify
        self.guitarra = False            # el tema es folklore / guitarra criolla
        self.funk = False                # suena funk o phonk: se sube al Camaro
        self.derrape_hasta = 0.0
        self.bajando_auto = None         # cuándo empezó a bajarse del auto (para ponerse a laburar)
        self.mate_ini = None             # cuándo empezó el mate de trabajo (None: sin mate)
        self.prox_mate = time.monotonic() + random.uniform(60, 180)
        self.trabajando_desde = None
        self.prox_baile = 0.0
        self.prox_nota = 0.0
        self.prox_confeti = 0.0
        self.tapados: set[str] = set()   # monitores con algo en pantalla completa
        self.al_llegar = None
        self.tras_herramienta = None
        self.durmiendo_desde = None
        # mouse
        self.presion = None
        self.arrastrando = False
        self.agarre = QPointF()
        self.historial: deque = deque(maxlen=12)
        self.sacudidas: deque = deque(maxlen=20)
        self._clic = QTimer(self)
        self._clic.setSingleShot(True)
        self._clic.timeout.connect(self.clic_silencio.emit)

        self.t0 = self._ult = time.monotonic()
        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)

    # ================================================================ API
    def actividad(self, nombre: str):
        if nombre == self.base:
            return
        self.tras_herramienta = None
        if self.base == 'dormir' and nombre != 'dormir':
            self.durmiendo_desde = None
        self.base = nombre
        if nombre in TRABAJOS and self.modo == 'suelo':
            if self.paseo == 'auto':
                self.bajando_auto, self.vx = time.monotonic(), 0.0     # salta del auto y se pone a laburar
            self.paseo, self.paseo_x = 'quieto', None

    def trabajando(self) -> bool:
        return self.base in TRABAJOS

    def despues_de_herramienta(self):
        """Terminó una herramienta: si en 1,5 s no empieza otra, se pone a pensar."""
        self.tras_herramienta = time.monotonic() + 1.5

    def momento(self, nombre: str, dur: float):
        ahora = time.monotonic()
        self.mom, self.mom_ini, self.mom_fin = nombre, ahora, ahora + dur
        cx, cy = self._cabeza()
        if nombre == 'festejar':
            for _ in range(28):
                self._particula(random.choice(COLORES_CONFETI), cx + random.uniform(-30, 30), cy,
                                random.uniform(-150, 150), random.uniform(-330, -160), 700, 1.9, confeti=True)
        elif nombre == 'mimo':
            for i in range(5):
                self._particula(S.CORAZON, cx + random.uniform(-40, 40), cy + 10, random.uniform(-15, 15), -45,
                                0, 1.5, retraso=i * 0.22, escala=0.75)
        elif nombre == 'silencio':
            self._particula(S.PARLANTE_MUDO, cx + 30, cy - 20, 0, -18, 0, 1.6, escala=0.75)
        elif nombre == 'voz':
            self._particula(S.PARLANTE, cx + 30, cy - 20, 0, -18, 0, 1.4, escala=0.75)
        elif nombre == 'mareado':
            for i in range(3):
                self._particula(S.ESTRELLA, cx, cy, 0, 0, 0, dur, orbita=i * 2.094, escala=0.75)
        elif nombre == 'orgulloso':
            for _ in range(40):
                self._particula(random.choice(COLORES_CONFETI), cx + random.uniform(-40, 40), cy,
                                random.uniform(-190, 190), random.uniform(-380, -180), 700, 2.2, confeti=True)
            for i in range(4):
                self._particula(S.ESTRELLA, cx + random.uniform(-50, 50), cy + 5, random.uniform(-20, 20), -40,
                                0, 1.8, retraso=i * 0.3, escala=0.8)

    def escuchar(self, si: bool):
        self.escuchando = si
        if si and self.mom in ('bailar', 'silbar', 'saludar', 'festejar', 'orgulloso', 'mimo', 'fiesta', 'casi'):
            self.mom = None                 # deja lo que estaba haciendo y te presta atención

    def monitores_tapados(self, tapados: set):
        """Un juego o video tapa un monitor: el cangrejito se muda a otro que esté libre."""
        self.tapados = set(tapados)
        libres = [s for s in QGuiApplication.screens() if s.name() not in self.tapados]
        if self.modo == 'oculto':
            return
        if not libres:
            self.pausar(True)
            return
        if self.pausado:
            self.pausar(False)
        if self._pantalla_actual().name() in self.tapados and self.modo != 'agarrado':
            self._mudarse(libres[0])

    def _mudarse(self, pant):
        """Aparece en otra pantalla cayendo desde arriba (sin pasar por el monitor tapado)."""
        ag = pant.availableGeometry()
        izq, der = self._limites(ag)
        x = self.cfg.get('x_' + pant.name())
        self.px = float(x) if x is not None and izq <= x <= der else float(der - 200)
        self.py = ag.top() + ag.height() * 0.35
        self.vx = self.vy = 0.0
        self.modo = 'cayendo'
        self.paseo, self.paseo_x = 'quieto', None
        self.move(round(self.px), round(self.py))

    def ayudante(self, delta: int):
        self.ayudantes = max(0, self.ayudantes + delta)

    def dormir(self):
        if self.base == 'libre' and self.modo == 'suelo':
            self.momento('bostezar', 1.8)
            self.base = 'dormir'
            self.durmiendo_desde = time.monotonic()

    def despertar(self) -> float:
        """Despierta si estaba dormido; devuelve cuántos segundos durmió."""
        if self.base != 'dormir':
            return 0.0
        dormido = time.monotonic() - (self.durmiendo_desde or time.monotonic())
        self.base = 'libre'
        self.durmiendo_desde = None
        self.momento('despertar', 1.0)
        return dormido

    def entrar(self, al_llegar=None):
        """Aparece caminando desde el borde de la pantalla donde estuvo la última vez."""
        pant = self._pantalla_guardada()
        libres = [s for s in QGuiApplication.screens() if s.name() not in self.tapados]
        if pant.name() in self.tapados and libres:
            pant = libres[0]
        ag = pant.availableGeometry()
        destino = self.cfg.get('x')
        izq, der = self._limites(ag)
        if destino is None or not (izq <= destino <= der):
            destino = der - 180
        desde_der = destino > ag.center().x()
        self.px = (ag.right() + 1 - (S.OX + 3) * self.E) if desde_der else (ag.left() - (S.OX + 31) * self.E)
        self.py = self._piso(ag)
        self.dir = -1 if desde_der else 1
        self.paseo_x = float(destino)
        self.modo = 'entrando'
        self.al_llegar = al_llegar
        self.pausado = False
        self.move(round(self.px), round(self.py))
        self.show()
        self._timer.start(33)
        if not libres:
            self.pausar(True)       # un juego tapa todo: entra (y saluda) cuando se libere un monitor

    def salir(self):
        if self.modo == 'oculto':
            return
        self._guardar_posicion()
        ag = self._pantalla_actual().availableGeometry()
        centro = self.px + S.W * self.E / 2
        self.dir = 1 if centro > ag.center().x() else -1
        self.momento('despedida', 2.2)
        self.modo = 'saliendo'
        self.paseo_x = (ag.right() + 40.0) if self.dir > 0 else (ag.left() - S.W * self.E - 40.0)

    def pausar(self, si: bool):
        """Juego o video en pantalla completa: se esconde y no gasta nada."""
        self.pausado = si
        if si:
            self.hide()
            self.globo.hide()
            self._timer.stop()
        elif self.modo != 'oculto':
            self.show()
            self._ult = time.monotonic()
            self._timer.start(33)

    def llevar_a_otro_monitor(self):
        pantallas = QGuiApplication.screens()
        if len(pantallas) < 2:
            return
        actual = self._pantalla_actual()
        otra = pantallas[(pantallas.index(actual) + 1) % len(pantallas)]
        ag = otra.availableGeometry()
        self.px = ag.center().x() - S.W * self.E / 2
        self.py = ag.top() + 80
        self.vx, self.vy = 0.0, 0.0
        self.modo = 'cayendo'

    def hwnds(self):
        out = []
        for w in (self, self.globo):
            if w.isVisible():
                out.append(int(w.winId()))
        return out

    # ================================================================ geometría
    def _pantalla_actual(self):
        c = QPoint(round(self.px + S.W * self.E / 2), round(self.py + (S.OY + 20) * self.E))
        pant = QGuiApplication.screenAt(c)
        if pant is None:
            pant = min(QGuiApplication.screens(), key=lambda s: _distancia(s.geometry(), c))
        return pant

    def _pantalla_guardada(self):
        nombre = self.cfg.get('pantalla')
        for s in QGuiApplication.screens():
            if s.name() == nombre:
                return s
        return QGuiApplication.primaryScreen()

    def _piso(self, ag: QRect) -> float:
        return ag.bottom() + 1 - S.PIES * self.E

    def _limites(self, ag: QRect):
        return ag.left() - (S.OX + 3) * self.E, ag.right() + 1 - (S.OX + 31) * self.E

    def _cabeza(self):
        return S.CABEZA[0] * self.E, (S.CABEZA[1] - 2) * self.E

    def _guardar_posicion(self):
        pant = self._pantalla_actual()
        self.cfg['x'] = round(self.px)
        self.cfg['x_' + pant.name()] = round(self.px)
        self.cfg['pantalla'] = pant.name()
        self.cfg.guardar()

    def _hay_pantalla_en(self, x_centro: float, y: float) -> bool:
        """Hay pantalla ahí y no está tapada por un juego o video."""
        s = QGuiApplication.screenAt(QPoint(round(x_centro), round(y)))
        return s is not None and s.name() not in self.tapados

    # ================================================================ reloj
    def _tick(self):
        ahora = time.monotonic()
        dt = min(0.05, ahora - self._ult)
        self._ult = ahora
        if self.mom and ahora >= self.mom_fin:
            fin = self.mom
            self.mom = None
            if fin == 'aterrizar' and self.pendiente_mareo:
                self.pendiente_mareo = False
                self.momento('mareado', 2.4)
        if self.tras_herramienta and ahora >= self.tras_herramienta:
            self.tras_herramienta = None
            if self.base in TRABAJOS - {'llamar', 'preguntar'}:
                self.base = 'pensar'
        if self.modo == 'oculto':
            return
        self._fisica(dt, ahora)
        if self.modo == 'oculto':
            return
        self._paseos(ahora)
        self._reloj_mate(ahora)
        pose = self._pose(ahora)
        img = S.dibujar(pose)
        self._mover_particulas(dt, ahora)
        cambio = self.imagen is None or img != self.imagen
        if cambio or self.particulas:
            self.imagen = img
            self.update()
        x, y = round(self.px), round(self.py)
        if (x, y) != (self.x(), self.y()):
            self.move(x, y)
        if cambio:
            self.topes.append((ahora, S.fila_superior(img)))
        while len(self.topes) > 1 and ahora - self.topes[0][0] > 1.0:
            self.topes.popleft()
        if self.globo.tick(dt):
            cx, _ = self._cabeza()
            tope = min(t for _, t in self.topes) if self.topes else S.OY + 16
            self.globo.seguir(x + cx, y + (tope - 1) * self.E, self._pantalla_actual().availableGeometry(),
                              y + S.H * self.E)
        # quieto y sin nada que animar: 15 cuadros por segundo alcanzan
        tranquilo = (self.modo == 'suelo' and not self.mom and self.paseo not in ('caminar', 'auto')
                     and (not self.particulas or self.base == 'dormir')
                     and self.base in ('libre', 'dormir') and not self.voz.hablando and not self.globo.isVisible())
        intervalo = 66 if tranquilo else 33
        if self._timer.interval() != intervalo:
            self._timer.setInterval(intervalo)

    # ================================================================ física
    def _fisica(self, dt: float, ahora: float):
        E = self.E
        if self.modo == 'agarrado':
            return
        pant = self._pantalla_actual()
        ag = pant.availableGeometry()
        piso = self._piso(ag)
        centro = self.px + S.W * E / 2

        if self.modo == 'cayendo':
            self.vy += GRAVEDAD * dt
            nx = self.px + self.vx * dt
            if not self._hay_pantalla_en(nx + S.W * E / 2, self.py + (S.OY + 20) * E):
                self.vx = -self.vx * 0.4
                nx = self.px
            self.px = nx
            self.py += self.vy * dt
            techo = ag.top() - (S.OY + 10) * E
            if self.py < techo and self.vy < 0:
                self.vy = abs(self.vy) * 0.3
            piso = self._piso(self._pantalla_actual().availableGeometry())
            if self.py >= piso:
                self.py = piso
                if self.vy > 520:
                    self.vy = -self.vy * 0.33
                    self.vx *= 0.6
                    self.momento('aterrizar', 0.14)
                else:
                    self.vx = self.vy = 0.0
                    self.modo = 'suelo'
                    self.momento('aterrizar', 0.2)
                    actual = self._pantalla_actual()
                    if actual.name() in self.tapados:
                        libres = [s for s in QGuiApplication.screens() if s.name() not in self.tapados]
                        if libres:
                            self._mudarse(libres[0])
                            return
                    self._guardar_posicion()
            return

        if self.modo in ('suelo', 'entrando', 'saliendo'):
            if self.modo == 'suelo' and self.py < piso - 8:
                self.modo = 'cayendo'
                self.vx = self.vy = 0.0
                return
            self.py = piso
            if self.modo == 'suelo' and self.paseo == 'auto':
                self._manejar(dt, ahora, ag)
                return
            if self.paseo_x is not None and (self.modo != 'suelo' or self.paseo == 'caminar'):
                vel = {'entrando': 75.0, 'saliendo': 85.0}.get(self.modo, VEL_PASEO)
                paso = vel * dt * (1 if self.paseo_x > self.px else -1)
                self.dir = 1 if paso > 0 else -1
                siguiente = self.px + paso
                if self.modo == 'suelo' and not self._hay_pantalla_en(siguiente + S.W * E / 2 + self.dir * 40,
                                                                     self.py + (S.OY + 20) * E):
                    self.paseo_x = None
                    self.paseo_fin = 0
                    return
                if abs(self.paseo_x - self.px) <= abs(paso):
                    self.px = self.paseo_x
                    self.paseo_x = None
                    if self.modo == 'entrando':
                        self.modo = 'suelo'
                        self.momento('saludar', 2.2)
                        self.paseo, self.paseo_fin = 'quieto', ahora + 4
                        if self.al_llegar:
                            cb, self.al_llegar = self.al_llegar, None
                            cb()
                    elif self.modo == 'saliendo':
                        self.modo = 'oculto'
                        self.hide()
                        self.globo.hide()
                        self.se_fue.emit()
                    else:
                        self.paseo_fin = 0
                        self._guardar_posicion()
                else:
                    self.px = siguiente

    def _manejar(self, dt: float, ahora: float, ag: QRect):
        """Arriba del Camaro: va de punta a punta del monitor y, en las puntas o de onda, derrapa
        echando humo y pega la vuelta."""
        E = self.E
        izq = ag.left() - S.OX * E                        # el auto entero adentro de la pantalla
        der = ag.right() + 1 - (S.OX + 34) * E
        if self.escuchando:
            self.vx -= self.vx * min(1.0, 4.0 * dt)       # le estás hablando: frena y te escucha desde el auto
        elif ahora < self.derrape_hasta:
            self.vx -= self.vx * min(1.0, 3.2 * dt)       # patina de costado y frena
            self._humo(3)
        else:
            self.vx += (200.0 * self.dir - self.vx) * min(1.0, 1.6 * dt)
            if self.vx * self.dir < 150:                  # arranca quemando goma
                self._humo(2)
            cerca = (self.dir > 0 and self.px > der - 70) or (self.dir < 0 and self.px < izq + 70)
            if cerca or random.random() < dt / 10:        # en las puntas, y cada tanto de onda
                self.derrape_hasta = ahora + 1.1
                self.dir = -self.dir
        self.px = max(izq, min(der, self.px + self.vx * dt))
        if ahora >= self.prox_nota and not self.escuchando:
            self.prox_nota = ahora + random.uniform(0.6, 1.0)
            cx, cy = self._cabeza()
            self._particula(S.NOTA, cx + random.uniform(-30, 30), cy - 20, -self.dir * 20, -30, 0, 1.6,
                            vaiven=True, escala=0.6)

    def _humo(self, cuantas: int):
        """Nubes de humo de la rueda de atrás (queda una estela, porque salen para el lado contrario)."""
        E = self.E
        rueda = (S.OX + S.RUEDAS_X[0 if self.dir > 0 else 1]) * E
        for _ in range(cuantas):
            self._particula(random.choice((S.HUMO, S.HUMO, S.HUMO_CLARO)), rueda + random.uniform(-8, 8),
                            (S.OY + 28) * E + random.uniform(-4, 3), -self.dir * random.uniform(20, 130),
                            random.uniform(-55, -10), -25, random.uniform(0.8, 1.5),
                            escala=random.uniform(0.5, 1.2))

    def _pose_bajarse(self, p: Pose, u: float, quiero: set) -> bool:
        """Tiene que laburar: salta del auto, aterriza, y el auto se va solo mientras lo saluda."""
        quiero.add('auto')
        p.dir = self.dir
        if u < 0.9:
            k = u / 0.9
            p.y = round(-5 + 5 * k - 8 * math.sin(math.pi * k))
            p.patas = 'abiertas'
            p.brazos, p.fase_brazos = ('festejo', 'festejo'), int(u * 10)
            p.ojos, p.boca_forma = 'grandes', 'o'
            p.auto_atras = k > 0.5                      # ya pasó por arriba de la puerta
            if k < 0.4:
                quiero.add('lentes')
        elif u < 1.1:
            p.aplastar, p.auto_atras = 1, True
        else:
            p.auto_atras = True
            p.auto_x = round(self.dir * (u - 1.1) * 55)
            p.brazos, p.fase_brazos = ('reposo', 'saludo'), int(u * 7)
            p.ojos, p.boca_forma, p.mirar = 'feliz', 'sonrisa', (self.dir, 0)
        return False

    # ================================================================ paseos (cuando no hay nada)
    def _reloj_mate(self, ahora: float):
        """Cada tanto, laburando, se ceba un mate. Si se mueve, el mate y el termo desaparecen."""
        moviendo = self.modo != 'suelo' or self.paseo == 'auto' or (
            self.paseo == 'caminar' and self.paseo_x is not None and self.base == 'libre')
        if moviendo:
            self.mate_ini = None
        if self.base in TRABAJOS:
            self.trabajando_desde = self.trabajando_desde or ahora
        else:
            self.trabajando_desde = None
        sin_mate = self.mate_ini is None or _fase_mate(ahora - self.mate_ini) == 'dejado'
        if (sin_mate and not moviendo and self.base in MATE_TRABAJOS and self.trabajando_desde
                and ahora - self.trabajando_desde > 40 and ahora >= self.prox_mate):
            self.mate_ini = ahora
            self.prox_mate = ahora + 300            # un mate cada 5 minutos de laburo

    def _pose_mate(self, p: Pose, ahora: float, quiero: set, manos: bool):
        fase = _fase_mate(ahora - self.mate_ini)
        if fase == 'dejado' or not manos:
            quiero |= {'termo', 'mate_piso'}
            return
        izq = p.brazos[0]
        if fase == 'cebar':
            quiero |= {'termo_sirve', 'mate_piso'}
            p.brazos, p.mirar = (izq, 'servir'), (1, 1)
        elif fase == 'sorbo':
            # se estira por arriba de la netbook y le da un sorbo, contento
            quiero |= {'termo', 'mate_boca'}
            p.brazos = (izq, 'acercar')
            p.ojos, p.rubor, p.aplastar, p.mirar = 'feliz', True, -1, (0, 0)
        else:                                   # teclea con una pinza y con la otra sostiene el mate
            quiero |= {'termo', 'mate_mano'}
            p.brazos = (izq, 'sostener')

    def _paseos(self, ahora: float):
        if self.paseo == 'guitarra' and not (self.musica and self.guitarra):
            self.paseo, self.paseo_fin = 'quieto', 0.0       # cambió el tema o se cortó: deja la guitarra
        if self.paseo == 'auto' and not (self.musica and self.funk):
            self.paseo, self.paseo_fin, self.vx = 'quieto', 0.0, 0.0   # se bajó del auto
        if self.paseo == 'auto' and self.escuchando:
            return                                               # te escucha sin bajarse
        if self.modo != 'suelo' or self.base != 'libre' or self.mom:
            return
        # estás jugando en el otro monitor: juega con vos, mira con pochoclos o te alienta
        juego = self._hacia_juego() is not None
        if juego and not self.escuchando:
            if (self.paseo == 'caminar' and self.paseo_x is not None) or ahora < self.paseo_fin:
                return
            r = random.random()
            if r < 0.30:
                self.paseo, self.paseo_x, self.paseo_fin = 'joystick', None, ahora + random.uniform(25, 50)
                return
            if r < 0.52:
                self.paseo, self.paseo_x, self.paseo_fin = 'pochoclos', None, ahora + random.uniform(20, 40)
                return
            if r < 0.62:
                self.paseo, self.paseo_x, self.paseo_fin = 'hinchada', None, ahora + random.uniform(5, 9)
                return
            if r < 0.70 and self.musica:
                self.paseo, self.paseo_x, self.paseo_fin = 'quieto', None, 0.0
                self.momento('bailar', 15)
                return
            # si no, algo de lo de siempre (caminar, sentarse, el mate…)
        # con música y sin nada que hacer: baila o se la escucha con los auriculares
        if self.musica and not self.escuchando and not juego:
            if self.paseo in ('auriculares', 'guitarra', 'auto') and ahora < self.paseo_fin:
                return
            if self.funk and random.random() < 0.85:
                # funk / phonk: arriba del Camaro con lentes, de punta a punta y derrapando
                if self.paseo != 'auto':
                    self.vx = 0.0
                self.paseo, self.paseo_x, self.paseo_fin = 'auto', None, ahora + random.uniform(25, 45)
            elif self.guitarra and random.random() < 0.75:
                # folklore: se sienta a tocar la criolla y canta
                self.paseo, self.paseo_x, self.paseo_fin = 'guitarra', None, ahora + random.uniform(25, 45)
            elif not self.guitarra and random.random() < 0.35:
                self.paseo, self.paseo_x, self.paseo_fin = 'auriculares', None, ahora + random.uniform(20, 35)
            else:
                self.paseo, self.paseo_x, self.paseo_fin = 'quieto', None, 0.0
                self.momento('bailar', 30)
            return
        if self.paseo == 'caminar' and self.paseo_x is not None:
            return
        if ahora < self.paseo_fin:
            return
        r = random.random()
        ag = self._pantalla_actual().availableGeometry()
        izq, der = self._limites(ag)
        noche = time.localtime().tm_hour < 6
        # pasatiempos largos: jueguito en el celu o música propia con auriculares
        pasa = random.random()
        if pasa < 0.10:
            self.paseo, self.paseo_fin = 'celular', ahora + random.uniform(15, 40)
            return
        if pasa < 0.14:
            self.paseo, self.paseo_fin = 'auriculares', ahora + random.uniform(15, 30)
            return
        if pasa < 0.20:
            self.paseo, self.paseo_fin = 'mate', ahora + random.uniform(25, 50)
            return
        if pasa < 0.23:
            self.paseo, self.paseo_fin = 'joystick', ahora + random.uniform(15, 35)
            return
        if r < 0.06:
            gestos = ['guino', 'silbar', 'aburrido'] + (['bostezo', 'sueño', 'sueño'] if noche else ['curioso'])
            g = random.choice(gestos)
            if g == 'bostezo':
                self.momento('bostezar', 1.8)
                self.paseo_fin = ahora + 3
            else:
                self.paseo = g
                self.paseo_fin = ahora + {'guino': 0.6, 'silbar': 4.0, 'aburrido': 5.0, 'sueño': 6.0,
                                          'curioso': 2.5}[g]
            return
        if r < 0.34:
            destino = self.px + random.choice((-1, 1)) * random.uniform(60, 320)
            self.paseo, self.paseo_x = 'caminar', max(izq + 10, min(der - 10, destino))
            self.paseo_fin = ahora + 12
        elif r < 0.60:
            self.paseo, self.paseo_fin = 'quieto', ahora + random.uniform(3, 7)
        elif r < 0.74:
            self.paseo, self.paseo_fin = 'mirar', ahora + random.uniform(2, 4)
        elif r < 0.86:
            self.paseo, self.paseo_fin = 'chasquear', ahora + 1.3
        elif r < 0.95:
            self.paseo, self.paseo_fin = 'sentado', ahora + random.uniform(6, 14)
        else:
            self.paseo, self.paseo_fin = 'saltito', ahora + 0.55

    # ================================================================ pose
    def _pose(self, ahora: float) -> Pose:
        t = ahora - self.t0
        p = Pose(t=t, dir=self.dir)
        quiero: set[str] = set()
        mirar_libre = True

        bajando = (self.bajando_auto is not None and ahora - self.bajando_auto < 1.8 and self.modo == 'suelo')
        if not bajando and self.bajando_auto is not None:
            self.bajando_auto = None
            self.alfas.pop('auto', None)        # el auto ya se fue: que no reaparezca desvaneciéndose

        caminando = (self.modo in ('entrando', 'saliendo')
                     or (self.modo == 'suelo' and self.paseo == 'caminar' and self.paseo_x is not None
                         and self.base == 'libre'))

        if self.modo == 'agarrado':
            sacudido = len([s for s in self.sacudidas if ahora - s < 1.2]) >= 4
            p.patas, p.fase = 'patalear', int(t * 10)
            p.brazos, p.fase_brazos = ('colgando', 'colgando'), int(t * 8)
            p.ojos = 'mareado' if sacudido else 'grandes'
            mirar_libre = False
        elif self.modo == 'cayendo':
            p.patas = 'abiertas'
            p.brazos, p.fase_brazos = ('festejo', 'festejo'), int(t * 10)
            p.ojos = 'grandes'
            p.aplastar = -1 if self.vy > 300 else 0
            mirar_libre = False
        elif bajando:
            mirar_libre = self._pose_bajarse(p, ahora - self.bajando_auto, quiero)
        elif self.mom and not (self.escuchando and self.mom == 'bailar'):
            mirar_libre = self._pose_momento(p, t, ahora, quiero)
        elif self.escuchando and not caminando:
            # le estás dictando: pinza en la oreja, cejas arriba y ondas de sonido
            p.brazos, p.fase_brazos = ('reposo', 'oreja'), int(t * 2)
            p.cejas, p.brillo = 'arriba', True
            p.cuerpo_y = 1 if int(t * 1.6) % 4 == 0 else 0      # asiente despacito
            quiero.add('ondas')
            if self.base in ('teclear', 'terminal', 'pensar'):
                quiero.add('netbook')
        else:
            mirar_libre = self._pose_base(p, t, ahora, quiero, caminando)

        if caminando and self.modo != 'agarrado' and p.patas == 'quietas':
            p.patas, p.fase = 'caminar', int(t * 9)
            p.mirar = (self.dir, 0)
            mirar_libre = False

        if self.ayudantes > 0:
            quiero.add('ayudante')
        if self.musica and self.guitarra:
            quiero.add('gaucho')
        if self.paseo == 'auto' and self.modo == 'suelo' and self.base == 'libre':
            # sentado adentro del Camaro descapotable, con lentes
            quiero |= {'auto', 'lentes'}
            p.y, p.patas, p.dir = p.y - 5, 'sentado', self.dir
            p.cuerpo_y = max(p.cuerpo_y, 3)
        if self.mate_ini is not None and self.modo == 'suelo':
            self._pose_mate(p, ahora, quiero, manos=(not self.mom and not self.escuchando
                                                    and self.base in MATE_TRABAJOS))

        # con música de fondo, labura con ritmo: cabecea al compás y le salen notitas
        if (self.musica and not self.mom and not self.escuchando and not bajando and self.modo == 'suelo'
                and self.base in TRABAJOS - {'llamar', 'preguntar'}):
            if p.cuerpo_y == 0:
                p.cuerpo_y = int(t * 4) % 2
            if ahora >= self.prox_nota:
                self.prox_nota = ahora + random.uniform(0.8, 1.3)
                cx, cy = self._cabeza()
                self._particula(S.NOTA, cx + random.uniform(-40, 40), cy + 10, random.uniform(-14, 14), -30,
                                0, 2.0, vaiven=True, escala=0.6)

        # ojos que siguen al mouse
        if mirar_libre:
            p.mirar = self._hacia_el_mouse()
            if self.hover_desde and ahora - self.hover_desde > 1.2 and p.ojos == 'normal':
                p.brillo = True
                p.rubor = True
        # parpadeo
        if ahora >= self.prox_parpadeo:
            self.parpadeo_hasta = ahora + 0.12
            self.prox_parpadeo = ahora + (0.25 if random.random() < 0.15 else random.uniform(2.5, 6.0))
        if p.ojos == 'normal' and ahora < self.parpadeo_hasta:
            p.ojos = 'cerrados'
        # boca con la voz
        if p.boca < 3 and not self.cfg['silencio']:
            n = self.voz.nivel()
            if n > 0.55:
                p.boca = 2
            elif n > 0.2:
                p.boca = 1
        # fundido de accesorios
        for k in quiero | set(self.alfas):
            objetivo = 1.0 if k in quiero else 0.0
            a = self.alfas.get(k, 0.0)
            a = min(objetivo, a + 0.2) if objetivo > a else max(objetivo, a - 0.2)
            if a <= 0 and objetivo == 0:
                self.alfas.pop(k, None)
            else:
                self.alfas[k] = a
        p.accesorios = dict(self.alfas)
        return p

    def _pose_momento(self, p: Pose, t: float, ahora: float, quiero: set) -> bool:
        m = self.mom
        u = (ahora - self.mom_ini)
        if m in ('saludar', 'voz'):
            p.brazos, p.fase_brazos = ('reposo', 'saludo'), int(t * 6)
            p.ojos, p.brillo, p.boca_forma = 'feliz', True, 'sonrisa'
        elif m == 'despedida':
            p.brazos, p.fase_brazos = ('reposo', 'saludo'), int(t * 5)
            p.ojos, p.cejas, p.boca_forma = 'llorar', 'preocupado', 'triste'
            return False
        elif m == 'sorpresa':
            p.ojos, p.cejas, p.boca_forma = 'grandes', 'arriba', 'o'
            p.y = -2 if u < 0.25 else 0
            quiero.add('exclamacion')
        elif m == 'error':
            p.ojos, p.cejas, p.boca_forma = 'sorpresa', 'preocupado', 'o'
            p.brazos, p.fase_brazos = ('reposo', 'rascar'), int(t * 6)
            quiero.add('sudor')
            return False
        elif m == 'frustrado':
            p.cejas, p.boca_forma = 'enojado', 'ondulada'
            p.brazos, p.fase_brazos = ('chasquear', 'chasquear'), int(t * 9)
            p.y = -1 if int(u * 6) % 2 else 0                  # zapateo
            return False
        elif m == 'orgulloso':
            salto = abs(math.sin(u * 6))
            p.y = -round(salto * 5)
            p.aplastar = -1 if salto > 0.7 else (1 if salto < 0.12 else 0)
            p.brazos, p.fase_brazos = ('festejo', 'festejo'), int(t * 7)
            p.ojos, p.cejas, p.boca_forma = 'estrella', 'arriba', 'sonrisa'
            p.patas = 'abiertas' if p.y < -1 else 'quietas'
            return False
        elif m == 'bailar':
            compas = int(u * 4)
            p.y = -1 if compas % 2 else 0
            p.cuerpo_y = 0 if compas % 2 else 1
            p.brazos = ('baile', 'reposo') if (compas // 2) % 2 else ('reposo', 'baile')
            p.fase_brazos = 1
            p.ojos, p.boca_forma = 'feliz', 'sonrisa'
            p.patas, p.fase, p.dir = 'caminar', compas, 1 if (compas // 4) % 2 else -1
            if ahora >= self.prox_nota:
                self.prox_nota = ahora + 0.7
                cx, cy = self._cabeza()
                self._particula(S.NOTA, cx + random.choice((-44, 44)), cy + 16, random.uniform(-12, 12), -32,
                                0, 2.2, vaiven=True, escala=0.7)
            return False
        elif m == 'festejar':
            salto = abs(math.sin(u * 7.5))
            p.y = -round(salto * 4)
            p.aplastar = -1 if salto > 0.7 else (1 if salto < 0.12 else 0)
            p.brazos, p.fase_brazos = ('festejo', 'festejo'), int(t * 6)
            p.ojos, p.boca = 'feliz', 2
            p.patas = 'abiertas' if p.y < -1 else 'quietas'
            return False
        elif m == 'resoplar':
            # «uff…»: se desinfla, ojos cansados y gotita
            p.ojos, p.cejas, p.boca_forma = 'medio', 'preocupado', 'ondulada'
            p.cuerpo_y = 1 if u < 1.4 else 0
            p.brazos = ('colgando', 'colgando')
            quiero.add('sudor')
            return False
        elif m == 'casi':
            # ¡ya casi!: ojitos de estrella y puñito arriba
            p.ojos, p.brillo, p.boca_forma = 'estrella', True, 'sonrisa'
            p.brazos, p.fase_brazos = ('reposo', 'festejo'), int(t * 6)
            p.y = -1 if int(u * 5) % 2 else 0
            return False
        elif m == 'fiesta':
            # terminó un laburo largo: 10 segundos de saltos y lluvia de confeti
            salto = abs(math.sin(u * (6 if int(u / 2.5) % 2 else 7.5)))
            p.y = -round(salto * 5)
            p.aplastar = -1 if salto > 0.7 else (1 if salto < 0.12 else 0)
            p.brazos, p.fase_brazos = ('festejo', 'festejo'), int(t * 7)
            p.ojos = 'estrella' if int(u / 2.5) % 2 else 'feliz'
            p.cejas, p.boca_forma = 'arriba', 'sonrisa'
            p.boca = 2 if not p.ojos == 'estrella' else 0
            p.patas = 'abiertas' if p.y < -1 else 'quietas'
            if u < 9 and ahora >= self.prox_confeti:
                self.prox_confeti = ahora + 0.35
                cx, cy = self._cabeza()
                for _ in range(9):
                    self._particula(random.choice(COLORES_CONFETI), cx + random.uniform(-60, 60), cy,
                                    random.uniform(-200, 200), random.uniform(-400, -200), 700, 2.2, confeti=True)
                if random.random() < 0.4:
                    self._particula(S.ESTRELLA, cx + random.uniform(-50, 50), cy + 5, random.uniform(-20, 20),
                                    -40, 0, 1.8, escala=0.8)
            return False
        elif m == 'mimo':
            p.ojos = 'corazon' if u > 0.5 else 'feliz'
            p.rubor, p.brillo, p.boca_forma = True, True, 'sonrisa'
            p.cuerpo_y = int(t * 5) % 2
            return False
        elif m == 'silencio':
            p.brazos = ('boca', 'reposo')
            p.ojos = 'normal'
        elif m == 'bostezar':
            p.brazos = ('estirar', 'estirar')
            p.ojos, p.boca = 'cerrados', 3
            return False
        elif m == 'despertar':
            p.ojos = 'grandes'
            p.y = -2 if u < 0.2 else 0
        elif m == 'aterrizar':
            p.aplastar = 1
            p.ojos = 'cerrados' if self.pendiente_mareo else 'normal'
            return False
        elif m == 'mareado':
            p.ojos = 'mareado'
            p.cuerpo_y = round(math.sin(u * 6))
            return False
        return True

    def _pose_base(self, p: Pose, t: float, ahora: float, quiero: set, caminando: bool) -> bool:
        b = self.base
        quiero |= ACCESORIOS.get(b, set())
        if b == 'teclear':
            p.brazos, p.fase_brazos = ('teclado', 'teclado'), int(t * 7)
            p.mirar = (0, 1)
            return False
        if b == 'terminal':
            p.brazos, p.fase_brazos = ('teclado', 'teclado'), int(t * 11)
            p.mirar = (1, 0) if int(t / 1.5) % 3 else (0, 1)
            return False
        if b == 'leer':
            p.brazos = ('sostener', 'sostener')
            p.mirar = (-1 if int(t / 1.2) % 2 else 1, 1)
            return False
        if b == 'buscar':
            p.brazos = ('reposo', 'nada')
            p.mirar = (1 if math.sin(t * 2.2) > 0.3 else (-1 if math.sin(t * 2.2) < -0.3 else 0), 0)
            return False
        if b == 'web':
            p.brazos = ('reposo', 'arriba')
            p.mirar = (1, -1)
            return False
        if b == 'pensar':
            # con la netbook: mira para arriba pensando y cada tanto teclea algo
            if int(t / 2.2) % 3 == 2:
                p.brazos, p.fase_brazos = ('teclado', 'teclado'), int(t * 6)
                p.mirar = (0, 1)
            else:
                p.mirar = (1, -1) if int(t / 2.2) % 3 else (-1, -1)
                p.cejas = 'arriba' if int(t / 4.4) % 2 else ''
            return False
        if b == 'llamar':
            p.brazos, p.fase_brazos = ('saludo', 'saludo'), int(t * 7)
            p.ojos, p.cejas = 'grandes', 'preocupado'
            p.y = -1 if int(t * 4) % 2 else 0
            return False
        if b == 'preguntar':
            p.brazos = ('reposo', 'arriba')
            p.ojos, p.cejas, p.boca_forma = 'grandes', 'arriba', 'o'
            return True
        if b == 'dormir':
            p.patas = 'sentado'
            p.cuerpo_y = 3 if int(t / 1.6) % 2 else 2
            p.ojos = 'cerrados'
            if ahora >= self.prox_z:
                self.prox_z = ahora + 1.5
                cx, cy = self._cabeza()
                grande = random.random() < 0.5
                self._particula(S.Z_GRANDE if grande else S.Z_CHICA, cx + 24, cy + 20, 14, -20, 0, 3.0,
                                vaiven=True, escala=0.8 if grande else 0.7)
            return False
        # libre
        if caminando:
            return False
        if self.paseo == 'sentado':
            p.patas, p.cuerpo_y = 'sentado', 3
        elif self.paseo == 'chasquear':
            p.brazos, p.fase_brazos = ('chasquear', 'chasquear'), int(t * 7)
        elif self.paseo == 'mirar':
            p.mirar = (-1 if int(t / 0.9) % 2 else 1, 0)
            return False
        elif self.paseo == 'saltito':
            u = self.paseo_fin - ahora
            p.y = -2 if 0.15 < u < 0.4 else 0
            p.aplastar = 1 if u <= 0.15 else 0
        elif self.paseo == 'guino':
            p.ojos, p.boca_forma = 'guino', 'sonrisa'
        elif self.paseo == 'silbar':
            p.boca_forma, p.mirar = 'o', (1, -1)
            if ahora >= self.prox_nota:
                self.prox_nota = ahora + 0.9
                cx, cy = self._cabeza()
                self._particula(S.NOTA, cx + 30, cy + 24, 16, -26, 0, 2.0, vaiven=True, escala=0.6)
            return False
        elif self.paseo == 'celular':
            # sentado jugando: concentrado, y cada tanto gana (festeja) o pierde (se enoja)
            quiero.add('celular')
            p.patas, p.cuerpo_y = 'sentado', 2
            p.brazos, p.mirar = ('sostener', 'sostener'), (0, 1)
            suerte = random.Random(int(t / 4)).random()
            if int(t) % 4 == 3 and suerte < 0.3:
                p.ojos, p.boca_forma = 'feliz', 'sonrisa'
                p.y = -1 if int(t * 6) % 2 else 0
            elif int(t) % 4 == 3 and suerte < 0.55:
                p.cejas, p.boca_forma = 'enojado', 'ondulada'
            else:
                p.boca_forma = 'o' if int(t / 2.5) % 3 == 0 else ''
            return False
        elif self.paseo == 'auriculares':
            # con los auriculares puestos: ojos cerrados, cabeceando al ritmo
            quiero.add('auriculares')
            p.ojos, p.boca_forma = ('cerrados' if int(t / 3) % 3 else 'feliz'), 'sonrisa'
            p.cuerpo_y = int(t * 4) % 2
            p.brazos, p.fase_brazos = ('reposo', 'chasquear'), int(t * 4)
            if ahora >= self.prox_nota:
                self.prox_nota = ahora + random.uniform(0.9, 1.4)
                cx, cy = self._cabeza()
                self._particula(S.NOTA, cx + random.choice((-40, 40)), cy + 14, random.uniform(-10, 10), -26,
                                0, 2.0, vaiven=True, escala=0.6)
            return False
        elif self.paseo == 'joystick':
            # juega con su joystick; si estás jugando, mira para tu monitor como si jugaran juntos
            quiero.add('joystick')
            p.patas, p.cuerpo_y = 'sentado', 2
            p.brazos = ('sostener', 'sostener')
            p.mirar = self._hacia_juego() or (0, 1)
            suerte = random.Random(int(t / 5)).random()
            if int(t) % 5 == 4 and suerte < 0.35:
                p.ojos, p.boca_forma = 'feliz', 'sonrisa'
                p.y = -1 if int(t * 6) % 2 else 0
            elif int(t) % 5 == 4 and suerte < 0.6:
                p.cejas, p.boca_forma = 'enojado', 'ondulada'
            else:
                p.cejas = 'arriba' if int(t / 3) % 2 else ''
                p.boca_forma = 'o' if int(t / 1.7) % 3 == 0 else ''
            return False
        elif self.paseo == 'auto':
            if ahora < self.derrape_hasta:
                p.brazos, p.boca_forma = ('arriba', 'arriba'), 'o'        # ¡derrape!
                p.y = -1 if int(t * 12) % 2 else 0
            else:
                p.brazos, p.fase_brazos = ('reposo', 'festejo'), int(t * 4)
                p.boca_forma = 'sonrisa'
                p.cuerpo_y = 3 + int(t * 4) % 2                       # cabecea al ritmo
            p.mirar = (self.dir, 0)
            return False
        elif self.paseo == 'guitarra':
            # sentado con la criolla: rasguea con una pinza y canta con los ojos cerrados
            quiero.add('guitarra')
            p.patas, p.cuerpo_y = 'sentado', 2
            p.brazos, p.fase_brazos = ('sostener', 'teclado'), int(t * 8)
            p.ojos = 'cerrados' if int(t / 3) % 3 else 'feliz'
            p.boca_forma = 'o' if int(t * 2) % 3 == 0 else 'sonrisa'
            p.cuerpo_y = 2 + (int(t * 2) % 2)
            if ahora >= self.prox_nota:
                self.prox_nota = ahora + random.uniform(0.7, 1.1)
                cx, cy = self._cabeza()
                self._particula(S.NOTA, cx + random.uniform(10, 50), cy + 20, random.uniform(-8, 14), -30,
                                0, 2.0, vaiven=True, escala=0.6)
            return False
        elif self.paseo == 'pochoclos':
            # te mira jugar comiendo pochoclos; cada tanto se sorprende
            quiero.add('pochoclos')
            p.patas, p.cuerpo_y = 'sentado', 2
            come = int(t / 1.6) % 3 == 0
            p.brazos = ('sostener', 'acercar' if come else 'reposo')
            p.mirar = self._hacia_juego() or (1, 0)
            if int(t / 6) % 4 == 3:
                p.ojos, p.cejas, p.boca_forma = 'grandes', 'arriba', 'o'
            elif not come:
                p.boca_forma = 'o' if int(t * 4) % 2 else ''        # mastica
            return False
        elif self.paseo == 'hinchada':
            # te alienta con la bandera
            quiero.add('bandera')
            p.brazos, p.fase_brazos = ('festejo', 'arriba'), int(t * 6)
            p.ojos, p.boca_forma, p.brillo = 'feliz', 'sonrisa', True
            p.y = -1 if int(t * 5) % 2 else 0
            p.patas = 'abiertas' if p.y else 'quietas'
            return False
        elif self.paseo == 'mate':
            # parado, con el mate en la pinza; cada 7 s le da un sorbo
            if S.mate_sorbo(t):
                quiero.add('mate_boca')
                p.brazos = ('reposo', 'acercar')
                p.ojos, p.rubor = 'feliz', True
            else:
                quiero.add('mate')
                p.brazos = ('reposo', 'sostener')
                p.boca_forma, p.mirar = 'sonrisa', (1 if int(t / 4) % 2 else -1, 0)
            return False
        elif self.paseo == 'aburrido':
            p.brazos, p.mirar, p.ojos = ('mirar_garra', 'reposo'), (-1, -1), 'medio'
            return False
        elif self.paseo == 'sueño':
            p.ojos, p.boca_forma = 'medio', ''
            p.cuerpo_y = 1
        elif self.paseo == 'curioso':
            p.cejas, p.brillo, p.boca_forma = 'arriba', True, 'o'
        # de madrugada anda con cara de sueño cada tanto
        if time.localtime().tm_hour < 6 and p.ojos == 'normal' and int(t / 7) % 4 == 3:
            p.ojos = 'medio'
        # si le pasás el mouse por encima, se pone curioso y contento
        if self.hover_desde and ahora - self.hover_desde > 0.4:
            p.cejas = p.cejas or 'arriba'
            p.boca_forma = p.boca_forma or 'sonrisa'
        return True

    def _hacia_juego(self):
        """(lado, 0) hacia el monitor donde estás jugando, o None si no hay juego en otro monitor."""
        if not self.tapados:
            return None
        mio = self._pantalla_actual()
        if mio.name() in self.tapados:
            return None
        for s in QGuiApplication.screens():
            if s.name() in self.tapados:
                return (1 if s.geometry().center().x() > mio.geometry().center().x() else -1, 0)
        return None

    def _hacia_el_mouse(self):
        c = QCursor.pos()
        ox = self.x() + S.CABEZA[0] * self.E
        oy = self.y() + (S.OY + 20) * self.E
        dx, dy = c.x() - ox, c.y() - oy
        if abs(dx) > 900 or abs(dy) > 700:
            return (0, 0)
        return (0 if abs(dx) < 40 else (1 if dx > 0 else -1), -1 if dy < -60 else (1 if dy > 50 else 0))

    # ================================================================ partículas
    def _particula(self, spr, x, y, vx, vy, g, vida, retraso=0.0, confeti=False, orbita=None, vaiven=False,
                   escala=1.0):
        self.particulas.append({'spr': spr, 'x': x, 'y': y, 'vx': vx, 'vy': vy, 'g': g, 'vida': vida,
                                'edad': -retraso, 'confeti': confeti, 'orbita': orbita, 'vaiven': vaiven,
                                'escala': escala, 'x0': x})

    def _mover_particulas(self, dt: float, ahora: float):
        vivas = []
        for q in self.particulas:
            q['edad'] += dt
            if q['edad'] < 0:
                vivas.append(q)
                continue
            if q['edad'] >= q['vida']:
                continue
            if q['orbita'] is not None:
                cx, cy = self._cabeza()
                ang = q['orbita'] + q['edad'] * 5
                q['x'], q['y'] = cx + math.cos(ang) * 44, cy + 6 + math.sin(ang) * 10
            else:
                q['vy'] += q['g'] * dt
                q['x'] += q['vx'] * dt
                q['y'] += q['vy'] * dt
                if q['vaiven']:
                    q['x'] = q['x0'] + q['edad'] * q['vx'] + math.sin(q['edad'] * 3) * 5
            vivas.append(q)
        self.particulas = vivas

    # ================================================================ pintar
    def paintEvent(self, _):
        if self.imagen is None:
            return
        p = QPainter(self)
        E = self.E
        if self.modo in ('suelo', 'entrando', 'saliendo'):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(0, 0, 0, 45))
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.drawEllipse(QPointF((S.OX + 17) * E, S.PIES * E), 15 * E, 1.3 * E)
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        p.drawImage(QRect(0, 0, S.W * E, S.H * E), self.imagen)
        for q in self.particulas:
            if q['edad'] < 0:
                continue
            u = q['edad'] / q['vida']
            alfa = min(1.0, u / 0.12) if u < 0.12 else (1.0 if u < 0.6 else max(0.0, (1 - u) / 0.4))
            p.setOpacity(alfa)
            if q['confeti']:
                col = QColor(S.PALETA[q['spr']])
                p.fillRect(round(q['x']), round(q['y']), E, E * (2 if int(q['edad'] * 8) % 2 else 1), col)
            else:
                img = S.sprite(q['spr'])
                e = max(1, round(E * q['escala']))
                p.drawImage(QRect(round(q['x'] - img.width() * e / 2), round(q['y'] - img.height() * e / 2),
                                  img.width() * e, img.height() * e), img)
        p.end()

    # ================================================================ mouse
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.presion = e.globalPosition()
            self.arrastrando = False
        elif e.button() == Qt.MouseButton.RightButton:
            self.menu_pedido.emit(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self.presion is None:
            return
        g = e.globalPosition()
        if not self.arrastrando:
            if (g - self.presion).manhattanLength() < 5:
                return
            self.arrastrando = True
            self._clic.stop()
            self.agarre = self.presion - QPointF(self.px, self.py)
            self.modo = 'agarrado'
            self.mom = None
            self.paseo, self.paseo_x = 'quieto', None
            self.historial.clear()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        ahora = time.monotonic()
        if self.historial:
            t_ant, p_ant = self.historial[-1]
            if ahora > t_ant:
                vx = (g.x() - p_ant.x()) / (ahora - t_ant)
                if abs(vx) > 700 and getattr(self, '_signo', 0) and (vx > 0) != (self._signo > 0):
                    self.sacudidas.append(ahora)
                if abs(vx) > 700:
                    self._signo = vx
        self.historial.append((ahora, g))
        self.px, self.py = g.x() - self.agarre.x(), g.y() - self.agarre.y()
        self.move(round(self.px), round(self.py))

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton or self.presion is None:
            return
        self.presion = None
        if self.arrastrando:
            self.arrastrando = False
            self.unsetCursor()
            ahora = time.monotonic()
            recientes = [(t, p) for (t, p) in self.historial if ahora - t < 0.12]
            if len(recientes) >= 2 and recientes[-1][0] > recientes[0][0]:
                (t0, p0), (t1, p1) = recientes[0], recientes[-1]
                self.vx = max(-2200.0, min(2200.0, (p1.x() - p0.x()) / (t1 - t0)))
                self.vy = max(-2200.0, min(2200.0, (p1.y() - p0.y()) / (t1 - t0)))
            else:
                self.vx = self.vy = 0.0
            self.pendiente_mareo = len([s for s in self.sacudidas if ahora - s < 1.5]) >= 4
            self.sacudidas.clear()
            self.modo = 'cayendo'
        else:
            self._clic.start(QApplication.doubleClickInterval())

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._clic.stop()
            self.presion = None
            self.momento('mimo', 1.7)
            self.mimado.emit()

    def enterEvent(self, _):
        self.hover_desde = time.monotonic()

    def leaveEvent(self, _):
        self.hover_desde = None


def _distancia(r: QRect, p: QPoint) -> float:
    dx = max(r.left() - p.x(), 0, p.x() - r.right())
    dy = max(r.top() - p.y(), 0, p.y() - r.bottom())
    return math.hypot(dx, dy)
