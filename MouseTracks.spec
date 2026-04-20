# -*- mode: python ; coding: utf-8 -*-

import glob
import os
import sys

import certifi
from scipy import __file__ as scipy_path

sys.path.insert(0, os.path.abspath('.'))
from mousetracks2 import __version__ as version
from mousetracks2.constants import PACKAGE_IDENTIFIER
from mousetracks2.utils.update import generate_exe_name

target_name = os.environ.get('EXE_BASENAME', generate_exe_name(with_extension=False))
datas = [
    ('config/colours.txt', 'config'),
    ('config/AppList.txt', 'config'),
    ('config/language/strings/en_GB.ini', 'config/language/strings'),
    ('config/language/keyboard/keys/en_GB.ini', 'config/language/keyboard/keys'),
    ('config/language/keyboard/layout/en_US.txt', 'config/language/keyboard/layout'),
    ('resources/images/icon.png', 'resources/images'),
    ('resources/fonts/liberation-sans.regular.ttf', 'resources/fonts'),
    (certifi.where(), 'certifi'),
]
excludes = ['scipy', 'markupsafe']
hiddenimports = ['resources.build.scipy', 'pynput.keyboard._xorg', 'pynput.mouse._xorg', '_cffi_backend']
upx_exclude = ['resources/build/scipy/ndimage/_nd_image.cp311-win_amd64.dll.a']

a_main = Analysis(
    ['mousetracks2/__main__.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz_main = PYZ(a_main.pure)

# Remove unused binaries
binaries = [
    (name, path, type) for name, path, type in a_main.binaries
    if name.startswith((
        os.path.join('PySide6', 'Qt6Core'),
        os.path.join('PySide6', 'Qt6Gui'),
        os.path.join('PySide6', 'Qt6Widgets'),
        os.path.join('PySide6', 'QtCore'),
        os.path.join('PySide6', 'QtGui'),
        os.path.join('PySide6', 'QtWidgets'),
        os.path.join('PySide6', 'plugins', 'platforms'),
        os.path.join('PySide6', 'plugins', 'styles'),
    ))

    or not (
        name.startswith(os.path.join('PySide6', 'Qt6')) and name.endswith('.dll')
        or name.startswith(os.path.join('PySide6', 'Qt')) and name.endswith('.pyd')
        or name.startswith((
            os.path.join('PIL', '_webp'),  # 398 kb
            os.path.join('PIL', '_imagingcms'),  # 257 kb
            os.path.join('PySide6', 'plugins'),  # 2864 kb
            os.path.join('PySide6', 'QtNetwork.abi3.so'),
            os.path.join('numpy', 'random'),  # 2288 kb
            os.path.join('numpy', 'fft'),  # 273 kb
        ))
        or name in (
            os.path.join('PySide6', 'opengl32sw.dll'),  # 20157 kb
            'python27.dll',  # 3352 kb
            '_decimal.pyd',  # 248 kb
            '_lzma.pyd',  # 156 kb
        )

        # Extra files added by Github Actions
        or name == 'ucrtbase.dll' or name.startswith('api-ms-win-')

        # Linux
        or name.startswith(os.path.join('PySide6', 'Qt', 'plugins', 'imageformats')) and name.endswith('.so') and 'png' not in name  # 1.8 mb
        or name.startswith(os.path.join('PySide6', 'Qt', 'plugins', 'tls')) and name.endswith('.so')  # 0.5 mb
        or name.startswith(os.path.join('PySide6', 'Qt', 'lib', 'libQt6Network'))  # 2.1mb
        or name.startswith(os.path.join('PySide6', 'Qt', 'lib', 'libQt6Quick'))  # 7.6mb
        or name.startswith(os.path.join('PySide6', 'Qt', 'lib', 'libQt6Qml'))  # 6.3mb
        or name.startswith(os.path.join('PySide6', 'Qt', 'lib', 'libQt6OpenGL'))  # 5.2mb
        or name.startswith(os.path.join('PySide6', 'Qt', 'lib', 'libQt6Pdf'))  # 5.2mb
        or name.startswith(os.path.join('PySide6', 'Qt', 'lib', 'libQt6Svg'))  # 0.5mb
    )
]

# Add scipy ndimage binaries
binaries.extend((f'resources/build/scipy/ndimage/{os.path.basename(filepath)}', filepath, 'BINARY')
                for filepath in glob.glob(os.path.join(os.path.dirname(scipy_path), 'ndimage', '_nd_image.*')))

# Remove unused data files
exe_datas = [
    (name, path, type) for name, path, type in a_main.datas
    if not name.startswith(os.path.join('PySide6', 'translations'))  # 6037 kb
    and not name.startswith('MarkupSafe')
]

exe_main = EXE(
    pyz_main,
    a_main.scripts,
    binaries,
    exe_datas,
    [],
    name=target_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=upx_exclude,
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

# Portable executable
a_portable = Analysis(
    ['mousetracks2/__main__.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['resources/build/hooks/portable.py'],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz_portable = PYZ(a_portable.pure)

exe_portable = EXE(
    pyz_portable,
    a_portable.scripts,
    binaries,
    exe_datas,
    [],
    name=target_name + '-portable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=upx_exclude,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='build\\version-portable.rc',
    icon=['resources\\images\\icon.ico'],
)


# Launcher executable
if sys.platform == 'win32':
    a_launcher = Analysis(
        ['launcher.py'],
        pathex=[],
        binaries=[],
        datas=[],
        excludes=[],
        hiddenimports=['_cffi_backend'],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        noarchive=False,
        optimize=0,
    )

    pyz_launcher = PYZ(a_launcher.pure)

    exe_launcher = EXE(
        pyz_launcher,
        a_launcher.scripts,
        a_launcher.binaries,
        a_launcher.datas,
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
        version='build\\version-installer.rc',
        icon='resources/images/icon.ico'
    )

# macOS bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe_main,
        name=f'{target_name}.app',
        icon='resources/images/icon.icns',
        bundle_identifier=PACKAGE_IDENTIFIER,
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False',
        },
    )
