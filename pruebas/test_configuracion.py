# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""La configuración (ventana y menú) cambia de verdad cómo habla el cangrejito."""
import config
import configuracion
import narrador as N


class Cfg(dict):
    def guardar(self):
        self.guardado = True


def test_la_ventana_guarda_lo_que_se_elige(app):
    cfg = Cfg(config.POR_DEFECTO)
    v = configuracion.Configuracion(cfg, bienvenida=True)
    v.nombre.setText('  Lu  ')
    v.habla.setCurrentIndex(0)                       # poco
    v.detalle.setCurrentIndex(0)                     # cortos
    v.groserias.setChecked(False)
    v.volumen.setValue(80)
    v.velocidad.setCurrentIndex(4)                   # 125 %
    v._guardar()
    assert (cfg['nombre'], cfg['habla'], cfg['detalle'], cfg['groserias']) == ('Lu', 'poco', 'corto', False)
    assert cfg['volumen'] == 0.8 and cfg['velocidad'] == 1.31 and cfg.guardado


class Grabador:
    """Narrador sin mascota ni voz: anota lo que diría."""
    def __init__(self, **prefs):
        self.n_ = N.Narrador.__new__(N.Narrador)
        self.n_.cfg = Cfg(config.POR_DEFECTO, nombre='Lu', **prefs)
        self.dichos = []
        self.n_.decir = lambda texto, **k: self.dichos.append(texto)


def test_cortos_y_detallados():
    texto = 'Encontré el error en el globo. Ahora pruebo con la fuente nueva. Y después reviso el resto.'
    corto = Grabador(detalle='corto').n_._sobre_claude(texto)
    largo = Grabador(detalle='detallado').n_._sobre_claude(texto)
    assert corto == 'Encontré el error en el globo.'
    assert largo.startswith(corto) and 'fuente nueva' in largo


def test_sin_malas_palabras():
    N.PREFERENCIAS['groserias'] = False
    try:
        for _ in range(60):
            for lista in (N.FRUSTRADO, N.HARTO, N.FIN_LARGO, N.ABURRIDO):
                assert not N.GROSERAS.search(N._uno(lista)), 'se coló una mala palabra'
    finally:
        N.PREFERENCIAS['groserias'] = True


def test_habla_poco_calla_los_pasos():
    g = Grabador(habla='poco')
    g.n_._actual = None
    g.n_._paso({'tool_use_id': 'x'}, 's', {}, None, 'leer', 'Leyendo algo', False, 'leer')
    assert g.dichos == [], 'con «poco» no narra cada paso'
