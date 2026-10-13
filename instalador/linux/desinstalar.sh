#!/usr/bin/env bash
# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
#
# Desinstala el Cangrejito en Linux: saca los hooks de Claude Code, el autoarranque y el programa.
# Tus ajustes quedan en ~/.local/share/cangrejito, por si lo volvés a instalar.
set -uo pipefail

DESTINO="${XDG_DATA_HOME:-$HOME/.local/share}/cangrejito-programa"
[[ -x "$DESTINO/Cangrejito" ]] && "$DESTINO/Cangrejito" --quitar-hooks
pkill -f "$DESTINO/Cangrejito" 2>/dev/null || true
rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/cangrejito.desktop" \
      "${XDG_DATA_HOME:-$HOME/.local/share}/applications/cangrejito.desktop"
rm -rf "$DESTINO"
echo "El Cangrejito se desinstaló. ¡Chau!  (Hecho por MaxCurat)"
