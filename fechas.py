# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fechas patrias y culturales argentinas: qué ropa lleva el cangrejito ese día, cómo saluda y qué
curiosidades cuenta de vez en cuando. Es un cangrejito hecho por argentinos.

Cada fecha:
  nombre        cómo se llama el día
  ropa          accesorios que se pone (los dibuja sprites.py)
  escarapela    fecha patria: lleva la escarapela todo el día
  respeto       día de memoria: nada de festejos ni chistes
  saludo        lo que dice al llegar ({n} es tu nombre)
  curiosidades  datos que cuenta cada tanto (sin repetir en el día)
  actividad     algo especial que hace ese día (paseo de mascota.py), o ''
"""
from __future__ import annotations

import datetime as dt


def _domingo(anio: int, mes: int, cual: int) -> dt.date:
    """El «cual»-ésimo domingo del mes (1 = el primero)."""
    d = dt.date(anio, mes, 1)
    d += dt.timedelta(days=(6 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=cual - 1)


def _dia_256(anio: int) -> dt.date:
    return dt.date(anio, 1, 1) + dt.timedelta(days=255)


FECHAS = {
    # ------------------------------------------------------------ patrias
    'memoria': dict(
        nombre='Día Nacional de la Memoria por la Verdad y la Justicia', respeto=True, escarapela=False,
        saludo='Hola, {n}. Hoy es el Día de la Memoria por la Verdad y la Justicia.',
        curiosidades=[
            'Hoy se recuerda a las víctimas de la última dictadura militar, que empezó el 24 de marzo de 1976.',
            'Es feriado nacional desde 2006, para que no se olvide nunca más.',
        ]),
    'malvinas': dict(
        nombre='Día del Veterano y de los Caídos en la Guerra de Malvinas', respeto=True, escarapela=True,
        saludo='Hola, {n}. Hoy recordamos a los veteranos y a los caídos en Malvinas.',
        curiosidades=[
            'La guerra de Malvinas fue en 1982. Murieron 649 soldados argentinos.',
            'Las islas Malvinas están en el Atlántico Sur, a unos 500 kilómetros de la costa patagónica.',
            'Hoy la escarapela va por los que dieron todo. Las Malvinas son argentinas.',
        ]),
    'escarapela': dict(
        nombre='Día de la Escarapela', escarapela=True,
        saludo='¡Buenas, {n}! Hoy es el Día de la Escarapela, mirá la mía.',
        curiosidades=[
            'La escarapela se aprobó el 18 de febrero de 1812, a pedido de Manuel Belgrano.',
            'Se usa del lado izquierdo, del lado del corazón.',
            'Belgrano la pidió para que los soldados patriotas no se confundieran con los realistas.',
        ]),
    'mayo': dict(
        nombre='Revolución de Mayo', escarapela=True, ropa={'galera'},
        saludo='¡Feliz 25 de mayo, {n}! Me puse la galera y todo.',
        curiosidades=[
            'El 25 de mayo de 1810 se formó la Primera Junta, el primer gobierno patrio.',
            'La Primera Junta la presidió Cornelio Saavedra.',
            'Dicen que ese día llovía y la gente tenía paraguas, pero muchos historiadores creen que es más leyenda que otra cosa.',
            'El Cabildo de Buenos Aires sigue en pie frente a la Plaza de Mayo, aunque más chico que en 1810.',
            'Para festejar se come locro y empanadas, y de postre, pastelitos.',
            'Mariano Moreno, secretario de la Junta, dirigió la Gazeta de Buenos Ayres. Por eso el 7 de junio es el Día del Periodista.',
            'Domingo French y Antonio Beruti repartían cintas a los patriotas en la plaza.',
        ]),
    'guemes': dict(
        nombre='Paso a la Inmortalidad del General Güemes', escarapela=True, ropa={'poncho'},
        saludo='¡Buenas, {n}! Hoy honramos a Güemes. Me puse el poncho salteño.',
        curiosidades=[
            'Martín Miguel de Güemes defendió la frontera norte con sus gauchos.',
            'Güemes murió el 17 de junio de 1821, herido en combate en Salta.',
            'Dicen que el poncho salteño lleva la guarda negra en señal de luto por Güemes.',
        ]),
    'bandera': dict(
        nombre='Día de la Bandera', escarapela=True, actividad='mastil',
        saludo='¡Feliz Día de la Bandera, {n}! Ahora la izo.',
        curiosidades=[
            'Belgrano creó la bandera el 27 de febrero de 1812, a orillas del río Paraná, en Rosario.',
            'El 20 de junio se recuerda porque ese día, en 1820, murió Manuel Belgrano.',
            'Belgrano murió pobre: le pagó al médico con su reloj.',
            'El Monumento a la Bandera está en Rosario, frente al río Paraná.',
            'El sol de la bandera es el Sol de Mayo. Se le agregó en 1818.',
            'Belgrano estudió leyes y fue economista y periodista, no solo militar.',
            'La canción que se le canta a la bandera es «Aurora».',
        ]),
    'independencia': dict(
        nombre='Día de la Independencia', escarapela=True, ropa={'galera'},
        saludo='¡Feliz Día de la Independencia, {n}! Hoy hay locro.',
        curiosidades=[
            'El 9 de julio de 1816 se declaró la independencia en San Miguel de Tucumán.',
            'Se firmó en la casa de Francisca Bazán de Laguna, hoy la Casa Histórica de Tucumán.',
            'El Congreso de Tucumán había empezado a sesionar el 24 de marzo de 1816.',
            'El acta se mandó a traducir al quechua y al aymara, para que la entendieran en todo el territorio.',
            'El 19 de julio le agregaron «y de toda otra dominación extranjera».',
            'Ese día presidía el Congreso Francisco Narciso de Laprida.',
        ]),
    'san_martin': dict(
        nombre='Paso a la Inmortalidad del General San Martín', escarapela=True, ropa={'bicornio'},
        saludo='¡Buenas, {n}! Hoy homenajeamos a San Martín. Mirá mi bicornio.',
        curiosidades=[
            'San Martín murió el 17 de agosto de 1850 en Boulogne-sur-Mer, Francia.',
            'En 1817 cruzó la cordillera de los Andes con el Ejército de los Andes.',
            'En el cruce de los Andes se usaron muchas más mulas que caballos.',
            'Creó el Regimiento de Granaderos a Caballo en 1812.',
            'Nació en Yapeyú, Corrientes, en 1778.',
            'Sus restos descansan en la Catedral de Buenos Aires.',
            'Su sable corvo está en el Museo Histórico Nacional.',
        ]),
    'maestro': dict(
        nombre='Día del Maestro', escarapela=False, ropa={'guardapolvo'},
        saludo='¡Feliz día a las maestras y los maestros, {n}! Me puse el guardapolvo.',
        curiosidades=[
            'Se recuerda a Domingo Faustino Sarmiento, que murió el 11 de septiembre de 1888 en Asunción del Paraguay.',
            'A Sarmiento le dicen «el padre del aula».',
            'Como presidente, Sarmiento trajo maestras de Estados Unidos para formar docentes.',
        ]),
    'diversidad': dict(
        nombre='Día del Respeto a la Diversidad Cultural', escarapela=False,
        saludo='¡Buenas, {n}! Hoy es el Día del Respeto a la Diversidad Cultural.',
        curiosidades=[
            'Hasta 2010 se llamaba Día de la Raza. Hoy se reconocen los pueblos originarios y todas las culturas.',
        ]),
    'soberania': dict(
        nombre='Día de la Soberanía Nacional', escarapela=True,
        saludo='¡Buenas, {n}! Hoy es el Día de la Soberanía Nacional.',
        curiosidades=[
            'Se recuerda la batalla de la Vuelta de Obligado, en 1845, sobre el río Paraná.',
            'Lucio Mansilla cruzó cadenas de costa a costa del río para frenar a la flota anglofrancesa.',
            'San Martín le dejó su sable corvo a Rosas por defender la soberanía.',
        ]),
    # ------------------------------------------------------------ culturales
    'noquis': dict(
        nombre='Día de los ñoquis', actividad='noquis',
        saludo='¡Hoy es 29, {n}! Ñoquis, y la plata abajo del plato.',
        curiosidades=[
            'Los ñoquis del 29 los trajeron los inmigrantes italianos.',
            'Hay que poner un billete abajo del plato, para que no falte la plata el mes que viene.',
            'A fin de mes la plata no alcanza y los ñoquis son baratos: por eso caen justo el 29.',
            'Dice la leyenda que San Pantaleón pidió comida a unos campesinos del Véneto, y ellos le convidaron ñoquis.',
        ]),
    'amigo': dict(
        nombre='Día del Amigo',
        saludo='¡Feliz Día del Amigo, {n}! Sos mi amig{o} favorit{o}.',
        curiosidades=[
            'El Día del Amigo lo inventó un argentino, Enrique Febbraro.',
            'Se eligió el 20 de julio por la llegada del hombre a la Luna, en 1969.',
        ]),
    'mate': dict(
        nombre='Día Nacional del Mate', ropa={'mate_fiesta'},
        saludo='¡Feliz Día del Mate, {n}! ¿Unos amargos?',
        curiosidades=[
            'Se festeja el 30 de noviembre por el nacimiento de Andrés Guacurarí, «Andresito», caudillo misionero.',
            'Argentina es el mayor productor de yerba mate del mundo.',
            'Desde 2013, el mate es la infusión nacional.',
            'El que ceba toma el primero, que es el más amargo.',
            'Decir «gracias» en una ronda de mate quiere decir que ya no querés más.',
        ]),
    'dulce_de_leche': dict(
        nombre='Día del Dulce de Leche',
        saludo='¡Hoy es el Día del Dulce de Leche, {n}! Qué rico.',
        curiosidades=[
            'Dice la leyenda que se inventó en 1829, cuando a una criada se le pasó la leche con azúcar en el fuego.',
            'Con Uruguay seguimos discutiendo de quién es el dulce de leche.',
        ]),
    'pachamama': dict(
        nombre='Día de la Pachamama', ropa={'ruda'},
        saludo='¡Buenas, {n}! Hoy es el Día de la Pachamama. ¿Tomaste la caña con ruda?',
        curiosidades=[
            'La Pachamama es la Madre Tierra para los pueblos andinos.',
            'El primero de agosto se toma caña con ruda en ayunas, para espantar los males del invierno.',
            'En el norte se le da de comer a la tierra: se hace un pozo y se le ofrenda comida y bebida.',
        ]),
    'tradicion': dict(
        nombre='Día de la Tradición', ropa={'gaucho'},
        saludo='¡Feliz Día de la Tradición, {n}! Hoy ando de gaucho.',
        curiosidades=[
            'Se celebra el nacimiento de José Hernández, el autor del Martín Fierro, en 1834.',
            'La fiesta de la tradición más famosa es la de San Antonio de Areco.',
        ]),
    'tango': dict(
        nombre='Día del Tango', ropa={'funyi', 'panuelo_blanco'},
        saludo='¡Feliz Día del Tango, {n}! Me puse el funyi.',
        curiosidades=[
            'Se eligió el 11 de diciembre porque ese día nacieron Carlos Gardel y Julio De Caro.',
            'El tango es Patrimonio de la Humanidad desde 2009, junto con Uruguay.',
            'Astor Piazzolla revolucionó el tango con el bandoneón.',
        ]),
    'folklore': dict(
        nombre='Día del Folklore', ropa={'gaucho'},
        saludo='¡Feliz Día del Folklore, {n}! Hoy suena una zamba.',
        curiosidades=[
            'El 22 de agosto de 1846 se usó por primera vez la palabra folklore.',
            'En Argentina también se recuerda a Juan Bautista Ambrosetti, pionero del folklore, que nació ese día.',
        ]),
    'estudiante': dict(
        nombre='Día del Estudiante y de la Primavera', ropa={'flor'},
        saludo='¡Feliz Día de la Primavera, {n}! Y feliz Día del Estudiante.',
        curiosidades=[
            'El Día del Estudiante recuerda que el 21 de septiembre de 1888 llegaron al país los restos de Sarmiento.',
            'Hoy es el clásico picnic en las plazas.',
        ]),
    'programador': dict(
        nombre='Día del Programador',
        saludo='¡Feliz Día del Programador, {n}! Hoy es nuestro día.',
        curiosidades=[
            'El Día del Programador es el día 256 del año, porque 256 es 2 a la octava.',
            'En años bisiestos cae el 12 de septiembre; si no, el 13.',
        ]),
    'padre': dict(
        nombre='Día del Padre',
        saludo='¡Feliz Día del Padre, {n}! Un abrazo a todos los papás.',
        curiosidades=['En Argentina, el Día del Padre es el tercer domingo de junio.']),
    'madre': dict(
        nombre='Día de la Madre',
        saludo='¡Feliz Día de la Madre, {n}! Un abrazo a todas las mamás.',
        curiosidades=['En Argentina, el Día de la Madre es el tercer domingo de octubre.']),
    'navidad': dict(
        nombre='Navidad', ropa={'gorro_navidad'},
        saludo='¡Feliz Navidad, {n}! Jo, jo, jo.',
        curiosidades=[
            'En Argentina la Navidad es con calor: pan dulce, turrón, sidra y, si se puede, pileta.',
            'A las doce se brinda y se tiran fuegos artificiales.',
        ]),
    'anio_nuevo': dict(
        nombre='Año Nuevo', ropa={'gorro_navidad'},
        saludo='¡Feliz año nuevo, {n}! Que sea un añazo.',
        curiosidades=['En la oficina, el último día hábil se tiran papelitos por la ventana.']),
}


def hoy(fecha: dt.date | None = None) -> str:
    """La clave de la fecha especial de hoy, o '' si es un día común."""
    d = fecha or dt.date.today()
    fijas = {
        (3, 24): 'memoria', (4, 2): 'malvinas', (5, 18): 'escarapela', (5, 25): 'mayo',
        (6, 17): 'guemes', (6, 20): 'bandera', (7, 9): 'independencia', (8, 17): 'san_martin',
        (9, 11): 'maestro', (10, 12): 'diversidad', (11, 20): 'soberania',
        (7, 20): 'amigo', (11, 30): 'mate', (10, 11): 'dulce_de_leche', (8, 1): 'pachamama',
        (11, 10): 'tradicion', (12, 11): 'tango', (8, 22): 'folklore', (9, 21): 'estudiante',
        (12, 24): 'navidad', (12, 25): 'navidad', (12, 31): 'anio_nuevo', (1, 1): 'anio_nuevo',
    }
    if (d.month, d.day) in fijas:
        return fijas[(d.month, d.day)]
    if d == _dia_256(d.year):
        return 'programador'
    if d == _domingo(d.year, 6, 3):
        return 'padre'
    if d == _domingo(d.year, 10, 3):
        return 'madre'
    if d.day == 29:
        return 'noquis'
    return ''


def datos(clave: str) -> dict:
    f = FECHAS.get(clave) or {}
    return {'clave': clave, 'nombre': f.get('nombre', ''), 'ropa': set(f.get('ropa') or ()),
            'escarapela': bool(f.get('escarapela')), 'respeto': bool(f.get('respeto')),
            'saludo': f.get('saludo', ''), 'curiosidades': list(f.get('curiosidades') or ()),
            'actividad': f.get('actividad', '')}
