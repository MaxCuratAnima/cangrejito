# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Lo argentino y lo personalizable: fechas, géneros musicales, el mástil, el trato, la voz y el confeti."""
import datetime as dt
import time

import fechas
import narrador as N
import sprites as S
import vigilante as V
import voz


def test_fechas_patrias_y_culturales():
    d = dt.date
    assert fechas.hoy(d(2026, 5, 25)) == 'mayo'
    assert fechas.hoy(d(2026, 6, 20)) == 'bandera'
    assert fechas.hoy(d(2026, 7, 9)) == 'independencia'
    assert fechas.hoy(d(2026, 8, 17)) == 'san_martin'
    assert fechas.hoy(d(2026, 1, 29)) == 'noquis'
    assert fechas.hoy(d(2026, 6, 21)) == 'padre'               # tercer domingo de junio de 2026
    assert fechas.hoy(d(2026, 9, 13)) == 'programador'         # día 256 (2026 no es bisiesto)
    assert fechas.hoy(d(2028, 9, 12)) == 'programador'         # bisiesto
    assert fechas.hoy(d(2026, 3, 3)) == ''
    assert fechas.datos('malvinas')['respeto'] and fechas.datos('malvinas')['escarapela']
    assert fechas.datos('bandera')['actividad'] == 'mastil'
    for clave, f in fechas.FECHAS.items():
        assert f['saludo'] and f['curiosidades'], clave
        f['saludo'].format(n='Lu', o='a', mate='un mate')


def test_generos_musicales_argentinos():
    casos = {'Carlos Gardel - Por una Cabeza': 'tango', 'La Mona Jiménez - Beso a Beso': 'cuarteto',
             'Rodrigo - Lo mejor del amor': 'cuarteto', 'Olivia Rodrigo - drivers license': '',
             'Damas Gratis - Se te ve la tanga': 'cumbia', 'Soda Stereo - De Música Ligera': 'rock',
             'Bizarrap, Duki - Bzrp Music Sessions #50': 'trap', 'Chaqueño Palavecino - Amor salvaje': 'folklore',
             'Kordhell - Murder In My Mind': 'funk', 'Taylor Swift - Shake It Off': '',
             'Daft Punk - One More Time': 'electronica', 'Bee Gees - Stayin Alive': 'disco',
             'Bob Marley - One Love': 'reggae', 'Metallica - Enter Sandman': 'metal',
             'Beethoven - Para Elisa': 'clasica', 'Bad Bunny - Tití Me Preguntó': '',
             'Anitta - Reggaeton Lento': ''}
    for tema, genero in casos.items():
        assert V.genero_musical(tema) == genero, tema
    assert V.genero_musical('Mi Banda - Tema', {'cumbia': ['Mi Banda']}) == 'cumbia', 'artistas propios'
    assert V.genero_musical('Soda Stereo - Persiana Americana', apagados={'rock'}) == '', 'género apagado'


def test_ropa_y_actividades_por_genero_y_fecha(mascota):
    mascota.musica = True
    for genero, ropa in M_ROPA().items():
        mascota.genero = genero
        acc = mascota._pose(time.monotonic()).accesorios
        mascota.alfas = {k: 1.0 for k in acc}
        acc = mascota._pose(time.monotonic()).accesorios
        assert ropa <= set(acc), genero
    mascota.musica, mascota.genero = False, ''
    mascota.fecha = fechas.datos('mayo')
    mascota._pose(time.monotonic())
    acc = mascota._pose(time.monotonic()).accesorios
    assert {'escarapela', 'galera'} <= set(acc)


def M_ROPA():
    import mascota as M
    return M.ROPA_GENERO


def test_todos_los_accesorios_y_banderas_se_dibujan(app):
    nombres = ['escarapela', 'galera', 'bicornio', 'poncho', 'guardapolvo', 'gorro_navidad', 'flor', 'funyi',
               'panuelo_blanco', 'bandoneon', 'lentejuelas', 'gorrita', 'camiseta', 'teclado_musical', 'campera',
               'electrica', 'gorra', 'cadena', 'microfono', 'noquis', 'tenedor', 'mate', 'mate_boca', 'bandera',
               'casco_plata', 'casco_oro', 'panuelo_baile', 'bola_disco', 'gorro_rasta', 'peluca', 'melena']
    for bebida in ('mate', 'cafe', 'te', 'ruda'):
        for pais in S.BANDERAS:
            S.dibujar(S.Pose(accesorios={k: 1.0 for k in nombres}, bebida=bebida, bandera=pais))
    for izada in (0.0, 0.5, 1.0):
        img = S.dibujar_mastil(3.0, izada)
        assert (img.width(), img.height()) == (S.MW, S.MH)
        assert S.MH > 29, 'el mástil es más alto que el cangrejito'


def test_mastil_se_iza_y_el_cangrejito_va(mascota, app):
    from mastil import Mastil
    mastil = Mastil(mascota.cfg, mascota._area)
    mascota.mastil = mastil
    pant = app.primaryScreen()
    mastil.plantar(mascota.px + 400, pant)
    assert mastil.izada == 0 and mastil.quieto()
    mascota._paseos(time.monotonic())
    assert mascota.paseo in ('caminar', 'izar'), 'va a izar la bandera'
    mascota._empezar_bandera('izar', time.monotonic())
    mastil.izando_desde -= 10                       # como si hubieran pasado 10 segundos
    mastil._tick()
    assert mastil.izada == 1.0
    mastil.sacar()
    assert not mastil.plantado


class _Cfg(dict):
    def guardar(self):
        pass


def test_trato_neutro_y_bebida():
    import config
    n = N.Narrador.__new__(N.Narrador)
    n.fecha = fechas.datos('')
    n.cfg = _Cfg(config.POR_DEFECTO, nombre='Lu', trato='neutro', bebida='cafe')
    n._al_dia()
    try:
        for _ in range(80):
            assert '{o}' not in N._uno(N.PEDIDO) and 'compañer' not in N._uno(N.PEDIDO)
        assert 'cafecito' in N._uno(['Preparate {mate}.'])
        n.cfg['trato'] = 'femenino'
        n._al_dia()
        assert N._uno(['Anotado, compañer{o}.']) == 'Anotado, compañera.'
    finally:
        n.cfg.update(trato='masculino', bebida='mate')
        n._al_dia()


def test_todas_las_frases_se_arman():
    marcas = dict(n='Lu', o='a', mate='un mate', f='a.py', p='Curso', k=3, h='03:00', a='Duki', d='algo', e='Eso.')
    for nombre, lista in vars(N).items():
        if nombre.isupper() and isinstance(lista, list) and lista and isinstance(lista[0], str):
            for f in lista:
                f.format(**marcas)
    assert N.animo_de(N._uno(N.FRUSTRADO)) == 'enojado'


def test_pronunciacion_y_respiro():
    assert voz.pronunciar('Listo ✅🦀') == 'Listo'
    assert 'por ejemplo' in voz.pronunciar('p. ej. esto')
    assert voz.pronunciar('Mmm, a ver') == 'Emm, a ver'
    assert '3 de 5' in voz.pronunciar('3/5 pruebas') and 'versión 1.3.0' in voz.pronunciar('v1.3.0')
    partes = voz.trozos(voz.pronunciar('Hola. ¿Todo bien? Arranco… ya'))
    assert [p for _, p in partes][:3] == [voz.PAUSAS['.'], voz.PAUSAS['?'], voz.PAUSAS['…']]
    largo = voz._respirar('Encontré el error en el globo porque la fuente nueva no tenía los acentos bien y entonces se cortaba')
    assert 'bien, y entonces' in largo


def test_confeti_suena():
    import efectos
    for nombre in ('confeti', 'fiesta'):
        a = efectos.generar(nombre, 22050)
        assert 0.5 < abs(a).max() <= 0.61 and len(a) > 22050 * 0.9
    mezcla, inicio = efectos.mezclar(efectos.generar('confeti', 22050), voz.np.ones(1000, voz.np.float32) * 0.1, 22050)
    assert inicio == int(22050 * 0.45) and len(mezcla) >= inicio + 1000
