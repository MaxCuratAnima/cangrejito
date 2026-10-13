from resultado import clasificar

MAL = ['No pude hacer que compile, sigue fallando.', 'Intenté dos veces pero no funcionó.', 'El build falló con un error de shader.',
       'No logré arreglar la física.', 'Es imposible hacerlo con esa versión.', 'No se pudo instalar el paquete.']
REGULAR = ['Quedó a medias: falta la parte de las texturas.', 'Funciona parcialmente.', 'Solo pude arreglar el brazo izquierdo.',
           'Quedó pendiente el export a Quest.', 'No del todo, pero avanzó.']
CASI = ['Quedó todo bien salvo un detalle menor en la cola.', 'Salió casi perfecto, quedan unos detalles.',
        'Pasan todos los tests excepto uno.', 'Compila con algunas advertencias.']
OK = ['Listo, todo funciona.', 'Agregué el toggle y lo probé: anda perfecto.', 'Terminé: quedó impecable.',
      'No hubo ningún error y funcionó a la primera.', 'Pasaron los 36 tests.', '',
      'Listo, todo anda. Si algo no funciona, avisame.', 'Corregí lo que fallaba. Si no anda, decime.',
      'Arreglé lo que falló ayer. Ahora anda.', 'Compila sin warnings y sin advertencias.', 'No faltó nada, quedó completo.',
      'El render parcial ya anda y se ve bien.']


def test_clasifica_resultados():
    for t in MAL:
        assert clasificar(t) == 'mal', t
    for t in REGULAR:
        assert clasificar(t) == 'regular', t
    for t in CASI:
        assert clasificar(t) == 'casi', t
    for t in OK:
        assert clasificar(t) == 'ok', t


def test_ultimo_fallo_sin_pistas_es_regular_pero_no_si_dice_que_anda():
    assert clasificar('Hice los cambios.', True) == 'regular'
    assert clasificar('Listo, funciona.', True) == 'ok'


def test_stop_reacciona_segun_como_salio(mascota, monkeypatch):
    from narrador import Narrador
    import narrador as N
    mascota.show()
    nar = Narrador(mascota, mascota.voz, mascota.cfg, lambda: {})
    dichas = []
    monkeypatch.setattr(nar, 'decir', lambda texto, **k: dichas.append((texto, k.get('animo'))))
    casos = [('No pude hacer que compile, sigue fallando.', 'fracaso', 'triste', N.FALLO),
             ('Quedó a medias: falta la parte de las texturas.', 'duda', 'cansado', N.PARCIAL),
             ('Quedó todo bien salvo un detalle menor en la cola.', 'meh', '', N.CASI_BIEN)]
    for texto, momento, animo, lista in casos:
        nar.evento({'hook_event_name': 'Stop', 'session_id': 'S', 'cwd': 'C:/x', 'last_assistant_message': texto})
        assert mascota.mom == momento, (texto, mascota.mom)
        dicho, an = dichas[-1]
        assert an == animo and any(dicho.startswith(f.split('{')[0]) for f in lista), dichas[-1]
    nar.evento({'hook_event_name': 'Stop', 'session_id': 'S', 'cwd': 'C:/x', 'last_assistant_message': 'Listo, anda perfecto.'})
    assert mascota.mom in ('festejar', 'orgulloso') and dichas[-1][1] == 'contento'
    # un error como última herramienta, sin texto que diga que anda → duda
    nar.evento({'hook_event_name': 'PostToolUseFailure', 'session_id': 'S', 'cwd': 'C:/x', 'error': 'boom', 'tool_use_id': 'u1'})
    nar.evento({'hook_event_name': 'Stop', 'session_id': 'S', 'cwd': 'C:/x', 'last_assistant_message': 'Hice los cambios.'})
    assert mascota.mom == 'duda'
