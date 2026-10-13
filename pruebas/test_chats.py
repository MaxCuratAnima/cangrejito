"""Chats normales de Claude: el narrador los comenta como el final de una tarea."""
from narrador import Narrador


def test_chat_respuesta_habla_y_respeta_la_opcion(mascota):
    dicho = []
    mascota.cfg['chats_normales'] = True
    nar = Narrador(mascota, mascota.voz, mascota.cfg, lambda: {})
    nar.oculto = False
    nar.decir = lambda texto, **kw: dicho.append(texto)
    nar.chat_respuesta('Claude respondió: Armé la receta con tres pasos. Después la probamos.')
    assert dicho and 'receta' in dicho[0]
    dicho.clear()
    mascota.cfg['chats_normales'] = False
    nar.chat_respuesta('Otra respuesta cualquiera para comentar.')
    assert not dicho


def test_chat_lleva_el_titulo_en_el_globo(mascota):
    from chats import nombre_del_chat
    assert nombre_del_chat('Receta de milanesas - Claude') == 'Receta de milanesas'
    assert nombre_del_chat('Claude') == '' and nombre_del_chat('') == ''
    dicho = []
    mascota.cfg['chats_normales'] = True
    nar = Narrador(mascota, mascota.voz, mascota.cfg, lambda: {})
    nar.oculto = False
    nar.decir = lambda texto, **kw: dicho.append((texto, kw.get('sub')))
    nar.chat_respuesta('Receta de milanesas', 'Claude respondió: Armé la receta con tres pasos. Después la probamos.')
    assert dicho[-1][1] == 'Receta de milanesas' and not dicho[-1][0].lower().startswith('claude respondió')
    nar.chat_respuesta('', 'Otra cosa distinta para comentar acá.')
    assert dicho[-1][1] == 'Chat de Claude'
