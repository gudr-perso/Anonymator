# anonymator.spec
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files

import os
import sys
from anonymator import __version__
from anonymator.brand import BRANDS, DEV_BRAND, build_target

# Marque de build (packaging, PAS runtime) : cap | cuma | dev (défaut).
_BUILD_BRAND = os.environ.get('ANONYMATOR_BUILD_BRAND', 'dev')
_ENTRY, _EXE_NAME, _ICON = build_target(_BUILD_BRAND)
_BRAND = BRANDS.get(_BUILD_BRAND, DEV_BRAND)

_IS_MAC = sys.platform == 'darwin'
# macOS n'accepte pas les .ico comme icône de bundle : il lui faut un .icns,
# généré au build par scripts/make_icns.sh (non versionné, cf. .gitignore).
# Le .ico reste embarqué dans les datas : Qt s'en sert pour l'icône de fenêtre
# au runtime, sur les trois OS.
if _IS_MAC:
    _ICON = _ICON.replace('.ico', '.icns')

# Gabarits par défaut (default.docx / default.pptx) chargés en package data
# par python-docx / python-pptx — indispensables dans l'exe figé.
ooxml_datas = collect_data_files('docx') + collect_data_files('pptx')

a = Analysis(
    [_ENTRY],
    pathex=[],
    binaries=[],
    datas=[
        ('LICENSE', '.'),
        ('third-party-licenses', 'third-party-licenses'),
        ('anonymator/config/entities.json', 'anonymator/config'),
        ('anonymator/ui/assets/anonymator.ico', 'anonymator/ui/assets'),
        ('anonymator/ui/assets/logo.png', 'anonymator/ui/assets'),
        ('anonymator/ui/assets/logo-cap.png', 'anonymator/ui/assets'),
        ('anonymator/ui/assets/logo-app.png', 'anonymator/ui/assets'),
        ('anonymator/ui/assets/picto.png', 'anonymator/ui/assets'),
        ('anonymator/ui/assets/icons', 'anonymator/ui/assets/icons'),
    ] + ooxml_datas,
    hiddenimports=[
        # Importé paresseusement dans un try/except au démarrage : on le déclare
        # pour garantir sa présence dans l'exe gelé (validation TLS via le
        # magasin Windows, cf. install_os_trust_store).
        'truststore',
        'anonymator.ui.colors',
        'anonymator.ui.theme',
        'anonymator.ui.preferences',
        'anonymator.ui.model_loader',
        'anonymator.ui.home_screen',
        'anonymator.ui.text_screen',
        'anonymator.ui.file_screen',
        'anonymator.ui.settings_screen',
        'anonymator.ui.download_worker',
        'anonymator.ui.main_window',
        'anonymator.ui.text_analyze_worker',
        'anonymator.core.review_session',
        'anonymator.core.chunking',
        'anonymator.core.model_status',
        'anonymator.files.anonymize_file',
        'anonymator.files.csv_io',
        'anonymator.files.xlsx_io',
        'anonymator.files.txt_io',
        'anonymator.files.pdf.extract',
        'anonymator.files.pdf.mapping',
        'anonymator.files.pdf.redact',
        'anonymator.files.pdf.render',
        'anonymator.files.pdf.pdf_io',
        'anonymator.core.pdf_review_session',
        'anonymator.ui.pdf_scan_worker',
        'anonymator.ui.pdf_canvas',
        'anonymator.ui.pdf_screen',
        'fitz',
        'pymupdf',
        'anonymator.files.encoding',
        'anonymator.files.columns',
        'anonymator.report.audit',
        'docx',
        'pptx',
        'anonymator.files.ooxml.docx_io',
        'anonymator.files.ooxml.pptx_io',
        'anonymator.files.ooxml.xml_parts',
        'anonymator.files.ooxml.scan',
        'anonymator.files.ooxml.metadata',
        'anonymator.files.ooxml.run_remap',
        'anonymator.files.ooxml.text_unit',
        'anonymator.core.ooxml_review_session',
        'anonymator.ui.ooxml_scan_worker',
        'anonymator.ui.components.perimetre_card',
        'gliner',
        'torch',
        'transformers',
        'huggingface_hub',
        'openpyxl',
        'PySide6.QtCore',
        'PySide6.QtWidgets',
        'PySide6.QtGui',
        'PySide6.QtSvg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'notebook', 'ipython', 'scipy', 'sklearn'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=_EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,    # pas de fenetre console sur Windows / macOS
    disable_windowed_traceback=False,
    argv_emulation=False,
    # None = architecture de la machine de build. PyInstaller ne cross-compile
    # pas : le .app macOS doit etre construit sur macOS (cf. le workflow
    # .github/workflows/build-macos.yml). 'universal2' est hors d'atteinte,
    # PyTorch ne publiant plus de wheels macOS x86_64 depuis la 2.3 —
    # la cible macOS est donc arm64 (Apple Silicon) uniquement.
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=f'anonymator/ui/assets/{_ICON}',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=_EXE_NAME,
)

# Sur macOS, COLLECT ne produit qu'un binaire Unix nu, non lançable depuis le
# Finder : c'est BUNDLE qui fabrique le .app double-cliquable.
if _IS_MAC:
    app = BUNDLE(
        coll,
        name=f'{_EXE_NAME}.app',
        icon=f'anonymator/ui/assets/{_ICON}',
        bundle_identifier=f'io.github.gudr-perso.{_EXE_NAME}',
        version=__version__,
        info_plist={
            'CFBundleName': _BRAND.product_name,
            'CFBundleDisplayName': _BRAND.product_name,
            'CFBundleShortVersionString': __version__,
            'CFBundleVersion': __version__,
            # Sans ce drapeau, macOS affiche l'app en 72 dpi flou sur Retina.
            'NSHighResolutionCapable': True,
            # Big Sur = premiere version Apple Silicon.
            'LSMinimumSystemVersion': '11.0',
            'LSApplicationCategoryType': 'public.app-category.productivity',
            'NSHumanReadableCopyright': 'AGPL-3.0-or-later',
        },
    )
