# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Los cangrejitos ayudantes: uno por cada agente que Claude manda a laburar.

El primero se sube a la cabeza del cangrejito, con casquito de obra y una tablita. Los demás caen desde arriba, andan de
costado por los lados (se paran a anotar en la tablita, pegan un saltito, cruzan de un lado al otro), lo
saludan de vez en cuando —y él los mira— y rebotan mientras él habla. Cuando un agente termina, su
cangrejito deja la tablita, se pone un tilde verde, corre a juntarse al lado del cangrejito y festeja un rato antes de irse.

Es una ventanita transparente que no recibe clics y que sigue al cangrejito; se agranda sola según
cuántos ayudantes haya.
"""
from __future__ import annotations

import math
import random
import time

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QWidget

import sprites as S
from globo import banderas_flotante

ANCHO, ALTO = 11, 5          # un mini-cangrejo, en unidades (sin el celular ni las pinzas levantadas)
BORDE_IZQ, BORDE_DER = -7, 36  # x del mini pegadito a las pinzas del cangrejito (izquierda y derecha)
FILA = 7                     # separación vertical entre «filas» de profundidad
FILAS = 3                    # filas de profundidad que usan a cada lado
SE_QUEDAN = 20.0             # segundos que se queda al lado, ya terminado
SE_PIERDE = 900.0            # un agente sin novedades en 15 minutos se da por perdido
GRAVEDAD = 260.0
BAILAN = {'bailar', 'fiesta', 'festejar', 'orgulloso'}   # momentos del grande en los que bailan con él
CABEZA_Y = S.OY + 10         # y del mini que va parado arriba de la cabeza


def margen(n: int) -> int:
    """Unidades extra a cada lado del lienzo del cangrejito para tantos agentes. Con uno solo también hace
    falta: va arriba de la cabeza, pero al terminar baja a su lugar al costado (si no, se ve recortado)."""
    if n <= 0:
        return 0
    por_lado = -(-max(n - 1, 1) // 2)                  # cuántos le tocan a cada lado
    return 9 + ANCHO * -(-por_lado // FILAS)     # una columna de ANCHO por cada FILAS minis


def zona(lado: int, marg: int) -> tuple[float, float]:
    """Rango de x del mini-cangrejo (esquina de la izquierda) a ese lado: -1 izquierda, +1 derecha."""
    if lado < 0:
        return float(-marg + 1), float(BORDE_IZQ)
    return float(BORDE_DER), float(S.W + marg - ANCHO - 1)


def _suelo(fila: int) -> float:
    return float(S.PIES - ALTO - FILA * fila)


def _mini(p: QPainter, x: float, y: float, a: dict, t: float, alfa: float):
    """Dibuja un mini-cangrejo. «a» trae su estado: look (-1, 0, 1), camina, celu, saluda, feliz, parpadea."""
    P = S.PALETA
    x, y = round(x), round(y)
    o, osc, h, k = P['o'], P['O'], P['h'], P['k']
    p.setOpacity(alfa)
    look, i = a.get('look', 0), a['n']
    # cuerpo (7×4) con brillo arriba y la panza más oscura
    p.fillRect(x + 2, y, 7, 4, o)
    p.fillRect(x + 3, y, 5, 1, h)
    p.fillRect(x + 2, y + 3, 7, 1, osc)
    # patitas: dos pasos alternados al caminar, abiertas cuando está quieto
    if a.get('camina'):
        paso = int(t * 11 + i) % 2
        for lx in ((2, 4, 6, 8) if paso else (3, 5, 7, 9)):
            p.fillRect(x + lx, y + 4, 1, 1, osc)
    else:
        for lx in (2, 4, 6, 8):
            p.fillRect(x + lx, y + 4, 1, 1, osc)
    # ojos: miran hacia donde van o hacia el celular; parpadean
    ex = (3, 7)
    if look:
        ex = (3 + (1 if look > 0 else 0), 7 - (1 if look < 0 else 0))
    if a.get('parpadea'):
        for e in ex:
            p.fillRect(x + e, y + 2, 1, 1, osc)
    elif a.get('feliz'):
        for e in ex:                                               # ojos contentos (^ ^)
            p.fillRect(x + e, y + 1, 1, 1, k)
            p.fillRect(x + e - 1, y + 2, 1, 1, k)
            p.fillRect(x + e + 1, y + 2, 1, 1, k)
        p.fillRect(x + 3, y + 3, 1, 1, P['R'])                     # cachetes
        p.fillRect(x + 7, y + 3, 1, 1, P['R'])
    else:
        for e in ex:
            p.fillRect(x + e, y + 1, 1, 2, k)
    # pinzas
    izq_y = y + 1 + (1 if a.get('tapea') and int(t * 6 + i) % 2 else 0)
    if a.get('choca'):                                              # choca la pinza con el de al lado
        lado = a['choca']
        arriba = int(t * 8 + i) % 2
        if lado < 0:
            p.fillRect(x - 1, y - 2 + arriba, 2, 2, o)
            p.fillRect(x, y + arriba, 1, 2 - arriba, o)
            p.fillRect(x + 9, y + 1, 2, 2, o)
        else:
            p.fillRect(x, y + 1, 2, 2, o)
            p.fillRect(x + 10, y - 2 + arriba, 2, 2, o)
            p.fillRect(x + 10, y + arriba, 1, 2 - arriba, o)
    elif a.get('saluda') or a.get('feliz'):
        arriba = int(t * 5 + i) % 2
        p.fillRect(x, y - 1 - arriba, 2, 2, o)                      # pinza izquierda saludando
        p.fillRect(x + 1, y + 1 - arriba, 1, 2 + arriba, o)
        if a.get('feliz'):
            p.fillRect(x + 9, y - 2 + arriba, 2, 2, o)              # y la derecha, al revés
            p.fillRect(x + 9, y + arriba, 1, 2 - arriba, o)
        else:
            p.fillRect(x + 9, y + 1, 2, 2, o)
    elif a.get('celu'):
        p.fillRect(x, izq_y, 2, 2, o)                               # la izquierda, apoyada
        # laburando: sostiene una tablita con papel y va anotando renglones (se ve que trabaja)
        p.fillRect(x + 9, y + 1, 2, 2, o)                           # la pinza
        p.fillRect(x + 8, y - 5, 5, 6, P['m'])                      # la tablita (5×6)
        p.fillRect(x + 9, y - 4, 3, 4, P['p'])                      # el papel
        p.fillRect(x + 9, y - 6, 3, 1, P['G'])                      # el clip
        llenos = 1 + int(t * 1.5 + i) % 2                           # renglones que se van llenando
        for j in range(llenos):
            p.fillRect(x + 9, y - 3 + 2 * j, 3 if j == 0 else 2, 1, P['G'])
    else:
        p.fillRect(x, y + 1, 2, 2, o)
        p.fillRect(x + 9, y + 1, 2, 2, o)
    # casquito amarillo de obra: lo que lo hace «ayudante» (trabaja para el cangrejo)
    p.fillRect(x + 3, y - 2, 5, 1, P['y'])
    p.fillRect(x + 2, y - 1, 7, 1, P['y'])
    p.fillRect(x + 5, y - 2, 1, 1, P['w'])
    if a.get('feliz'):                                              # misión cumplida: un tilde verde
        b = int(t * 3 + i) % 2
        p.fillRect(x + 3, y - 5 - b, 1, 1, P['n'])
        p.fillRect(x + 4, y - 4 - b, 1, 1, P['n'])
        p.fillRect(x + 5, y - 5 - b, 1, 1, P['n'])
        p.fillRect(x + 6, y - 6 - b, 1, 1, P['n'])
        p.fillRect(x + 7, y - 7 - b, 1, 1, P['n'])
    p.setOpacity(1.0)


class Ayudantes(QWidget):
    def __init__(self, cfg, mascota):
        super().__init__(None, banderas_flotante(Qt.WindowType.WindowDoesNotAcceptFocus,
                                                 Qt.WindowType.WindowTransparentForInput))
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.cfg = cfg
        self.m = mascota
        self.E = int(cfg['escala'])
        self.agentes: dict[str, dict] = {}
        self.marg = 0
        self.cuenta = 0
        self.t0 = time.monotonic()
        self._ult = self.t0
        self.prox_saludo = self.t0 + 8
        self.pares: list[dict] = []           # escenas de a dos en curso (choque, torre, persecución)
        self.efectos: list[tuple] = []        # chispitas: (x, y, inicio)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._img = None
        self.setFixedSize(S.W * self.E, S.H * self.E)

    # ------------------------------------------------------------ API
    def cuantos(self) -> int:
        """Cuántos agentes están trabajando ahora (los que ya terminaron no cuentan)."""
        return sum(1 for a in self.agentes.values() if a['estado'] == 'buscando')

    def hay(self) -> bool:
        return bool(self.agentes)

    def nuevo(self, aid: str, sid: str = ''):
        if aid in self.agentes:
            return
        ahora = time.monotonic()
        self.cuenta += 1
        cabeza = not any(a['cabeza'] for a in self.agentes.values())     # el primero se sube a la cabeza
        a = {'sid': sid, 'estado': 'buscando', 'alfa': 0.0, 'vivo': True, 'desde': ahora, 'fin': 0.0,
             'n': self.cuenta, 'cabeza': cabeza, 'modo': 'cae', 'x': 0.0, 'y': -14.0, 'vy': 0.0,
             'tx': 0.0, 'ty': 0.0, 'fila': 0, 'vel': random.uniform(9, 14), 'hasta': 0.0,
             'parp': ahora + random.uniform(1, 4), 'parp_fin': 0.0, 'rebotes': 0, 'lado': 1}
        self.agentes[aid] = a
        self._marg()
        izq = sum(1 for v in self.agentes.values() if v is not a and not v['cabeza'] and v['lado'] < 0)
        der = sum(1 for v in self.agentes.values() if v is not a and not v['cabeza'] and v['lado'] > 0)
        lado = -1 if izq < der else (1 if der < izq else random.choice((-1, 1)))
        if cabeza:
            a['x'] = S.OX + 17 - ANCHO / 2 + self.marg
            a['ty'] = float(CABEZA_Y)
        else:
            a['lado'] = lado
            lo, hi = zona(lado, self.marg)
            otros = [v for v in self.agentes.values() if v is not a and not v['cabeza'] and v['lado'] == lado]
            for _ in range(14):
                x = random.uniform(lo, hi) + self.marg
                if all(abs(x - v['x']) >= ANCHO - 1 and abs(x - v['tx']) >= ANCHO - 1 for v in otros):
                    break
            a['x'] = a['tx'] = x
            a['ty'] = _suelo(0)
        self.sincronizar()

    def listo(self, aid: str, sid: str = ''):
        """Terminó: deja la tablita, se pone un tilde verde, corre al lado del cangrejito y festeja. Sin id, el más viejo de esa sesión."""
        a = self.agentes.get(aid)
        if a is None and not aid:
            viejos = [(v['desde'], k) for k, v in self.agentes.items()
                      if v['estado'] == 'buscando' and (not sid or v['sid'] == sid)]
            a = self.agentes.get(min(viejos)[1]) if viejos else None
        if a is not None and a['estado'] == 'buscando':
            self._terminar(a)

    def terminar_sesion(self, sid: str):
        """Cerró la respuesta (o la sesión): los que seguían buscando se dan por terminados."""
        for a in self.agentes.values():
            if a['sid'] == sid and a['estado'] == 'buscando':
                self._terminar(a)

    def limpiar(self, sid: str = ''):
        for a in self.agentes.values():
            if not sid or a['sid'] == sid:
                a['vivo'] = False

    def sincronizar(self):
        """Lo llama el cangrejito cuando se mueve, aparece o se esconde."""
        if self.agentes and self.m.isVisible():
            self._colocar()
            if not self.isVisible():
                self.show()
                self.m.subir()
            if not self._timer.isActive():
                self._ult = time.monotonic()
                self._timer.start(50)
        elif self.isVisible():
            self.hide()
            self._timer.stop()

    # ------------------------------------------------------------ comportamiento
    def _terminar(self, a: dict):
        ahora = time.monotonic()
        a['estado'], a['fin'] = 'listo', ahora
        if a['cabeza']:
            a['lado'] = self._lado_menos_lleno()
            a['cabeza'] = False                    # baja de la cabeza (el próximo que llegue la ocupa)
            a['modo'] = 'cae'
            a['vy'] = -45.0                        # salta y cae al lado del cangrejito
        self._ir_al_lado(a)
        self._atencion(a['lado'], 3.0)

    def _grande(self, nombre: str, dur: float):
        """Le hace hacer algo al grande solo si está libre (no lo corta bailando, festejando ni agarrado)."""
        if not getattr(self.m, 'mom', None) and getattr(self.m, 'modo', 'suelo') == 'suelo':
            self.m.momento(nombre, dur)

    def _lado_menos_lleno(self) -> int:
        izq = sum(1 for v in self.agentes.values() if v['estado'] == 'listo' and v['lado'] < 0)
        der = sum(1 for v in self.agentes.values() if v['estado'] == 'listo' and v['lado'] > 0)
        return -1 if izq < der else 1

    def _ir_al_lado(self, a: dict):
        """Se acomoda pegadito al cangrejito: primero en el piso, después en una fila más atrás."""
        usados = {v.get('lugar') for v in self.agentes.values()
                  if v is not a and v['estado'] == 'listo' and v['lado'] == a['lado']}
        k = next(i for i in range(len(self.agentes) + 1) if i not in usados)     # el primer lugar libre
        a['lugar'] = k
        fila, col = k % FILAS, k // FILAS
        base = BORDE_IZQ if a['lado'] < 0 else BORDE_DER
        a['tx'] = base + a['lado'] * (col * ANCHO) + self.marg + 2 * fila * a['lado']
        a['ty'] = _suelo(fila)
        a['fila'] = fila
        if a['modo'] != 'cae':
            a['modo'] = 'camina'
        a['vel'] = random.uniform(18, 26)

    def _atencion(self, lado: int, seg: float):
        """El cangrejito se da vuelta a mirar de ese lado un ratito."""
        self.m.atencion = (lado, time.monotonic() + seg)

    def _elegir_destino(self, a: dict, ahora: float):
        lo, hi = zona(a['lado'], self.marg)
        lo, hi = lo + self.marg, hi + self.marg
        otros = [v for v in self.agentes.values() if v is not a and not v['cabeza'] and v['lado'] == a['lado']]
        for _ in range(14):                                   # un lugar que no pise a otro
            tx, fila = random.uniform(lo, hi), random.randrange(FILAS)
            if all(abs(tx - v['tx']) >= ANCHO - 1 or v['fila'] != fila for v in otros):
                a['tx'], a['fila'] = tx, fila
                a['ty'] = _suelo(fila)
                a['vel'] = random.uniform(8, 15)
                a['modo'] = 'camina'
                return
        a['modo'], a['hasta'] = 'quieto', ahora + random.uniform(2, 5)     # está lleno: se queda donde está

    def _mover(self, a: dict, dt: float, ahora: float, habla: bool):
        if a['modo'] == 'cae':
            if a['estado'] == 'listo' or a.get('desliza'):
                a['x'] += (a['tx'] - a['x']) * min(1.0, dt * 7)      # salta de la cabeza (o de la torre) a su lugar
            a['vy'] += GRAVEDAD * dt
            a['y'] += a['vy'] * dt
            if a['y'] >= a['ty'] and a['vy'] > 0:
                a['y'] = a['ty']
                if a['rebotes'] < 1 and a['vy'] > 60:           # un rebotecito al llegar
                    a['vy'], a['rebotes'] = -a['vy'] * 0.35, a['rebotes'] + 1
                else:
                    a['vy'], a['rebotes'] = 0.0, 0
                    a.pop('desliza', None)
                    if a['estado'] == 'listo':
                        a['modo'], a['hasta'] = 'camina', ahora
                    else:
                        a['modo'], a['hasta'] = 'quieto', ahora + random.uniform(1.5, 4)
            return
        if a['cabeza'] and a['estado'] == 'buscando':
            a['x'] = S.OX + 17 - ANCHO / 2 + self.marg
            a['y'] = float(CABEZA_Y)
            return
        if a['modo'] == 'camina':
            dx, dy = a['tx'] - a['x'], a['ty'] - a['y']
            d = math.hypot(dx, dy)
            paso = a['vel'] * dt
            if d <= max(paso, 0.4):
                a['x'], a['y'] = a['tx'], a['ty']
                if a.pop('saludar', False) and a['estado'] == 'buscando':
                    a['modo'], a['hasta'] = 'saluda', ahora + 2.6         # llegó al lado de él: lo saluda
                    self._atencion(a['lado'], 2.8)
                    algo = a.pop('con_grande', 'saludo')
                    if algo == 'choque':                                   # se chocan las pinzas
                        a['choca'] = 1 if a['lado'] < 0 else -1
                        self.efectos.append((a['x'] + (10.5 if a['lado'] < 0 else 0.5), a['y'] - 1, ahora))
                        self._grande('saludar', 1.3)
                    elif algo == 'mimo':                                   # él le hace un mimo
                        self._grande('mimo', 1.7)
                else:
                    a['modo'] = 'quieto'
                    a['hasta'] = ahora + (random.uniform(3, 9) if a['estado'] == 'buscando' else 1e9)
            else:
                a['x'] += dx / d * paso
                a['y'] += dy / d * paso
        elif a['modo'] in ('quieto', 'salta', 'saluda', 'choque'):
            if a['modo'] == 'salta':
                s = (ahora - a['salto']) / 0.55
                a['y'] = a['ty'] - 3 * max(0.0, math.sin(s * math.pi * 2)) if 0 <= s < 1 else a['ty']
                if s >= 1:
                    a['y'], a['modo'] = a['ty'], 'quieto'
            if ahora >= a['hasta'] and a['estado'] == 'buscando' and a['modo'] != 'salta':
                if a['modo'] == 'saluda':
                    a.pop('choca', None)
                    a['modo'] = 'quieto'
                    a['hasta'] = ahora + random.uniform(2, 6)
                elif random.random() < 0.3:
                    a['modo'], a['salto'] = 'salta', ahora
                else:
                    self._elegir_destino(a, ahora)

    def _saludar(self, ahora: float):
        """Uno va al costado del cangrejito y lo saluda; él lo mira (a veces le choca la pinza o lo mima)."""
        quien = [a for a in self.agentes.values()
                 if a['estado'] == 'buscando' and not a['cabeza'] and a['modo'] in ('quieto', 'camina')
                 and not a.get('par')]
        if not quien:
            return
        a = random.choice(quien)
        a['tx'] = (BORDE_IZQ if a['lado'] < 0 else BORDE_DER) + self.marg
        a['ty'], a['fila'], a['vel'] = _suelo(0), 0, random.uniform(14, 20)
        a['modo'], a['saludar'] = 'camina', True
        a['con_grande'] = random.choice(('choque', 'mimo', 'saludo', 'saludo'))

    def _libres(self, lado: int) -> list:
        """Los que buscan, quietos en el piso de ese lado y sin nada que hacer con otro (de izquierda a derecha)."""
        return sorted((a for a in self.agentes.values()
                       if a['estado'] == 'buscando' and not a['cabeza'] and a['lado'] == lado
                       and a['modo'] == 'quieto' and not a.get('par')), key=lambda v: v['x'])

    def _social(self, ahora: float):
        """Cada tanto pasa algo entre ellos o con el grande: saludo, choque de pinzas, ola, torre o
        persecución. Con pocos solo saludan; lo de a dos y la ola necesitan compañía."""
        self.prox_saludo = ahora + random.uniform(10, 20)
        opciones = ['saludo', 'saludo']
        lados = [lado for lado in (-1, 1) if len(self._libres(lado)) >= 2]
        todos = [a for lado in (-1, 1) for a in self._libres(lado)]
        if lados:
            opciones += ['choque', 'torre', 'persecucion']
        if len(todos) >= 3:
            opciones.append('ola')
        eleg = random.choice(opciones)
        if eleg == 'saludo':
            self._saludar(ahora)
            return
        if eleg == 'ola':
            for k, a in enumerate(sorted(todos, key=lambda v: v['x'])):
                a['modo'], a['salto'], a['hasta'] = 'salta', ahora + k * 0.22, ahora + k * 0.22 + 4
            return
        lado = random.choice(lados)
        libres = self._libres(lado)
        i = random.randrange(len(libres) - 1)
        a, b = libres[i], libres[i + 1]
        lo, hi = zona(lado, self.marg)
        lo, hi = lo + self.marg, hi + self.marg
        ids = [k for k, v in self.agentes.items() if v is a or v is b]
        if eleg == 'choque':
            centro = max(lo + 5, min(hi - 5, (a['x'] + b['x']) / 2))
            a['tx'], b['tx'] = centro - 5, centro + 5
            a['ty'] = b['ty'] = _suelo(a['fila'])
            b['fila'] = a['fila']
            a['modo'] = b['modo'] = 'camina'
        elif eleg == 'torre':
            a['tx'], a['ty'] = b['x'], b['y'] - 6                      # sube a la cabeza del otro
            a['modo'], a['vel'] = 'camina', 14.0
            b['modo'], b['hasta'] = 'quieto', 1e9
        else:                                                          # persecución: uno escapa, el otro lo sigue
            a['tx'] = random.choice((lo, hi))
            a['ty'] = _suelo(a['fila'])
            b['tx'] = max(lo, min(hi, a['tx'] + (10 if a['tx'] < (lo + hi) / 2 else -10)))
            b['ty'] = a['ty']
            a['vel'], b['vel'] = 34.0, 32.0
            a['modo'] = b['modo'] = 'camina'
        for v in (a, b):
            v['par'] = eleg
        self.pares.append({'tipo': eleg, 'ids': ids, 'ini': ahora, 'fase': 0})

    def _soltar(self, a: dict, ahora: float):
        a.pop('par', None)
        a.pop('choca', None)
        if a['estado'] == 'buscando' and a['modo'] in ('quieto', 'choque', 'camina'):
            a['modo'], a['hasta'] = 'quieto', ahora + random.uniform(1.5, 4)

    def _tick_pares(self, ahora: float):
        for par in list(self.pares):
            ag = [self.agentes.get(k) for k in par['ids']]
            if len(ag) < 2 or any(v is None or v['estado'] != 'buscando' or not v['vivo'] for v in ag) \
                    or ahora - par['ini'] > 25:
                for v in ag:                                  # alguno terminó o se fue: se corta la escena
                    if v is not None:
                        self._soltar(v, ahora)
                        if par['tipo'] == 'torre' and v['vivo'] and v['y'] < _suelo(v['fila']) - 2:
                            v['ty'], v['modo'], v['vy'] = _suelo(v['fila']), 'cae', 0.0      # baja de la torre
                self.pares.remove(par)
                continue
            a, b = ag
            cerca = [abs(v['tx'] - v['x']) < 0.8 and abs(v['ty'] - v['y']) < 0.8 for v in ag]
            if par['tipo'] == 'choque':
                if par['fase'] == 0 and all(cerca):
                    par['fase'], par['t'] = 1, ahora
                    for v, otro in ((a, b), (b, a)):
                        v['modo'], v['hasta'] = 'choque', 1e9
                        v['choca'] = 1 if otro['x'] > v['x'] else -1
                    self.efectos.append(((a['x'] + b['x']) / 2 + 5.5, a['y'] - 1, ahora))
                elif par['fase'] == 1 and ahora - par['t'] > 1.4:
                    for v in ag:
                        self._soltar(v, ahora)
                    self.pares.remove(par)
            elif par['tipo'] == 'torre':
                if par['fase'] == 0 and cerca[0]:
                    par['fase'], par['t'] = 1, ahora
                    a['modo'], a['hasta'] = 'quieto', 1e9
                elif par['fase'] == 1 and ahora - par['t'] > 3.5:
                    # baja de un salto hacia afuera (lejos del cangrejito grande) y se vuelve a lo suyo
                    lo, hi = zona(a['lado'], self.marg)
                    afuera = -1 if a['lado'] < 0 else 1
                    a['tx'] = max(lo + self.marg, min(hi + self.marg, a['x'] + 11 * afuera))
                    a['ty'], a['modo'], a['vy'], a['desliza'] = _suelo(b['fila']), 'cae', -40.0, True
                    a.pop('par', None)
                    b.pop('par', None)
                    b['modo'], b['hasta'] = 'quieto', ahora + 2
                    self.pares.remove(par)
            elif all(cerca) or ahora - par['ini'] > 12:         # persecución
                for v in ag:
                    self._soltar(v, ahora)
                    v['vel'] = random.uniform(8, 15)
                self.pares.remove(par)

    def _marg(self):
        vivos = len(self.agentes)
        marg = margen(vivos)
        if marg > self.marg:                                  # creció: los demás se corren con la ventana
            for a in self.agentes.values():
                a['x'] += marg - self.marg
                a['tx'] += marg - self.marg
            self.marg = marg
        elif marg < self.marg and vivos <= 1:
            for a in self.agentes.values():
                a['x'] -= self.marg - marg
                a['tx'] -= self.marg - marg
            self.marg = marg

    def _colocar(self):
        if self.width() != (S.W + 2 * self.marg) * self.E:
            self.setFixedSize((S.W + 2 * self.marg) * self.E, S.H * self.E)
        g = self.m.geometry()
        self.move(g.x() - self.marg * self.E, g.y())

    def _tick(self):
        ahora = time.monotonic()
        dt, self._ult = min(0.1, ahora - self._ult), ahora
        paso = min(1.0, dt / 0.35)
        habla = bool(getattr(self.m.voz, 'hablando', False))
        if ahora >= self.prox_saludo:
            self._social(ahora)
        self._tick_pares(ahora)
        self.efectos = [e for e in self.efectos if ahora - e[2] < 0.6]
        for aid in list(self.agentes):
            a = self.agentes[aid]
            if a['estado'] == 'buscando' and ahora - a['desde'] > SE_PIERDE:
                self._terminar(a)
            if a['estado'] == 'listo' and ahora - a['fin'] > SE_QUEDAN:
                a['vivo'] = False
            a['alfa'] = min(1.0, a['alfa'] + paso) if a['vivo'] else max(0.0, a['alfa'] - paso)
            if not a['vivo'] and a['alfa'] <= 0:
                del self.agentes[aid]
                continue
            self._mover(a, dt, ahora, habla)
        if not self.agentes:
            self.hide()
            self._timer.stop()
            return
        self._colocar()
        img = self._dibujar(ahora)
        if self._img is None or img != self._img:       # solo se repinta (y se actualiza la ventana) si cambió algo
            self._img = img
            self.update()

    def _estado(self, a: dict, t: float, ahora: float, habla: bool) -> dict:
        """Cómo se ve ese agente ahora (lo que necesita _mini)."""
        e = {'n': a['n'], 'look': 0, 'camina': False}
        if ahora >= a['parp']:
            a['parp'], a['parp_fin'] = ahora + random.uniform(2, 5), ahora + 0.12
        e['parpadea'] = ahora < a['parp_fin']
        centro = S.OX + 17 + self.marg
        hacia = 1 if centro > a['x'] + ANCHO / 2 else -1            # hacia el cangrejito
        listo = a['estado'] == 'listo'
        if a['modo'] == 'cae':
            e['look'] = 0
        elif a['modo'] == 'camina':
            e['camina'] = True
            e['look'] = 1 if a['tx'] > a['x'] else -1
        elif a['modo'] in ('saluda', 'choque'):
            e['saluda'], e['look'] = True, hacia
            e['choca'] = a.get('choca', 0)
        elif listo:
            e['feliz'], e['look'] = True, hacia
        else:
            if habla:
                e['look'] = hacia                                  # lo escucha
            else:
                e['celu'], e['tapea'] = True, True
                e['look'] = 1                                      # mira el celu (a la derecha, donde lo tiene)
            if a['cabeza']:
                e['look'] = hacia if habla else (1 if int(t / 3 + a['n']) % 3 else 0)
        return e

    def _dibujar(self, ahora: float) -> QImage:
        marg = self.marg
        img = QImage(S.W + 2 * marg, S.H, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        q = QPainter(img)
        t = ahora - self.t0
        habla = bool(getattr(self.m.voz, 'hablando', False))
        bailan = getattr(self.m, 'mom', None) in BAILAN and not habla
        for a in sorted(self.agentes.values(), key=lambda v: v['y'] + (50 if v.get('par') == 'torre' and v['modo'] == 'quieto' and v['y'] < _suelo(v['fila']) - 2 else 0)):
            e = self._estado(a, t, ahora, habla)
            dy = 0.0
            if habla and a['modo'] == 'quieto':
                dy = -1.0 if int(t * 7 + a['n']) % 2 else 0.0      # rebotan al ritmo de la voz
            elif a['estado'] == 'listo' and a['modo'] == 'quieto':
                dy = -1.0 if int(t * 4 + a['n']) % 3 == 0 else 0.0   # saltitos de alegría
            if bailan and a['modo'] == 'quieto':                      # bailan con él, al compás
                dy = -2.0 * abs(math.sin(t * 7 + a['n']))
                e['saluda'] = e.get('saluda') or int(t * 4 + a['n']) % 2 == 0
                e.pop('celu', None)
            _mini(q, a['x'], a['y'] + dy, e, t, a['alfa'])
        for (ex, ey, ini) in self.efectos:                            # chispitas del choque de pinzas
            f = (ahora - ini) / 0.6
            q.setOpacity(max(0.0, 1.0 - f))
            r = 1 + int(f * 3)
            col = S.PALETA['w'] if f < 0.3 else S.PALETA['y']
            for dx, dy2 in ((r, 0), (-r, 0), (0, r), (0, -r)):
                q.fillRect(round(ex + dx), round(ey + dy2), 1, 1, col)
            q.fillRect(round(ex), round(ey), 1, 1, S.PALETA['w'])
        q.setOpacity(1.0)
        q.end()
        return img

    def paintEvent(self, _):
        if not self.agentes:
            return
        if self._img is None or self._img.width() != S.W + 2 * self.marg:
            self._img = self._dibujar(time.monotonic())
        p = QPainter(self)
        p.drawImage(QRect(0, 0, self.width(), self.height()), self._img)
