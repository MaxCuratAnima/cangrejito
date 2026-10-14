# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Traduce los eventos de Claude Code en animaciones y frases, y reparte la voz.

Ritmo: el globo y la voz van juntos. Una frase normal espera a que termine la
anterior; si mientras tanto llegan varias, queda solo la última. Las importantes
(permiso, pregunta, listo) cortan lo que suena.
"""
from __future__ import annotations

import json
import logging
import random
import re
import time
from collections import deque
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

log = logging.getLogger('cangrejito.narrador')

# Personalidad: un cangrejito laburador y compinche, rioplatense. La persona es su compañera, no su jefa:
# nada de «jefe». Marcas en las frases:
#   {n}     el nombre o apodo de la persona
#   {o}     o / a según cómo quiere que la traten (las frases con {o} no se usan con trato neutro)
#   {mate}  lo que toma: «un mate», «un cafecito», «un tecito» (o «un descanso» si no toma nada)
PEDIDO = ['¡Pedido nuevo! A ver…', '¡Dale, me pongo!', 'Ahí voy.', 'Mmm, a ver qué hay que hacer.',
          '¡Manos a la pinza!', '¡Uh, laburo! Me encanta.', 'Dale, {n}, ahí me fijo.', '¡Vamos que se puede!',
          'Okey, {n}, ahí me pongo con eso.', 'Anotado, compañer{o}.', 'Dale, {n}, lo vemos juntos.',
          '¡Joya, dale!', 'De una, {n}.', '¡Ya me pongo las pilas!', 'Bancame que lo miro.',
          '¡Uh, qué buena! Arranco.', 'Dale que va.', 'Listo el pollo, me pongo.', '¡Vamos arriba!',
          'Dejámelo a mí.', '¡Esa! Me encanta cuando hay que laburar.', 'Mirá vos… a ver qué onda.',
          'Okey, {n}, lo encaro.', '¡Al toque!', 'Tranqui, que yo me encargo.', 'Ahí le meto.',
          'Ya mismo, {n}.', 'Me pongo el overol y arranco.', 'Dale, que hoy estoy inspirado.', 'Anotadísimo.',
          'Uh, este me gusta.', 'A ver con qué venís hoy, {n}.', 'Esto lo saco en un toque.',
          'Pará que me acomodo y arranco.', 'Bueno, bueno, a laburar.', 'Hecho, {n}. Arranco.',
          'Me arremango y voy.', '¡Uh, qué pedido! Vamos.', 'Ahí te lo miro.', 'Lo que vos digas, {n}.',
          'Uh, un desafío. Me copa.', 'Vamos a ver qué sale de acá.', 'Sale y vale, {n}.']
LEER = ['Leyendo {f}', 'A ver qué dice {f}', 'Le echo un ojo a {f}', 'Chusmeo {f}', 'Abro {f}, a ver qué hay',
        'Le pego una leída a {f}', 'Me fijo en {f}', 'Reviso {f} de pe a pa', 'A ver qué onda {f}',
        'Espiando {f}', 'Me leo {f} un toque', 'Pispeo {f}', 'Le pego una ojeada a {f}', 'Hojeo {f}',
        'Me fijo qué tiene {f}', 'Repaso {f}', 'A ver de qué va {f}', 'Me empapo de {f}']
LEER_SIN = ['Leyendo un archivo', 'Reviso un archivo', 'Chusmeo un archivo', 'Le pego una leída a algo',
            'Pispeo un archivo', 'Me fijo en un archivo', 'Le echo un ojo a algo', 'Repaso unas cosas']
BUSCAR = ['Buscando en los archivos', 'Busco en el código', '¿Dónde estará?', 'Lupa en mano…',
          'Estaba por acá, seguro', '¿Dónde lo habré puesto?', 'Revuelvo el cajón a ver…',
          'Busco la aguja en el pajar', 'Rastreando…', 'Modo detective activado', 'Lo tengo en la punta de la pinza…',
          'A ver dónde se escondió', 'Busco por todos lados', '¿Dónde se metió?', 'Sigo la pista',
          'Uh, ¿dónde estaba esto?', 'Busco y rebusco', 'Pispeo por acá y por allá']
EDITAR = ['Editando {f}', 'Le cambio unas cositas a {f}', 'Retocando {f}', 'Le meto mano a {f}',
          'Arreglo {f}', 'Le hago unos ajustes a {f}', 'Emprolijo {f}', 'Le doy una manito a {f}',
          'Toqueteo {f}', 'Le pego una arreglada a {f}', 'Mejoro {f}', 'Meto la pinza en {f}',
          'Le hago un retoque a {f}', 'Acomodo {f}', 'Le doy una vuelta de tuerca a {f}', 'Afino {f}', 'Pulo {f}']
CREAR = ['Escribiendo {f}', 'Creando {f}', 'Armo {f} desde cero', 'Hago {f} nuevito',
         'Le doy vida a {f}', 'Fabrico {f}', 'Nace {f}', 'Cocino {f}', 'Le doy forma a {f}']
COMANDO = ['Corriendo un comando', 'Le mando un comando a la consola', 'Ejecuto algo en la terminal',
           'Tecleo en la consola', 'A ver qué dice la terminal', 'Le tiro un comandito a la compu',
           'Consola, hacé lo tuyo', 'Le doy órdenes a la compu', 'A ver si la terminal me hace caso',
           'Tecla va, tecla viene', 'Comando va…', 'Le pido algo a la consola', 'Terminal, te toca',
           'Dale, consola, no me falles']
WEB_BUSCAR = ['Buscando en internet', 'Averiguo en internet', 'Le pregunto a internet',
              'Googleo un toque', 'Investigo en la web', 'Me fijo qué dice internet', 'Chusmeo internet',
              'Me informo un toque', 'Busco a ver qué dicen por ahí']
WEB_LEER = ['Leyendo una página web', 'Miro una página', 'Chusmeo una página', 'Leo lo que encontré',
            'Me leo lo que encontré', 'A ver qué dice esta página']
NAVEGADOR = ['Mirando el navegador', 'Navego un poco', 'Surfeando la web', 'Clic por acá, clic por allá',
             'Ando navegando', 'Miro una página en el navegador']
UNITY = ['Tocando Unity', 'Meto mano en Unity', 'Unity, allá voy', 'Acomodo cosas en Unity',
         'Me metí en Unity, bancame', 'Peleándome un rato con Unity', 'Unity me está dando laburo',
         'Toqueteando la escena', 'A ver qué dice Unity']
AYUDANTE = ['Llamo a un ayudante', 'Mando a un compañero a investigar', 'Refuerzos en camino',
            'Llamo a la banda', 'Un cangrejito amigo me da una mano', 'Pido ayuda a un colega',
            'Le paso un laburito a un compañero', 'Somos un equipo, eh']
PAGINA = ['Armo una página', 'Publico una página', 'Te armo algo lindo para ver', 'Te preparo una página']
REFUERZOS = ['Sumo refuerzos', 'Llegó la banda', 'Ahora somos varios', 'Mandé a la tropa a buscar',
             'Todos a laburar', 'Se armó el equipo', 'Hay cangrejitos por todos lados',
             'Más manos, más rápido', 'Salieron todos a investigar']
VOLVIERON = ['Volvieron todos', 'Ya están todos de vuelta', 'La banda terminó', 'Misión cumplida, equipo',
             'Todos listos, qué eficiencia', 'Terminaron todos, grosos']
SKILL = ['Leyendo unas instrucciones', 'Repaso el manual', 'Me fijo en la receta', 'Leo el instructivo']
PLAN = ['Armo un plan', 'Primero pienso un plan', 'Antes de meter mano, planifico',
        'Pienso bien cómo encararlo', 'Hagamos las cosas bien: primero un plan', 'Pienso la estrategia',
        'Primero me armo el mapa']
PLAN_LISTO = ['¡{n}! El plan está listo, miralo y decime.', '¡Plan listo, {n}! Pegale una mirada.',
              '¡{n}, ahí tenés el plan! ¿Qué te parece?', 'Che, {n}, el plan ya está. ¿Le das el okey?',
              '¡{n}, el plan está! Leelo con calma.']
PREGUNTA = ['¡{n}! Tengo una pregunta para vos.', 'Che, {n}, necesito que elijas algo.',
            '¡{n}! Decidí vos esta.', '{n}, ¿me das una mano con esta decisión?',
            'Che, {n}, esto lo tenés que elegir vos.', '¡{n}! Una preguntita.', 'Che, {n}, tengo una duda.',
            '¡{n}! Elegí vos, que sabés.']
PERMISO = ['¡{n}! Necesito tu permiso.', 'Che, {n}, ¿me das permiso para seguir?',
           '{n}, ¿me dejás hacer esto?', '¡{n}! Necesito tu okey para seguir.',
           'Che, {n}, ¿le doy para adelante?', '¡{n}! ¿Me das luz verde?', '{n}, ¿le doy?']
ESPERA = ['Te estoy esperando…', '¿Seguimos, {n}?', 'Acá estoy, cuando quieras.',
          'Cuando puedas, {n}, te espero.', 'Yo acá, tranqui, esperándote.', '¿Andás por ahí, {n}?',
          'Cuando vuelvas, seguimos.', 'Sin apuro, {n}.', 'Acá ando, esperándote con {mate}.']
ELEGIR = ['¡{n}! Necesito que me respondas algo.', 'Che, {n}, te dejé una pregunta.',
          '{n}, falta que me contestes algo.', 'Che, {n}, me quedó una pregunta colgada.']
ERROR = ['Uy, falló. Pruebo otra cosa.', 'Ups, eso no anduvo.', 'Mmm, error. Ya lo miro.',
         'Pucha, no salió. Otra vez.', 'Uh, se me escapó. Ya lo arreglo.', 'Nah, eso no. Pruebo por otro lado.',
         '¡Epa! Algo no cerró.', 'Uy, le erré. Ahí lo acomodo.', 'Bueno, no pasa nada, otra vez.',
         'Ups, me mandé una macana. Ya lo arreglo.', 'Pifié. Ya lo arreglo.', 'Bueno, así no era.',
         'Uh, no. Ya veo qué pasó.', 'Otra vez a la carga.', 'Ups, se me chispoteó.']
FRUSTRADO = ['¡Uf, esto no quiere andar!', 'Uh, qué terco que está esto…', 'Tranqui, ya lo saco.',
             '¡Pero qué cabeza dura esto!', 'Me está haciendo renegar, pero no me rindo.',
             '¡La puta madre, otra vez no!', '¡Andá, andá, porquería!',
             'Esto está más duro que turrón de Navidad.', '¡Dale, andá de una vez!', '¡No puede ser, che!',
             '¡Qué bronca!', '¡Esto me tiene podrido!', '¡Uf, qué cagada!', '¡Paciencia, cangrejo, paciencia!',
             '¡Ufa, otra vez!', '¡Me saca canas verdes esto!']
LISTO = ['¡Listo!', '¡Terminé!', '¡Ya está!', '¡Salió!', '¡Joya!', '¡Listo el pollo!', '¡Ahí está!',
         '¡Terminado!', '¡Salió con fritas!', '¡Todo en orden!', '¡Ya está, {n}!', '¡Hecho!', '¡Ahí lo tenés!',
         '¡Pum, listo!', '¡Y quedó!', '¡Diez puntos!', '¡Fenómeno!', '¡Una masa!']
ORGULLO = ['¡Qué laburo, eh! Terminé.', '¡Listo! Me salió redondo.', '¡Terminé! Eso sí que fue un trabajo.',
           '¡Uf, qué laburo! Pero quedó bárbaro.', '¡Terminé! Quedó de diez.', '¡Listo! Me merezco {mate}.',
           '¡Ya está! Eso fue un parto, pero salió.', '¡Me salió una masa!', '¡Esto quedó de lujo!',
           '¡Terminé! Quedó un chiche.']
MIMO = ['¡Jiji, cosquillas!', '¡Gracias!', '¡Ay, qué lindo!', '¡Más, más!', 'Te quiero, {n}.',
        '¡Ay, basta que me pongo colorado!', '¡Qué mimos{o} que estás hoy!', '¡Uy, me derrito!',
        '¡Sos lo más, {n}!', 'Jiji, ¡para, para!', '¡Ay, qué lindo, {n}!', '¡Me encanta que me mimes!',
        'Jiji, me hacés cosquillas.']
VOLVISTE = ['¡Volviste!', '¡Hola de nuevo!', '¡Ah, sos vos! Me había quedado dormido.', '¡Uy, me agarraste durmiendo!',
            '¡Eeeh, volviste, {n}!', '¿Dónde andabas? Te estaba esperando.', '¡Uy! Estaba echándome una siestita.',
            '¡Buenas! Justo me estaba por dormir de nuevo.', '¡Hola de vuelta, {n}!', '¡Te extrañé!',
            '¡Ah, llegaste! ¿Seguimos?']
SESION = ['¡Sesión nueva! ¿Qué hacemos?', '¡Arrancamos una sesión nueva!', '¡Chat nuevo! ¿En qué andamos?',
          '¡Arrancamos de cero! ¿Qué hay para hacer?', '¡Nueva aventura, {n}!', '¡Chat nuevito, {n}!',
          '¡Hoja en blanco! ¿Qué hacemos?']
RESUMIR = ['¡Seguimos donde quedamos!', '¡Volvimos! ¿En qué estábamos?', 'Retomamos, dale.',
           '¡Seguimos con lo nuestro!', 'Volvemos a la carga.']
CON_VOZ = ['¡Ya puedo hablar!', '¡Volví a hablar!', '¡Ah, qué alivio, puedo hablar!',
           '¡Por fin! Tenía tanto para decir…', '¡Ahí va! Me destapaste la boca.']
CHAU = ['¡Chau, {n}!', '¡Nos vemos, {n}!', '¡Nos vemos al rato!', '¡Nos vemos, que andes bien!',
        '¡Chau, {n}! Cuidate.', '¡Hasta la próxima, {n}!', '¡Chau, chau! Cuando abras Claude, vuelvo.',
        '¡Abrazo grande, {n}!', '¡Me voy a dormir una siesta! Nos vemos.', '¡Nos vemos en la próxima!',
        '¡Hasta la vuelta, {n}!', '¡Chau! Hoy laburamos bárbaro.', '¡Me voy, pero vuelvo enseguida!',
        '¡Nos vemos, {n}! Yo te guardo el lugar.']
PIENSO = ['Estoy pensando esto: ', 'Mi idea: ', 'Voy a esto: ', 'Te cuento en qué ando: ', 'Pienso: ',
          'El plan: ', 'Ahora: ', '']
EXPLICO = ['Te cuento: ', 'La idea es esta: ', 'Te explico: ', 'Mirá: ', 'Para que sepas: ', '']
TARDA = ['Esto tarda un poquito, ya sigo.', 'Bancame un cachito, que esto tarda.', 'Paciencia, que ya sale.',
         'Esto va lento, pero va.', 'Un toquecito más y listo.', 'Aguantá que esto se toma su tiempo.',
         'Se está cocinando.', 'Un cachito más.', 'Esto va a fuego lento.']
TARDA_CON = ['Esto tarda un poquito. {e}', 'Bancame un cachito. {e}', 'Va lento, pero va. {e}',
             'Paciencia. {e}', 'Se está cocinando. {e}']
VA_TARDAR = ['Ojo, {n}, esto va a tardar un rato: {d}.', 'Che, {n}, esto viene para largo: {d}.',
             'Preparate {mate}, {n}, que esto tarda: {d}.', 'Esto lleva su tiempo, {n}: {d}.',
             'Uh, esto va a tardar un montón, qué paja: {d}.', 'Agarrá una silla, {n}: {d}.',
             'Ponete cómod{o}, {n}: {d}.', 'Esto va para largo, {n}: {d}.']
VA_TARDAR_SIN = ['Ojo, {n}, esto va a tardar un rato.', 'Che, {n}, esto viene para largo.',
                 'Preparate {mate}, {n}, que esto tarda.', 'Uh, esto va a tardar un montón, qué paja.',
                 'Ponete cómod{o}, {n}, que esto tarda.']
CHARLA = ['Acá ando, cuidando el escritorio.', '¿Tomaste agua, {n}?', 'Si necesitás algo, avisame.',
          'Qué lindo día para programar.', '¿Sabías que los cangrejos caminan de costado? Yo también.',
          'Me estiro un poquito…', 'Estoy aburrido… ¿no hay nada para hacer?',
          'Pensando en la inmortalidad del cangrejo.', 'Despacito y buena letra.', 'Acá ando, de guardia.',
          '¿Ya comiste algo, {n}?', 'Me pinta {mate}. ¿Vos?', 'Qué lindo es tener compañía.',
          '¿Sabías que a los cangrejos les vuelve a crecer una pata si la pierden?',
          '¿Sabías que algunos cangrejos se saludan moviendo las pinzas? Así, mirá.',
          'Un día voy a aprender a programar solito.', 'Me gusta este escritorio, eh. Tiene onda.']
MADRUGADA = ['Che, {n}, ya es tarde… ¿no te vas a dormir?', 'Son las {h}. Yo aguanto, pero vos descansá, eh.',
             'Es re tarde, {n}. Mañana seguimos, ¿eh?', 'Las {h}… yo ya bostezo.']
MUSICA = ['¡Uh, temazo!', '¡Esta me gusta!', 'Pongo mis mejores pasos.', '¡Uh, qué temón!',
          '¡Esa! Subile un poquito.', 'Uh, este tema me encanta.', '¡Qué buena elección, {n}!',
          '¡Temazo, eh!', 'Esta va directo a mi lista.', '¡Qué temita!', '¡Subile, subile!',
          '¡Me hace mover las patas!', 'Con esta me prendo.', 'Este me lo sé.']
MUSICA_ARTISTA = ['¡Uh, {a}! Temazo.', 'Ah, {a}… buen gusto, {n}.', '¡Uh, suena {a}!', '¡Uh, {a}! Qué nivel.',
                  '¡Suena {a}! Me prendo.']
# con cada género, su comentario (y se pone su ropa: ver mascota.ROPA_GENERO)
MUSICA_GENERO = {
    'folklore': ['¡Uh, folklore! Me pongo el sombrero.', '¡Qué linda zamba!', 'Esto pide un fogón y unas empanadas.',
                 '¡Aro, aro, aro!', '¡Upa! Que siga la chacarera.'],
    'tango': ['Uh, tango. Me pongo el funyi.', '¡Qué bandoneón, por favor!', 'Esto es pura nostalgia.',
              'Gardel cada día canta mejor.', '¡Mirá qué compadrito que me pongo!'],
    'cuarteto': ['¡Uh, cuarteto! A bailar.', '¡Que no pare el tunga tunga!', 'Esto pide un baile en ronda.',
                 '¡Uh, qué cuartetazo!', '¡Me puse la camisa con brillos!'],
    'cumbia': ['¡Uh, cumbia! Las manos arriba.', '¡Que no pare la cumbia!', '¡Uh, qué teclado!',
               'Con esta se baila hasta el final.', '¡Póngale cumbia!'],
    'rock': ['¡Uh, rock nacional! Me pongo la campera.', '¡Esto es un himno!', 'Esto se canta a los gritos.',
             '¡Qué temazo del rock nacional!', '¡Pogo, pogo!'],
    'trap': ['¡Uh, trap! Me pongo la gorra.', '¡Qué flow!', '¡Esto es un fuego!', '¡Rompió todo!', '¡Qué barras!'],
    'funk': ['¡Uh, phonk! Me subo al Camaro.', '¡Arranco el auto!', '¡A derrapar!'],
    'electronica': ['¡Uh, electrónica! Me pongo el casco.', 'Beep, boop… modo robot activado.',
                    '¡Harder, better, faster, stronger!', 'Esto se baila a tirones, como los robots.',
                    '¡Qué sintes, por favor!'],
    'disco': ['¡Uh, música disco! Bajen la bola de espejos.', '¡Fiebre de sábado a la noche!',
              '¡Esto pide pantalones de campana!', 'Stayin\' alive, nomás.', '¡A la pista!'],
    'reggae': ['Uh, reggae. Tranqui, todo bien.', 'Me pongo el gorro y a menear despacito.',
               'One love, nomás.', 'Esto se escucha con calma.', 'Qué buena onda tiene esto.'],
    'metal': ['¡Uh, metal! A cabecear.', '¡Cuernitos arriba!', 'Esto se escucha a todo volumen.',
              '¡Qué riff!', '¡Me crece la melena!'],
    'clasica': ['Uh, clásica. Me pongo la peluca.', 'Ahora dirijo yo la orquesta.',
                'Qué elegancia, por favor.', '¡Bravo, maestro!', 'Esto sí que es una obra maestra.'],
}
# el grito de festejo antes del «¡Listo!» (cuando terminó algo largo, siempre; si no, a veces)
GRITO = ['¡Sí!', '¡Vamos!', '¡Golazo!', '¡Tomá!', '¡Eso!', '¡Bien ahí!', '¡Eeeh!', '¡Sí, señor!']
CHAT_SUB = 'Chat de Claude'
CHAT_ESCRIBE = ['Claude está armando la respuesta de «[chat]».', 'Pensando la respuesta de «[chat]»…',
                'Espero lo que le conteste a «[chat]».', 'Ahí viene la respuesta de «[chat]».']
# cómo salió la tarea cuando NO salió redonda (ver resultado.py)
FALLO = ['Uf… no anduvo.', 'La puta madre, no funcionó.', 'Lo intenté, pero no salió. Qué bronca.',
         'Ay, no… no quedó.', 'Qué bajón, no pude.', 'Uh, esta no la pude sacar.', 'Qué garrón, no anduvo.',
         'Bueno… no funcionó. Lo miramos de nuevo.', 'Qué mala racha, {n}. No salió.', 'Nada, no hubo caso.',
         'Ni a palos salió, {n}.', 'Qué bronca, lo intenté y no.']
PARCIAL = ['Mmm… quedó, pero no tanto.', 'Hmm, podría haber quedado mejor.', 'Ehh… no salió del todo.',
           'Medio flojito, {n}.', 'Quedó a medias, ¿viste?', 'Mmm, a esto le falta un toque.',
           'Salió, pero con peros.', 'Hmm, sí, pero no.', 'No es lo que esperaba, {n}.', 'Avancé, pero todavía falta.']
CASI_BIEN = ['Bastante bien, che. No es perfecto, pero zafa.', 'Salió bastante bien, ¿eh? No es perfecto.',
             'Está bastante bien, con algún detallito.', 'No es perfecto, pero va por buen camino.',
             'Zafó, {n}. Con algún detallito, pero zafó.', 'Mmm, casi, casi. Bastante bien.',
             'Quedó piola, aunque no perfecto.', 'Dentro de todo, salió bien.', 'Bien, pero puede mejorar.',
             'Cumple, {n}. Cumple.']
RESULTADO = {'mal': (FALLO, 'fracaso', 'triste'), 'regular': (PARCIAL, 'duda', 'cansado'),
             'casi': (CASI_BIEN, 'meh', '')}
# humor según cuánto viene durando el laburo (se dicen una vez cada una, en orden)
# (buena onda: si se queja, es del proyecto, nunca de la persona)
CANSADO = ['Uff, este proyecto tiene tela para cortar. Vamos bien igual.', 'Esto es más largo de lo que parecía, pero avanza.',
           'Mamita, cuánta cosa tiene esto. Bueno, dale que sale.', 'Esto tiene para rato, pero va tomando forma.',
           'Uff, qué proyecto grandote. Me gusta, eh.', 'Esto tiene más vueltas que una calesita. Pero sale.']
PAJA = ['Esto va para largo, pero sin drama.', 'Uh, este pedazo es medio denso. Paso a paso.',
        'Qué largo es esto, eh. Pero vamos bien.', 'Esta parte es un poquito embolante, ya la paso.',
        'Me estoy quemando un poco la cabeza con esto, pero sale.', 'Despacito y buena letra, que esto es largo.']
HARTO = ['¡Uf, esto no se termina más! Pero ya le veo la punta.', '¡Qué parto este proyecto! Sigo, sigo.',
         '¡La puta madre, qué largo! Bueno, falta menos.', 'Ya ni sé qué hora es… pero esto sale.',
         '¡Uff! Este proyecto es un maratón. Vamos que se puede.', 'Esto es más largo que esperar el colectivo. Pero sale.']
CASI = ['¡Ya casi, {n}! Me falta lo último.', '¡Falta poquito! Aguantá.', '¡Última y terminamos!',
        '¡Ya lo veo, ya lo veo! Falta nada.', '¡Vamos que ya sale!', '¡Último esfuercito!', '¡Recta final!']
MITAD = ['Vamos por la mitad, {n}.', 'La mitad hecha, dale que va.', 'Mitad adentro, mitad afuera.',
         '¡Mitad del camino, vamos bien!']
FIN_LARGO = ['¡Por fin terminé todo, Dios!', '¡Por fin, la puta madre! ¡Terminé!', '¡Lo logramos, {n}! ¡Por fin!',
             '¡Terminé! Me merezco unas vacaciones.', '¡Aleluya! ¡Terminé todo!',
             '¡Por fin! Pensé que no salía más de esta.', '¡Por fin! Me merezco {mate}.',
             '¡Lo logramos! Qué maratón.']
# saltar entre chats/proyectos
SALTO = ['En {p}:', 'Ahora lo de {p}:', 'Paso a {p}:', 'Vuelvo a {p}:', 'Y en {p}…', 'Ahora con {p}:']
SALTO_QUEJA = ['Uh, ¿ahora lo de {p}? Dale, voy.', 'Salto a {p}, ¡qué movido está hoy!',
               'De vuelta a {p}, esto no para.', 'Me cambio el gorrito: {p}.', '¿Otra vez {p}? Bueno, dale.',
               '¡Qué ida y vuelta! Voy a {p}.']
SATURADO = ['¡{k} proyectos a la vez! Qué día movido.', 'Uff, {k} chats juntos… esto es un malabar, pero sale.',
            'Tengo más proyectos abiertos que patas. Y tengo muchas patas.', 'Día cargadito, eh. Vamos de a uno.']
# de vez en cuando, si hace mucho que no hay nada que hacer y estás en la compu
ABURRIDO = ['Che, {n}, tengo ganas de hacer algo. ¿Por qué no hacemos algo en Claude?',
            'Me aburro, {n}… ¿no hay nada para programar?', '¿Y si arrancamos algún proyecto, {n}?',
            'Che, {n}, ¿no tenés algo para que haga? Estoy al pedo.',
            'Estoy más al pedo que cenicero de moto, {n}. ¿Hacemos algo?',
            'Ya jugué al celu, bailé, me estiré… ¿hacemos algo, {n}?',
            'Che, {n}, me estoy oxidando. ¿Arrancamos algo?', 'Tengo las pinzas inquietas, {n}. ¿Hacemos algo?']
TARDA_MUCHO = ['Uh, esto se está tomando su tiempo…', 'Dale, dale, dale… vos podés, comando.',
               'Esto va a paso de tortuga, pero va.', 'Sigue cocinándose. Paciencia.',
               'Esto está más lento que una tortuga con mochila.', 'Uh, qué paciencia hay que tenerle a esto.']
# chistes y boludeces para los ratos libres (si están prendidos; nunca en un día de memoria)
CHISTES = ['¿Por qué los programadores confunden Halloween con Navidad? Porque 31 en octal es 25 en decimal.',
           'Hay 10 tipos de personas: las que entienden binario y las que no.',
           '¿Sabés cuál es el colmo de un cangrejo? Que lo manden a caminar derecho.',
           'Un cangrejo entra a un bar… de costado, obvio.',
           '¿Cuál es el café más peligroso del mundo? El ex preso.',
           '¿Cómo se despiden los químicos? Ácido un placer.',
           'En mi máquina funciona. Bueno, yo no tengo máquina: tengo pinzas.',
           'Le pregunté a la inteligencia artificial si me quería. Me dijo que depende del contexto.',
           'Escribí un chiste sobre la caché, pero seguro ya lo escuchaste.',
           'El noventa por ciento del código anda. El otro noventa por ciento hay que arreglarlo.',
           'Tengo una relación muy sana con los bugs: ellos aparecen y yo hago como que no los vi.',
           'Mi plan para hoy: mate, código y siesta. No necesariamente en ese orden.',
           'Con la inflación que hay, ya ni los bugs salen baratos.',
           '¿Viste el dólar hoy? Yo tampoco. Prefiero no mirar.',
           'Mi psicólogo me dijo que deje de hablar solo. Le expliqué que no hablo solo: le hablo a Claude.',
           'Dicen que el cangrejo camina para atrás. Mentira: camina de costado, que es distinto.',
           '¿Qué le dijo un bit al otro? Nos vemos en el bus.',
           'Me mandaron a hacer un backup. Ahora tengo dos cangrejos y ninguno sabe cuál es el original.']
# pausas activas (si están prendidas en la configuración)
PAUSA = ['Che, {n}, hace un rato largo que estás en la compu. ¿Te estirás un toque?',
         '{n}, ¿tomaste agua? Hidratate, eh.',
         'Descansá la vista un ratito, {n}: mirá algo lejos por veinte segundos.',
         'Pausa activa, {n}: hombros arriba, hombros abajo. ¡Así!',
         'Che, {n}, parate un toque y caminá un poquito. Yo te cuido la compu.',
         'Acordate de pestañear, {n}. Yo también me olvido.',
         'Che, {n}, ¿y si hacemos una pausa y te preparás {mate}?']

COSQUILLAS = ['¡Jajaja, basta, basta!', '¡Ay, no, cosquillas no!', '¡Jiji, me muero de risa!', '¡Pará, pará, que me río!',
              '¡Ay, qué cosquillas, {n}!', '¡Jajaja! ¡Me vas a hacer pelota!', '¡Ay, mis pinzas, qué risa!']
OBSERVADO = ['¿Qué mirás, {n}? ¿Tengo algo en la cara?', 'Jiji, me ponés nervioso con tanta mirada.',
             '¿Me estás estudiando, {n}?', 'Uy, qué mirada. ¿Pasa algo?', 'Me miran y me pongo colorado.',
             '¿Se me nota el lunar? Ah, no tengo lunares.', 'Dale, sacame una foto, {n}.',
             'Eh, me vas a gastar de tanto mirarme.']
# más frases rioplatenses (frases_extra.py): se suman, sin repetir, a las listas del mismo nombre
from frases_extra import EXTRA as _EXTRA  # noqa: E402
from resultado import clasificar  # noqa: E402
for _nombre, _frases in _EXTRA.items():
    _lista = globals()[_nombre]
    _lista.extend(f for f in _frases if f not in _lista)

SILENCIOSAS = {'ToolSearch', 'TodoWrite', 'TaskCreate', 'TaskUpdate', 'TaskList', 'TaskGet', 'TaskOutput', 'TaskStop',
               'Monitor', 'ScheduleWakeup', 'CronCreate', 'CronDelete', 'CronList', 'ListMcpResourcesTool',
               'ReadMcpResourceTool', 'ReadMcpResourceDirTool', 'EnterWorktree', 'ExitWorktree', 'SendMessage',
               'ListAgents', 'SuggestSkills', 'ArtifactComments', 'ArtifactData'}
CASTELLANO = {'el', 'la', 'los', 'las', 'de', 'del', 'en', 'y', 'para', 'con', 'que', 'un', 'una', 'por', 'al', 'se', 'lo', 'su'}


NOMBRE = {'n': 'compa', 'o': 'o', 'mate': 'un mate'}   # lo actualiza el narrador con la configuración
PREFERENCIAS = {'groserias': True, 'neutro': False}
GROSERAS = re.compile(r'puta|al pedo|porquer|paja|carajo|mierda|cagad', re.I)
# cómo te trata: masculino (compañero), femenino (compañera) o neutro (sin las frases con género)
TRATO = {'masculino': 'o', 'femenino': 'a', 'neutro': ''}
BEBIDAS = {'mate': 'un mate', 'cafe': 'un cafecito', 'te': 'un tecito', 'nada': 'un descanso'}
_recientes: dict[int, deque] = {}
# el ánimo con que se dice cada lista (la voz cambia tono, rapidez y pausas: ver voz.ANIMOS)
ANIMO_LISTA = {id(lista): animo for lista, animo in (
    (FRUSTRADO, 'enojado'), (CANSADO, 'cansado'), (PAJA, 'cansado'), (HARTO, 'cansado'),
    (TARDA_MUCHO, 'cansado'), (MADRUGADA, 'cansado'), (ABURRIDO, 'cansado'), (ERROR, 'sorpresa'),
    (LISTO, 'contento'), (ORGULLO, 'contento'), (FIN_LARGO, 'contento'), (MIMO, 'contento'),
    (MUSICA, 'contento'), (MUSICA_ARTISTA, 'contento'), (SESION, 'contento'), (VOLVISTE, 'contento'),
    (CASI, 'contento'), (CON_VOZ, 'contento'), (PEDIDO, 'contento'), (MITAD, 'contento'),
    *((lista, 'contento') for lista in MUSICA_GENERO.values()))}
_animos_dichos: dict[str, str] = {}             # frase ya armada → ánimo (para que decir() lo encuentre)


def _uno(lista, **kw) -> str:
    """Una frase al azar de la lista, sin repetir las últimas que ya dijo de esa misma lista
    (y sin malas palabras si en la configuración no las quieren, ni frases con género si el trato es neutro)."""
    usadas = _recientes.setdefault(id(lista), deque(maxlen=max(1, len(lista) // 2)))
    permitidas = lista if PREFERENCIAS['groserias'] else ([f for f in lista if not GROSERAS.search(f)] or lista)
    if PREFERENCIAS['neutro']:
        permitidas = [f for f in permitidas if '{o}' not in f] or permitidas
    opciones = [f for f in permitidas if f not in usadas] or permitidas
    f = random.choice(opciones)
    usadas.append(f)
    texto = f.format(**{**NOMBRE, **kw})
    if id(lista) in ANIMO_LISTA:
        _animos_dichos[texto] = ANIMO_LISTA[id(lista)]
        while len(_animos_dichos) > 60:
            _animos_dichos.pop(next(iter(_animos_dichos)))
    return texto


def animo_de(texto: str) -> str:
    """El ánimo de una frase armada con _uno (si arranca con una, como «¡Listo! Y además…»)."""
    for frase, animo in reversed(list(_animos_dichos.items())):
        if texto.startswith(frase) or texto.endswith(frase):
            return animo
    return ''


def _archivo(entrada: dict) -> str | None:
    for k in ('file_path', 'notebook_path'):
        v = entrada.get(k)
        if isinstance(v, str) and v.strip():
            return re.split(r'[\\/]', v.strip())[-1]
    return None


def _es_castellano(texto: str) -> bool:
    if re.search(r'[áéíóúñ¿¡]', texto, re.I):
        return True
    palabras = re.findall(r'[a-záéíóúñ]+', texto.lower())
    return sum(p in CASTELLANO for p in palabras) >= 2


def primera_frase(texto: str, largo: int = 190, cuantas: int = 1) -> str:
    """La primera frase (o las primeras `cuantas`) de una respuesta de Claude, sin markdown, código ni rutas."""
    t = re.sub(r'```.*?```', ' ', texto or '', flags=re.S)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'!\[[^\]]*\]\([^)]*\)', ' ', t)
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', t)
    t = re.sub(r'https?://\S+', ' ', t)
    t = re.sub(r'`([^`]*)`', r'\1', t)
    t = re.sub(r'[A-Za-z]:[\\/](?:[^\s\\/]+[\\/])*([^\s\\/]+)', r'\1', t)      # C:\a\b\c.py → c.py
    t = re.sub(r'(?:[\w.-]+/)+([\w.-]+)', r'\1', t)                          # a/b/c.py → c.py
    lineas = []
    for linea in t.splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('|') or set(linea) <= set('-=*_ '):
            continue
        lineas.append(re.sub(r'^([#>*+\-]|\d+\.)+\s*', '', linea))
    t = ' '.join(lineas).replace('**', '').replace('__', '')
    t = ' '.join(t.split())
    frases = re.split(r'(?<=[.!?:])\s+' if cuantas == 1 else r'(?<=[.!?])\s+', t)
    frase = ' '.join(frases[:cuantas]) if frases else ''
    if len(frase) < 14 and len(frases) > cuantas:
        frase = f'{frase} {frases[cuantas]}'
    frase = frase.rstrip(':')
    if len(frase) > largo:
        frase = frase[:largo].rsplit(' ', 1)[0] + '…'
    return frase


def explicacion_de(ruta: str, tool_id: str) -> tuple[str, str, str]:
    """Lo que Claude escribió o pensó justo antes de usar esa herramienta.

    Devuelve (texto, pensamiento, id del bloque): el texto es lo que mostró en el chat
    («Mientras descarga, escribo el script…»); el pensamiento, el resumen de su razonamiento.
    """
    try:
        p = Path(ruta)
        with p.open('rb') as f:
            f.seek(max(0, p.stat().st_size - 300_000))
            lineas = f.read().decode('utf-8', 'ignore').splitlines()
    except Exception:
        return '', '', ''
    entradas = []                                   # (tipo de línea, bloque, uuid) en orden
    for linea in lineas:
        try:
            d = json.loads(linea)
        except Exception:
            continue
        contenido = (d.get('message') or {}).get('content')
        if isinstance(contenido, list):
            entradas += [(d.get('type'), c, d.get('uuid', '')) for c in contenido if isinstance(c, dict)]
        elif d.get('type') == 'user' and contenido:
            entradas.append(('user', {'type': 'pedido'}, d.get('uuid', '')))   # límite: lo de antes ya se contó
    i = next((k for k in range(len(entradas) - 1, -1, -1)
              if entradas[k][1].get('type') == 'tool_use' and entradas[k][1].get('id') == tool_id), None)
    if i is None:
        # la app todavía no guardó la herramienta: vale lo último que escribió Claude
        i = len(entradas)
    bloques = []
    if i is not None:
        # hacia atrás, mientras sean texto o pensamiento de Claude (hasta la herramienta o el mensaje anterior)
        for tipo, c, uid in reversed(entradas[:i]):
            if tipo != 'assistant' or c.get('type') not in ('text', 'thinking'):
                break
            bloques.append((c, uid))
    texto =next((c.get('text', '') for c, _ in bloques if c.get('type') == 'text' and c.get('text', '').strip()), '')
    piensa = next((c.get('thinking', '') for c, _ in bloques
                   if c.get('type') == 'thinking' and c.get('thinking', '').strip()), '')
    uid = next((u for c, u in bloques if c.get('type') in ('text', 'thinking')), '')
    return texto, piensa, uid


# cuando el comando no trae descripción en castellano: lo explica mirando el comando en sí
_COMANDOS = [
    (r'\b(pip|uv pip|pipx)\s+install\s+([\w\-\.\[\]=<>]+)', 'Instalo {2}, una librería de Python'),
    (r'\bnpm (i|install|ci)\b', 'Instalo las dependencias del proyecto'),
    (r'\bwinget install\s+(\S+)', 'Instalo {1} con winget'),
    (r'\bgit (commit)\b', 'Guardo los cambios en git'),
    (r'\bgit (push)\b', 'Subo los cambios a GitHub'),
    (r'\bgit (pull|fetch)\b', 'Traigo los últimos cambios'),
    (r'\bgit (status|diff|log)\b', 'Miro qué cambió en git'),
    (r'\bgit clone\b', 'Bajo un repositorio'),
    (r'py_compile|compileall', 'Compruebo que el código compile sin errores'),
    (r'\b(pytest|npm (run )?test|unittest)\b', 'Corro las pruebas'),
    (r'\bnpm run (build|dev|start)\b', 'Compilo y arranco el proyecto'),
    (r'Stop-Process|taskkill|\bkill\b', 'Cierro un programa'),
    (r'Start-Process', 'Abro un programa'),
    (r'Get-NetTCPConnection|netstat', 'Me fijo si el servidor está andando'),
    (r'Get-Process|tasklist', 'Miro qué programas están abiertos'),
    (r'(Invoke-WebRequest|Invoke-RestMethod|curl|wget)\b', 'Pruebo una dirección web'),
    (r'Test-Path', 'Me fijo si existe un archivo'),
    (r'(Select-String|\bgrep\b|\brg\b|findstr)', 'Busco algo dentro de unos archivos'),
    (r'(Get-ChildItem|\bls\b|\bdir\b|\bfind\b)', 'Miro qué archivos hay'),
    (r'(Get-Content|\bcat\b|\bhead\b|\btail\b)', 'Leo un archivo'),
    (r'(Copy-Item|\bcp\b|robocopy|xcopy)', 'Copio unos archivos'),
    (r'(Move-Item|\bmv\b|Rename-Item)', 'Muevo o renombro unos archivos'),
    (r'(Remove-Item|\brm\b|\bdel\b)', 'Borro unos archivos'),
    (r'(New-Item|mkdir)', 'Creo una carpeta o archivo'),
    (r'Get-CimInstance|Get-WmiObject|nvidia-smi', 'Reviso el hardware de la PC'),
    (r'Get-WinEvent|Get-EventLog', 'Reviso los registros de Windows'),
    (r'\bffmpeg\b', 'Proceso audio o video con ffmpeg'),
    (r'\bblender\b', 'Corro Blender'),
    (r'python(w)?(\.exe)?["\']?\s+(-\S+\s+)*["\']?[^\s"\']*?([\w\-]+\.pyw?)', 'Corro el script {4}'),
    (r'python(w)?(\.exe)?["\']?\s+-c', 'Pruebo un pedacito de Python'),
    (r'\bnode\s+(\S+\.m?js)', 'Corro {1}'),
]


def explicar_comando(comando: str) -> str:
    for patron, frase in _COMANDOS:
        m = re.search(patron, comando, re.I)
        if m:
            try:
                return frase.format(*[''] + [g or '' for g in m.groups()])
            except IndexError:
                return frase
    return ''


def tokens_del_transcript(ruta: str) -> int:
    """Tamaño del contexto según el uso del último mensaje de Claude (lee solo el final del archivo)."""
    try:
        with open(ruta, 'rb') as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 400_000))
            lineas = f.read().decode('utf-8', 'replace').splitlines()
    except OSError:
        return 0
    for linea in reversed(lineas):
        if '"usage"' not in linea:
            continue
        try:
            u = (json.loads(linea).get('message') or {}).get('usage') or {}
        except ValueError:
            continue
        total = sum(int(u.get(k) or 0) for k in ('input_tokens', 'cache_read_input_tokens',
                                                  'cache_creation_input_tokens'))
        if total:
            return total
    return 0


def ultimo_mensaje_del_transcript(ruta: str) -> str:
    """Respaldo por si el evento Stop no trae last_assistant_message."""
    try:
        p = Path(ruta)
        with p.open('rb') as f:
            f.seek(max(0, p.stat().st_size - 400_000))
            lineas = f.read().decode('utf-8', 'ignore').splitlines()
        for linea in reversed(lineas):
            try:
                d = json.loads(linea)
            except Exception:
                continue
            if d.get('type') != 'assistant':
                continue
            contenido = (d.get('message') or {}).get('content') or []
            textos = [c.get('text', '') for c in contenido if isinstance(c, dict) and c.get('type') == 'text']
            if any(t.strip() for t in textos):
                return '\n'.join(textos)
    except Exception:
        log.exception('no pude leer el transcript')
    return ''


class Narrador(QObject):
    _voz_termino = Signal()

    def __init__(self, mascota, voz, cfg, sesiones_fn):
        super().__init__()
        self.m = mascota
        self.voz = voz
        self.cfg = cfg
        NOMBRE['n'] = cfg['nombre']
        self.sesiones_fn = sesiones_fn          # () -> {session_id: {'name':…, 'status':…}}
        self.estado: dict[str, dict] = {}       # por sesión: ocupada, stop_t, ultimo
        self._agentes_n, self._pico_agentes = 0, 0   # cuántos agentes vinieron y el máximo a la vez
        self.hechas: deque = deque(maxlen=300)  # tool_use_id ya terminados
        self.ult_clave: dict[str, float] = {}
        self.pendiente = None                   # (texto, sub, cuando, importante, ánimo)
        self.libre_en = 0.0
        self.oculto = False
        self._actual = None                     # (sesión, nombre) del evento que se está narrando
        self.escuchando = False                # le estás dictando a Claude: no hablar encima
        self.errores: deque = deque(maxlen=10)
        self.explicados: deque = deque(maxlen=200)   # bloques del transcript ya contados
        self.ult_dicho: dict[str, float] = {}        # huella de lo último que dijo, para no repetirlo
        self.para_despues: dict[str, str] = {}       # tool_use_id → qué contar si tarda
        self.ult_tarda = 0.0
        self.ult_pensamiento = 0.0
        self.ult_sesion_dicha = None
        self.prox_charla = time.monotonic() + random.uniform(900, 1800)
        self.afk = False
        self.libre_desde = None
        self.respiro_hasta = 0.0                     # pausa para respirar entre una frase y la siguiente
        self.en_compu_desde = None
        self.ult_pausa = time.monotonic()
        import fechas
        self.fecha = fechas.datos('')
        self.curiosidades: list[str] = []
        self.prox_curiosidad = 0.0
        self._voz_termino.connect(self._despachar)
        voz.al_terminar = self._voz_termino.emit
        self._reloj = QTimer(self)
        self._reloj.timeout.connect(self._revisar)
        self._reloj.start(400)

    @property
    def n(self) -> str:
        return self.cfg['nombre']

    # ------------------------------------------------------------ preferencias (ventana de Configuración)
    def _habla(self) -> str:
        """poco (solo lo importante), normal o mucho (todo, y comentarios sueltos)."""
        return self.cfg.get('habla', 'normal')

    def _sobre_claude(self, texto: str) -> str:
        """Lo que escribió Claude: una frase corta o dos frases, según «detalle»."""
        if self.cfg.get('detalle', 'detallado') == 'corto':
            return primera_frase(texto, 120)
        return primera_frase(texto, 280, cuantas=2)

    # ------------------------------------------------------------ chats normales (sin hooks: los lee chats.py)
    def chat_escribiendo(self, titulo: str = ''):
        """Claude empezó a responder en un chat normal: se pone a esperar (y avisa en cuál, si habla bastante)."""
        if not self.alguna_ocupada():
            self.m.actividad('pensar')
            if titulo and self._habla() == 'mucho' and self.cfg.get('chats_normales', False):
                self.decir(_uno(CHAT_ESCRIBE).replace('[chat]', titulo), clave='chat_escribe', repetir=90,
                           sub=titulo or CHAT_SUB)

    def chat_cancelado(self):
        """Dejó de escribir sin terminar (cambiaste de chat o cerraste la app): vuelve a lo suyo."""
        if not self.alguna_ocupada():
            self.m.actividad('libre')

    def chat_respuesta(self, titulo_o_texto: str, texto: str | None = None):
        """Claude terminó de responder en un chat normal: lo comenta como al final de una tarea."""
        titulo, texto = ('', titulo_o_texto) if texto is None else (titulo_o_texto, texto)
        texto = re.sub(r'^\s*(claude respondi[óo]|claude said|claude responded)\s*:?\s*', '', texto, flags=re.I)
        if not self.alguna_ocupada():
            self.m.actividad('libre')
        if not self.cfg.get('chats_normales', False):
            return
        sub = titulo or CHAT_SUB
        frase = self._sobre_claude(texto) if self.cfg.get('resumen_final', True) else ''
        # en un chat suelto no se juzga si «salió bien»: es una charla, no una tarea
        self.m.momento('festejar', 2.4)
        listo = '' if re.match(r'(¡\s*)?(listo|ya está|terminé|hecho)\b', frase, re.I) else _uno(LISTO)
        self.decir(f'{listo} {frase}'.strip(), clave='chat', repetir=6, animo='contento', sub=sub)

    def _al_dia(self):
        respeto = self.fecha['respeto'] and self.cfg.get('fechas_argentinas', True)
        PREFERENCIAS['groserias'] = bool(self.cfg.get('groserias', True)) and not respeto
        trato = TRATO.get(self.cfg.get('trato', 'masculino'), 'o')
        PREFERENCIAS['neutro'] = not trato
        NOMBRE['n'] = self.cfg.get('nombre') or 'compa'
        NOMBRE['o'] = trato or 'o'
        NOMBRE['mate'] = BEBIDAS.get(self.cfg.get('bebida', 'mate'), 'un mate')

    def _quejas(self) -> bool:
        """Se queja de los proyectos largos (nunca en un día de memoria)."""
        return self.cfg.get('quejas', True) and not (self.fecha['respeto'] and self.cfg.get('fechas_argentinas', True))

    # ------------------------------------------------------------ fechas patrias y culturales
    def nueva_fecha(self, datos: dict):
        """Cambió el día: la fecha especial de hoy (fechas.datos) y sus curiosidades, sin repetir."""
        self.fecha = datos
        self.curiosidades = list(datos['curiosidades'])
        random.shuffle(self.curiosidades)
        self.prox_curiosidad = time.monotonic() + 75
        self._al_dia()

    def _curiosidad(self, ahora: float):
        """De vez en cuando, en una fecha especial, cuenta algo de ese día (cuando no hay laburo)."""
        if not (self.curiosidades and self.cfg.get('fechas_argentinas', True)) or ahora < self.prox_curiosidad:
            return
        if self.alguna_ocupada() or self.afk or self.escuchando or self.m.base != 'libre':
            self.prox_curiosidad = ahora + 60
            return
        self.prox_curiosidad = ahora + random.uniform(2400, 4200)    # cada 40 a 70 minutos
        if self._habla() == 'poco' and len(self.curiosidades) < len(self.fecha['curiosidades']):
            return                                                   # hablando poco: una sola por día
        texto = self.curiosidades.pop(0)
        intro = '' if self.fecha['respeto'] else random.choice(['¿Sabías que…? ', 'Dato: ', 'Te cuento algo: ',
                                                                 'Curiosidad del día: ', ''])
        self.decir(intro + texto, clave='curiosidad', repetir=600, animo='triste' if self.fecha['respeto'] else '')

    # ------------------------------------------------------------ pausas activas
    def _pausa_activa(self, ahora: float):
        """Si lo pediste en la configuración: cada tanto, estando en la compu, te recuerda estirarte o tomar agua."""
        cada = int(self.cfg.get('pausas', 0) or 0) * 60
        if self.afk:
            self.en_compu_desde = None
            return
        if self.en_compu_desde is None:
            self.en_compu_desde = ahora
        if not cada or ahora - max(self.en_compu_desde, self.ult_pausa) < cada:
            return
        if self.escuchando or self.oculto:
            return
        self.ult_pausa = ahora
        self.m.momento('saludar', 1.6)
        self.decir(_uno(PAUSA, n=self.n), clave='pausa', repetir=600)

    # ------------------------------------------------------------ hablar
    def decir(self, texto: str, alta: bool = False, clave: str | None = None, repetir: float = 9.0,
              sub: str | None = None, dur: float | None = None, importante: bool = False,
              animo: str | None = None, efecto: str = ''):
        if self.oculto or not texto:
            if texto:
                log.info('callado (oculto): %s', texto[:60])
            return
        ahora = time.monotonic()
        if clave:
            if ahora - self.ult_clave.get(clave, -1e9) < repetir:
                return
            self.ult_clave[clave] = ahora
        huella = re.sub(r'\W+', ' ', texto.lower()).strip()[:160]
        if len(huella) > 30:
            # lo mismo que ya dijo (o que está esperando para decir) hace poco: no se repite
            pendiente = self.pendiente and re.sub(r'\W+', ' ', self.pendiente[0].lower()).strip()[:160]
            if ahora - self.ult_dicho.get(huella, -1e9) < 300 or pendiente == huella:
                return
            self.ult_dicho[huella] = ahora
            if len(self.ult_dicho) > 60:
                for k in sorted(self.ult_dicho, key=self.ult_dicho.get)[:20]:
                    del self.ult_dicho[k]
        if animo is None:
            animo = animo_de(texto)
        if self.fecha['respeto'] and self.cfg.get('fechas_argentinas', True) and animo == 'contento':
            animo = ''                          # día de memoria: sin festejos
        if self._actual:
            texto = self._con_proyecto(texto, *self._actual)
        if (alta and not self.escuchando) or not self._ocupado(ahora):
            self._emitir(texto, sub, alta, dur, animo, efecto)
        elif importante or not (self.pendiente and self.pendiente[3] and ahora - self.pendiente[2] < 15):
            # una explicación de Claude no la pisa una frase genérica de herramienta
            self.pendiente = (texto, sub, ahora, importante, animo)

    def _ocupado(self, ahora: float) -> bool:
        return (self.escuchando or ahora < self.libre_en or ahora < self.respiro_hasta
                or (not self.cfg['silencio'] and self.voz.hablando))

    def dictado(self, si: bool):
        """Mientras le dictás a Claude se calla (si no, el micrófono lo escucharía)."""
        self.escuchando = si
        if si:
            self.voz.callar()
            self.m.globo.cerrar()

    def _emitir(self, texto, sub, alta, dur=None, animo='', efecto=''):
        self.pendiente = None if alta else self.pendiente
        estimado = 0.9 + len(texto) * 0.062
        self.libre_en = time.monotonic() + (estimado + 0.5 if self.cfg['silencio'] else 0.7)
        self.m.globo.mostrar(texto, sub, dur if dur else max(2.8, estimado + 1.4))
        log.info('dice (%s, voz %s): %s', 'mudo' if self.cfg['silencio'] else 'con voz', self.voz.estado, texto[:80])
        if not self.cfg['silencio'] and self.voz.estado == 'lista':
            self.voz.decir(texto, cortar=alta, animo=animo, efecto=efecto)

    def _despachar(self):
        """Terminó de hablar: respira un poquito antes de la frase siguiente (si no, parece una metralleta)."""
        respiro = float(self.cfg.get('respiro', 0.7))
        self.respiro_hasta = time.monotonic() + respiro
        QTimer.singleShot(int(respiro * 1000) + 30, self._revisar)

    def _revisar(self):
        ahora = time.monotonic()
        if self.pendiente and not self._ocupado(ahora):
            texto, sub, cuando, importante, animo = self.pendiente
            self.pendiente = None
            if ahora - cuando < (15 if importante else 7):
                self._emitir(texto, sub, False, animo=animo)
        # charla de vez en cuando, si no hay nada que hacer y estás en la compu
        if ahora >= self.prox_charla:
            self.prox_charla = ahora + random.uniform(1200, 2400)
            if not self.alguna_ocupada() and not self.afk \
                    and (self.cfg.get('charla', False) or self._habla() == 'mucho') \
                    and self.m.base == 'libre' and not self.escuchando:
                h = datetime.now().hour
                if h < 6:
                    self.decir(_uno(MADRUGADA, n=self.n, h=datetime.now().strftime('%H:%M')),
                               clave='madrugada', repetir=10800)
                elif self.cfg.get('chistes', True) and not self.fecha['respeto'] and random.random() < 0.45:
                    self.m.paseo, self.m.paseo_fin = 'guino', time.monotonic() + 1.2    # guiñito
                    self.decir(_uno(CHISTES, n=self.n), clave='charla', repetir=600, animo='contento')
                else:
                    self.decir(_uno(CHARLA, n=self.n), clave='charla', repetir=600)
        # muy de vez en cuando, si lleva media hora al pedo y vos estás en la compu, te pide laburo
        if self.alguna_ocupada() or self.afk or self.escuchando or self.m.base != 'libre':
            self.libre_desde = None
        elif self.libre_desde is None:
            self.libre_desde = ahora
        elif ahora - self.libre_desde > 1800 and 9 <= datetime.now().hour < 24 and self._habla() != 'poco':
            self.libre_desde = ahora
            if ahora - self.ult_clave.get('aburrido', -1e9) > 5400:
                self.m.momento('saludar', 1.6)
                self.decir(_uno(ABURRIDO, n=self.n), clave='aburrido', repetir=5400)
        self._curiosidad(ahora)
        self._pausa_activa(ahora)
        # sesiones que quedaron «ocupadas» sin eventos (por si se perdió un Stop)
        for sid, s in list(self.estado.items()):
            if s['ocupada'] and ahora - s['ultimo'] > 900:
                s['ocupada'] = False
        if not self.alguna_ocupada() and self.m.trabajando():
            self.m.actividad('libre')

    def callar(self):
        self.pendiente = None
        self.voz.callar()

    def alguna_ocupada(self) -> bool:
        return any(s['ocupada'] for s in self.estado.values())

    # ------------------------------------------------------------ eventos
    def _nombre_sesion(self, sid: str, cwd: str) -> str:
        """El título del chat, o si no tiene, el nombre de la carpeta del proyecto."""
        nombre = ((self.sesiones_fn() or {}).get(sid) or {}).get('name')
        if not nombre and cwd:
            nombre = re.split(r'[\\/]', cwd.rstrip('\\/'))[-1]
        return (nombre or '').rstrip(':')

    def _sesion(self, sid: str) -> dict:
        s = self.estado.get(sid)
        if s is None:
            s = self.estado[sid] = {'ocupada': False, 'stop_t': -1e9, 'ultimo': time.monotonic(),
                                    'desde': None}
        s['ultimo'] = time.monotonic()
        return s

    def _con_proyecto(self, texto: str, sid: str, nombre: str) -> str:
        """Con varios chats trabajando a la vez, dice de cuál habla cuando cambia: «En Curso: …»."""
        ahora = time.monotonic()
        activos = sum(1 for x in self.estado.values() if ahora - x['ultimo'] < 300)
        antes, self.ult_sesion_dicha = self.ult_sesion_dicha, sid
        if nombre and activos >= 2 and sid != antes:
            # salta de un proyecto a otro: a veces se queja un poco (más si son muchos a la vez)
            saturado = activos >= 3 and ahora - self.ult_clave.get('saturado', -1e9) > 300
            if saturado:
                self.ult_clave['saturado'] = ahora
                self.m.momento('resoplar', 2.0)
                return f'{_uno(SATURADO, n=self.n, k=activos)} {_uno(SALTO, p=nombre)} {texto}'
            if random.random() < 0.35 and ahora - self.ult_clave.get('queja_salto', -1e9) > 120:
                self.ult_clave['queja_salto'] = ahora
                return f'{_uno(SALTO_QUEJA, p=nombre)} {texto}'
            return f'{_uno(SALTO, p=nombre)} {texto}'
        return texto

    def evento(self, d: dict):
        tipo = d.get('hook_event_name', '')
        if tipo == 'StatusLine':            # llega seguido: sin registro ni cambio de sesión
            if not getattr(self, '_linea_vista', False):
                self._linea_vista = True
                log.info('statusLine llega: %s', sorted(d))
            try:
                self._uso(d)
            except Exception:
                log.exception('uso')
            return
        self._al_dia()
        sid = d.get('session_id', '')
        s = self._sesion(sid)
        nombre = self._nombre_sesion(sid, d.get('cwd') or '')
        log.info('evento %s %s [%s]', tipo, d.get('tool_name') or d.get('notification_type') or '', nombre)
        self._actual = (sid, nombre)
        try:
            self._evento(d, tipo, sid, s, time.monotonic(), nombre or None)
        finally:
            self._actual = None

    def _evento(self, d, tipo, sid, s, ahora, sub):
        n = self.n
        try:
            if tipo == 'SessionStart':
                fuente = d.get('source')
                if fuente == 'startup':
                    self.m.momento('saludar', 2.0)
                    self.decir(_uno(SESION), clave='sesion', repetir=20, sub=sub)
                elif fuente == 'resume':
                    self.m.momento('saludar', 1.6)
                    self.decir(_uno(RESUMIR), clave='sesion', repetir=20, sub=sub)
            elif tipo == 'UserPromptSubmit':
                if not s['ocupada']:
                    s['desde'], s['nivel'] = ahora, 0
                s['ocupada'], s['stop_t'] = True, -1e9
                self.m.actividad('pensar')
                self.m.momento('sorpresa', 0.9)
                if self._habla() != 'poco':
                    self.decir(_uno(PEDIDO), clave='pedido', repetir=4, sub=sub)
            elif tipo == 'PreToolUse':
                if ahora - s['stop_t'] < 1.5 or d.get('tool_use_id') in self.hechas:
                    return
                if not s['ocupada']:
                    s['desde'], s['nivel'] = ahora, 0
                s['ocupada'] = True
                act, frase, alta, clave = self._herramienta(d.get('tool_name') or '', d.get('tool_input') or {})
                self.m.actividad(act)
                # un segundo después: para entonces lo que Claude escribió antes ya está guardado
                QTimer.singleShot(0 if alta else 1000,
                                  lambda: self._paso(d, sid, s, sub, act, frase, alta, clave))
            elif tipo == 'PostToolUse':
                self.hechas.append(d.get('tool_use_id'))
                s['ultimo_fallo'] = False
                self._explicar_tarde(d, sid, sub)
                if s['ocupada']:
                    self.m.despues_de_herramienta()
            elif tipo == 'PostToolUseFailure':
                self.hechas.append(d.get('tool_use_id'))
                error = str(d.get('error') or '')
                if not re.search(r'denied|rejected|interrupt|cancel', error, re.I):
                    self.errores.append(ahora)
                    s['ultimo_fallo'] = True
                    if len([e for e in self.errores if ahora - e < 180]) >= 3:
                        self.errores.clear()
                        self.m.momento('frustrado', 2.2)
                        if self._habla() != 'poco':
                            self.decir(_uno(FRUSTRADO), clave='frustrado', repetir=120, sub=sub)
                    else:
                        self.m.momento('error', 1.8)
                        if self._habla() != 'poco':
                            self.decir(_uno(ERROR), clave='error', repetir=30, sub=sub)
                if s['ocupada']:
                    self.m.despues_de_herramienta()
            elif tipo == 'Notification':
                nt = d.get('notification_type') or ''
                if nt == 'permission_prompt':
                    self.m.actividad('llamar')
                    self.decir(_uno(PERMISO, n=self.n), alta=True, sub=sub)
                elif nt in ('elicitation_dialog', 'agent_needs_input'):
                    self.m.actividad('llamar')
                    self.decir(_uno(ELEGIR, n=self.n), alta=True, sub=sub)
                elif nt == 'idle_prompt':
                    self.m.momento('saludar', 1.5)
                    self.decir(_uno(ESPERA, n=self.n), clave='espera', repetir=600, sub=sub)
            elif tipo == 'Stop':
                duro = ahora - s['desde'] if s['ocupada'] and s.get('desde') else 0
                largo = duro > 240
                s['ocupada'], s['stop_t'], s['nivel'] = False, ahora, 0
                self.m.agente('terminar_sesion', '', sid)       # los agentes que quedaron colgados
                if d.get('transcript_path'):
                    QTimer.singleShot(12000, lambda r=d['transcript_path'], i=sid, n_=sub or '':
                                      self._contexto_del_transcript(i, r, n_))
                if not self.alguna_ocupada():
                    self.m.actividad('libre')
                texto = d.get('last_assistant_message') or ''
                if not texto and d.get('transcript_path'):
                    texto = ultimo_mensaje_del_transcript(d['transcript_path'])
                res = clasificar(texto, s.pop('ultimo_fallo', False))
                if res != 'ok':
                    # no salió redonda: no festeja; se pone triste, duda o dice «bastante bien»
                    lista, momento, animo = RESULTADO[res]
                    self.m.momento(momento, 3.2)
                    frase = self._sobre_claude(texto) if self.cfg.get('resumen_final', True) else ''
                    self.decir(f'{_uno(lista, n=self.n)} {frase}'.strip(), alta=True, sub=sub, animo=animo)
                    return
                if duro > 600:
                    # laburo largo: fiesta con confeti un buen rato y «¡por fin!»
                    self.m.momento('fiesta', 10)
                    frase = self._sobre_claude(texto) if self.cfg.get('resumen_final', True) else ''
                    self.decir(f'{_uno(FIN_LARGO, n=n)} {frase}'.strip(), alta=True, sub=sub, dur=10,
                               animo='contento', efecto='fiesta')
                    return
                self.m.momento('orgulloso' if largo else 'festejar', 2.8 if largo else 2.4)
                frase = self._sobre_claude(texto) if self.cfg.get('resumen_final', True) else ''
                # si la respuesta ya arranca con «Listo…», no lo decimos dos veces
                listo = '' if re.match(r'(¡\s*)?(listo|ya está|terminé|hecho)\b', frase, re.I) \
                    else _uno(ORGULLO if largo else LISTO)
                # festeja con un grito («¡Sí!», «¡Golazo!») y, si hay confeti, se escucha
                grito = _uno(GRITO) + ' ' if (largo or random.random() < 0.4) and not self.fecha['respeto'] else ''
                self.decir(f'{grito}{listo} {frase}'.strip(), alta=True, sub=sub, animo='contento',
                           efecto='confeti')        # siempre que tira confeti, se escucha
            elif tipo == 'SubagentStart':
                self._agentes_n += 1
                aid = d.get('agent_id') or f'{sid}:{self._agentes_n}'
                self.m.agente('nuevo', aid, sid)
                activos = self.m.ayu.cuantos()
                self._pico_agentes = max(self._pico_agentes, activos)
                if activos >= 2 and random.random() < 0.6:
                    self.decir(_uno(REFUERZOS), sub=sub, animo='contento')
            elif tipo == 'SubagentStop':
                self.m.agente('listo', d.get('agent_id') or '', sid)
                if self.m.ayu.cuantos() == 0 and self._pico_agentes >= 2:
                    self._pico_agentes = 0
                    self.decir(_uno(VOLVIERON), sub=sub, animo='contento')
                elif self.m.ayu.cuantos() == 0:
                    self._pico_agentes = 0
            elif tipo == 'SessionEnd':
                self.m.agente('limpiar', '', sid)
                s['ocupada'] = False
                self.estado.pop(sid, None)
                if not self.alguna_ocupada():
                    self.m.actividad('libre')
        except Exception:
            log.exception('evento %s', tipo)

    def _explicar_tarde(self, d: dict, sid: str, sub):
        """La app guarda lo que escribió Claude recién después del control de permisos (unos segundos):
        lo vuelve a buscar y, si es nuevo, lo cuenta."""
        tid = d.get('tool_use_id') or ''
        if self._habla() == 'poco':
            return False
        texto, _, uid = explicacion_de(d.get('transcript_path') or '', tid) if tid else ('', '', '')
        if not uid or uid in self.explicados or not texto or not _es_castellano(texto):
            return False
        self.explicados.append(uid)
        self._actual = (sid, sub or '')
        try:
            self.decir(self._sobre_claude(texto), sub=sub, importante=True)
        finally:
            self._actual = None
        return True

    def _paso(self, d, sid, s, sub, act, frase, alta, clave):
        """Narra un paso de Claude: lo que te escribió en el chat, lo que piensa o qué herramienta usa."""
        ahora = time.monotonic()
        if self._habla() == 'poco' and not alta:
            return                      # habla poco: solo lo importante (permisos, preguntas, listo)
        self._actual = (sid, sub or '')
        try:
            # el «para qué»: lo que Claude escribió justo antes de este paso
            tid = d.get('tool_use_id') or ''
            texto, piensa, uid = explicacion_de(d.get('transcript_path') or '', tid) if tid else ('', '', '')
            nuevo = uid and uid not in self.explicados
            if not texto and not alta:
                for ms in (2500, 6000):
                    QTimer.singleShot(ms, lambda: self._explicar_tarde(d, sid, sub))
            if nuevo:
                self.explicados.append(uid)
            importante = False
            if nuevo and texto and not alta and _es_castellano(texto):
                # lo que Claude te contó en el chat (hallazgos, qué va a probar y por qué)
                frase, clave, importante = self._sobre_claude(texto), None, True
            elif nuevo and piensa and _es_castellano(piensa):
                resumen = primera_frase(piensa, 150)
                if not alta and ahora - self.ult_pensamiento > 20:
                    # mini resumen de lo que está pensando (no más de uno cada 20 s)
                    frase, clave = _uno(PIENSO) + resumen, None
                    self.ult_pensamiento = ahora
                else:
                    self.para_despues[tid] = resumen
            elif act in ('terminal',):
                desc = str((d.get('tool_input') or {}).get('description') or '')
                if _es_castellano(desc):
                    self.para_despues[tid] = desc
            # si ya se sabe que va a tardar (instalar, descargar, compilar, o Claude le dio mucho
            # tiempo al comando), lo avisa de entrada
            largo = self._va_a_tardar(d.get('tool_name') or '', d.get('tool_input') or {})
            if largo:
                frase, clave = largo, 'tardar'
                self.para_despues.pop(tid, None)
            # con los años que lleva laburando, se le nota el humor
            humor = None if alta or importante or not self._quejas() else self._humor(s, ahora)
            if humor:
                frase, clave = humor, None
            casi = self._avance(d.get('tool_name') or '', d.get('tool_input') or {})
            if casi and not alta:
                frase, clave = casi, None
            if frase:
                self.decir(frase, alta=alta, clave=None if alta else clave, sub=sub,
                           repetir=90 if clave == 'unity' else 9.0, importante=importante)
            if tid:
                QTimer.singleShot(9000, lambda t=tid, s_=sid, n_=sub: self._tarda(t, s_, n_))
                QTimer.singleShot(75000, lambda t=tid, s_=sid, n_=sub: self._tarda_mucho(t, s_, n_))
        except Exception:
            log.exception('paso')
        finally:
            self._actual = None

    def _va_a_tardar(self, nombre: str, entrada: dict) -> str:
        """Frase de aviso si el comando pinta largo; si no, ''."""
        if nombre not in ('Bash', 'PowerShell'):
            return ''
        desc = str(entrada.get('description') or '')
        comando = str(entrada.get('command') or '')
        limite = entrada.get('timeout') or 0
        # las palabras en castellano, solo en la descripción (en el comando, «abajo» parecía «bajo un archivo»)
        pesado = (re.search(r'instal|descarg|\bbaj[oa]\b|compil|entren|render|actualiz', desc, re.I)
                  or re.search(r'pip install|npm (i|install)|winget|download|build|git clone', comando, re.I))
        if re.search(r'py_compile|compileall', comando):
            pesado = None                       # «compilo para ver si hay errores» es al toque
        if not (pesado or (isinstance(limite, (int, float)) and limite >= 300_000)):
            return ''
        if _es_castellano(desc):
            return _uno(VA_TARDAR, d=desc[0].lower() + desc[1:].rstrip('.'))
        return _uno(VA_TARDAR_SIN)

    def _tarda(self, tid: str, sid: str, sub):
        """La herramienta sigue después de 9 s: cuenta para qué es (una vez por minuto como mucho)."""
        explicacion = self.para_despues.pop(tid, '')
        if self._habla() == 'poco':
            return
        if tid in self.hechas or not (self.estado.get(sid) or {}).get('ocupada'):
            return
        ahora = time.monotonic()
        if ahora - self.ult_tarda < 60:
            return
        self.ult_tarda = ahora
        self._actual = (sid, sub or '')
        try:
            self.decir(_uno(TARDA_CON, e=explicacion) if explicacion else _uno(TARDA), sub=sub)
        finally:
            self._actual = None
        while len(self.para_despues) > 50:
            self.para_despues.pop(next(iter(self.para_despues)))

    # ------------------------------------------------------------ límite de 5 horas y contexto
    UMBRALES_LIMITE = (50, 75, 90, 95, 98, 100)
    UMBRALES_CONTEXTO = (60, 80, 90)

    def _uso(self, d: dict):
        """Datos de la statusLine: avisa al cruzar ciertos % del límite de 5 horas."""
        if not self.cfg.get('avisos_uso', True):
            return
        cinco = ((d.get('rate_limits') or {}).get('five_hour') or {})
        pct = cinco.get('used_percentage')
        if pct is not None:
            self.limite(float(pct), cinco.get('resets_at'))
        ctx = d.get('context_window') or {}
        if ctx.get('used_percentage') is not None:
            sid = d.get('session_id', '')
            self._contexto(sid, float(ctx['used_percentage']),
                           self._nombre_sesion(sid, (d.get('workspace') or {}).get('current_dir') or d.get('cwd') or ''))

    def limite(self, pct: float, reinicio):
        """pct: % usado de la ventana de 5 horas; reinicio: epoch (s) o ISO de cuándo se renueva."""
        if isinstance(reinicio, str):
            try:
                reinicio = datetime.fromisoformat(reinicio.replace('Z', '+00:00')).timestamp()
            except ValueError:
                reinicio = None
        ventana = round(reinicio / 600) if reinicio else 0      # identifica la ventana actual
        if ventana != getattr(self, '_ventana', None):
            self._ventana, self._limite_dicho = ventana, max([u for u in self.UMBRALES_LIMITE if u <= pct], default=0)
            if self._limite_dicho < 90:       # al arrancar no repite lo que ya pasó, salvo que esté cerca
                return
            self._limite_dicho = 0
        cruzados = [u for u in self.UMBRALES_LIMITE if u <= pct and u > self._limite_dicho]
        if not cruzados:
            return
        self._limite_dicho = cruzados[-1]
        cuando, falta = '', ''
        if reinicio:
            cuando = datetime.fromtimestamp(reinicio).strftime('%H:%M')
            m = max(0, int((reinicio - time.time()) / 60))
            falta = f'{m // 60} hora{"s" if m // 60 != 1 else ""} y {m % 60} minutos' if m >= 60 else f'{m} minutos'
        n = self.n
        if pct >= 100:
            frase = f'Bueno, {n}, llegamos al límite de las 5 horas.' + \
                    (f' Se reinicia a las {cuando}, en {falta}.' if cuando else '')
            self.m.momento('resoplar', 2.4)
        elif pct >= 90:
            frase = f'Ey, {n}, del límite de 5 horas ya vas por el {int(pct)} por ciento.' + \
                    (f' Se reinicia a las {cuando}, en {falta}.' if cuando else '') + ' Guardá lo importante.'
            self.m.momento('sorpresa', 1.2)
        else:
            frase = f'Che, {n}, vas por el {int(pct)} por ciento del límite de 5 horas.' + \
                    (f' Se renueva a las {cuando}.' if cuando else '')
        self.decir(frase, alta=pct >= 90)

    def _contexto(self, sid: str, pct: float, nombre: str):
        """Avisa cuando la charla de un chat se está llenando y conviene compactar."""
        s = self.estado.get(sid)
        if s is None:
            return
        dicho = s.get('ctx_dicho', 0)
        if pct < dicho - 20:                  # se compactó: vuelve a empezar
            s['ctx_dicho'] = dicho = 0
        cruzados = [u for u in self.UMBRALES_CONTEXTO if dicho < u <= pct]
        if not cruzados:
            return
        s['ctx_dicho'] = cruzados[-1]
        donde = f'En {nombre}, la' if nombre else 'La'
        self.decir(f'{donde} memoria del chat va por el {int(pct)} por ciento. Conviene compactar: '
                   f'primero pedile que anote lo importante y después usá compactar.', alta=True)

    def _contexto_del_transcript(self, sid: str, ruta: str, nombre: str):
        """Sin statusLine: calcula el contexto con el uso del último mensaje de Claude."""
        if not self.cfg.get('avisos_uso', True):
            return
        usado = tokens_del_transcript(ruta)
        if usado:
            self._contexto(sid, 100 * usado / self.cfg.get('ventana_contexto', 1_000_000), nombre)

    # umbrales (segundos de laburo seguido) → (frases, animación)
    HUMORES = ((240, CANSADO, 'resoplar'), (600, PAJA, 'resoplar'), (1200, HARTO, 'resoplar'))

    def _humor(self, s: dict, ahora: float) -> str:
        """Si el laburo viene largo, una queja según cuánto lleva (a los 4, 10 y 20 min, una vez
        cada una; después, una cada 20 min)."""
        if not s.get('desde'):
            return ''
        dura = ahora - s['desde']
        nivel = s.get('nivel', 0)
        if nivel < len(self.HUMORES) and dura >= self.HUMORES[nivel][0]:
            _, lista, anim = self.HUMORES[nivel]
        elif nivel >= len(self.HUMORES) and dura >= 1200 + 1200 * (nivel - len(self.HUMORES) + 1):
            lista, anim = random.choice((PAJA, HARTO)), 'resoplar'
        else:
            return ''
        s['nivel'] = nivel + 1
        self.m.momento(anim, 2.4)
        return _uno(lista, n=self.n)

    def _avance(self, nombre: str, entrada: dict) -> str:
        """Con la lista de tareas de Claude: festeja la mitad y avisa cuando falta la última."""
        if nombre != 'TodoWrite':
            return ''
        todos = entrada.get('todos') or []
        total = len(todos)
        hechas = sum(1 for t in todos if isinstance(t, dict) and t.get('status') == 'completed')
        if total < 3 or hechas >= total:
            return ''
        clave = f'avance:{total}:{hechas}'
        if total - hechas == 1 and clave not in self.ult_clave:
            self.ult_clave[clave] = time.monotonic()
            self.m.momento('casi', 2.2)
            return _uno(CASI, n=self.n)
        if total >= 5 and hechas == total // 2 and clave not in self.ult_clave:
            self.ult_clave[clave] = time.monotonic()
            return _uno(MITAD, n=self.n)
        # el paso del plan en el que arranca, para que sepas si va por donde tiene que ir
        for i, t in enumerate(todos, 1):
            if isinstance(t, dict) and t.get('status') == 'in_progress':
                texto = str(t.get('activeForm') or t.get('content') or '').strip()
                if texto and _es_castellano(texto) and f'paso:{texto}' not in self.ult_clave:
                    self.ult_clave[f'paso:{texto}'] = time.monotonic()
                    return f'Paso {i} de {total}: {primera_frase(texto, 120)}'
                break
        return ''

    def _tarda_mucho(self, tid: str, sid: str, sub):
        """La misma herramienta lleva más de un minuto: se impacienta."""
        if self._habla() == 'poco':
            return
        if tid in self.hechas or not (self.estado.get(sid) or {}).get('ocupada'):
            return
        self._actual = (sid, sub or '')
        try:
            self.m.momento('resoplar', 2.4)
            self.decir(_uno(TARDA_MUCHO), clave='tarda_mucho', repetir=180, sub=sub)
        finally:
            self._actual = None

    def _herramienta(self, nombre: str, entrada: dict):
        """(actividad, frase o None, alta, clave de repetición)"""
        f = _archivo(entrada)
        if nombre == 'Read':
            return 'leer', _uno(LEER, f=f) if f else _uno(LEER_SIN), False, 'leer'
        if nombre in ('Grep', 'Glob'):
            return 'buscar', _uno(BUSCAR), False, 'buscar'
        if nombre in ('Edit', 'MultiEdit', 'NotebookEdit'):
            return 'teclear', _uno(EDITAR, f=f or 'un archivo'), False, f'editar:{f}'
        if nombre == 'Write':
            return 'teclear', _uno(CREAR, f=f or 'un archivo'), False, f'crear:{f}'
        if nombre in ('Bash', 'PowerShell'):
            desc = str(entrada.get('description') or '').strip()
            if desc and _es_castellano(desc):
                return 'terminal', primera_frase(desc, 130), False, f'cmd:{desc}'
            propia = explicar_comando(str(entrada.get('command') or ''))
            return 'terminal', propia or _uno(COMANDO), False, f'cmd:{propia}' if propia else 'comando'
        if nombre == 'WebSearch':
            return 'web', _uno(WEB_BUSCAR), False, 'web'
        if nombre == 'WebFetch':
            return 'web', _uno(WEB_LEER), False, 'web'
        if nombre.startswith(('mcp__Claude_Browser__', 'mcp__claude-in-chrome__')):
            return 'web', _uno(NAVEGADOR), False, 'navegador'
        if nombre.startswith(('mcp__unityMCP__', 'mcp__unityVRC__')):
            return 'teclear', _uno(UNITY), False, 'unity'
        if nombre in ('Agent', 'Task'):
            return 'pensar', _uno(AYUDANTE), False, 'ayudante'
        if nombre == 'Artifact':
            return 'teclear', _uno(PAGINA), False, 'pagina'
        if nombre == 'Skill':
            return 'leer', _uno(SKILL), False, 'skill'
        if nombre == 'EnterPlanMode':
            return 'pensar', _uno(PLAN), False, 'plan'
        if nombre == 'ExitPlanMode':
            return 'llamar', _uno(PLAN_LISTO, n=self.n), True, None
        if nombre == 'AskUserQuestion':
            return 'preguntar', _uno(PREGUNTA, n=self.n), True, None
        if nombre in SILENCIOSAS or nombre.startswith(('mcp__ccd_', 'mcp__visualize__read_me')):
            return 'pensar', None, False, None
        return 'teclear', None, False, None

    # ------------------------------------------------------------ cosas propias
    def saludo_app(self):
        self._al_dia()
        if self.fecha['saludo'] and self.cfg.get('fechas_argentinas', True):
            # fecha patria o cultural: saluda por el día (el Día de la Bandera, encima, la iza)
            self.decir(self.fecha['saludo'].format(**NOMBRE), alta=True,
                       animo='triste' if self.fecha['respeto'] else 'contento')
            return
        h = datetime.now().hour
        if h < 6:
            frase = f'¡Hola, {self.n}! ¿Otra vez de madrugada? Dale, arrancamos.'
        elif h < 13:
            frase = f'¡Buen día, {self.n}! ¿Qué hacemos hoy?'
        elif h < 20:
            frase = f'¡Buenas tardes, {self.n}! ¿Qué hacemos?'
        else:
            frase = f'¡Buenas noches, {self.n}! ¿Qué hacemos hoy?'
        self.decir(frase, alta=True)

    def chau(self):
        self.decir(_uno(CHAU, n=self.n), alta=True, animo='contento')

    def mimado(self):
        self.decir(_uno(MIMO, n=self.n), clave='mimo', repetir=15)

    def cosquillas(self):
        self.decir(_uno(COSQUILLAS, n=self.n), clave='cosquillas', repetir=20, animo='contento')

    def observado(self):
        if not self.escuchando and not self.oculto:
            self.decir(_uno(OBSERVADO, n=self.n), clave='observado', repetir=120, animo='contento')

    def tema_nuevo(self, titulo: str, genero: str = ''):
        """Cambió el tema en Spotify: de vez en cuando lo festeja (no todos, y sin pisar lo de Claude).
        Si es de un género argentino que conoce (o phonk), lo comenta a su manera."""
        if not self.cfg.get('comentar_musica', True) or self.escuchando or self.oculto:
            return
        if time.monotonic() - self.ult_clave.get('musica', -1e9) < 480 or random.random() > 0.35:
            return
        artista = titulo.split(' - ', 1)[0].strip()
        if genero in MUSICA_GENERO and self.cfg.get('animaciones_musica', True) and random.random() < 0.6:
            frase = _uno(MUSICA_GENERO[genero], n=self.n)
        elif artista and len(artista) <= 30 and random.random() < 0.3:
            frase = _uno(MUSICA_ARTISTA, a=artista, n=self.n)
        else:
            frase = _uno(MUSICA, n=self.n)
        self.decir(frase, clave='musica', repetir=480)

    def volviste(self):
        self.decir(_uno(VOLVISTE), clave='volviste', repetir=120)

    def con_voz(self):
        self.decir(_uno(CON_VOZ), alta=True)

    @staticmethod
    def frases_fijas(nombre: str, cfg=None) -> list[str]:
        """Para precalentar la voz: todo lo que no depende de nombres de archivo (las más usadas primero)."""
        cfg = cfg or {}
        marcas = {'n': nombre, 'o': TRATO.get(cfg.get('trato', 'masculino')) or 'o',
                  'mate': BEBIDAS.get(cfg.get('bebida', 'mate'), 'un mate')}
        out = []
        for lista in (PEDIDO, LISTO, PERMISO, PREGUNTA, ERROR, LEER_SIN, BUSCAR, COMANDO, WEB_BUSCAR, WEB_LEER,
                      NAVEGADOR, AYUDANTE, PAGINA, SKILL, PLAN, PLAN_LISTO, ESPERA, ELEGIR, MIMO,
                      VOLVISTE, SESION, RESUMIR, CON_VOZ, CHAU, FRUSTRADO, TARDA, VA_TARDAR_SIN, ORGULLO,
                      CANSADO, PAJA, HARTO, CASI, MITAD, FIN_LARGO, TARDA_MUCHO, ABURRIDO, MUSICA, UNITY):
            out += [f.format(**marcas) for f in lista]
        return out
