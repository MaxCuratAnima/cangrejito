# Receta de PyInstaller para Cangrejito.exe (una carpeta con el programa y sus librerías).
#   python -m PyInstaller cangrejito.spec --noconfirm
# Sale en dist\Cangrejito\. El instalador (instalador\cangrejito.iss) empaqueta esa carpeta.
from PyInstaller.utils.hooks import collect_data_files

datas = [('cangrejito.ico', '.'), ('temas_auto.ejemplo.json', '.')]
# Piper necesita el diccionario de pronunciación de espeak-ng (nada de lo de entrenamiento)
datas += collect_data_files('piper', includes=['espeak-ng-data/**'])

a = Analysis(
    ['app.py'],
    pathex=['.'],
    datas=datas,
    hiddenimports=['avisar', 'lanzador', 'microfono', 'instalar_claude', 'cangrejito_app',
                   'piper.voice', 'piper.config', 'comtypes.stream'],
    excludes=['tkinter', 'torch', 'TTS', 'piper.train', 'matplotlib', 'pytest', 'IPython'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name='Cangrejito',
    icon='cangrejito.ico',
    console=False,                 # sin ventana negra
    upx=False,
    version=None,
)
coll = COLLECT(exe, a.binaries, a.datas, name='Cangrejito', upx=False)
