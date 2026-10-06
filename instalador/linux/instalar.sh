#!/usr/bin/env bash
# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: MIT
#
# Instalador para Linux: se corre desde la carpeta descomprimida (./instalar.sh).
#   --si    acepta todo lo recomendado sin preguntar (para instalaciones automáticas)
set -euo pipefail

AQUI="$(cd "$(dirname "$0")" && pwd)"
DESTINO="${XDG_DATA_HOME:-$HOME/.local/share}/cangrejito-programa"
AUTOARRANQUE="${XDG_CONFIG_HOME:-$HOME/.config}/autostart/cangrejito.desktop"
MENU="${XDG_DATA_HOME:-$HOME/.local/share}/applications/cangrejito.desktop"
SI=0; [[ "${1:-}" == "--si" ]] && SI=1

naranja=$'\e[38;5;209m'; gris=$'\e[90m'; verde=$'\e[32m'; amarillo=$'\e[33m'; nada=$'\e[0m'

cabecera() {
    clear 2>/dev/null || true
    cat <<EOF
${naranja}
            ▄▄       ▄▄
           ▀█▀       ▀█▀
     ▄▄▄▄   █▄▄▄▄▄▄▄▄▄█
    ▀▀▀██▄▄█           █    Cangrejito ${1:-}
           █  ▀▄▀  ▀▄▀  █   tu compañero que narra
           █     ▀▀     █   lo que hace Claude Code
            ▀█▀█▀▀▀▀█▀█▀
             ▀ ▀    ▀ ▀
${nada}
EOF
}

pie() { printf '\n%s──────────────────────────────────────────────\n  Hecho por MaxCurat · github.com/MaxCuratAnima/cangrejito%s\n\n' "$gris" "$nada"; }

preguntar() {   # preguntar "texto" s|n  → devuelve 0 si es sí
    local def="$2" r
    if [[ $SI == 1 ]]; then [[ "$def" == s ]]; return; fi
    local opciones="[S/n]"; [[ "$def" == n ]] && opciones="[s/N]"
    read -r -p "  $1 $opciones " r || true
    r="${r:-$def}"; [[ "${r,,}" == s* ]]
}

seguir() { [[ $SI == 1 ]] || read -r -p "  Tocá Enter para seguir (Ctrl+C para salir)... " _ || true; }

# ── 1. Bienvenida ─────────────────────────────────────────────
cabecera "· instalador"
echo "  ¡Hola! Esto instala el Cangrejito en tu usuario (no hace falta ser administrador)."
echo "  Es una mascota que vive en tu escritorio y te cuenta en voz alta lo que hace Claude Code."
echo "  Todo corre en tu PC."
pie; seguir

# ── 2. Licencia ───────────────────────────────────────────────
cabecera "· licencia"
echo "  El Cangrejito es libre: licencia MIT (podés usarlo, cambiarlo y compartirlo, nombrando a su autor)."
echo "  La voz «Daniela» (Piper) se baja aparte la primera vez y tiene licencia CC BY-SA 4.0."
echo "  Proyecto de fan, no oficial: no está afiliado a Anthropic."
pie
preguntar "¿Aceptás la licencia?" s || { echo "  Sin aceptar la licencia no se instala. ¡Chau!"; exit 1; }

# ── 3. Lo que hace falta ──────────────────────────────────────
cabecera "· revisión"
falta=()
command -v xprop >/dev/null 2>&1 || falta+=("x11-utils (para esconderse cuando un juego ocupa la pantalla)")
command -v xprintidle >/dev/null 2>&1 || falta+=("xprintidle (para dormirse cuando no estás)")
command -v playerctl >/dev/null 2>&1 || falta+=("playerctl (para bailar con Spotify)")
ldconfig -p 2>/dev/null | grep -q libportaudio || falta+=("libportaudio2 (para que hable)")
if [[ ${#falta[@]} -eq 0 ]]; then
    echo "  ${verde}Está todo lo que usa.${nada}"
else
    echo "  ${amarillo}Anda igual, pero sin esto algunas cosas se apagan:${nada}"
    for f in "${falta[@]}"; do echo "    · $f"; done
    echo; echo "  En Ubuntu o Debian se instalan con:"
    echo "    sudo apt install x11-utils xprintidle playerctl libportaudio2"
fi
if [[ "${XDG_SESSION_TYPE:-}" == wayland ]]; then
    echo; echo "  Tu escritorio usa Wayland: el cangrejito corre por XWayland (viene en casi todas las distros)."
fi
pie; seguir

# ── 4. Opciones ───────────────────────────────────────────────
cabecera "· opciones"
echo "  En Linux no hay app de escritorio de Claude: el cangrejito aparece cuando corre Claude Code."
echo
OPC=()
if preguntar "¿Narración en castellano? (le pide a Claude Code que explique cada paso; recomendado)" s; then
    OPC+=(--narracion)
fi
if preguntar "¿Mostrarlo siempre, aunque Claude Code no esté abierto?" n; then
    OPC+=(--siempre-visible)
fi
pie

# ── 5. Instalar ───────────────────────────────────────────────
cabecera "· instalando"
pkill -f "$DESTINO/Cangrejito" 2>/dev/null || true
rm -rf "$DESTINO"
mkdir -p "$DESTINO" "$(dirname "$AUTOARRANQUE")" "$(dirname "$MENU")"
cp -r "$AQUI/Cangrejito/." "$DESTINO/"
cp "$AQUI/desinstalar.sh" "$DESTINO/desinstalar.sh"
cp "$AQUI/cangrejito.png" "$DESTINO/cangrejito.png"
chmod +x "$DESTINO/Cangrejito" "$DESTINO/desinstalar.sh"
echo "  · programa en $DESTINO"

for archivo in "$AUTOARRANQUE" "$MENU"; do
    cat > "$archivo" <<EOF
[Desktop Entry]
Type=Application
Name=Cangrejito
Comment=Tu compañero que narra lo que hace Claude Code
Exec="$DESTINO/Cangrejito" --lanzador
Icon=$DESTINO/cangrejito.png
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
EOF
done
echo "  · arranca solo al iniciar sesión y está en el menú de aplicaciones"

"$DESTINO/Cangrejito" --instalar-hooks "${OPC[@]}" \
    && echo "  · Claude Code conectado (hooks en ~/.claude/settings.json, con copia de seguridad)" \
    || echo "  ${amarillo}· no pude conectar Claude Code: mirá ~/.local/share/cangrejito/error-instalacion.txt${nada}"

if [[ $SI == 0 ]]; then
    setsid "$DESTINO/Cangrejito" --lanzador >/dev/null 2>&1 < /dev/null &
fi

# ── 6. Listo ──────────────────────────────────────────────────
cabecera "· ¡listo!"
echo "  ${verde}El Cangrejito quedó instalado.${nada}"
echo "  Aparece cuando corrés Claude Code. La primera vez te pregunta cómo llamarte y baja su voz (unos 110 MB)."
echo "  Para desinstalarlo: $DESTINO/desinstalar.sh"
pie
