# Cangrejito — mascota de escritorio que narra lo que hace Claude Code.
# Copyright (c) 2026 MaxCurat (https://github.com/MaxCuratAnima/cangrejito)
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Receta de PyInstaller para Cangrejito.exe (una carpeta con el programa y sus librerías).
#   python -m PyInstaller cangrejito.spec --noconfirm
# Sale en dist\Cangrejito\. El instalador (instalador\cangrejito.iss) empaqueta esa carpeta.
import sys

from PyInstaller.utils.hooks import collect_data_files

sys.path.insert(0, '.')
import version as V  # noqa: E402

WINDOWS = sys.platform == 'win32'
datas = [('cangrejito.ico', '.'), ('temas_auto.ejemplo.json', '.')]
# Piper necesita el diccionario de pronunciación de espeak-ng (nada de lo de entrenamiento)
datas += collect_data_files('piper', includes=['espeak-ng-data/**'])

a = Analysis(
    ['app.py'],
    pathex=['.'],
    datas=datas,
    hiddenimports=['avisar', 'lanzador', 'instalar_claude', 'cangrejito_app', 'version',
                   'piper.voice', 'piper.config']
                  + (['microfono', 'sistema_windows', 'comtypes.stream'] if WINDOWS else ['sistema_linux']),
    excludes=['tkinter', 'torch', 'TTS', 'piper.train', 'matplotlib', 'pytest', 'IPython'],
    noarchive=False,
)

# datos del autor en las propiedades del .exe (clic derecho → Propiedades → Detalles)
version_info = None
if WINDOWS:
    from PyInstaller.utils.win32.versioninfo import (FixedFileInfo, StringFileInfo, StringStruct, StringTable,
                                                     VarFileInfo, VarStruct, VSVersionInfo)
    numeros = tuple(int(x) for x in V.VERSION.split('.')) + (0,)
    version_info = VSVersionInfo(
        ffi=FixedFileInfo(filevers=numeros, prodvers=numeros),
        kids=[StringFileInfo([StringTable('0C0A04B0', [
            StringStruct('CompanyName', V.AUTOR),
            StringStruct('FileDescription', 'Cangrejito: mascota que narra lo que hace Claude Code'),
            StringStruct('FileVersion', V.VERSION),
            StringStruct('LegalCopyright', V.COPYRIGHT),
            StringStruct('ProductName', V.NOMBRE),
            StringStruct('ProductVersion', V.VERSION),
            StringStruct('OriginalFilename', 'Cangrejito.exe')])]),
              VarFileInfo([VarStruct('Translation', [0x0C0A, 1200])])])
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Cangrejito',
    icon='cangrejito.ico',
    console=False,                 # sin ventana negra
    upx=False,
    version=version_info,
)
coll = COLLECT(exe, a.binaries, a.datas, name='Cangrejito', upx=False)
