# -*- mode: python ; coding: utf-8 -*-
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import copy_metadata

datas = [("D:/Python311/Lib/site-packages/streamlit/runtime","./streamlit/runtime")]
datas += collect_data_files("streamlit")
datas += collect_data_files("st_aggrid")
datas += collect_data_files("streamlit_ace")
datas += collect_data_files("barfi")
datas += copy_metadata("streamlit")
datas += copy_metadata("streamlit-aggrid")
datas += copy_metadata("streamlit_ace")
datas += copy_metadata("barfi")
block_cipher = None


a = Analysis(
    [
        'run.py',
        'D:\\Python311\\Lib\\site-packages\\streamlit\\__init__.py',
        'D:\\Python311\\Lib\\site-packages\\streamlit_ace\\__init__.py',
        'D:\\Python311\\Lib\\site-packages\\st_aggrid\\__init__.py',
        'D:\\Python311\\Lib\\site-packages\\flashtext\\__init__.py',
        'D:\\Python311\\Lib\\site-packages\\jsonpath_rw\\__init__.py',
        'D:\\Python311\\Lib\\site-packages\\jsonpath_rw\\bin\\__init__.py',
        'D:\\Python311\\Lib\\site-packages\\jsonpath_rw\\parser.py',
        'D:\\Python311\\Lib\\site-packages\\deepdiff\\__init__.py',
        'D:\\Python311\\Lib\\site-packages\\deepdiff\\diff.py',
        'D:\\Python311\\Lib\\site-packages\\pyarrow\\__init__.py',
        'D:\\Python311\\Lib\\site-packages\\barfi\\__init__.py'
    ],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'pandas','matplotlib.pyplot','numpy','pyarrow.vendored.version','barfi'
    ],
    hookspath=['./hooks'],
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
    name='run',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='D:\\IMRMToolsLibrary\\Hsmoking\\img\\favicon.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
