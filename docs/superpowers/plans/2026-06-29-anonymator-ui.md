# Anonymator — Plan 3 : Application UI (PySide6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Une application de bureau PySide6 qui orchestre le moteur des Plans 1-2 : accueil, **revue de texte avec surlignage couleur par type**, mode fichier avec aperçu et sélection de colonnes, écran Paramètres (thème commutable, dossier de sortie, référentiel), point d'entrée exécutable.

**Architecture :** Toute la logique non-graphique vit dans des modules **testables sans Qt** : palette de couleurs fonctionnelles, construction du QSS depuis des tokens de thème, préférences persistées, **`ReviewSession`** (état de la revue : entités détectées, cochées/décochées, ajouts manuels → texte masqué + rapport), et **découpage du texte long**. Les écrans Qt sont des vues fines au-dessus de ces modules, vérifiées par smoke-tests `pytest-qt` + checklists manuelles. GLiNER est chargé **paresseusement** dans un thread, avec indicateur d'attente.

**Tech Stack:** PySide6, pytest, pytest-qt. Réutilise tout `anonymator.*` des Plans 1-2.

**Référence spec :** [2026-06-29-anonymator-design.md](../specs/2026-06-29-anonymator-design.md) — §5 (texte), §6 (fichier), §8 (thèmes), §9 (chunking).

> **Hors périmètre (→ Plan 4) :** packaging PyInstaller, README d'installation, écran de guidage 1er téléchargement du modèle.

---

## Structure des fichiers (Plan 3)

```
anonymator/ui/__init__.py
anonymator/ui/colors.py          palette couleurs fonctionnelles par type d'entité (fixe)
anonymator/ui/theme.py           tokens CAP/CUMA + build_qss(theme)
anonymator/ui/preferences.py     Preferences (thème, dossier sortie, overrides) load/save JSON
anonymator/ui/model_loader.py    chargement paresseux/threadé de GlinerDetector
anonymator/ui/main_window.py     QMainWindow + navigation (QStackedWidget)
anonymator/ui/home_screen.py     écran d'accueil (Texte / Fichier)
anonymator/ui/text_screen.py     saisie + revue couleur + masquage + export
anonymator/ui/file_screen.py     ouverture + aperçu + colonnes + enregistrement + rapport
anonymator/ui/settings_screen.py thème, dossier sortie, référentiel
anonymator/core/review_session.py  ReviewSession (logique de revue, non-Qt)
anonymator/core/chunking.py        découpage texte long + détection rebasée
anonymator/__main__.py           point d'entrée (python -m anonymator)
tests/...                        TDD pour les modules non-Qt ; smoke pytest-qt pour les écrans
```

> Les tests Qt tournent en mode **offscreen** : exporter `QT_QPA_PLATFORM=offscreen` avant pytest (voir Task 0).

---

### Task 0 : Dépendances UI + package + mode test offscreen

**Files:** Modify `requirements.txt` ; Modify `pyproject.toml` ; Create `anonymator/ui/__init__.py`, `anonymator/core/__init__.py`, `tests/conftest.py`.

- [ ] **Step 1 : Ajouter PySide6 + pytest-qt à `requirements.txt`**

```
gliner>=0.2.13
openpyxl>=3.1
PySide6>=6.6
pytest>=8.0
pytest-qt>=4.4
```

- [ ] **Step 2 : Installer**

Run : `.venv/Scripts/python -m pip install "PySide6>=6.6" "pytest-qt>=4.4"`
Expected : OK (PySide6 ~ plusieurs centaines de Mo ; ne PAS installer gliner/torch ici).

- [ ] **Step 3 : Forcer la plateforme Qt offscreen pour les tests** — créer `tests/conftest.py`

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

- [ ] **Step 4 : Créer les packages** `anonymator/ui/__init__.py` et `anonymator/core/__init__.py` (vides).

- [ ] **Step 5 : Vérifier la suite existante**

Run : `.venv/Scripts/python -m pytest -q`
Expected : 68 passed, 1 deselected.

- [ ] **Step 6 : Commit**

```bash
git add requirements.txt pyproject.toml anonymator/ui/__init__.py anonymator/core/__init__.py tests/conftest.py
git commit -m "chore: dépendances UI (PySide6, pytest-qt) + tests offscreen"
```

---

### Task 1 : Palette de couleurs fonctionnelles par type

**Files:** Create `anonymator/ui/colors.py` ; Test `tests/test_colors.py`.

Jeu **fixe**, indépendant du thème (préserve le repère couleur=type, spec §8).

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_colors.py
from anonymator.ui.colors import color_for, ENTITY_COLORS

def test_known_types_have_distinct_colors():
    for code in ["PERSON", "ADDRESS", "ORG", "EMAIL", "PHONE", "IBAN"]:
        assert color_for(code).startswith("#")
    # couleurs distinctes entre Personne et Adresse
    assert color_for("PERSON") != color_for("ADDRESS")

def test_unknown_type_falls_back_to_grey():
    assert color_for("ZZZ") == "#8499AB"
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/ui/colors.py
ENTITY_COLORS = {
    "PERSON":      "#2d6cdf",
    "ADDRESS":     "#1f9d57",
    "ORG":         "#0c8a93",
    "EMAIL":       "#8a3ffc",
    "PHONE":       "#d97400",
    "IBAN":        "#d62828",
    "BIC":         "#b5179e",
    "SIREN":       "#3a0ca3",
    "SIRET":       "#7209b7",
    "NIR":         "#c1121f",
    "POSTAL_CODE": "#4d908e",
    "URL":         "#577590",
}
_FALLBACK = "#8499AB"

def color_for(code: str) -> str:
    return ENTITY_COLORS.get(code, _FALLBACK)
```

- [ ] **Step 4 : Run → PASS** (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/colors.py tests/test_colors.py
git commit -m "feat: palette de couleurs fonctionnelles par type d'entité"
```

---

### Task 2 : Thèmes (tokens CAP/CUMA) + construction du QSS

**Files:** Create `anonymator/ui/theme.py` ; Test `tests/test_theme.py`.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_theme.py
from anonymator.ui.theme import THEMES, build_qss, DEFAULT_THEME

def test_two_themes_with_required_tokens():
    assert set(THEMES) == {"cuma", "cap"}
    for tokens in THEMES.values():
        for key in ["primary", "action", "dark", "accent", "bg", "text"]:
            assert tokens[key].startswith("#")

def test_default_theme_is_cuma():
    assert DEFAULT_THEME == "cuma"

def test_build_qss_injects_theme_colors():
    qss = build_qss("cap")
    assert THEMES["cap"]["action"] in qss
    assert "QPushButton" in qss

def test_build_qss_unknown_theme_falls_back_to_default():
    assert build_qss("zzz") == build_qss(DEFAULT_THEME)
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/ui/theme.py
DEFAULT_THEME = "cuma"

THEMES = {
    "cuma": {"primary": "#31B700", "action": "#00965E", "dark": "#063b27",
             "accent": "#93C90E", "bg": "#F3FAF4", "text": "#10331f"},
    "cap":  {"primary": "#1DA8E2", "action": "#1570B8", "dark": "#0D1A35",
             "accent": "#E8621A", "bg": "#FFFFFF", "text": "#1E1E2E"},
}

_TEMPLATE = """
QWidget {{ background: {bg}; color: {text};
          font-family: 'Inter','Segoe UI',sans-serif; font-size: 14px; }}
QLabel#title {{ font-family: 'Space Grotesk','Segoe UI',sans-serif;
               font-size: 22px; font-weight: 700; color: {dark}; }}
QPushButton {{ background: {action}; color: white; border: none;
              border-radius: 6px; padding: 8px 16px; font-weight: 600; }}
QPushButton:hover {{ background: {primary}; }}
QPushButton#accent {{ background: {accent}; }}
QPushButton#ghost {{ background: transparent; color: {action};
                    border: 1px solid {action}; }}
"""

def build_qss(theme: str) -> str:
    tokens = THEMES.get(theme, THEMES[DEFAULT_THEME])
    return _TEMPLATE.format(**tokens)
```

- [ ] **Step 4 : Run → PASS** (4 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/theme.py tests/test_theme.py
git commit -m "feat: thèmes CAP/CUMA + construction du QSS"
```

---

### Task 3 : Préférences persistées

**Files:** Create `anonymator/ui/preferences.py` ; Test `tests/test_preferences.py`.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_preferences.py
from pathlib import Path
from anonymator.ui.preferences import Preferences

def test_defaults():
    p = Preferences()
    assert p.theme == "cuma"
    assert p.output_dir is None
    assert p.entity_overrides == {}

def test_roundtrip_save_load(tmp_path):
    path = tmp_path / "prefs.json"
    p = Preferences(theme="cap", output_dir="D:/out",
                    entity_overrides={"BIC": True})
    p.save(path)
    loaded = Preferences.load(path)
    assert loaded.theme == "cap"
    assert loaded.output_dir == "D:/out"
    assert loaded.entity_overrides == {"BIC": True}

def test_load_missing_file_returns_defaults(tmp_path):
    assert Preferences.load(tmp_path / "absent.json").theme == "cuma"
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/ui/preferences.py
import json
from dataclasses import dataclass, field, asdict
from pathlib import Path

@dataclass
class Preferences:
    theme: str = "cuma"
    output_dir: str | None = None
    entity_overrides: dict[str, bool] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                        encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Preferences":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(theme=data.get("theme", "cuma"),
                   output_dir=data.get("output_dir"),
                   entity_overrides=data.get("entity_overrides", {}))
```

- [ ] **Step 4 : Run → PASS** (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/preferences.py tests/test_preferences.py
git commit -m "feat: préférences persistées (thème, dossier sortie, overrides)"
```

---

### Task 4 : ReviewSession (cœur testable de la revue)

**Files:** Create `anonymator/core/review_session.py` ; Test `tests/test_review_session.py`.

Modèle d'état de la revue (mode texte) : entités détectées + état coché/décoché par entité et par type + ajouts manuels → entités retenues, texte masqué, rapport. **Aucune dépendance Qt.**

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_review_session.py
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.core.review_session import ReviewSession

REF = Referential.load_default()

def _session():
    text = "Claire Martin, mail c@x.fr, société SARL Bidule"
    ents = [Entity("PERSON", "Claire Martin", 0, 13, "ner", 0.9),
            Entity("EMAIL", "c@x.fr", 20, 26, "deterministic", 1.0),
            Entity("ORG", "SARL Bidule", 36, 47, "ner", 0.8)]
    return ReviewSession(text, ents)

def test_all_detected_retained_by_default():
    s = _session()
    assert {e.type for e in s.retained()} == {"PERSON", "EMAIL", "ORG"}
    assert s.masked_text(REF) == "[PERSONNE], mail [EMAIL], société [ORG]"

def test_disable_single_entity():
    s = _session()
    s.set_entity_enabled(2, False)            # l'ORG
    assert "SARL Bidule" in s.masked_text(REF)
    assert all(e.type != "ORG" for e in s.retained())

def test_disable_whole_type():
    s = _session()
    s.set_type_enabled("PERSON", False)
    assert s.masked_text(REF).startswith("Claire Martin")

def test_add_manual_entity():
    s = _session()
    # ajouter "Bidule" déjà couvert -> on ajoute plutôt un manque : "mail" non, prenons un cas
    s.add_manual("PERSON", 0, 13)             # idempotent sur un span déjà là
    assert s.masked_text(REF).count("[PERSONNE]") == 1

def test_report_counts_retained_only():
    s = _session()
    s.set_type_enabled("ORG", False)
    rows = s.report(REF).to_rows()
    assert {r["type"] for r in rows} == {"PERSON", "EMAIL"}
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/core/review_session.py
from anonymator.model import Entity
from anonymator.merge import merge_entities
from anonymator.anonymize import apply_masking
from anonymator.report.audit import AuditReport

class ReviewSession:
    def __init__(self, text: str, entities: list[Entity]):
        self.text = text
        # entités fusionnées + état activé (par défaut True)
        self._entities = merge_entities(list(entities))
        self._enabled = [True] * len(self._entities)
        self._disabled_types: set[str] = set()

    def entities(self) -> list[Entity]:
        return list(self._entities)

    def set_entity_enabled(self, index: int, enabled: bool) -> None:
        self._enabled[index] = enabled

    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        if enabled:
            self._disabled_types.discard(etype)
        else:
            self._disabled_types.add(etype)

    def add_manual(self, etype: str, start: int, end: int) -> None:
        value = self.text[start:end]
        new = Entity(etype, value, start, end, "manual", 1.0)
        self._entities = merge_entities(self._entities + [new])
        # recalcule la map d'activation (les nouveaux sont activés)
        self._enabled = [True] * len(self._entities)

    def retained(self) -> list[Entity]:
        out = []
        for e, on in zip(self._entities, self._enabled):
            if on and e.type not in self._disabled_types:
                out.append(e)
        return out

    def masked_text(self, ref) -> str:
        return apply_masking(self.text, self.retained(), ref)

    def report(self, ref) -> AuditReport:
        rep = AuditReport()
        for e in self.retained():
            rep.add(e.type, e.value, ref.tag_for(e.type), "texte")
        return rep
```

- [ ] **Step 4 : Run → PASS** (5 tests). Puis suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/review_session.py tests/test_review_session.py
git commit -m "feat: ReviewSession (état de revue texte, non-Qt)"
```

---

### Task 5 : Découpage du texte long (chunking)

**Files:** Create `anonymator/core/chunking.py` ; Test `tests/test_chunking.py`.

Spec §9 : pour un texte dépassant un seuil, découper **sans couper une entité** (sur des frontières de ligne/espace), détecter par morceau, **rebaser les offsets**, fusionner.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_chunking.py
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.core.chunking import chunk_spans, detect_long

def test_chunk_spans_cover_text_without_overlap():
    text = "abc def ghi jkl mno pqr"
    spans = chunk_spans(text, max_len=10)
    # couvre tout le texte, dans l'ordre, sans trou
    assert spans[0][0] == 0
    assert spans[-1][1] == len(text)
    for (s, e) in spans:
        assert e - s <= 10 or " " not in text[s:e]  # ne coupe pas en plein mot

def test_detect_long_rebases_offsets():
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    text = ("x " * 40) + "Claire Martin"      # le nom est loin dans le texte
    ents = detect_long(text, ner, ref, max_len=30)
    person = next(e for e in ents if e.type == "PERSON")
    assert text[person.start:person.end] == "Claire Martin"
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/core/chunking.py
from anonymator.model import Entity
from anonymator.pipeline import detect
from anonymator.merge import merge_entities

def chunk_spans(text: str, max_len: int) -> list[tuple[int, int]]:
    """Découpe [text] en segments <= max_len, en coupant de préférence sur le
    dernier espace avant la limite (jamais en plein mot si possible)."""
    spans, start, n = [], 0, len(text)
    while start < n:
        end = min(start + max_len, n)
        if end < n:
            cut = text.rfind(" ", start, end)
            if cut > start:
                end = cut + 1
        spans.append((start, end))
        start = end
    return spans

def detect_long(text: str, ner, ref, max_len: int = 4000) -> list[Entity]:
    if len(text) <= max_len:
        return detect(text, ner, ref)
    found: list[Entity] = []
    for start, end in chunk_spans(text, max_len):
        for e in detect(text[start:end], ner, ref):
            found.append(Entity(e.type, e.value, e.start + start,
                                e.end + start, e.source, e.confidence))
    return merge_entities(found)
```

- [ ] **Step 4 : Run → PASS** (2 tests). Puis suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/chunking.py tests/test_chunking.py
git commit -m "feat: découpage texte long + détection rebasée (spec §9)"
```

---

### Task 6 : Chargeur de modèle paresseux + MainWindow + accueil

**Files:** Create `anonymator/ui/model_loader.py`, `anonymator/ui/main_window.py`, `anonymator/ui/home_screen.py` ; Test `tests/test_ui_smoke.py`.

- [ ] **Step 1 : Smoke test qui échoue**

```python
# tests/test_ui_smoke.py
from anonymator.ui.main_window import MainWindow

def test_main_window_builds_and_has_home(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    assert win.stack.count() >= 1
    # l'accueil expose deux actions
    assert win.home.btn_text is not None
    assert win.home.btn_file is not None

def test_navigation_to_text_and_file(qtbot):
    win = MainWindow()
    qtbot.addWidget(win)
    win.show_text()
    assert win.stack.currentWidget() is win.text_screen
    win.show_file()
    assert win.stack.currentWidget() is win.file_screen
    win.show_home()
    assert win.stack.currentWidget() is win.home
```

- [ ] **Step 2 : Run → FAIL** : `QT_QPA_PLATFORM=offscreen .venv/Scripts/python -m pytest tests/test_ui_smoke.py -q`

- [ ] **Step 3 : Implémenter**

`anonymator/ui/model_loader.py` :
```python
from anonymator.ner import NerDetector

class ModelLoader:
    """Charge GlinerDetector à la demande (import torch différé). Injectable
    pour les tests via un détecteur fourni."""
    def __init__(self, detector: NerDetector | None = None):
        self._detector = detector

    def get(self) -> NerDetector:
        if self._detector is None:
            from anonymator.ner import GlinerDetector
            self._detector = GlinerDetector()
        return self._detector
```

`anonymator/ui/home_screen.py` :
```python
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt

class HomeScreen(QWidget):
    def __init__(self, on_text, on_file, on_settings):
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel("Anonymator"); title.setObjectName("title")
        title.setAlignment(Qt.AlignCenter)
        self.btn_text = QPushButton("Texte")
        self.btn_file = QPushButton("Fichier")
        self.btn_settings = QPushButton("Paramètres"); self.btn_settings.setObjectName("ghost")
        self.btn_text.clicked.connect(on_text)
        self.btn_file.clicked.connect(on_file)
        self.btn_settings.clicked.connect(on_settings)
        for w in (title, self.btn_text, self.btn_file, self.btn_settings):
            layout.addWidget(w)
        layout.addStretch()
```

`anonymator/ui/main_window.py` :
```python
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

PREFS_PATH = Path.home() / ".anonymator" / "preferences.json"

class MainWindow(QMainWindow):
    def __init__(self, loader: ModelLoader | None = None,
                 prefs_path: Path = PREFS_PATH):
        super().__init__()
        self.setWindowTitle("Anonymator")
        self.prefs_path = prefs_path
        self.prefs = Preferences.load(prefs_path)
        self.ref = Referential.load_default()
        self.loader = loader or ModelLoader()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings)
        self.text_screen = TextScreen(self.ref, self.loader, self.prefs, self.show_home)
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs, self.show_home)
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        for w in (self.home, self.text_screen, self.file_screen, self.settings_screen):
            self.stack.addWidget(w)
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(build_qss(self.prefs.theme))

    def _apply_prefs(self):
        self.prefs.save(self.prefs_path)
        self._apply_theme()

    def show_home(self): self.stack.setCurrentWidget(self.home)
    def show_text(self): self.stack.setCurrentWidget(self.text_screen)
    def show_file(self): self.stack.setCurrentWidget(self.file_screen)
    def show_settings(self): self.stack.setCurrentWidget(self.settings_screen)
```

> Les écrans `TextScreen`, `FileScreen`, `SettingsScreen` sont créés aux Tasks 7-9 ; pour faire passer ce smoke test, crée d'abord des **stubs minimaux** (un `QWidget` vide avec la bonne signature `__init__`) puis remplace-les. Le stub :
> ```python
> # squelette temporaire pour chaque écran, à étoffer dans sa task
> from PySide6.QtWidgets import QWidget
> class TextScreen(QWidget):
>     def __init__(self, ref, loader, prefs, on_back): super().__init__()
> ```

- [ ] **Step 4 : Run → PASS** (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/model_loader.py anonymator/ui/main_window.py anonymator/ui/home_screen.py anonymator/ui/text_screen.py anonymator/ui/file_screen.py anonymator/ui/settings_screen.py tests/test_ui_smoke.py
git commit -m "feat: MainWindow + accueil + chargeur modèle (stubs écrans)"
```

---

### Task 7 : Écran TEXTE (revue couleur + masquage + export)

**Files:** Modify `anonymator/ui/text_screen.py` ; Test `tests/test_text_screen.py`.

L'écran : zone de saisie → bouton Analyser → surlignage couleur (via `QTextEdit.setExtraSelections`) + liste des entités cochables → Appliquer → texte masqué + boutons Copier / Exporter .txt / Exporter rapport. Détection injectée via `ModelLoader` (tests : `FakeNer`).

- [ ] **Step 1 : Smoke test qui échoue**

```python
# tests/test_text_screen.py
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.text_screen import TextScreen

def _screen():
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    return TextScreen(ref, loader, Preferences(), on_back=lambda: None)

def test_analyze_populates_session(qtbot):
    s = _screen(); qtbot.addWidget(s)
    s.input.setPlainText("Claire Martin mail c@x.fr")
    s.analyze()
    types = {e.type for e in s.session.entities()}
    assert {"PERSON", "EMAIL"} <= types

def test_apply_produces_masked_text(qtbot):
    s = _screen(); qtbot.addWidget(s)
    s.input.setPlainText("Claire Martin mail c@x.fr")
    s.analyze(); s.apply()
    assert s.output.toPlainText() == "[PERSONNE] mail [EMAIL]"
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** `anonymator/ui/text_screen.py`

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QListWidget, QListWidgetItem, QLabel,
                               QFileDialog, QApplication)
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import Qt
from anonymator.core.chunking import detect_long
from anonymator.core.review_session import ReviewSession
from anonymator.ui.colors import color_for

class TextScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.session: ReviewSession | None = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Texte à anonymiser"))
        self.input = QTextEdit()
        self.entity_list = QListWidget()
        self.output = QTextEdit(); self.output.setReadOnly(True)
        btns = QHBoxLayout()
        self.btn_analyze = QPushButton("Analyser"); self.btn_analyze.clicked.connect(self.analyze)
        self.btn_apply = QPushButton("Appliquer le masquage"); self.btn_apply.clicked.connect(self.apply)
        self.btn_copy = QPushButton("Copier"); self.btn_copy.setObjectName("ghost"); self.btn_copy.clicked.connect(self._copy)
        self.btn_export = QPushButton("Exporter .txt"); self.btn_export.setObjectName("ghost"); self.btn_export.clicked.connect(self._export)
        self.btn_back = QPushButton("Accueil"); self.btn_back.setObjectName("ghost"); self.btn_back.clicked.connect(on_back)
        for b in (self.btn_analyze, self.btn_apply, self.btn_copy, self.btn_export, self.btn_back):
            btns.addWidget(b)
        layout.addWidget(self.input)
        layout.addWidget(QLabel("Entités détectées (décocher = ne pas masquer)"))
        layout.addWidget(self.entity_list)
        layout.addLayout(btns)
        layout.addWidget(QLabel("Résultat"))
        layout.addWidget(self.output)
        self.entity_list.itemChanged.connect(self._on_item_changed)

    def analyze(self):
        text = self.input.toPlainText()
        ner = self.loader.get()
        ents = detect_long(text, ner, self.ref)
        self.session = ReviewSession(text, ents)
        self._refresh_list(); self._highlight()

    def _refresh_list(self):
        self.entity_list.blockSignals(True)
        self.entity_list.clear()
        for i, e in enumerate(self.session.entities()):
            item = QListWidgetItem(f"{e.type} — {e.value}")
            item.setData(Qt.UserRole, i)
            item.setForeground(QColor(color_for(e.type)))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.entity_list.addItem(item)
        self.entity_list.blockSignals(False)

    def _on_item_changed(self, item):
        idx = item.data(Qt.UserRole)
        self.session.set_entity_enabled(idx, item.checkState() == Qt.Checked)
        self._highlight()

    def _highlight(self):
        selections = []
        retained = set(id(e) for e in self.session.retained())
        cursor_doc = self.input.document()
        extra = []
        for e in self.session.entities():
            if id(e) not in retained:
                continue
            fmt = QTextCharFormat()
            c = QColor(color_for(e.type)); c.setAlpha(70)
            fmt.setBackground(c)
            cur = QTextCursor(cursor_doc)
            cur.setPosition(e.start); cur.setPosition(e.end, QTextCursor.KeepAnchor)
            sel = QTextEdit.ExtraSelection(); sel.cursor = cur; sel.format = fmt
            extra.append(sel)
        self.input.setExtraSelections(extra)

    def apply(self):
        self.output.setPlainText(self.session.masked_text(self.ref))

    def _copy(self):
        QApplication.clipboard().setText(self.output.toPlainText())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter", "anonymise.txt", "*.txt")
        if path:
            from pathlib import Path
            Path(path).write_text(self.output.toPlainText(), encoding="utf-8")
```

- [ ] **Step 4 : Run → PASS** (2 tests).

- [ ] **Step 5 : Vérification manuelle** (checklist — l'exécutant lance `python -m anonymator` après la Task 10) :
  - [ ] Coller un texte avec nom/email/IBAN → Analyser → les entités sont surlignées **dans leur couleur de type**.
  - [ ] Décocher une entité → son surlignage disparaît.
  - [ ] Appliquer → le résultat remplace par `[CATÉGORIE]`. Copier / Exporter fonctionnent.

- [ ] **Step 6 : Commit**

```bash
git add anonymator/ui/text_screen.py tests/test_text_screen.py
git commit -m "feat: écran texte (revue couleur, masquage, export)"
```

---

### Task 8 : Écran FICHIER (aperçu + colonnes + enregistrement + rapport)

**Files:** Modify `anonymator/ui/file_screen.py` ; Test `tests/test_file_screen.py`.

Ouvre un fichier, affiche un aperçu, laisse inclure/exclure des colonnes (CSV), lance l'anonymisation via `anonymize_file`, enregistre dans le dossier de sortie et propose d'exporter le rapport.

- [ ] **Step 1 : Smoke test qui échoue**

```python
# tests/test_file_screen.py
from datetime import datetime
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.file_screen import FileScreen

def test_run_on_csv_writes_output(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    prefs = Preferences(output_dir=str(tmp_path))
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    screen = FileScreen(Referential.load_default(), loader, prefs, on_back=lambda: None)
    qtbot.addWidget(screen)
    screen.load_path(str(src))
    result = screen.run(when=datetime(2026, 1, 2, 3, 4, 5))
    assert result.output_path.exists()
    out = result.output_path.read_bytes().decode("cp1252")
    assert "[PERSONNE]" in out and "Claire Martin" not in out
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** `anonymator/ui/file_screen.py`

```python
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox)
from anonymator.files.anonymize_file import anonymize_file, UnsupportedFormat
from anonymator.files import csv_io
from anonymator.files.columns import default_maskable_columns

class FileScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.path: Path | None = None
        self.excluded: set[int] = set()
        layout = QVBoxLayout(self)
        self.label = QLabel("Aucun fichier")
        self.table = QTableWidget()
        btns = QHBoxLayout()
        self.btn_open = QPushButton("Ouvrir…"); self.btn_open.clicked.connect(self._open)
        self.btn_run = QPushButton("Anonymiser et enregistrer"); self.btn_run.clicked.connect(lambda: self.run())
        self.btn_back = QPushButton("Accueil"); self.btn_back.setObjectName("ghost"); self.btn_back.clicked.connect(on_back)
        for b in (self.btn_open, self.btn_run, self.btn_back):
            btns.addWidget(b)
        layout.addWidget(self.label); layout.addLayout(btns); layout.addWidget(self.table)

    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir", "", "Fichiers (*.txt *.csv *.xlsx)")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        self.path = Path(path); self.excluded = set()
        self.label.setText(self.path.name)
        if self.path.suffix.lower() == ".csv":
            doc = csv_io.read_csv(self.path)
            self._fill_preview(doc.rows[:50])

    def _fill_preview(self, rows):
        if not rows: return
        self.table.setColumnCount(max(len(r) for r in rows))
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(val))

    def run(self, when: datetime | None = None):
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        try:
            ner = self.loader.get()
            exclude = self.excluded if self.path.suffix.lower() == ".csv" else None
            result = anonymize_file(self.path, ner, self.ref, out_dir, when, exclude=exclude)
        except UnsupportedFormat as e:
            QMessageBox.warning(self, "Format non supporté", str(e)); return None
        return result
```

- [ ] **Step 4 : Run → PASS** (1 test).

- [ ] **Step 5 : Vérification manuelle :**
  - [ ] Ouvrir un vrai FEC/grand livre → aperçu tableau, séparateur correct.
  - [ ] Lancer → fichier `_ano_…` créé dans le dossier de sortie, original intact.
  - [ ] Refuser un .pdf avec message clair.

- [ ] **Step 6 : Commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen.py
git commit -m "feat: écran fichier (aperçu, colonnes, enregistrement)"
```

---

### Task 9 : Écran PARAMÈTRES (thème + dossier sortie + référentiel)

**Files:** Modify `anonymator/ui/settings_screen.py` ; Test `tests/test_settings_screen.py`.

- [ ] **Step 1 : Smoke test qui échoue**

```python
# tests/test_settings_screen.py
from anonymator.referential import Referential
from anonymator.ui.preferences import Preferences
from anonymator.ui.settings_screen import SettingsScreen

def test_changing_theme_updates_prefs_and_calls_apply(qtbot):
    prefs = Preferences()
    called = []
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: called.append(True), on_back=lambda: None)
    qtbot.addWidget(s)
    s.select_theme("cap")
    assert prefs.theme == "cap"
    assert called  # on_apply déclenché → réapplique le QSS + sauvegarde
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** `anonymator/ui/settings_screen.py`

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit, QFileDialog)

class SettingsScreen(QWidget):
    def __init__(self, ref, prefs, on_apply, on_back):
        super().__init__()
        self.ref, self.prefs, self.on_apply = ref, prefs, on_apply
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paramètres"))
        # thème
        layout.addWidget(QLabel("Thème"))
        self.theme_box = QComboBox(); self.theme_box.addItems(["cuma", "cap"])
        self.theme_box.setCurrentText(prefs.theme)
        self.theme_box.currentTextChanged.connect(self.select_theme)
        layout.addWidget(self.theme_box)
        # dossier de sortie
        layout.addWidget(QLabel("Dossier de sortie"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(prefs.output_dir or "")
        btn_dir = QPushButton("Choisir…"); btn_dir.clicked.connect(self._choose_dir)
        row.addWidget(self.dir_edit); row.addWidget(btn_dir)
        layout.addLayout(row)
        back = QPushButton("Accueil"); back.setObjectName("ghost"); back.clicked.connect(on_back)
        layout.addStretch(); layout.addWidget(back)

    def select_theme(self, theme: str):
        self.prefs.theme = theme
        self.on_apply()

    def _choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if path:
            self.dir_edit.setText(path)
            self.prefs.output_dir = path
            self.on_apply()
```

> Le **référentiel d'entités** (activer/désactiver BIC, CP, etc.) peut être ajouté ici de la même façon (liste de cases reliées à `prefs.entity_overrides`) ; pour la v1 du Plan 3, le thème + dossier suffisent au smoke test. Étendre si le temps le permet (cf. spec §6.6).

- [ ] **Step 4 : Run → PASS** (1 test). Puis suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py
git commit -m "feat: écran paramètres (thème commutable, dossier de sortie)"
```

---

### Task 10 : Point d'entrée exécutable

**Files:** Create `anonymator/__main__.py` ; Test `tests/test_entrypoint.py`.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_entrypoint.py
def test_build_app_returns_window(qtbot):
    from anonymator.__main__ import build_window
    win = build_window()
    qtbot.addWidget(win)
    assert win.windowTitle() == "Anonymator"
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/__main__.py
import sys
from PySide6.QtWidgets import QApplication
from anonymator.ui.main_window import MainWindow

def build_window() -> MainWindow:
    return MainWindow()

def main() -> int:
    app = QApplication(sys.argv)
    win = build_window()
    win.resize(900, 700)
    win.show()
    return app.exec()

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4 : Run → PASS** (1 test). Puis suite complète verte.

- [ ] **Step 5 : Vérification manuelle finale** (nécessite GLiNER installé, cf. docs/installation-gliner.md) :
  - [ ] `.venv/Scripts/python -m anonymator` ouvre la fenêtre, thème **CUMA** par défaut.
  - [ ] Parcours texte complet (analyser → revue couleur → appliquer → export).
  - [ ] Parcours fichier complet (ouvrir FEC → anonymiser → fichier de sortie + rapport).
  - [ ] Paramètres → bascule **CAP** → l'UI repasse en bleu instantanément ; au redémarrage le choix est mémorisé.

- [ ] **Step 6 : Commit**

```bash
git add anonymator/__main__.py tests/test_entrypoint.py
git commit -m "feat: point d'entrée python -m anonymator"
```

---

## Couverture du spec (auto-revue Plan 3)

- §5 mode texte : revue couleur (décocher/ajouter), masquage, copier/exporter → Tasks 4,7. ✓ (export rapport texte via `ReviewSession.report` — bouton à câbler dans la checklist).
- §6 mode fichier : ouverture, aperçu, colonnes (exclude), enregistrement, refus PDF → Task 8 (réutilise Plan 2). ✓
- §8 thèmes commutables CAP/CUMA, défaut CUMA, couleurs fonctionnelles fixes, polices → Tasks 1,2,9. ✓
- §9 chunking texte long → Task 5. ✓
- §6.6 référentiel éditable dans Paramètres → **partiel** (thème+dossier livrés ; toggles d'entités notés comme extension).

**Limites volontaires :** vérification visuelle fine = manuelle (smoke-tests `pytest-qt` couvrent construction + logique) ; **packaging PyInstaller + README + écran 1er téléchargement du modèle = Plan 4** ; navigation onglets xlsx dans l'aperçu fichier = simple (aperçu CSV prioritaire), à enrichir si besoin.
```
