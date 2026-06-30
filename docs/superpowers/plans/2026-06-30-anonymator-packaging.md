# Anonymator — Plan 4 : Packaging PyInstaller + README + Écran 1er téléchargement modèle

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Distribuer Anonymator comme dossier exécutable Windows (PyInstaller `--onedir`), afficher un écran de guidage au 1er lancement pour le téléchargement du modèle GLiNER, et fournir un README utilisateur.

**Architecture:** Trois éléments ajoutés au projet existant : (1) `model_status.py` (non-Qt) détecte si le modèle GLiNER est dans le cache HuggingFace ; (2) `setup_screen.py` + `download_worker.py` guident le téléchargement en UI avec un `QThread`, intégrés dans `MainWindow` via un paramètre `skip_setup` pour les tests ; (3) `anonymator.spec` PyInstaller pour le build, plus `README.md` utilisateur.

**Tech Stack:** PyInstaller ≥ 6.0, pyinstaller-hooks-contrib, PySide6, gliner. Réutilise tout `anonymator.*` des Plans 1-3.

**Référence spec :** `docs/superpowers/specs/2026-06-29-anonymator-design.md` §2 (packaging exe Windows, modèle découplé), §9 (modèle absent → téléchargement guidé).

> **Hors périmètre :** NSIS/Inno Setup, code signing, auto-update, icône personnalisée.

> **Pré-requis pour Task 4 (build) :** `gliner` + `torch` installés dans `.venv` et `.venv` exclu de la synchro pCloud (cf. `docs/installation-gliner.md` §2-3). Les Tasks 0-3 ne nécessitent PAS torch.

---

## Structure des fichiers (Plan 4)

```
anonymator/core/model_status.py    détection disponibilité modèle (non-Qt, testable)
anonymator/ui/download_worker.py   QThread téléchargement modèle GLiNER
anonymator/ui/setup_screen.py      écran de guidage 1er lancement
anonymator/ui/main_window.py       modifié : vérifie le modèle au démarrage (+ skip_setup)
tests/test_model_status.py         TDD model_status (sans Qt, sans torch)
tests/test_setup_screen.py         smoke test pytest-qt (sans vrai téléchargement)
tests/test_ui_smoke.py             modifié : skip_setup=True + 2 nouveaux tests
tests/test_entrypoint.py           modifié : patch is_model_available
anonymator.spec                    configuration PyInstaller (onedir, windowed)
README.md                          guide utilisateur (installation, 1er lancement, usage)
requirements.txt                   + pyinstaller>=6.0, pyinstaller-hooks-contrib
.gitignore                         + dist/ build/
```

---

### Task 0 : Détection disponibilité modèle (non-Qt)

**Files:** Create `anonymator/core/model_status.py` ; Create `tests/test_model_status.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_model_status.py
from pathlib import Path
from unittest.mock import patch
from anonymator.core.model_status import is_model_available, MODEL_NAME, model_cache_dir

def test_model_name_is_gliner_multi():
    assert MODEL_NAME == "urchade/gliner_multi-v2.1"

def test_cache_dir_is_in_home():
    d = model_cache_dir()
    assert d.parts[-1] == "models--urchade--gliner_multi-v2.1"
    assert str(Path.home()) in str(d)

def test_available_when_snapshots_exist(tmp_path):
    fake_dir = tmp_path / "models--urchade--gliner_multi-v2.1" / "snapshots" / "abc123"
    fake_dir.mkdir(parents=True)
    with patch("anonymator.core.model_status.model_cache_dir",
               return_value=tmp_path / "models--urchade--gliner_multi-v2.1"):
        assert is_model_available() is True

def test_unavailable_when_dir_absent(tmp_path):
    with patch("anonymator.core.model_status.model_cache_dir",
               return_value=tmp_path / "absent"):
        assert is_model_available() is False
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_model_status.py -q`
Expected : `ModuleNotFoundError` ou `ImportError`.

- [ ] **Step 3 : Implémenter**

```python
# anonymator/core/model_status.py
from pathlib import Path

MODEL_NAME = "urchade/gliner_multi-v2.1"
_CACHE_SUBDIR = "models--urchade--gliner_multi-v2.1"

def model_cache_dir() -> Path:
    return Path.home() / ".cache" / "huggingface" / "hub" / _CACHE_SUBDIR

def is_model_available() -> bool:
    snapshots = model_cache_dir() / "snapshots"
    return snapshots.exists() and any(snapshots.iterdir())
```

- [ ] **Step 4 : Run → PASS** (4 tests).

- [ ] **Step 5 : Suite complète**

Run : `.venv\Scripts\python.exe -m pytest -q`
Attendu : 95 passed, 1 deselected.

- [ ] **Step 6 : Commit**

```bash
git add anonymator/core/model_status.py tests/test_model_status.py
git commit -m "feat: détection disponibilité modèle GLiNER en cache HuggingFace"
```

---

### Task 1 : SetupScreen + DownloadWorker

**Files:** Create `anonymator/ui/download_worker.py` ; Create `anonymator/ui/setup_screen.py` ; Create `tests/test_setup_screen.py`

- [ ] **Step 1 : Test smoke qui échoue**

```python
# tests/test_setup_screen.py
from anonymator.ui.setup_screen import SetupScreen

def test_setup_screen_builds(qtbot):
    s = SetupScreen()
    qtbot.addWidget(s)
    assert s.btn_start is not None
    assert s.label_status is not None

def test_on_download_finished_emits_model_ready(qtbot):
    """Appelle _on_download_finished directement pour éviter le vrai téléchargement."""
    s = SetupScreen()
    qtbot.addWidget(s)
    ready = []
    s.model_ready.connect(lambda: ready.append(True))
    s._on_download_finished()
    assert ready
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_setup_screen.py -q`

- [ ] **Step 3 : Implémenter download_worker.py**

```python
# anonymator/ui/download_worker.py
from PySide6.QtCore import QThread, Signal

class DownloadWorker(QThread):
    status = Signal(str)
    finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            self.status.emit("Chargement du modèle GLiNER…")
            from anonymator.ner import GlinerDetector  # import torch différé
            GlinerDetector()                            # déclenche le téléchargement HF
            self.finished.emit()
        except Exception as exc:
            self.error.emit(str(exc))
```

- [ ] **Step 4 : Implémenter setup_screen.py**

```python
# anonymator/ui/setup_screen.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                               QProgressBar, QTextEdit)
from PySide6.QtCore import Qt, Signal
from anonymator.ui.download_worker import DownloadWorker

class SetupScreen(QWidget):
    model_ready = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Anonymator — Configuration initiale")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        desc = QLabel(
            "Le modèle de détection GLiNER (~300 Mo) doit être téléchargé\n"
            "une seule fois. Une connexion Internet est nécessaire."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        self.label_status = QLabel("Prêt.")
        self.label_status.setAlignment(Qt.AlignCenter)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)    # indéterminé
        self.progress.setVisible(False)
        self.btn_start = QPushButton("Télécharger le modèle")
        self.btn_start.clicked.connect(self._start)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(100)
        for w in (title, desc, self.label_status, self.progress,
                  self.btn_start, self._log):
            layout.addWidget(w)
        layout.addStretch()
        self._worker: DownloadWorker | None = None

    def _start(self):
        self.btn_start.setEnabled(False)
        self.progress.setVisible(True)
        self.label_status.setText("Téléchargement en cours…")
        self._worker = DownloadWorker()
        self._worker.status.connect(self._on_status)
        self._worker.finished.connect(self._on_download_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_status(self, msg: str):
        self._log.append(msg)

    def _on_download_finished(self):
        self.progress.setVisible(False)
        self.label_status.setText("Modèle prêt !")
        self.model_ready.emit()

    def _on_error(self, msg: str):
        self.progress.setVisible(False)
        self.label_status.setText("Erreur lors du téléchargement.")
        self._log.append(f"[ERREUR] {msg}")
        self.btn_start.setEnabled(True)
```

- [ ] **Step 5 : Run → PASS** (2 tests).

- [ ] **Step 6 : Suite complète**

Run : `.venv\Scripts\python.exe -m pytest -q`
Attendu : 97 passed, 1 deselected.

- [ ] **Step 7 : Commit**

```bash
git add anonymator/ui/download_worker.py anonymator/ui/setup_screen.py tests/test_setup_screen.py
git commit -m "feat: SetupScreen + DownloadWorker (guidage 1er téléchargement modèle)"
```

---

### Task 2 : Intégrer SetupScreen dans MainWindow

**Files:** Modify `anonymator/ui/main_window.py` ; Modify `tests/test_ui_smoke.py` ; Modify `tests/test_entrypoint.py`

- [ ] **Step 1 : Modifier tests/test_ui_smoke.py**

Remplacer le contenu complet du fichier par :

```python
# tests/test_ui_smoke.py
from unittest.mock import patch
from anonymator.ui.main_window import MainWindow

def test_main_window_builds_and_has_home(qtbot):
    win = MainWindow(skip_setup=True)
    qtbot.addWidget(win)
    assert win.stack.count() >= 1
    assert win.home.btn_text is not None
    assert win.home.btn_file is not None

def test_navigation_to_text_and_file(qtbot):
    win = MainWindow(skip_setup=True)
    qtbot.addWidget(win)
    win.show_text()
    assert win.stack.currentWidget() is win.text_screen
    win.show_file()
    assert win.stack.currentWidget() is win.file_screen
    win.show_home()
    assert win.stack.currentWidget() is win.home

def test_main_window_shows_setup_when_model_absent(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=False):
        win = MainWindow()
        qtbot.addWidget(win)
        assert win.stack.currentWidget() is win.setup_screen

def test_main_window_skips_setup_when_model_present(qtbot):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = MainWindow()
        qtbot.addWidget(win)
        assert win.stack.currentWidget() is win.home
```

- [ ] **Step 2 : Modifier tests/test_entrypoint.py**

```python
# tests/test_entrypoint.py
from unittest.mock import patch

def test_build_app_returns_window(qtbot):
    from anonymator.__main__ import build_window
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = build_window()
    qtbot.addWidget(win)
    assert win.windowTitle() == "Anonymator"
```

- [ ] **Step 3 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_ui_smoke.py tests/test_entrypoint.py -q`
Les 4 tests de smoke + 1 entrypoint échouent (MainWindow ne prend pas encore `skip_setup`).

- [ ] **Step 4 : Modifier anonymator/ui/main_window.py**

Remplacer le contenu complet du fichier par :

```python
# anonymator/ui/main_window.py
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from anonymator.referential import Referential
from anonymator.ui.preferences import Preferences
from anonymator.ui.theme import build_qss
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.home_screen import HomeScreen
from anonymator.ui.text_screen import TextScreen
from anonymator.ui.file_screen import FileScreen
from anonymator.ui.settings_screen import SettingsScreen
from anonymator.ui.setup_screen import SetupScreen
from anonymator.core.model_status import is_model_available

PREFS_PATH = Path.home() / ".anonymator" / "preferences.json"

class MainWindow(QMainWindow):
    def __init__(self, loader: ModelLoader | None = None,
                 prefs_path: Path = PREFS_PATH,
                 skip_setup: bool = False):
        super().__init__()
        self.setWindowTitle("Anonymator")
        self.prefs_path = prefs_path
        self.prefs = Preferences.load(prefs_path)
        self.ref = Referential.load_default()
        self.loader = loader or ModelLoader()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.setup_screen = SetupScreen()
        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings)
        self.text_screen = TextScreen(self.ref, self.loader, self.prefs, self.show_home)
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs, self.show_home)
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        for w in (self.setup_screen, self.home, self.text_screen,
                  self.file_screen, self.settings_screen):
            self.stack.addWidget(w)

        self.setup_screen.model_ready.connect(self.show_home)
        self._apply_theme()

        if skip_setup or is_model_available():
            self.show_home()
        else:
            self.stack.setCurrentWidget(self.setup_screen)

    def _apply_theme(self):
        self.setStyleSheet(build_qss(self.prefs.theme))

    def _apply_prefs(self):
        self.prefs.save(self.prefs_path)
        self._apply_theme()

    def show_home(self):     self.stack.setCurrentWidget(self.home)
    def show_text(self):     self.stack.setCurrentWidget(self.text_screen)
    def show_file(self):     self.stack.setCurrentWidget(self.file_screen)
    def show_settings(self): self.stack.setCurrentWidget(self.settings_screen)
```

- [ ] **Step 5 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest -q`
Attendu : 99 passed, 1 deselected.

- [ ] **Step 6 : Commit**

```bash
git add anonymator/ui/main_window.py tests/test_ui_smoke.py tests/test_entrypoint.py
git commit -m "feat: SetupScreen intégrée dans MainWindow (skip_setup pour tests)"
```

---

### Task 3 : README utilisateur

**Files:** Create `README.md`

- [ ] **Step 1 : Créer README.md**

```markdown
# Anonymator

Application locale Windows d'anonymisation de texte et de fichiers comptables.

Détecte et remplace les données personnelles (noms, emails, IBAN, numéros de téléphone…) par des étiquettes de catégorie (`[PERSONNE]`, `[EMAIL]`…). **Aucune donnée ne quitte votre machine.**

---

## Installation

1. Télécharger et dézipper `Anonymator-vX.X.zip`.
2. Lancer `anonymator.exe` dans le dossier dézippé.
3. Au **premier lancement**, l'application télécharge le modèle de détection GLiNER (~300 Mo).
   Une connexion Internet est nécessaire pour cette étape initiale uniquement.
   Les lancements suivants fonctionnent hors-ligne.

---

## Utilisation

### Mode Texte

1. Cliquer **Texte** sur l'écran d'accueil.
2. Coller ou saisir du texte dans la zone de saisie.
3. Cliquer **Analyser** → les entités détectées apparaissent surlignées (couleur par type) et listées.
4. Décocher les entités à **ne pas** masquer.
5. Cliquer **Appliquer le masquage** → le texte anonymisé s'affiche.
6. **Copier** ou **Exporter .txt**.

### Mode Fichier

1. Cliquer **Fichier** sur l'écran d'accueil.
2. Cliquer **Ouvrir…** → sélectionner un `.txt`, `.csv` ou `.xlsx`.
3. Aperçu du fichier dans le tableau.
4. Cliquer **Anonymiser et enregistrer** → le fichier anonymisé est sauvegardé dans le dossier de sortie.
5. L'original n'est **jamais modifié**.

### Paramètres

- **Thème** : France Cuma Numérique (vert) ou CAP Consulting (bleu).
- **Dossier de sortie** : dossier cible pour les fichiers anonymisés.

---

## Formats supportés

| Format | Support |
|--------|---------|
| `.txt` | ✅ Texte intégral |
| `.csv` | ✅ Par colonnes (séparateur auto-détecté, encodage préservé) |
| `.xlsx` | ✅ Édition en place (styles, formules et onglets conservés) |
| `.pdf` | ❌ Non supporté en v1 |

---

## Données & confidentialité

- Traitement **100 % local** : aucun appel réseau en usage normal.
- Le téléchargement initial du modèle GLiNER est le seul accès réseau (une seule fois).
- Le modèle est mis en cache dans `%USERPROFILE%\.cache\huggingface`.
- Le rapport d'audit (optionnel) contient les valeurs remplacées — à stocker et partager avec précaution.

---

## Problèmes connus

| Symptôme | Solution |
|----------|----------|
| Téléchargement très lent au 1er lancement | Connexion Internet requise (~300 Mo) ; patienter |
| Fichier CSV mal parsé | Vérifier encodage (Latin-1/UTF-8) et séparateur |
| `.pdf` refusé | Non supporté en v1 |
| Nom manqué lors de la détection | Ajouter manuellement via la sélection de texte (mode Texte) |
```

- [ ] **Step 2 : Commit**

```bash
git add README.md
git commit -m "docs: README utilisateur (installation, usage, formats)"
```

---

### Task 4 : PyInstaller — configuration et build

**Files:** Create `anonymator.spec` ; Modify `requirements.txt` ; Create/modify `.gitignore`

> **Pré-requis :** Avant cette task, installer `gliner` + `torch` dans `.venv` et exclure `.venv` de pCloud (cf. `docs/installation-gliner.md` §2-3). Sans torch, PyInstaller ne peut pas résoudre les imports et le build échoue.

- [ ] **Step 1 : Installer PyInstaller**

```
.venv\Scripts\python.exe -m pip install "pyinstaller>=6.0" pyinstaller-hooks-contrib
```

Ajouter en fin de `requirements.txt` :
```
pyinstaller>=6.0
pyinstaller-hooks-contrib
```

- [ ] **Step 2 : Créer anonymator.spec**

```python
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
    console=False,    # pas de fenêtre console sur Windows
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
```

- [ ] **Step 3 : Build**

```
.venv\Scripts\python.exe -m PyInstaller anonymator.spec --clean
```

Attendu : dossier `dist\anonymator\` créé avec `anonymator.exe` dedans.

En cas d'erreur `ModuleNotFoundError` dans la sortie de build, ajouter le module manquant à `hiddenimports` dans le `.spec` et relancer.

En cas d'erreur au **lancement** de l'exe, activer la console pour voir les logs :
- Dans `anonymator.spec`, remplacer `console=False` par `console=True`
- Relancer le build et l'exe pour lire la traceback

- [ ] **Step 4 : Vérifier le lancement**

Lancer manuellement `dist\anonymator\anonymator.exe` :
- Si le modèle GLiNER est absent du cache `~/.cache/huggingface` → écran **SetupScreen** affiché.
- Si le modèle est présent → écran **Accueil** affiché directement.

- [ ] **Step 5 : Ajouter dist/ et build/ au .gitignore**

Créer (ou modifier) `.gitignore` à la racine du projet :

```
.venv/
__pycache__/
*.pyc
*.pyo
dist/
build/
```

- [ ] **Step 6 : Commit**

```bash
git add anonymator.spec requirements.txt .gitignore
git commit -m "feat: configuration PyInstaller (onedir, windowed, hidden imports)"
```

---

## Couverture du spec (auto-revue Plan 4)

- §2 packaging PyInstaller exe Windows, modèle découplé → Task 4 ✓
- §9 modèle absent → téléchargement guidé au 1er lancement → Tasks 0, 1, 2 ✓
- README utilisateur → Task 3 ✓
- Pré-requis pCloud (`.venv` exclu de synchro) → rappelé en Task 4 ✓

**Limites volontaires :** PyInstaller peut produire un dossier de 2-3 Go (torch bundlé) — c'est attendu. L'icône `.exe`, la signature de code et NSIS sont Plan 5+. Le test `test_build_launches_exe` (vérification end-to-end de l'exe) est une checklist manuelle (Task 4 Step 4) car automatiser le lancement d'un exe PyInstaller en CI sort du périmètre v1.
