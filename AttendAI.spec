# PyInstaller spec for AttendAI
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

hiddenimports = collect_submodules('flask')
datas = collect_data_files('app')

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas + [('app/templates', 'app/templates'), ('app/static', 'app/static'), ('models', 'models'), ('data', 'data')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='AttendAI', debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=True)
