# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['start_hub.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/colours.txt', 'config'),
        ('resources/images/icon.png', 'resources/images'),
    ],
    hiddenimports=['resources.build.scipy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# Remove unused binaries
binaries = [
    (name, path, type) for name, path, type in a.binaries
    if name in (r'PySide6\Qt6Core.dll', r'PySide6\Qt6Gui.dll', r'PySide6\Qt6Widgets.dll',
                r'PySide6\QtCore.pyd', r'PySide6\QtGui.pyd', r'PySide6\QtWidgets.pyd')
    or name.startswith((r'PySide6\plugins\platforms', r'PySide6\plugins\styles'))
    or not (
        name.startswith(r'PySide6\Qt6') and name.endswith('.dll')
        or name.startswith(r'PySide6\Qt') and name.endswith('.pyd')
        or name.startswith((
            r'PIL\_webp',  # 398 kb
            r'PIL\_imagingcms',  # 257 kb
            r'PySide6\plugins',  # 2864 kb
            r'numpy\random',  # 2288 kb
            r'numpy\fft',  # 273 kb
        ))
        or name in (
            r'PySide6\opengl32sw.dll',  # 20157 kb
            'libcrypto-3.dll',  # 5071 kb
            'python27.dll',  # 3352 kb
            'libssl-3.dll',  # 769 kb
            '_decimal.pyd',  # 248 kb
            '_lzma.pyd',  # 156 kb
        )
    )
]

# Remove unused data files
datas = [
    (name, path, type) for name, path, type in a.datas
    if not name.startswith(r'PySide6\translations')  # 6037 kb
]

exe = EXE(
    pyz,
    a.scripts,
    binaries,
    datas,
    [],
    name='MouseTracks',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources\\images\\icon.ico'],
)
