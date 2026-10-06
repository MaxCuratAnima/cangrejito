# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
"""Cangrejito de Claude: mascota de escritorio que comenta lo que hace Claude Code.

Arranca con Windows escondido; aparece cuando abrís la app de Claude.
  --ya        aparece enseguida aunque la app esté cerrada (para probar)
  --sin-voz   arranca silenciado
"""
import logging
import os
import struct
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

from PySide6.QtCore import QBuffer, QIODevice, QPoint, Qt
from PySide6.QtGui import QAction, QActionGroup, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

import version

import configuracion
import eventos
import rutas
import sprites as S
from config import Config
from mascota import Mascota
from narrador import Narrador
from vigilante import Vigilante
from voz import Voz

log = logging.getLogger('cangrejito')


def _registro():
    rutas.preparar()
    h = RotatingFileHandler(rutas.DATOS / 'registro.txt', maxBytes=300_000, backupCount=1, encoding='utf-8')
    logging.basicConfig(level=logging.INFO, handlers=[h], format='%(asctime)s %(name)s %(levelname)s %(message)s')
    sys.excepthook = lambda *e: log.critical('error sin atrapar', exc_info=e)


def _icono() -> QIcon:
    img = S.dibujar(S.Pose()).copy(S.recorte_cangrejo())
    lado = max(img.width(), img.height())
    cuadro = QImage(lado, lado, QImage.Format.Format_ARGB32_Premultiplied)
    cuadro.fill(0)
    p = QPainter(cuadro)
    p.drawImage((lado - img.width()) // 2, (lado - img.height()) // 2, img)
    p.end()
    grande = cuadro.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
    ico = AQUI / 'cangrejito.ico'
    if not ico.exists() and not rutas.CONGELADO:
        # .ico con un PNG adentro (lo usan los accesos directos)
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        grande.save(buf, 'PNG')
        png = bytes(buf.data())
        try:
            ico.write_bytes(struct.pack('<HHH', 0, 1, 1)
                            + struct.pack('<BBBBHHII', 0, 0, 0, 0, 1, 32, len(png), 22) + png)
        except OSError:
            pass
    return QIcon(QPixmap.fromImage(grande))


def main():
    _registro()
    args = set(sys.argv[1:])
    if sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY') and os.environ.get('DISPLAY') \
            and not os.environ.get('QT_QPA_PLATFORM'):
        # en Wayland una ventana no puede ubicarse sola ni quedar siempre encima: va por XWayland
        os.environ['QT_QPA_PLATFORM'] = 'xcb'
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    cfg = Config()
    if '--sin-voz' in args:
        cfg['silencio'] = True

    receptor = eventos.Receptor()
    if eventos.arrancar(receptor) is None:
        log.info('ya hay otro cangrejito andando: salgo')
        return
    log.info('arranca el cangrejito')

    voz = Voz(cfg)
    if not cfg.get('nombre'):
        # la primera vez: bienvenida con la configuración (nombre, cuánto habla, personalidad, voz)
        configuracion.abrir(cfg, lambda: voz.decir(f'¡Hola, {cfg["nombre"] or "compa"}! Así sueno yo.',
                                                    cortar=True), bienvenida=True)
    voz.precalentar(Narrador.frases_fijas(cfg['nombre']))
    m = Mascota(cfg, voz)
    vig = Vigilante(cfg, m.hwnds)
    vig.forzar = '--ya' in args
    nar =Narrador(m, voz, cfg, lambda: vig.sesiones)
    nar.oculto = True

    # ---------------------------------------------------------------- menú (clic derecho y bandeja)
    # Todo lo que se configura está acá, en submenús, como el menú del clic derecho de Windows.
    # Cada vez que se abre, marca lo que dice la config (que también cambia la ventana de Configuración).
    menu = QMenu()
    sincronizar = []

    def poner(clave, valor):
        cfg[clave] = valor
        cfg.guardar()
        nar._al_dia()

    def opciones(padre, titulo, clave, valores, cercano=False):
        sub = padre.addMenu(titulo)
        grupo = QActionGroup(sub)
        acciones = []
        for valor, texto in valores:
            a = QAction(texto, sub, checkable=True)
            a.triggered.connect(lambda _=False, v=valor: poner(clave, v))
            grupo.addAction(a)
            sub.addAction(a)
            acciones.append((a, valor))

        def marcar():
            actual = cfg.get(clave)
            if cercano:              # números (volumen, velocidad): el más parecido
                elegido = min(acciones, key=lambda av: abs(av[1] - float(actual or 0)))[0]
            else:
                elegido = next((a for a, v in acciones if v == actual), None)
            for a, _ in acciones:
                a.setChecked(a is elegido)
        sincronizar.append(marcar)
        return sub

    def interruptor(padre, texto, clave, defecto=True):
        a = QAction(texto, padre, checkable=True)
        a.triggered.connect(lambda si: poner(clave, si))
        padre.addAction(a)
        sincronizar.append(lambda: a.setChecked(bool(cfg.get(clave, defecto))))

    a_config = menu.addAction('Configuración…')
    menu.addSeparator()
    opciones(menu, 'Cuánto habla', 'habla', configuracion.HABLA_MENU)
    opciones(menu, 'Comentarios', 'detalle', configuracion.DETALLE_MENU)
    sub_personalidad = menu.addMenu('Personalidad')
    interruptor(sub_personalidad, 'Malas palabras suaves', 'groserias')
    interruptor(sub_personalidad, 'Se queja de los proyectos largos', 'quejas')
    sub_musica = menu.addMenu('Música')
    interruptor(sub_musica, 'Comenta los temas de Spotify', 'comentar_musica')
    interruptor(sub_musica, 'Baila (guitarra con folklore, Camaro con phonk)', 'animaciones_musica')
    sub_voz = menu.addMenu('Voz')
    a_silencio = QAction('Silenciar', sub_voz, checkable=True)
    sub_voz.addAction(a_silencio)
    sincronizar.append(lambda: a_silencio.setChecked(bool(cfg['silencio'])))
    opciones(sub_voz, 'Volumen', 'volumen', configuracion.VOLUMEN, cercano=True)
    opciones(sub_voz, 'Velocidad', 'velocidad', configuracion.VELOCIDAD, cercano=True)
    if cfg.get('xtts_python'):                # solo si hay XTTS configurado (opcional, desde el código)
        sub_motor = sub_voz.addMenu('Motor de voz')
        grupo_motor = QActionGroup(sub_motor)
        for clave, texto in (('xtts', 'XTTS argentina (placa de video)'), ('daniela', 'Daniela (liviana)')):
            a = QAction(texto, sub_motor, checkable=True, checked=cfg.get('motor') == clave)
            a.triggered.connect(lambda _=False, k=clave: _motor(k))
            grupo_motor.addAction(a)
            sub_motor.addAction(a)
    sub_voz.addSeparator()
    a_probar = sub_voz.addAction('Probar la voz')
    menu.aboutToShow.connect(lambda: [f() for f in sincronizar])
    menu.addSeparator()
    a_dormir = menu.addAction('Dormir / despertar')
    a_monitor = menu.addAction('Llevar al otro monitor')
    menu.addSeparator()
    a_acerca = menu.addAction('Acerca del Cangrejito')
    a_salir = menu.addAction('Salir')

    def configurar():
        configuracion.abrir(cfg, lambda: nar.decir(f'¡Hola, {cfg["nombre"]}! Así sueno yo.', alta=True))
        a_silencio.setChecked(cfg['silencio'])
        nar._al_dia()

    def _motor(k):
        cfg['motor'] = k
        cfg.guardar()
        if k == 'xtts' and not m.tapados:
            voz.iniciar_xtts()
        elif k != 'xtts':
            voz.apagar_xtts()

    def alternar_silencio():
        cfg['silencio'] = not cfg['silencio']
        cfg.guardar()
        a_silencio.setChecked(cfg['silencio'])
        if cfg['silencio']:
            nar.callar()
            m.momento('silencio', 1.4)
        else:
            m.momento('voz', 1.2)
            nar.con_voz()

    def dormir_despertar():
        if m.base == 'dormir':
            m.despertar()
        else:
            m.actividad('libre')
            m.dormir()

    a_silencio.triggered.connect(lambda _=False: alternar_silencio())
    a_probar.triggered.connect(lambda: nar.decir(f'¡Hola, {cfg["nombre"]}! Así sueno yo.', alta=True))
    a_acerca.triggered.connect(lambda: QMessageBox.about(
        None, 'Acerca del Cangrejito',
        f'<b>{version.NOMBRE} {version.VERSION}</b><br>'
        'Mascota de escritorio que narra lo que hace Claude Code.<br><br>'
        f'Creado por <b>{version.AUTOR}</b>.<br>{version.COPYRIGHT}. Licencia {version.LICENCIA}.<br>'
        f'<a href="{version.REPO}">{version.REPO}</a><br><br>'
        'Voz «Daniela» (Piper, es_AR): CC BY-SA 4.0, dataset OpenSLR 61.<br>'
        'Proyecto de fan, no oficial: no está afiliado a Anthropic.'))
    a_dormir.triggered.connect(dormir_despertar)
    a_monitor.triggered.connect(m.llevar_a_otro_monitor)
    a_config.triggered.connect(configurar)
    def salir():
        # «Salir» vale hasta que cierres esta app de Claude: el lanzador no lo vuelve a abrir antes
        try:
            from vigilante import pids_app_claude
            # los procesos de Claude de ahora; «0» si no hay (siempre visible: vale hasta la próxima sesión)
            (rutas.DATOS / 'apagado.txt').write_text(' '.join(str(p) for p in pids_app_claude()) or '0')
        except Exception:
            log.exception('no pude anotar el apagado')
        app.quit()

    a_salir.triggered.connect(salir)

    bandeja = QSystemTrayIcon(_icono())
    bandeja.setToolTip('Cangrejito de Claude')
    bandeja.setContextMenu(menu)
    bandeja.show()

    # ---------------------------------------------------------------- conexiones
    m.clic_silencio.connect(alternar_silencio)
    m.mimado.connect(nar.mimado)
    m.menu_pedido.connect(lambda pos: menu.exec(pos))
    receptor.evento.connect(nar.evento)

    def app_claude(abierta: bool):
        if abierta:
            nar.oculto = {s.name() for s in app.screens()} <= nombres(vig.tapados)
            if m.modo == 'oculto':
                m.tapados = nombres(vig.tapados)
                m.entrar(al_llegar=llegar)
        elif m.modo != 'oculto':
            nar.chau()
            m.salir()
        else:
            # Claude cerrada y el cangrejito ni había salido: se cierra (el lanzador lo vuelve a abrir)
            app.quit()

    def llegar():
        nar.saludo_app()
        if voz.estado == 'bajando':
            nar.decir('Estoy bajando mi voz de internet, es una sola vez. En un ratito te hablo.')

    def se_fue():
        # se despidió y salió caminando: se cierra del todo, así no ocupa memoria
        nar.oculto = True
        nar.callar()
        app.quit()

    def afk(si: bool):
        nar.afk = si
        if si:
            if not nar.alguna_ocupada():
                m.dormir()
        elif m.despertar() > 60:
            nar.volviste()

    def nombres(rects: set) -> set:
        """Rectángulos de Windows → nombres de pantalla de Qt."""
        out = set()
        for (l, t, r, b) in rects:
            s = app.screenAt(QPoint((l + r) // 2, (t + b) // 2))
            if s is not None:
                out.add(s.name())
        return out

    def tapados(rects: set):
        # juego o video en pantalla completa: se muda al monitor libre; si no queda ninguno, se esconde
        monitores = nombres(rects)
        m.monitores_tapados(monitores)
        estado_gpu['completa'] = bool(monitores)
        placa()
        callar_si_no_se_ve()

    def callar_si_no_se_ve():
        # si no queda ningún monitor libre, el cangrejito se esconde y tampoco habla
        todos = {s.name() for s in app.screens()}
        nar.oculto = m.modo == 'oculto' or todos <= nombres(vig.tapados)
        if nar.oculto:
            nar.callar()

    estado_gpu = {'completa': False, 'vr': False}

    def placa():
        # con un juego en pantalla completa o VR abierto, XTTS suelta la placa de video y habla Daniela
        ocupada = estado_gpu['completa'] or estado_gpu['vr']
        voz.pausar_xtts = ocupada
        if ocupada:
            voz.apagar_xtts()
        elif cfg.get('motor') == 'xtts':
            voz.iniciar_xtts()

    def vr(si: bool):
        estado_gpu['vr'] = si
        placa()
        callar_si_no_se_ve()

    def escuchando(si: bool):
        m.escuchar(si)
        nar.dictado(si)

    def musica(si: bool):
        m.musica = si
        if not si and m.mom == 'bailar':
            m.mom_fin = 0          # se cortó la música: deja de bailar enseguida

    vig.app.connect(app_claude)
    vig.afk.connect(afk)
    vig.monitores_tapados.connect(tapados)
    vig.escuchando.connect(escuchando)
    vig.musica.connect(musica)
    def tema(titulo: str):
        from vigilante import es_de_guitarra, es_funk
        m.funk = es_funk(titulo, cfg.get('artistas_funk') or ())
        m.guitarra = not m.funk and es_de_guitarra(titulo, cfg.get('artistas_guitarra') or ())
        nar.tema_nuevo(titulo)

    vig.tema.connect(tema)
    vig.juego_pesado.connect(vr)
    m.se_fue.connect(se_fue)
    vig.arrancar()

    app.aboutToQuit.connect(lambda: (voz.callar(), cfg.guardar()))
    app.exec()


if __name__ == '__main__':
    main()
