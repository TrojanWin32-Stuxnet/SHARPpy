# -*- mode: python -*-
from pathlib import Path
import sys

from PyInstaller.config import CONF

PROJECT_ROOT = Path(SPECPATH).resolve().parent
RUNSHARP_PATH = PROJECT_ROOT / 'runsharp'
sys.path.insert(0, str(PROJECT_ROOT))

from runsharp.pyinstaller_support import (
    collect_windows_resources,
    collect_windows_ssl_binaries,
    write_version_runtime_hook,
)
from sharppy._version import get_versions

version_hook = write_version_runtime_hook(CONF['workpath'], get_versions())

a = Analysis(
    [str(RUNSHARP_PATH / 'SHARPpy.py')],
    pathex=[str(RUNSHARP_PATH), str(PROJECT_ROOT)],
    binaries=collect_windows_ssl_binaries([sys.prefix, sys.base_prefix]),
    datas=collect_windows_resources(PROJECT_ROOT),
    hiddenimports=[
        'xml.etree.ElementTree', 'sharppy.io.pecan_decoder',
        'sharppy.io.spc_decoder', 'sharppy.io.buf_decoder',
        'sharppy.io.uwyo_decoder', 'sharppy.io.nucaps_decoder',
        'datasources.available', 'sharppy.sharptab.prof_collection', 'certifi',
    ],
    hookspath=[],
    runtime_hooks=[str(version_hook)],
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SHARPpy',
    debug=False,
    strip=False,
    upx=False,
    console=True,
    icon=str(RUNSHARP_PATH / 'icons' / 'SHARPpy.ico'),
)
