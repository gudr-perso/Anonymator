# V1 — Fondations visuelles — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Poser le socle visuel : tokens/QSS étendus, calcul du niveau de risque, jeu d'icônes SVG, et la bibliothèque de composants réutilisables (HeaderBand, NavCard, StatCard, ToggleSwitch, CategoryBadge, Card).

**Architecture:** Composants autonomes dans `anonymator/ui/components/`, chacun testable par smoke-test pytest-qt. Le thème reste piloté par `build_qss(theme)` (swap CAP/CUMA conservé). La logique de risque vit hors Qt (`anonymator/core/risk.py`).

**Tech Stack:** PySide6, pytest-qt (offscreen, déjà configuré). Couleurs fonctionnelles via `anonymator/ui/colors.py`.

**Référence spec :** [2026-06-30-systeme-visuel-design.md](../specs/2026-06-30-systeme-visuel-design.md).

**Prérequis :** branche `feat/revue-fichier-coloree`. Tests : `.venv\Scripts\python.exe -m pytest -q` (Qt en offscreen via `tests/conftest.py`).

---

## Structure des fichiers (V1)

```
anonymator/ui/theme.py                 MODIFIER : tokens étendus + QSS riche
anonymator/core/risk.py                CRÉER : risk_level(...)
anonymator/referential.py              MODIFIER : sensitivity_for(code)
anonymator/ui/assets/icons/*.svg       CRÉER : jeu d'icônes
anonymator/ui/icons.py                 CRÉER : icon(name) + tinting
anonymator/ui/components/__init__.py   CRÉER
anonymator/ui/components/toggle.py     CRÉER : ToggleSwitch
anonymator/ui/components/badge.py      CRÉER : CategoryBadge
anonymator/ui/components/cards.py      CRÉER : Card, StatCard, NavCard
anonymator/ui/components/header.py     CRÉER : HeaderBand
tests/test_theme.py                    MODIFIER
tests/test_risk.py                     CRÉER
tests/test_referential.py             MODIFIER
tests/test_components.py               CRÉER
```

---

### Task 1 : Thème étendu (tokens + QSS)

**Files:** Modify `anonymator/ui/theme.py` ; Test `tests/test_theme.py`.

- [ ] **Step 1 : Tests qui échouent** — ajouter à `tests/test_theme.py`

```python
from anonymator.ui.theme import THEMES, build_qss, DEFAULT_THEME

def test_themes_have_extended_tokens():
    for tokens in THEMES.values():
        for key in ["bg", "bg_hero", "surface", "surface_alt", "border",
                    "primary", "action", "accent", "text", "text_muted"]:
            assert key in tokens and tokens[key].startswith("#")

def test_qss_includes_card_and_header_styles():
    qss = build_qss("cuma")
    assert "#card" in qss or "Card" in qss
    assert "HeaderBand" in qss or "#header" in qss
```

- [ ] **Step 2 : Run → FAIL** : `.venv\Scripts\python.exe -m pytest tests/test_theme.py -q`

- [ ] **Step 3 : Implémenter** — étendre `THEMES` et `_TEMPLATE` dans `anonymator/ui/theme.py`. Conserver `DEFAULT_THEME = "cuma"`, `build_qss`, et les clés existantes (`primary`, `action`, `dark`, `accent`, `bg`, `text`). Ajouter les nouvelles clés et des styles QSS par `objectName`.

```python
DEFAULT_THEME = "cuma"

THEMES = {
    "cuma": {"primary": "#31B700", "action": "#00965E", "dark": "#063b27",
             "accent": "#E8621A", "bg": "#FFFFFF", "text": "#10331F",
             "bg_hero": "#E8F3EA", "surface": "#FFFFFF", "surface_alt": "#F3FAF4",
             "border": "#E2E8E4", "text_muted": "#6B7C72"},
    "cap":  {"primary": "#1DA8E2", "action": "#1570B8", "dark": "#0D1A35",
             "accent": "#E8621A", "bg": "#FFFFFF", "text": "#1E1E2E",
             "bg_hero": "#EAF4FB", "surface": "#FFFFFF", "surface_alt": "#F4F9FD",
             "border": "#E1E8EF", "text_muted": "#6B7280"},
}

_TEMPLATE = """
QWidget {{ background: {bg}; color: {text};
          font-family: 'Inter','Segoe UI',sans-serif; font-size: 14px; }}
QLabel#title {{ font-family: 'Space Grotesk','Segoe UI',sans-serif;
               font-size: 26px; font-weight: 700; color: {text}; }}
QLabel#muted {{ color: {text_muted}; }}
QLabel#sectionLabel {{ color: {text_muted}; font-size: 11px; font-weight: 700;
                      letter-spacing: 1px; }}
#HeaderBand {{ background: {surface}; border-bottom: 1px solid {border}; }}
#Card {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; }}
#StatCard {{ background: {surface_alt}; border: 1px solid {border}; border-radius: 10px; }}
#NavCard {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; }}
#NavCard:hover {{ background: {surface_alt}; border-color: {action}; }}
QPushButton#primary {{ background: {action}; color: white; border: none;
                      border-radius: 8px; padding: 10px 18px; font-weight: 600; }}
QPushButton#primary:hover {{ background: {primary}; }}
QPushButton#secondary {{ background: transparent; color: {text};
                        border: 1px solid {border}; border-radius: 8px; padding: 10px 18px; }}
QPushButton#ghost {{ background: transparent; color: {action}; border: none; padding: 8px 14px; }}
"""

def build_qss(theme: str) -> str:
    tokens = THEMES.get(theme, THEMES[DEFAULT_THEME])
    return _TEMPLATE.format(**tokens)
```

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_theme.py -q` (dont les tests existants : `build_qss("cap")` contient `action`, fallback thème inconnu, défaut cuma). Suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/theme.py tests/test_theme.py
git commit -m "feat(theme): tokens etendus + QSS composants (cartes, header, boutons)"
```

---

### Task 2 : Niveau de risque + sensibilité au référentiel

**Files:** Create `anonymator/core/risk.py` ; Modify `anonymator/referential.py` ; Test `tests/test_risk.py`, `tests/test_referential.py`.

- [ ] **Step 1 : Tests qui échouent**

`tests/test_referential.py` (ajouter) :
```python
def test_sensitivity_for():
    ref = Referential.load_default()
    assert ref.sensitivity_for("PERSON") == "Haute"
    assert ref.sensitivity_for("POSTAL_CODE") == "Basse"
    assert ref.sensitivity_for("INCONNU") == "Basse"   # défaut prudent
```

`tests/test_risk.py` (créer) :
```python
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.core.risk import risk_level

REF = Referential.load_default()

def _e(t):
    return Entity(t, "x", 0, 1, "deterministic")

def test_high_when_any_haute():
    assert risk_level([_e("PERSON")], REF) == "Élevé"

def test_medium_when_moyenne_only():
    assert risk_level([_e("ORG")], REF) == "Moyen"     # ORG = Moyenne

def test_low_when_empty_or_basse():
    assert risk_level([], REF) == "Faible"
    assert risk_level([_e("POSTAL_CODE")], REF) == "Faible"
```

- [ ] **Step 2 : Run → FAIL** : `.venv\Scripts\python.exe -m pytest tests/test_risk.py tests/test_referential.py -q`

- [ ] **Step 3 : Implémenter**

Dans `anonymator/referential.py`, ajouter la méthode :
```python
    def sensitivity_for(self, code: str) -> str:
        return self._by_code.get(code, {}).get("sensitivity", "Basse")
```

Créer `anonymator/core/risk.py` :
```python
from anonymator.model import Entity
from anonymator.referential import Referential

_ORDER = {"Haute": 3, "Moyenne": 2, "Basse": 1}


def risk_level(entities: list[Entity], ref: Referential) -> str:
    """Niveau de risque d'après la plus haute sensibilité parmi les entités retenues."""
    top = max((_ORDER.get(ref.sensitivity_for(e.type), 1) for e in entities), default=0)
    if top >= 3:
        return "Élevé"
    if top == 2:
        return "Moyen"
    return "Faible"
```

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_risk.py tests/test_referential.py -q`. Suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/risk.py anonymator/referential.py tests/test_risk.py tests/test_referential.py
git commit -m "feat(core): niveau de risque + sensitivity_for au referentiel"
```

---

### Task 3 : Jeu d'icônes SVG + helper

**Files:** Create `anonymator/ui/assets/icons/*.svg`, `anonymator/ui/icons.py` ; Test `tests/test_components.py`.

- [ ] **Step 1 : Test qui échoue** — créer `tests/test_components.py`

```python
from PySide6.QtGui import QIcon
from anonymator.ui.icons import icon, ICON_NAMES

def test_icons_load(qtbot):
    for name in ICON_NAMES:
        ic = icon(name)
        assert isinstance(ic, QIcon)
        assert not ic.isNull()
```

- [ ] **Step 2 : Run → FAIL** : `.venv\Scripts\python.exe -m pytest tests/test_components.py -q`

- [ ] **Step 3 : Implémenter**

Créer le dossier `anonymator/ui/assets/icons/` et y écrire ces fichiers SVG (trait `currentColor`, 24×24). Exemples concrets (créer AU MOINS ces 8 ; tous doivent être des SVG valides) :

`document.svg` :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
```
`folder.svg` :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z"/></svg>
```
`settings.svg` :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="4" y1="8" x2="20" y2="8"/><line x1="4" y1="16" x2="20" y2="16"/><circle cx="9" cy="8" r="2" fill="currentColor"/><circle cx="15" cy="16" r="2" fill="currentColor"/></svg>
```
`chevron-right.svg` :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>
```
`shield.svg` :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 3v6c0 4.5-3 7.5-8 9-5-1.5-8-4.5-8-9V6z"/></svg>
```
`layers.svg` :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/></svg>
```
`eye-off.svg` :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3l18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.4 5.2A9 9 0 0 1 21 12a9.8 9.8 0 0 1-2 2.6M6 6.3A9.8 9.8 0 0 0 3 12a9 9 0 0 0 11 6.7"/></svg>
```
`alert.svg` :
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9 16H3z"/><line x1="12" y1="9" x2="12" y2="14"/><circle cx="12" cy="17" r="0.6" fill="currentColor"/></svg>
```

Créer `anonymator/ui/icons.py` :
```python
from pathlib import Path
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer

_DIR = Path(__file__).parent / "assets" / "icons"
ICON_NAMES = ["document", "folder", "settings", "chevron-right",
              "shield", "layers", "eye-off", "alert"]


def icon(name: str, color: str | None = None, size: int = 24) -> QIcon:
    path = _DIR / f"{name}.svg"
    renderer = QSvgRenderer(str(path))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    if color is not None:
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pix.rect(), QColor(color))
    painter.end()
    return QIcon(pix)
```

Note : `QtSvg` est fourni par PySide6. Si `QSvgRenderer` n'est pas disponible, ajouter `from PySide6.QtSvgWidgets import ...` n'est PAS nécessaire — `QtSvg.QSvgRenderer` suffit.

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_components.py -q`.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/assets/icons anonymator/ui/icons.py tests/test_components.py
git commit -m "feat(ui): jeu d'icones SVG + helper icon() teintable"
```

---

### Task 4 : `ToggleSwitch`

**Files:** Create `anonymator/ui/components/__init__.py`, `anonymator/ui/components/toggle.py` ; Test `tests/test_components.py`.

- [ ] **Step 1 : Test qui échoue** (ajouter)

```python
from anonymator.ui.components.toggle import ToggleSwitch

def test_toggle_switch(qtbot):
    t = ToggleSwitch(); qtbot.addWidget(t)
    assert t.isChecked() is False
    states = []
    t.toggled.connect(states.append)
    t.setChecked(True)
    assert t.isChecked() is True and states == [True]
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

`anonymator/ui/components/__init__.py` : fichier vide.

`anonymator/ui/components/toggle.py` :
```python
from PySide6.QtWidgets import QAbstractButton
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QSize

_ON = "#00965E"
_OFF = "#C7D2CC"


class ToggleSwitch(QAbstractButton):
    """Interrupteur on/off stylé (vert)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(44, 24)

    def sizeHint(self) -> QSize:
        return QSize(44, 24)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        track = QColor(_ON if self.isChecked() else _OFF)
        p.setBrush(track); p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)
        d = 18
        x = self.width() - d - 3 if self.isChecked() else 3
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(x, 3, d, d)
        p.end()
```

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_components.py -q`.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/__init__.py anonymator/ui/components/toggle.py tests/test_components.py
git commit -m "feat(ui): composant ToggleSwitch"
```

---

### Task 5 : `CategoryBadge`

**Files:** Create `anonymator/ui/components/badge.py` ; Test `tests/test_components.py`.

- [ ] **Step 1 : Test qui échoue** (ajouter)

```python
from anonymator.ui.components.badge import CategoryBadge
from anonymator.ui.colors import color_for

def test_category_badge(qtbot):
    b = CategoryBadge("PERSON", "NOM"); qtbot.addWidget(b)
    assert b.text() == "NOM"
    assert color_for("PERSON").lstrip("#").lower() in b.styleSheet().lower()
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** `anonymator/ui/components/badge.py`

```python
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from anonymator.ui.colors import color_for


class CategoryBadge(QLabel):
    """Étiquette arrondie colorée pour une typologie."""
    def __init__(self, etype: str, label: str | None = None, parent=None):
        super().__init__(label or etype, parent)
        c = color_for(etype)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"background: {c}22; color: {c}; border-radius: 8px;"
            f"padding: 2px 8px; font-size: 11px; font-weight: 700;")
```

- [ ] **Step 4 : Run → PASS**.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/badge.py tests/test_components.py
git commit -m "feat(ui): composant CategoryBadge"
```

---

### Task 6 : `Card`, `StatCard`, `NavCard`

**Files:** Create `anonymator/ui/components/cards.py` ; Test `tests/test_components.py`.

- [ ] **Step 1 : Tests qui échouent** (ajouter)

```python
from anonymator.ui.components.cards import Card, StatCard, NavCard

def test_stat_card(qtbot):
    s = StatCard("layers", "Catégories"); qtbot.addWidget(s)
    s.set_value("6")
    assert s.value_label.text() == "6"

def test_nav_card_clicked(qtbot):
    clicks = []
    n = NavCard("document", "Coller du texte", "Analyser un texte", on_click=lambda: clicks.append(1))
    qtbot.addWidget(n)
    n._emit()           # déclenche le clic programmatiquement
    assert clicks == [1]

def test_card_title(qtbot):
    c = Card("shield", "Entités détectées"); qtbot.addWidget(c)
    assert "Entités détectées" in c.title_label.text()
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** `anonymator/ui/components/cards.py`

```python
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QGraphicsColorizeEffect)
from PySide6.QtCore import Qt
from anonymator.ui.icons import icon


class Card(QFrame):
    """Conteneur titré (icône + titre en capitales + corps via .body)."""
    def __init__(self, icon_name: str, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        head = QHBoxLayout()
        ic = QLabel(); ic.setPixmap(icon(icon_name, "#00965E").pixmap(16, 16))
        self.title_label = QLabel(title.upper())
        self.title_label.setObjectName("sectionLabel")
        head.addWidget(ic); head.addWidget(self.title_label); head.addStretch()
        outer.addLayout(head)
        self.body = QVBoxLayout()
        outer.addLayout(self.body)


class StatCard(QFrame):
    """Icône + grand nombre + libellé."""
    def __init__(self, icon_name: str, label: str, accent: str = "#00965E", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        row = QHBoxLayout(self)
        ic = QLabel(); ic.setPixmap(icon(icon_name, accent).pixmap(20, 20))
        col = QVBoxLayout()
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet("font-size: 22px; font-weight: 700;")
        lbl = QLabel(label); lbl.setObjectName("muted")
        col.addWidget(self.value_label); col.addWidget(lbl)
        row.addWidget(ic); row.addLayout(col); row.addStretch()

    def set_value(self, value) -> None:
        self.value_label.setText(str(value))


class NavCard(QFrame):
    """Carte cliquable : icône + titre + sous-titre + chevron."""
    def __init__(self, icon_name: str, title: str, subtitle: str,
                 on_click=None, parent=None):
        super().__init__(parent)
        self.setObjectName("NavCard")
        self.setCursor(Qt.PointingHandCursor)
        self._on_click = on_click
        row = QHBoxLayout(self)
        ic = QLabel(); ic.setPixmap(icon(icon_name, "#00965E").pixmap(22, 22))
        col = QVBoxLayout()
        t = QLabel(title); t.setStyleSheet("font-size: 15px; font-weight: 700;")
        s = QLabel(subtitle); s.setObjectName("muted")
        col.addWidget(t); col.addWidget(s)
        chev = QLabel(); chev.setPixmap(icon("chevron-right", "#6B7C72").pixmap(18, 18))
        row.addWidget(ic); row.addLayout(col); row.addStretch(); row.addWidget(chev)

    def _emit(self):
        if self._on_click:
            self._on_click()

    def mouseReleaseEvent(self, event):
        self._emit()
        super().mouseReleaseEvent(event)
```

- [ ] **Step 4 : Run → PASS** : `.venv\Scripts\python.exe -m pytest tests/test_components.py -q`.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/cards.py tests/test_components.py
git commit -m "feat(ui): composants Card, StatCard, NavCard"
```

---

### Task 7 : `HeaderBand`

**Files:** Create `anonymator/ui/components/header.py` ; Test `tests/test_components.py`.

- [ ] **Step 1 : Test qui échoue** (ajouter)

```python
from PySide6.QtWidgets import QLabel
from anonymator.ui.components.header import HeaderBand

def test_header_band(qtbot):
    h = HeaderBand(); qtbot.addWidget(h)
    assert h.objectName() == "HeaderBand"
    labels = [w.text() for w in h.findChildren(QLabel)]
    assert "Anonymator" in labels
    assert any("CUMA" in t for t in labels)
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** `anonymator/ui/components/header.py`

```python
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from anonymator.ui.icons import icon


class HeaderBand(QFrame):
    """Bandeau d'en-tête : logo + nom de l'app + réseau."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBand")
        row = QHBoxLayout(self)
        logo = QLabel(); logo.setPixmap(icon("shield", "#31B700").pixmap(20, 20))
        name = QLabel("Anonymator"); name.setStyleSheet("font-weight: 700;")
        sep = QLabel("|"); sep.setObjectName("muted")
        net = QLabel("RÉSEAU CUMA"); net.setObjectName("muted")
        net.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
        for w in (logo, name, sep, net):
            row.addWidget(w)
        row.addStretch()
```

- [ ] **Step 4 : Run → PASS**.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/header.py tests/test_components.py
git commit -m "feat(ui): composant HeaderBand"
```

---

## Auto-revue (V1 vs spec système visuel)

- §3 tokens étendus + QSS → Task 1. ✓
- §5 niveau de risque → Task 2. ✓
- §4 icônes SVG + helper → Task 3. ✓
- §4 ToggleSwitch / CategoryBadge / Card / StatCard / NavCard / HeaderBand → Tasks 4-7. ✓

**Hors V1 (→ V2)** : restyle des écrans accueil/texte/paramètres avec ces composants ; **(→ P-C révisé)** :
écran fichier stylé. Le `pills` du résultat et le helper `highlight_format(type)` (surlignage texte)
seront posés lors du restyle de l'écran texte (V2), au plus près de leur usage.
