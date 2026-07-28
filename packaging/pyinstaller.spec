# -*- mode: python ; coding: utf-8 -*-
# Single spec used identically by the Linux, macOS, and Windows CI runners.
# PyInstaller reads the current platform at build time and emits the matching
# binary format (ELF, Mach-O, or PE/.exe) — it does not cross-compile.

import os

SRC_DIR = os.path.join(SPECPATH, "..", "src")

a = Analysis(
    [os.path.join(SRC_DIR, "workstation_setup", "__main__.py")],
    pathex=[SRC_DIR],
    binaries=[],
    datas=[],
    # questionary/prompt_toolkit lazily import some renderer/style modules
    # that PyInstaller's static analysis can miss; listed explicitly here.
    hiddenimports=["questionary", "prompt_toolkit", "rich"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="workstation-setup",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
