# V2 — Restyle des écrans — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Habiller les écrans **accueil**, **texte** et **paramètres** avec les composants V1 (HeaderBand, NavCard, StatCard, ToggleSwitch, CategoryBadge, Card), ajouter l'éditeur de détection aux Paramètres (toggles de types + liste d'exclusion), et brancher le `Referential` sur les préférences dans `MainWindow`.

**Architecture:** Pure couche de présentation au-dessus de la logique existante. **Contrainte absolue : préserver les interfaces publiques** que les tests et `MainWindow` utilisent déjà (attributs et méthodes listés dans chaque tâche) — on change l'apparence, pas le contrat.

**Tech Stack:** PySide6, pytest-qt (offscreen). Composants : `anonymator/ui/components/`.

**Référence spec :** [2026-06-30-systeme-visuel-design.md](../specs/2026-06-30-systeme-visuel-design.md) §6-7.

**Prérequis :** V1 mergé/présent sur `feat/revue-fichier-coloree`. Tests : `.venv\Scripts\python.exe -m pytest -q`.

---

## Structure des fichiers (V2)

```
anonymator/ui/preferences.py      MODIFIER : champ ner_stoplist
anonymator/ui/home_screen.py      RÉÉCRIRE : hero + 3 NavCards
anonymator/ui/text_screen.py      RÉÉCRIRE : header + stats + cards + panneau toggles + risque
anonymator/ui/settings_screen.py  RÉÉCRIRE : restyle + toggles types + éditeur stoplist
anonymator/ui/main_window.py      MODIFIER : Referential(overrides/stoplist) + refresh
tests/test_preferences.py         MODIFIER
tests/test_text_screen.py         (doit rester vert ; + assertions stats)
tests/test_settings_screen.py     MODIFIER
tests/test_ui_smoke.py            MODIFIER
```

---

### Task 1 : `Preferences.ner_stoplist`

**Files:** Modify `anonymator/ui/preferences.py` ; Test `tests/test_preferences.py`.

- [ ] **Step 1 : Tests qui échouent** (ajouter à `tests/test_preferences.py`)

```python
def test_ner_stoplist_roundtrip(tmp_path):
    from anonymator.ui.preferences import Preferences
    p = Preferences(ner_stoplist=["service client", "divers"])
    path = tmp_path / "p.json"
    p.save(path)
    loaded = Preferences.load(path)
    assert loaded.ner_stoplist == ["service client", "divers"]

def test_ner_stoplist_defaults_none():
    from anonymator.ui.preferences import Preferences
    assert Preferences().ner_stoplist is None
```

- [ ] **Step 2 : Run → FAIL** : `.venv\Scripts\python.exe -m pytest tests/test_preferences.py -q`

- [ ] **Step 3 : Implémenter** — ajouter le champ et le charger dans `Preferences`

```python
@dataclass
class Preferences:
    theme: str = "cuma"
    output_dir: str | None = None
    entity_overrides: dict[str, bool] = field(default_factory=dict)
    ner_stoplist: list[str] | None = None     # None = utiliser la liste par défaut du config

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
                   entity_overrides=data.get("entity_overrides", {}),
                   ner_stoplist=data.get("ner_stoplist"))
```

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_preferences.py -q`. Suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/preferences.py tests/test_preferences.py
git commit -m "feat(prefs): champ ner_stoplist (liste d'exclusion utilisateur)"
```

---

### Task 2 : Restyle accueil (hero + NavCards)

**Files:** Rewrite `anonymator/ui/home_screen.py` ; Test `tests/test_ui_smoke.py`.

**Interface à préserver :** constructeur `HomeScreen(on_text, on_file, on_settings)` ; attributs `btn_text`, `btn_file`, `btn_settings` non nuls (le smoke test les vérifie). Ici, `btn_text/btn_file/btn_settings` seront les instances `NavCard`.

- [ ] **Step 1 : Test (déjà existant) qui doit rester vert + une assertion ajoutée** — dans `tests/test_ui_smoke.py`, le test `test_main_window_builds_and_has_home` vérifie déjà `win.home.btn_text`/`btn_file`. Ajouter :

```python
def test_home_navcards_trigger_callbacks(qtbot):
    from anonymator.ui.home_screen import HomeScreen
    calls = []
    h = HomeScreen(lambda: calls.append("t"), lambda: calls.append("f"), lambda: calls.append("s"))
    qtbot.addWidget(h)
    h.btn_text._emit(); h.btn_file._emit(); h.btn_settings._emit()
    assert calls == ["t", "f", "s"]
```

- [ ] **Step 2 : Run → FAIL** : `.venv\Scripts\python.exe -m pytest tests/test_ui_smoke.py::test_home_navcards_trigger_callbacks -q`

- [ ] **Step 3 : Réécrire** `anonymator/ui/home_screen.py`

```python
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel)
from PySide6.QtCore import Qt
from anonymator.ui.components.cards import NavCard


class HomeScreen(QWidget):
    def __init__(self, on_text, on_file, on_settings):
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- panneau gauche (hero) ----
        hero = QWidget(); hero.setObjectName("Hero")
        hero.setStyleSheet("#Hero { background: #E8F3EA; }")
        hv = QVBoxLayout(hero)
        hv.setContentsMargins(40, 40, 40, 40)
        logo = QLabel("CUMA"); logo.setObjectName("title")
        logo.setStyleSheet("color: #31B700; font-size: 34px; font-weight: 800;")
        hv.addStretch()
        title = QLabel("Anonymisez.\nPartagez l'essentiel.")
        title.setObjectName("title")
        sub = QLabel("Protégez noms, adresses et coordonnées avant tout partage. "
                     "Traitement 100% local, aucune donnée envoyée.")
        sub.setObjectName("muted"); sub.setWordWrap(True)
        hv.addWidget(logo); hv.addSpacing(120); hv.addWidget(title); hv.addWidget(sub)
        hv.addStretch()
        foot = QLabel("la puissance du <span style='color:#E8621A;font-weight:700'>groupe</span>")
        foot.setTextFormat(Qt.RichText)
        hv.addWidget(foot)

        # ---- panneau droit (actions) ----
        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(40, 60, 40, 40)
        label = QLabel("PAR OÙ COMMENCER ?"); label.setObjectName("sectionLabel")
        rv.addWidget(label); rv.addSpacing(12)
        self.btn_text = NavCard("document", "Coller du texte",
                                "Analyser et masquer un texte collé", on_click=on_text)
        self.btn_file = NavCard("folder", "Importer un fichier",
                                ".txt, .csv ou .xlsx", on_click=on_file)
        self.btn_settings = NavCard("settings", "Paramètres",
                                    "Règles de détection & masquage", on_click=on_settings)
        for c in (self.btn_text, self.btn_file, self.btn_settings):
            rv.addWidget(c)
        rv.addStretch()

        root.addWidget(hero, 5)
        root.addWidget(right, 6)
```

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_ui_smoke.py -q` (le nouveau test + les existants `btn_text/btn_file is not None`).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/home_screen.py tests/test_ui_smoke.py
git commit -m "feat(ui): restyle accueil (hero CUMA + NavCards)"
```

---

### Task 3 : Restyle écran texte (header, stats, cards, panneau toggles, risque)

**Files:** Rewrite `anonymator/ui/text_screen.py` ; Test `tests/test_text_screen.py`.

**Interface à préserver :** `TextScreen(ref, loader, prefs, on_back)` ; attributs `input` (QTextEdit éditable), `output` (QTextEdit lecture seule) ; méthodes `analyze()` et `apply()` ; attribut `session`. Les tests existants (`test_analyze_populates_session`, `test_apply_produces_masked_text`) doivent rester verts.

- [ ] **Step 1 : Tests** — garder les existants ; ajouter dans `tests/test_text_screen.py`

```python
def test_stats_update_after_analyze(qtbot):
    s = _screen(); qtbot.addWidget(s)
    s.input.setPlainText("Claire Martin mail c@x.fr")
    s.analyze()
    # 2 entités détectées (PERSON, EMAIL) → carte "À masquer" = 2, risque Élevé
    assert s.stat_detected.value_label.text() == "2"
    assert s.stat_risk.value_label.text() == "Élevé"
```

(Le helper `_screen()` existant fournit un `FakeNer({"Claire Martin": "PERSON"})` ; l'EMAIL vient du déterministe.)

- [ ] **Step 2 : Run → FAIL** : `.venv\Scripts\python.exe -m pytest tests/test_text_screen.py::test_stats_update_after_analyze -q`

- [ ] **Step 3 : Réécrire** `anonymator/ui/text_screen.py`

```python
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLabel, QFileDialog, QApplication,
                               QScrollArea)
from PySide6.QtGui import QTextCharFormat, QColor, QTextCursor
from PySide6.QtCore import Qt
from anonymator.core.chunking import detect_long
from anonymator.core.review_session import ReviewSession
from anonymator.core.risk import risk_level
from anonymator.ui.colors import color_for
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.cards import Card, StatCard
from anonymator.ui.components.badge import CategoryBadge
from anonymator.ui.components.toggle import ToggleSwitch


class TextScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.session: ReviewSession | None = None

        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())

        nav = QHBoxLayout()
        back = QPushButton("Accueil"); back.setObjectName("ghost"); back.clicked.connect(on_back)
        nav.addWidget(back); nav.addWidget(QLabel("Texte")); nav.addStretch()
        root.addLayout(nav)

        # bandeau de stats
        stats = QHBoxLayout()
        self.stat_detected = StatCard("shield", "Entités détectées")
        self.stat_categories = StatCard("layers", "Catégories")
        self.stat_mask = StatCard("eye-off", "À masquer")
        self.stat_keep = StatCard("document", "Conservées", "#E8621A")
        self.stat_risk = StatCard("alert", "Niveau de risque", "#9a031e")
        for c in (self.stat_detected, self.stat_categories, self.stat_mask,
                  self.stat_keep, self.stat_risk):
            stats.addWidget(c)
        root.addLayout(stats)

        body = QHBoxLayout()
        left = QVBoxLayout()
        in_card = Card("document", "Texte à anonymiser")
        self.input = QTextEdit()
        in_card.body.addWidget(self.input)
        out_card = Card("shield", "Résultat anonymisé")
        self.output = QTextEdit(); self.output.setReadOnly(True)
        out_card.body.addWidget(self.output)
        left.addWidget(in_card); left.addWidget(out_card)

        ent_card = Card("shield", "Entités détectées")
        self.entity_area = QScrollArea(); self.entity_area.setWidgetResizable(True)
        self._entity_host = QWidget(); self._entity_layout = QVBoxLayout(self._entity_host)
        self._entity_layout.addStretch()
        self.entity_area.setWidget(self._entity_host)
        ent_card.body.addWidget(self.entity_area)

        body.addLayout(left, 3); body.addWidget(ent_card, 2)
        root.addLayout(body)

        actions = QHBoxLayout()
        self.btn_apply = QPushButton("Appliquer le masquage"); self.btn_apply.setObjectName("primary")
        self.btn_apply.clicked.connect(self.apply)
        self.btn_analyze = QPushButton("Analyser"); self.btn_analyze.setObjectName("secondary")
        self.btn_analyze.clicked.connect(self.analyze)
        self.btn_copy = QPushButton("Copier"); self.btn_copy.setObjectName("ghost"); self.btn_copy.clicked.connect(self._copy)
        self.btn_export = QPushButton("Exporter .txt"); self.btn_export.setObjectName("ghost"); self.btn_export.clicked.connect(self._export)
        actions.addWidget(self.btn_apply); actions.addWidget(self.btn_analyze); actions.addStretch()
        actions.addWidget(self.btn_copy); actions.addWidget(self.btn_export)
        root.addLayout(actions)

    def analyze(self):
        text = self.input.toPlainText()
        ner = self.loader.get()
        ents = detect_long(text, ner, self.ref)
        self.session = ReviewSession(text, ents)
        self._refresh_entities(); self._highlight(); self._refresh_stats()

    def _clear_entities(self):
        while self._entity_layout.count() > 1:   # garde le stretch final
            item = self._entity_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _refresh_entities(self):
        self._clear_entities()
        if self.session is None:
            return
        for i, e in enumerate(self.session.entities()):
            row = QWidget(); h = QHBoxLayout(row); h.setContentsMargins(2, 2, 2, 2)
            h.addWidget(CategoryBadge(e.type))
            val = QLabel(e.value); val.setStyleSheet("font-size: 13px;")
            h.addWidget(val); h.addStretch()
            tog = ToggleSwitch(); tog.setChecked(e.confirmed)
            tog.toggled.connect(lambda on, idx=i: self._on_toggle(idx, on))
            h.addWidget(tog)
            self._entity_layout.insertWidget(self._entity_layout.count() - 1, row)

    def _on_toggle(self, idx, on):
        if self.session is not None:
            self.session.set_entity_enabled(idx, on)
            self._highlight(); self._refresh_stats()

    def _highlight(self):
        if self.session is None:
            return
        retained = set(id(e) for e in self.session.retained())
        doc = self.input.document(); extra = []
        for e in self.session.entities():
            if id(e) not in retained:
                continue
            fmt = QTextCharFormat(); c = QColor(color_for(e.type)); c.setAlpha(70)
            fmt.setBackground(c); fmt.setUnderlineColor(QColor(color_for(e.type)))
            fmt.setUnderlineStyle(QTextCharFormat.SingleUnderline)
            cur = QTextCursor(doc); cur.setPosition(e.start)
            cur.setPosition(e.end, QTextCursor.KeepAnchor)
            sel = QTextEdit.ExtraSelection(); sel.cursor = cur; sel.format = fmt
            extra.append(sel)
        self.input.setExtraSelections(extra)

    def _refresh_stats(self):
        if self.session is None:
            return
        ents = self.session.entities(); retained = self.session.retained()
        self.stat_detected.set_value(len(ents))
        self.stat_categories.set_value(len({e.type for e in ents}))
        self.stat_mask.set_value(len(retained))
        self.stat_keep.set_value(len(ents) - len(retained))
        self.stat_risk.set_value(risk_level(retained, self.ref))

    def apply(self):
        if self.session is not None:
            self.output.setPlainText(self.session.masked_text(self.ref))

    def _copy(self):
        QApplication.clipboard().setText(self.output.toPlainText())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter", "anonymise.txt", "*.txt")
        if path:
            Path(path).write_text(self.output.toPlainText(), encoding="utf-8")
```

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_text_screen.py -q` (existants + nouveau). Suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/text_screen.py tests/test_text_screen.py
git commit -m "feat(ui): restyle ecran texte (header, stats, cards, toggles, risque)"
```

---

### Task 4 : Restyle Paramètres + éditeur de détection

**Files:** Rewrite `anonymator/ui/settings_screen.py` ; Test `tests/test_settings_screen.py`.

**Interface à préserver :** `SettingsScreen(ref, prefs, on_apply, on_back)` ; méthode `select_theme(theme)` (met `prefs.theme` + appelle `on_apply`). **Nouvelles** méthodes : `set_type_active(code, bool)`, `add_stop_term(term)`, `remove_stop_term(term)`.

- [ ] **Step 1 : Tests** — garder l'existant `test_changing_theme_updates_prefs_and_calls_apply` ; ajouter

```python
def test_toggle_entity_type_updates_overrides(qtbot):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    prefs = Preferences(); called = []
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: called.append(True), on_back=lambda: None)
    qtbot.addWidget(s)
    s.set_type_active("BIC", True)
    assert prefs.entity_overrides["BIC"] is True and called

def test_add_and_remove_stoplist_term(qtbot):
    from anonymator.referential import Referential
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.settings_screen import SettingsScreen
    prefs = Preferences()
    s = SettingsScreen(Referential.load_default(), prefs,
                       on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_stop_term("service client")
    assert "service client" in prefs.ner_stoplist
    s.remove_stop_term("service client")
    assert "service client" not in prefs.ner_stoplist
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Réécrire** `anonymator/ui/settings_screen.py`

```python
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QLineEdit, QFileDialog,
                               QListWidget, QListWidgetItem, QScrollArea)
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.toggle import ToggleSwitch
from anonymator.referential import Referential

_TYPES = ["PERSON", "ADDRESS", "ORG", "EMAIL", "PHONE", "IBAN", "BIC",
          "SIREN", "SIRET", "NIR", "POSTAL_CODE", "URL", "LOGIN", "PASSWORD"]


class SettingsScreen(QWidget):
    def __init__(self, ref, prefs, on_apply, on_back):
        super().__init__()
        self.ref, self.prefs, self.on_apply = ref, prefs, on_apply
        root = QVBoxLayout(self)
        root.addWidget(HeaderBand())
        nav = QHBoxLayout()
        back = QPushButton("Accueil"); back.setObjectName("ghost"); back.clicked.connect(on_back)
        nav.addWidget(back); nav.addWidget(QLabel("Règles de détection & masquage")); nav.addStretch()
        root.addLayout(nav)

        # thème
        root.addWidget(QLabel("Thème"))
        self.theme_box = QComboBox(); self.theme_box.addItems(["cuma", "cap"])
        self.theme_box.setCurrentText(prefs.theme)
        self.theme_box.currentTextChanged.connect(self.select_theme)
        root.addWidget(self.theme_box)

        # dossier de sortie
        root.addWidget(QLabel("Dossier de sortie"))
        row = QHBoxLayout()
        self.dir_edit = QLineEdit(prefs.output_dir or "")
        btn_dir = QPushButton("Choisir…"); btn_dir.setObjectName("secondary"); btn_dir.clicked.connect(self._choose_dir)
        row.addWidget(self.dir_edit); row.addWidget(btn_dir)
        root.addLayout(row)

        # types d'entités (toggles)
        root.addWidget(QLabel("Types d'entités à détecter"))
        self._type_toggles = {}
        grid = QScrollArea(); grid.setWidgetResizable(True)
        host = QWidget(); hv = QVBoxLayout(host)
        for code in _TYPES:
            r = QHBoxLayout(); lbl = QLabel(code); tog = ToggleSwitch()
            tog.setChecked(self.ref.is_active(code))
            tog.toggled.connect(lambda on, c=code: self.set_type_active(c, on))
            r.addWidget(lbl); r.addStretch(); r.addWidget(tog)
            hv.addLayout(r); self._type_toggles[code] = tog
        grid.setWidget(host); root.addWidget(grid)

        # liste d'exclusion
        root.addWidget(QLabel("Liste d'exclusion (NER)"))
        base = self.prefs.ner_stoplist
        if base is None:
            base = sorted(Referential.load_default().ner_stoplist())
        self.prefs.ner_stoplist = list(base)
        add_row = QHBoxLayout()
        self.stop_edit = QLineEdit()
        add = QPushButton("Ajouter"); add.setObjectName("secondary")
        add.clicked.connect(lambda: self.add_stop_term(self.stop_edit.text().strip()))
        add_row.addWidget(self.stop_edit); add_row.addWidget(add)
        root.addLayout(add_row)
        self.stop_list = QListWidget(); root.addWidget(self.stop_list)
        self._reload_stoplist()

    def select_theme(self, theme: str):
        self.prefs.theme = theme
        self.on_apply()

    def set_type_active(self, code: str, active: bool):
        self.prefs.entity_overrides[code] = active
        self.on_apply()

    def _reload_stoplist(self):
        self.stop_list.clear()
        for term in self.prefs.ner_stoplist:
            host = QWidget(); h = QHBoxLayout(host); h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QLabel(term)); h.addStretch()
            x = QPushButton("✕"); x.setObjectName("ghost"); x.setFixedWidth(30)
            x.clicked.connect(lambda _=False, t=term: self.remove_stop_term(t))
            h.addWidget(x)
            it = QListWidgetItem(); it.setSizeHint(host.sizeHint())
            self.stop_list.addItem(it); self.stop_list.setItemWidget(it, host)

    def add_stop_term(self, term: str):
        if term and term not in self.prefs.ner_stoplist:
            self.prefs.ner_stoplist.append(term)
            self.stop_edit.clear(); self._reload_stoplist(); self.on_apply()

    def remove_stop_term(self, term: str):
        if term in self.prefs.ner_stoplist:
            self.prefs.ner_stoplist.remove(term)
            self._reload_stoplist(); self.on_apply()

    def _choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Dossier de sortie")
        if path:
            self.dir_edit.setText(path); self.prefs.output_dir = path; self.on_apply()
```

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_settings_screen.py -q`. Suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py
git commit -m "feat(ui): restyle parametres + editeur detection (toggles types, stoplist)"
```

---

### Task 5 : `MainWindow` — HeaderBand global, Referential piloté par préférences

**Files:** Modify `anonymator/ui/main_window.py` ; Test `tests/test_ui_smoke.py`.

- [ ] **Step 1 : Test qui échoue** (ajouter)

```python
def test_referential_uses_prefs_overrides(qtbot, tmp_path):
    from anonymator.ui.main_window import MainWindow
    from anonymator.ui.model_loader import ModelLoader
    from anonymator.ner import FakeNer
    prefs_path = tmp_path / "prefs.json"
    prefs_path.write_text('{"theme":"cuma","entity_overrides":{"BIC":true},'
                          '"ner_stoplist":["truc"]}', encoding="utf-8")
    win = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs_path)
    qtbot.addWidget(win)
    assert win.ref.is_active("BIC") is True
    assert "truc" in win.ref.ner_stoplist()
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** — dans `MainWindow`, construire le ref depuis les prefs et le rebâtir au `_apply_prefs`. Ajouter un helper et l'utiliser :

```python
    def _build_ref(self):
        ref = Referential.load_default(overrides=self.prefs.entity_overrides)
        if self.prefs.ner_stoplist is not None:
            ref = ref.with_stoplist(self.prefs.ner_stoplist)
        return ref
```

Dans `__init__`, remplacer `self.ref = Referential.load_default()` par :
```python
        self.prefs = Preferences.load(prefs_path)
        self.ref = self._build_ref()
```

Dans `_apply_prefs`, rafraîchir le ref et le propager :
```python
    def _apply_prefs(self):
        self.prefs.save(self.prefs_path)
        self.ref = self._build_ref()
        self.text_screen.ref = self.ref
        self.file_screen.ref = self.ref
        self._apply_theme()
```

(Garder le reste de `MainWindow` inchangé. La fenêtre garde la barre native ; le `HeaderBand` est porté par chaque écran, pas par `MainWindow`.)

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_ui_smoke.py -q`. Suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/main_window.py tests/test_ui_smoke.py
git commit -m "feat(ui): Referential pilote par les preferences + refresh"
```

---

## Auto-revue (V2 vs spec)

- §6 accueil hero + NavCards → Task 2. ✓
- §6 texte : header, stats, cards, panneau toggles + badges, risque → Task 3. ✓
- §6-7 paramètres : restyle + toggles types + éditeur stoplist → Task 4. ✓
- §7 Referential piloté par préférences (overrides + stoplist), refresh → Task 5. ✓
- `preferences.ner_stoplist` → Task 1. ✓

**Hors V2 (→ P-C révisé) :** écran fichier (scan worker, table paginée, panneau) dans ce style ; routage
txt→revue texte via `on_text_review` ; `file_screen.ref` est déjà rafraîchi par `_apply_prefs` (Task 5).
**Note cosmétique :** titres de section passés en MAJUSCULES dans le code (Qt QSS ignore text-transform).
