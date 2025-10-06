# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

import os
import vgamepad

vgamepad_path = os.path.dirname(vgamepad.__file__)
icon_path = 'icon.ico'

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[
        (os.path.join(vgamepad_path, 'win', 'vigem', 'client', 'x64', '*.dll'), 'vgamepad/win/vigem/client/x64'),
    ],
    datas=[
        ('config', 'config'),
        ('src', 'src'),
    ],
    hiddenimports=[
        'vgamepad',
        'pygame',
        'tkinter',
        'json',
        'logging',
        'config_manager',
        'logger_config',
        'recorder.gamepad_recorder',
        'recorder.gamepad_state',
        'recorder.sequence_manager',
        'recorder.virtual_gamepad',
        'ui.overlay_gui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HollowKnightGamepadRecorder',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Без консоли!
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,  # Иконка приложения
)
