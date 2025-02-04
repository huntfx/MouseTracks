# -*- mode: python ; coding: utf-8 -*-

import glob
import os
from scipy import __file__ as scipy_path

a = Analysis(
    ['launch.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/colours.txt', 'config'),
        ('config/language/strings/en_GB.ini', 'config/language/strings'),
        ('config/language/keyboard/keys/en_GB.ini', 'config/language/keyboard/keys'),
        ('config/language/keyboard/layout/en_US.txt', 'config/language/keyboard/layout'),
        ('resources/images/icon.png', 'resources/images'),
    ],
    hiddenimports=['resources.build.scipy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['scipy', 'markupsafe'],
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
            'python27.dll',  # 3352 kb
            '_decimal.pyd',  # 248 kb
            '_lzma.pyd',  # 156 kb
        )
        or name.startswith('libcrypto-3') and name.endswith('.dll')  # 5071 kb
        or name.startswith('libssl-3') and name.endswith('.dll')  # 5071 kb

        # Extra files added by Github Actions
        or name == 'ucrtbase.dll' or name.startswith('api-ms-win-')
    )
]

# Add scipy ndimage binaries
binaries.extend((f'resources/build/scipy/ndimage/{os.path.basename(filepath)}', filepath, 'BINARY')
                for filepath in glob.glob(os.path.join(os.path.dirname(scipy_path), 'ndimage', '_nd_image.*')))

# Remove unused data files
datas = [
    (name, path, type) for name, path, type in a.datas
    if not name.startswith(r'PySide6\translations')  # 6037 kb
    and not name.startswith('MarkupSafe')
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
    version='build\\version.rc',
    icon=['resources\\images\\icon.ico'],
)
