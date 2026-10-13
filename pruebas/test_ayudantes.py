# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Los mini-cangrejos de los agentes: lugares, conteo y que sigan al cangrejito."""
import ayudantes as A
import sprites as S


def test_zonas_dentro_de_la_ventana_y_fuera_del_cangrejo():
    for n in (2, 3, 9, 20, 41):
        marg = A.margen(n)
        izq, der = A.zona(-1, marg), A.zona(1, marg)
        assert izq[0] >= -marg and izq[1] + A.ANCHO <= 5 + 4        # no pisa la pinza izquierda (x=5)
        assert der[0] >= 35 and der[1] + A.ANCHO <= S.W + marg
        assert izq[1] > izq[0] and der[1] > der[0]
    assert A.margen(0) == 0 and A.margen(1) == A.margen(2) > 0


def test_un_solo_agente_que_termina_no_queda_recortado(mascota):
    """Con un agente solo (arriba de la cabeza) que termina rápido, su lugar al costado entra en la ventana."""
    a = mascota.ayu
    a.agentes.clear()
    for lado in (-1, 1):
        a.nuevo('x', 's')
        v = a.agentes['x']
        v['lado'] = lado
        a._terminar(v)
        assert v['tx'] >= 0 and v['tx'] + A.ANCHO + 2 <= S.W + 2 * a.marg, (lado, v['tx'], a.marg)
        a.agentes.clear()


def test_conteo_y_estados(mascota):
    a = mascota.ayu
    a.nuevo('a1', 's')
    a.nuevo('a2', 's')
    a.nuevo('a2', 's')                         # repetido: no suma
    assert a.cuantos() == 2
    a.listo('a1')
    assert a.cuantos() == 1 and a.hay()
    a.listo('', 's')                           # sin id: termina el más viejo que siga buscando
    assert a.cuantos() == 0
    a.limpiar('s')
    for v in a.agentes.values():
        assert not v['vivo']


def test_terminar_sesion_y_lugar_reusado(mascota):
    a = mascota.ayu
    a.agentes.clear()
    for i in range(4):
        a.nuevo(f'x{i}', 'sesion')
    assert sum(v['cabeza'] for v in a.agentes.values()) == 1        # solo uno va arriba de la cabeza
    a.terminar_sesion('sesion')
    assert a.cuantos() == 0
    assert sum(v['cabeza'] for v in a.agentes.values()) == 0        # al terminar, todos bajaron de la cabeza
    a.nuevo('nuevo', 'sesion')
    assert a.agentes['nuevo']['cabeza']                             # y el próximo que llega la ocupa


def test_pintar_y_seguir_al_cangrejo(mascota):
    mascota.show()
    a = mascota.ayu
    a.agentes.clear()
    for i in range(9):
        a.nuevo(f'p{i}', 's')
    a.listo('p0')
    assert a.isVisible()
    mascota.move(300, 200)
    assert a.y() == mascota.y()
    assert a.x() == mascota.x() - A.margen(9) * a.E
    assert a.width() == (S.W + 2 * A.margen(9)) * a.E
    a.grab()                                    # se dibuja sin errores
    mascota.hide()
    assert not a.isVisible()


def test_eventos_de_agentes_por_el_narrador(mascota):
    from narrador import Narrador
    mascota.show()
    nar = Narrador(mascota, mascota.voz, mascota.cfg, lambda: {})
    ev = lambda tipo, **k: nar.evento({'hook_event_name': tipo, 'session_id': 'S1', 'cwd': 'C:/x', **k})
    ev('SessionStart')
    ev('SubagentStart', agent_id='a')
    ev('SubagentStart', agent_id='b')
    ev('SubagentStart')                       # sin id: se inventa uno
    assert mascota.ayu.cuantos() == 3
    ev('SubagentStop', agent_id='a')
    assert mascota.ayu.cuantos() == 2
    ev('SubagentStop', agent_id='b')
    ev('SubagentStop')                        # sin id: termina el más viejo que siga buscando
    assert mascota.ayu.cuantos() == 0 and mascota.ayu.hay()      # siguen un rato al lado, ya terminados
    ev('SubagentStart', agent_id='z')
    ev('SessionEnd')
    assert all(not v['vivo'] for v in mascota.ayu.agentes.values())


def test_simulacion_no_pisa_al_cangrejo(mascota, monkeypatch):
    """Con reloj falso: 12 agentes andan, saludan y terminan; ninguno atraviesa el cuerpo del cangrejito."""
    import random
    reloj = [500.0]
    monkeypatch.setattr(A.time, 'monotonic', lambda: reloj[0])
    random.seed(3)
    mascota.show()
    a = mascota.ayu
    a.agentes.clear()
    a._ult = reloj[0]
    for i in range(12):
        a.nuevo(f'm{i}', 's')
    cuerpo = (S.OX + 3 + a.marg, S.OX + 32 + a.marg)       # x del cuerpo, sin las pinzas
    for paso in range(1500):
        reloj[0] += 0.1
        a._ult = reloj[0] - 0.1
        if paso == 600:
            for i in range(0, 12, 2):
                a.listo(f'm{i}')
        a._tick()
        for v in a.agentes.values():
            if v['modo'] != 'cae' and not v['cabeza']:
                assert v['x'] + A.ANCHO <= cuerpo[0] + 1 or v['x'] >= cuerpo[1] - 1, (paso, v['x'])
    assert a.cuantos() == 6


def test_escenas_entre_chiquitos_terminan_y_no_dejan_basura(mascota, monkeypatch):
    """Choque de pinzas, torre, persecución y ola: arrancan, terminan y nadie queda marcado ni trabado."""
    import random
    for tipo in ('choque', 'torre', 'persecucion', 'ola'):
        reloj = [900.0]
        monkeypatch.setattr(A.time, 'monotonic', lambda: reloj[0])
        random.seed(5)
        mascota.show()
        a = mascota.ayu
        a.agentes.clear()
        a.pares.clear()
        a._ult = reloj[0]
        for i in range(8):
            a.nuevo(f'm{i}', 's')
        original = random.choice
        monkeypatch.setattr(A.random, 'choice', lambda seq, t=tipo: t if t in seq else original(seq))
        visto = False
        for paso in range(900):
            reloj[0] += 0.1
            a._ult = reloj[0] - 0.1
            if paso % 40 == 20:
                a.prox_saludo = 0                       # fuerza una escena nueva cada 4 segundos
            a._tick()
            visto = visto or bool(a.pares) or any(v['modo'] == 'salta' for v in a.agentes.values())
        monkeypatch.setattr(A.random, 'choice', original)
        assert visto, tipo
        for _ in range(300):                            # lo que quedó en marcha termina solo
            reloj[0] += 0.1
            a._ult = reloj[0] - 0.1
            a.prox_saludo = reloj[0] + 999
            a._tick()
        assert not a.pares, (tipo, a.pares)
        assert not [v for v in a.agentes.values() if v.get('par') or v.get('choca')], tipo
        assert not [v for v in a.agentes.values() if v['modo'] == 'cae' and v['estado'] == 'buscando'
                    and not v['cabeza'] and v['y'] < 0], tipo


def test_muchos_ayudantes_no_quedan_encimados(mascota, monkeypatch):
    """Con 9 agentes (algunos ya terminados) nadie queda pisando a otro de su lado y su fila."""
    import random
    reloj = [900.0]
    monkeypatch.setattr(A.time, 'monotonic', lambda: reloj[0])
    random.seed(9)
    mascota.show()
    a = mascota.ayu
    a.agentes.clear()
    a._ult = reloj[0]
    for i in range(9):
        a.nuevo(f'm{i}', 's')
        for _ in range(6):
            reloj[0] += 0.1
            a._ult = reloj[0] - 0.1
            a._tick()
    for i in (1, 3, 4, 6):
        a.listo(f'm{i}', 's')
    for _ in range(120):
        reloj[0] += 0.1
        a._ult = reloj[0] - 0.1
        a.prox_saludo = reloj[0] + 999
        a._tick()
    quietos = [v for v in a.agentes.values() if not v['cabeza'] and v['modo'] == 'quieto']
    assert len(quietos) >= 4
    for i, v in enumerate(quietos):
        for w in quietos[i + 1:]:
            if v['lado'] == w['lado'] and v['fila'] == w['fila']:
                assert abs(v['x'] - w['x']) >= A.ANCHO - 2, (v['x'], w['x'], v['fila'])
