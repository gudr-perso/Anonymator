# anonymator.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['anonymator/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('anonymator/config/entities.json', 'anonymator/config'),
    ],
    hiddenimports=[
        'anonymator.ui.colors',
        'anonymator.ui.theme',
        'anonymator.ui.preferences',
        'anonymator.ui.model_loader',
        'anonymator.ui.home_screen',
        'anonymator.ui.text_screen',
        'anonymator.ui.file_screen',
        'anonymator.ui.settings_screen',
        'anonymator.ui.setup_screen',
        'anonymator.ui.download_worker',
        'anonymator.core.review_session',
        'anonymator.core.chunking',
        'anonymator.core.model_status',
        'anonymator.files.anonymize_file',
        'anonymator.files.csv_io',
        'anonymator.files.xlsx_io',
        'anonymator.files.txt_io',
        'anonymator.files.encoding',
        'anonymator.files.columns',
        'anonymator.report.audit',
        'gliner',
        'torch',
        'transformers',
        'huggingface_hub',
        'openpyxl',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'notebook', 'ipython', 'scipy', 'sklearn'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='anonymator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,    # pas de fenetre console sur Windows
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='anonymator',
)
