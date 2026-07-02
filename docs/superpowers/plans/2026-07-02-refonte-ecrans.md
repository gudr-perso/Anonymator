# Refonte visuelle des écrans — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Porter les écrans Paramètres, Règles et À propos sur le design system carte (fidèle aux maquettes) et ajouter un bandeau d'onglets global à toutes les pages.

**Architecture:** On introduit un composant nav partagé (`NavBand`) inclus par chaque écran, des mini-composants (`EntityCard`, `RuleActionBadge`), un module de métadonnées d'entités, de nouvelles icônes SVG, et des ajouts QSS. Les trois écrans cibles sont réécrits (présentation seule) ; Accueil/Texte/Fichier/PDF reçoivent le `NavBand`. Aucune logique métier (référentiel, prefs, user_rules, téléchargement modèle) n'est modifiée.

**Tech Stack:** PySide6 (Qt Widgets), pytest + pytest-qt, QSS.

**Environnement de test :** `.venv\Scripts\python -m pytest ...` (venv déjà créé). Sous Windows, exécuter avec `QT_QPA_PLATFORM=offscreen` si pas de display.

---

## File Structure

- Create: `anonymator/ui/entity_meta.py` — libellés/sous-titres/icônes des 14 types
- Create: `anonymator/ui/components/nav_band.py` — bandeau d'onglets partagé
- Create: `anonymator/ui/components/entity_card.py` — mini-carte type + toggle
- Create: `anonymator/ui/components/rule_action_badge.py` — badge vert/orange
- Create: `anonymator/ui/assets/icons/*.svg` — 17 nouvelles icônes
- Modify: `anonymator/ui/icons.py` — `ICON_NAMES`
- Modify: `anonymator/ui/theme.py` — mapping libellés thème + QSS
- Modify: `anonymator/ui/settings_screen.py` — réécriture vue
- Modify: `anonymator/ui/rules_screen.py` — réécriture vue (liste → table)
- Modify: `anonymator/ui/about_screen.py` — réécriture vue
- Modify: `home_screen.py`, `text_screen.py`, `file_screen.py`, `pdf_screen.py` — insertion `NavBand`
- Test: `tests/test_*` correspondants

---

## Task 1: Nouvelles icônes SVG

**Files:**
- Create: `anonymator/ui/assets/icons/{person,user,building,map-pin,mail,phone,credit-card,scale,id-card,globe,lock,eye,trash,palette,cpu,github,package}.svg`
- Modify: `anonymator/ui/icons.py:6-8` (`ICON_NAMES`)
- Test: `tests/test_icons_new.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_icons_new.py
import pytest
from anonymator.ui.icons import icon

NEW = ["person", "user", "building", "map-pin", "mail", "phone",
       "credit-card", "scale", "id-card", "globe", "lock", "eye",
       "trash", "palette", "cpu", "github", "package"]

@pytest.mark.parametrize("name", NEW)
def test_new_icon_loads_and_tints(qtbot, name):
    ic = icon(name, "#00965E", size=16)
    assert not ic.isNull()
    assert not ic.pixmap(16, 16).isNull()
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_icons_new.py -v`
Expected: FAIL (fichiers SVG absents → pixmap nul / QSvgRenderer invalide)

- [ ] **Step 3: Créer les 17 SVG**

Chaque icône : `viewBox="0 0 24 24"`, traits `stroke="#000"` (teintés au runtime par `icon()` via SourceIn). Créer un fichier par nom avec ce contenu :

`person.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/></svg>
```
`user.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="10" r="3"/><path d="M6.5 18a5.5 5.5 0 0 1 11 0"/></svg>
```
`building.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2"/></svg>
```
`map-pin.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-6.5 7-12a7 7 0 0 0-14 0c0 5.5 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/></svg>
```
`mail.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg>
```
`phone.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/></svg>
```
`credit-card.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M2 10h20M6 15h4"/></svg>
```
`scale.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18M7 21h10M5 7h14M5 7 2.5 13h5zM19 7l-2.5 6h5z"/></svg>
```
`id-card.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="11" r="2"/><path d="M13 9h5M13 13h5M5.5 16a3 3 0 0 1 6 0"/></svg>
```
`globe.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18"/></svg>
```
`lock.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
```
`eye.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>
```
`trash.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M6 7l1 13a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1l1-13"/></svg>
```
`palette.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3a9 9 0 0 0 0 18c1.5 0 2-1 2-2s-1-1-1-2 1-2 2-2h2a4 4 0 0 0 4-4c0-3.9-4-6-9-6z"/><circle cx="7.5" cy="11" r="1"/><circle cx="12" cy="8" r="1"/><circle cx="16" cy="11" r="1"/></svg>
```
`cpu.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="7" width="10" height="10" rx="1"/><path d="M10 2v3M14 2v3M10 19v3M14 19v3M2 10h3M2 14h3M19 10h3M19 14h3"/></svg>
```
`github.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 19c-4 1.5-4-2-6-2m12 4v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2 4.3 4.3 0 0 0-.1-3.2s-1-.3-3.5 1.3a12 12 0 0 0-6 0C6.5 2.8 5.5 3.1 5.5 3.1a4.3 4.3 0 0 0-.1 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/></svg>
```
`package.svg`
```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z"/><path d="M4 7.5 12 12l8-4.5M12 12v9"/></svg>
```

- [ ] **Step 4: Enregistrer les noms dans `icons.py`**

Remplacer la liste `ICON_NAMES` (lignes 6-8) par :
```python
ICON_NAMES = ["document", "folder", "settings", "chevron-right",
              "shield", "layers", "eye-off", "alert",
              "sparkle", "scan", "home",
              "person", "user", "building", "map-pin", "mail", "phone",
              "credit-card", "scale", "id-card", "globe", "lock", "eye",
              "trash", "palette", "cpu", "github", "package"]
```

- [ ] **Step 5: Lancer le test (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_icons_new.py -v`
Expected: PASS (17 cas)

- [ ] **Step 6: Commit**

```bash
git add anonymator/ui/assets/icons tests/test_icons_new.py anonymator/ui/icons.py
git commit -m "feat(ui): icônes SVG pour cartes d'entités, nav et à propos"
```

---

## Task 2: Métadonnées des 14 types d'entités

**Files:**
- Create: `anonymator/ui/entity_meta.py`
- Test: `tests/test_entity_meta.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_entity_meta.py
from anonymator.ui.entity_meta import ENTITY_META, EntityMeta
from anonymator.ui.settings_screen import _TYPES  # liste source des 14 codes

def test_all_types_have_meta():
    for code in _TYPES:
        assert code in ENTITY_META, f"métadonnée manquante : {code}"
        m = ENTITY_META[code]
        assert isinstance(m, EntityMeta)
        assert m.label and m.subtitle and m.icon

def test_person_meta():
    m = ENTITY_META["PERSON"]
    assert m.label == "PERSON"
    assert m.subtitle == "Noms et prénoms de personnes"
    assert m.icon == "person"
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_entity_meta.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Écrire le module**

```python
# anonymator/ui/entity_meta.py
"""Métadonnées d'affichage des types d'entités (libellé, sous-titre, icône).
Présentation uniquement — la liste des codes fait foi dans settings_screen._TYPES."""
from dataclasses import dataclass


@dataclass(frozen=True)
class EntityMeta:
    label: str
    subtitle: str
    icon: str


ENTITY_META = {
    "PERSON":      EntityMeta("PERSON", "Noms et prénoms de personnes", "person"),
    "ADDRESS":     EntityMeta("ADDRESS", "Adresses postales", "map-pin"),
    "ORG":         EntityMeta("ORG", "Organisations, entreprises", "building"),
    "EMAIL":       EntityMeta("EMAIL", "Adresses e-mail", "mail"),
    "PHONE":       EntityMeta("PHONE", "Numéros de téléphone", "phone"),
    "IBAN":        EntityMeta("IBAN", "Coordonnées bancaires", "credit-card"),
    "BIC":         EntityMeta("BIC", "Codes banque · SWIFT", "scale"),
    "SIREN":       EntityMeta("SIREN", "Identifiants d'entreprise", "building"),
    "SIRET":       EntityMeta("SIRET", "Établissements (SIREN + NIC)", "building"),
    "NIR":         EntityMeta("NIR", "Numéro de sécurité sociale", "id-card"),
    "POSTAL_CODE": EntityMeta("POSTAL_CODE", "Codes postaux", "map-pin"),
    "URL":         EntityMeta("URL", "Adresses web", "globe"),
    "LOGIN":       EntityMeta("LOGIN", "Identifiants de connexion", "user"),
    "PASSWORD":    EntityMeta("PASSWORD", "Mots de passe", "lock"),
}
```

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_entity_meta.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/entity_meta.py tests/test_entity_meta.py
git commit -m "feat(ui): métadonnées d'affichage des 14 types d'entités"
```

---

## Task 3: Mapping libellés de thème

**Files:**
- Modify: `anonymator/ui/theme.py` (ajout en tête, après `THEMES`)
- Test: `tests/test_theme_labels.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_theme_labels.py
from anonymator.ui.theme import THEME_LABELS, label_for_theme, theme_for_label, THEMES

def test_every_theme_has_label():
    for key in THEMES:
        assert key in THEME_LABELS

def test_roundtrip():
    for key in THEMES:
        assert theme_for_label(label_for_theme(key)) == key

def test_cuma_label():
    assert label_for_theme("cuma") == "CUMA — vert identitaire"
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_theme_labels.py -v`
Expected: FAIL (`ImportError`)

- [ ] **Step 3: Ajouter dans `theme.py` (juste après le dict `THEMES`, avant `_TEMPLATE`)**

```python
THEME_LABELS = {
    "cuma": "CUMA — vert identitaire",
    "cap":  "CAP — bleu",
}


def label_for_theme(theme: str) -> str:
    return THEME_LABELS.get(theme, theme)


def theme_for_label(label: str) -> str:
    for key, lbl in THEME_LABELS.items():
        if lbl == label:
            return key
    return DEFAULT_THEME
```

- [ ] **Step 4: Lancer le test (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_theme_labels.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/theme.py tests/test_theme_labels.py
git commit -m "feat(ui): libellés lisibles des thèmes"
```

---

## Task 4: Composant NavBand + QSS

**Files:**
- Create: `anonymator/ui/components/nav_band.py`
- Modify: `anonymator/ui/theme.py` (`_TEMPLATE`, ajout règles nav)
- Test: `tests/test_nav_band.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_nav_band.py
from anonymator.ui.components.nav_band import NavBand

def test_home_callback(qtbot):
    called = []
    band = NavBand("Détection & masquage", "settings", on_home=lambda: called.append(True))
    qtbot.addWidget(band)
    band.home_btn.click()
    assert called == [True]

def test_active_title(qtbot):
    band = NavBand("Règles métier", "layers", on_home=lambda: None)
    qtbot.addWidget(band)
    assert band.active_btn.text().strip() == "Règles métier"
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_nav_band.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Écrire le composant**

```python
# anonymator/ui/components/nav_band.py
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from anonymator.ui.icons import icon


class NavBand(QFrame):
    """Bandeau d'onglets : « Accueil » + onglet de l'écran actif (souligné).

    home_btn : retour accueil. active_btn : onglet non cliquable de l'écran courant.
    Sur l'écran Accueil, passer title="Accueil"/icon="home" et on_home=None."""
    def __init__(self, title: str, icon_name: str, on_home=None, parent=None):
        super().__init__(parent)
        self.setObjectName("NavBand")
        row = QHBoxLayout(self)
        row.setContentsMargins(16, 0, 16, 0)
        row.setSpacing(4)

        self.home_btn = QPushButton("  Accueil")
        self.home_btn.setObjectName("tab")
        self.home_btn.setIcon(icon("home", "#6B7C72", 18))
        self.home_btn.setCursor(Qt.PointingHandCursor)
        if on_home is not None:
            self.home_btn.clicked.connect(on_home)
        else:
            self.home_btn.setObjectName("tabActive")

        self.active_btn = QPushButton("  " + title)
        self.active_btn.setObjectName("tabActive")
        self.active_btn.setIcon(icon(icon_name, "#00965E", 18))
        self.active_btn.setEnabled(False)

        row.addWidget(self.home_btn)
        if on_home is not None:
            row.addWidget(self.active_btn)
        row.addStretch()
```

- [ ] **Step 4: Ajouter le QSS dans `theme.py` `_TEMPLATE`** (avant la triple-quote fermante)

```
#NavBand {{ background: {surface}; border-bottom: 1px solid {border}; }}
QPushButton#tab {{ background: transparent; color: {text_muted}; border: none;
                  border-bottom: 3px solid transparent; padding: 12px 14px; font-weight: 600; }}
QPushButton#tab:hover {{ color: {text}; }}
QPushButton#tabActive {{ background: transparent; color: {action}; border: none;
                        border-bottom: 3px solid {action}; padding: 12px 14px; font-weight: 700; }}
QPushButton#tabActive:disabled {{ color: {action}; }}
```

- [ ] **Step 5: Lancer les tests (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_nav_band.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add anonymator/ui/components/nav_band.py anonymator/ui/theme.py tests/test_nav_band.py
git commit -m "feat(ui): bandeau d'onglets NavBand + QSS"
```

---

## Task 5: Composant EntityCard + QSS

**Files:**
- Create: `anonymator/ui/components/entity_card.py`
- Modify: `anonymator/ui/theme.py` (`_TEMPLATE`, `#EntityCard`)
- Test: `tests/test_entity_card.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_entity_card.py
from anonymator.ui.components.entity_card import EntityCard

def test_reflects_initial_state(qtbot):
    card = EntityCard("PERSON", active=True)
    qtbot.addWidget(card)
    assert card.toggle.isChecked() is True

def test_emits_on_toggle(qtbot):
    seen = []
    card = EntityCard("EMAIL", active=False)
    qtbot.addWidget(card)
    card.toggled.connect(lambda code, on: seen.append((code, on)))
    card.toggle.setChecked(True)
    assert seen == [("EMAIL", True)]
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_entity_card.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Écrire le composant**

```python
# anonymator/ui/components/entity_card.py
from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel
from PySide6.QtCore import Signal
from anonymator.ui.icons import icon
from anonymator.ui.components.toggle import ToggleSwitch
from anonymator.ui.entity_meta import ENTITY_META
from anonymator.ui.colors import color_for


class EntityCard(QFrame):
    """Mini-carte d'un type d'entité : icône + libellé + sous-titre + toggle."""
    toggled = Signal(str, bool)

    def __init__(self, code: str, active: bool, parent=None):
        super().__init__(parent)
        self.code = code
        self.setObjectName("EntityCard")
        meta = ENTITY_META[code]
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 12, 14, 12)
        ic = QLabel()
        ic.setPixmap(icon(meta.icon, color_for(code), 20).pixmap(20, 20))
        col = QVBoxLayout(); col.setSpacing(1)
        t = QLabel(meta.label); t.setStyleSheet("font-weight: 700;")
        s = QLabel(meta.subtitle); s.setObjectName("muted"); s.setStyleSheet("font-size: 12px;")
        col.addWidget(t); col.addWidget(s)
        self.toggle = ToggleSwitch(); self.toggle.setChecked(active)
        self.toggle.toggled.connect(lambda on: self.toggled.emit(self.code, on))
        row.addWidget(ic); row.addSpacing(6); row.addLayout(col); row.addStretch()
        row.addWidget(self.toggle)
```

- [ ] **Step 4: Ajouter le QSS dans `theme.py` `_TEMPLATE`**

```
#EntityCard {{ background: {surface}; border: 1px solid {border}; border-radius: 10px; }}
#EntityCard:hover {{ border-color: {action}; }}
```

- [ ] **Step 5: Lancer les tests (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_entity_card.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add anonymator/ui/components/entity_card.py anonymator/ui/theme.py tests/test_entity_card.py
git commit -m "feat(ui): mini-carte EntityCard type + toggle"
```

---

## Task 6: Badge d'action de règle

**Files:**
- Create: `anonymator/ui/components/rule_action_badge.py`
- Test: `tests/test_rule_action_badge.py`

- [ ] **Step 1: Écrire le test qui échoue**

```python
# tests/test_rule_action_badge.py
from anonymator.ui.components.rule_action_badge import RuleActionBadge

def test_keep_is_green_eye(qtbot):
    b = RuleActionBadge("keep")
    qtbot.addWidget(b)
    assert "Ne jamais masquer" in b.text()
    assert "00965E" in b.styleSheet().upper() or "31B700" in b.styleSheet().upper()

def test_mask_is_orange(qtbot):
    b = RuleActionBadge("mask")
    qtbot.addWidget(b)
    assert "Toujours masquer" in b.text()
    assert "E8621A" in b.styleSheet().upper()
```

- [ ] **Step 2: Lancer le test (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_rule_action_badge.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Écrire le composant**

```python
# anonymator/ui/components/rule_action_badge.py
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


class RuleActionBadge(QLabel):
    """Badge coloré pour l'action d'une règle. action ∈ {'keep','mask'}."""
    _KEEP = "#00965E"
    _MASK = "#E8621A"

    def __init__(self, action: str, parent=None):
        keep = action == "keep"
        text = "👁  Ne jamais masquer" if keep else "🚫  Toujours masquer"
        color = self._KEEP if keep else self._MASK
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(
            f"background: {_rgba(color, 0.14)}; color: {color}; border-radius: 8px;"
            f"padding: 3px 10px; font-size: 12px; font-weight: 700;")
```

- [ ] **Step 4: Lancer les tests (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_rule_action_badge.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/components/rule_action_badge.py tests/test_rule_action_badge.py
git commit -m "feat(ui): badge d'action de règle (vert/orange)"
```

---

## Task 7: Réécriture de l'écran Paramètres

**Files:**
- Modify: `anonymator/ui/settings_screen.py` (méthode `__init__` — construction de la vue)
- Test: `tests/test_settings_screen.py`

Contrainte : conserver **toute** la logique existante (`select_theme`, `set_type_active`, `_choose_dir`, section modèle : `_refresh_model_section`, `start_model_download`, `_on_model_*`, `stop_download`, `closeEvent`, `model_ready`, `_TYPES`). Seule la construction des widgets dans `__init__` change.

- [ ] **Step 1: Adapter/écrire les tests**

Lire `tests/test_settings_screen.py` puis remplacer les accroches de structure par des accroches de comportement. Tests attendus :
```python
# tests/test_settings_screen.py (extraits clés)
from anonymator.ui.settings_screen import SettingsScreen, _TYPES

class _Prefs:
    theme = "cuma"; output_dir = ""; entity_overrides = {}

def _mk(qtbot, ref):
    applied = []
    scr = SettingsScreen(ref, _Prefs(), on_apply=lambda: applied.append(1), on_back=lambda: None)
    qtbot.addWidget(scr)
    return scr, applied

def test_one_card_per_type(qtbot, ref_all_active):
    scr, _ = _mk(qtbot, ref_all_active)
    assert len(scr._type_toggles) == len(_TYPES)

def test_active_counter(qtbot, ref_all_active):
    scr, _ = _mk(qtbot, ref_all_active)
    assert f"/ {len(_TYPES)}" in scr.count_badge.text()

def test_toggle_sets_override(qtbot, ref_all_active):
    scr, applied = _mk(qtbot, ref_all_active)
    scr._type_toggles["PERSON"].setChecked(False)
    assert scr.prefs.entity_overrides["PERSON"] is False
    assert applied  # on_apply déclenché
```
(`ref_all_active` : fixture renvoyant un `Referential` où `is_active(code)` est vrai — réutiliser la fixture existante du fichier ou un stub avec `is_active=lambda c: True`.)

- [ ] **Step 2: Lancer les tests (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_settings_screen.py -v`
Expected: FAIL (`count_badge` absent, structure différente)

- [ ] **Step 3: Réécrire `__init__` (garder les méthodes intactes)**

```python
def __init__(self, ref, prefs, on_apply, on_back):
    super().__init__()
    from PySide6.QtWidgets import QGridLayout
    from anonymator.ui.components.header import HeaderBand
    from anonymator.ui.components.nav_band import NavBand
    from anonymator.ui.components.cards import Card
    from anonymator.ui.components.entity_card import EntityCard
    from anonymator.ui.theme import THEME_LABELS, label_for_theme, theme_for_label
    self.ref, self.prefs, self.on_apply = ref, prefs, on_apply

    root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
    root.addWidget(HeaderBand())
    root.addWidget(NavBand("Détection & masquage", "settings", on_home=on_back))

    scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
    host = QWidget(); body = QVBoxLayout(host)
    body.setContentsMargins(40, 24, 40, 40); body.setSpacing(18)
    scroll.setWidget(host); root.addWidget(scroll)

    title = QLabel("Détection & masquage"); title.setObjectName("title")
    subtitle = QLabel("Réglez le thème, la sortie et ce que l'application repère automatiquement.")
    subtitle.setObjectName("muted")
    body.addWidget(title); body.addWidget(subtitle)

    # --- Carte GÉNÉRAL ---
    general = Card("palette", "Général")
    general.body.addWidget(QLabel("Thème de l'application"))
    self.theme_box = QComboBox()
    self.theme_box.addItems([THEME_LABELS[k] for k in ("cuma", "cap")])
    self.theme_box.setCurrentText(label_for_theme(prefs.theme))
    self.theme_box.currentTextChanged.connect(
        lambda lbl: self.select_theme(theme_for_label(lbl)))
    general.body.addWidget(self.theme_box)
    general.body.addWidget(QLabel("Dossier de sortie"))
    row = QHBoxLayout()
    self.dir_edit = QLineEdit(prefs.output_dir or "")
    btn_dir = QPushButton("Choisir…"); btn_dir.setObjectName("secondary")
    btn_dir.clicked.connect(self._choose_dir)
    row.addWidget(self.dir_edit); row.addWidget(btn_dir)
    general.body.addLayout(row)
    body.addWidget(general)

    # --- Carte TYPES D'ENTITÉS ---
    types_card = Card("shield", "Types d'entités à détecter")
    self.count_badge = QLabel(""); self.count_badge.setObjectName("occBadge")
    types_card.head.addWidget(self.count_badge)
    grid = QGridLayout(); grid.setSpacing(10)
    self._type_toggles = {}
    for i, code in enumerate(_TYPES):
        card = EntityCard(code, active=self.ref.is_active(code))
        card.toggled.connect(self.set_type_active)
        grid.addWidget(card, i // 2, i % 2)
        self._type_toggles[code] = card.toggle
    types_card.body.addLayout(grid)
    body.addWidget(types_card)
    self._refresh_type_count()

    # --- Carte MODÈLE ---
    self._dl_worker = None
    model_card = Card("cpu", "Modèle de détection intelligente")
    explain = QLabel(
        "La détection intelligente des noms, adresses et organisations utilise "
        "le modèle GLiNER (~300 Mo), téléchargé une seule fois puis utilisé hors ligne. "
        "Sans lui, les détections par règles (IBAN, e-mail, téléphone, mots de passe…) "
        "fonctionnent quand même.")
    explain.setWordWrap(True); explain.setObjectName("muted")
    model_card.body.addWidget(explain)
    self.model_status_label = QLabel(""); model_card.body.addWidget(self.model_status_label)
    self.model_location_label = QLabel(""); self.model_location_label.setObjectName("muted")
    self.model_location_label.setWordWrap(True); model_card.body.addWidget(self.model_location_label)
    self.btn_model = QPushButton(""); self.btn_model.setObjectName("primary")
    self.btn_model.clicked.connect(self.start_model_download); model_card.body.addWidget(self.btn_model)
    self.model_progress = QProgressBar(); self.model_progress.setVisible(False)
    model_card.body.addWidget(self.model_progress)
    self.model_dl_status = QLabel(""); self.model_dl_status.setObjectName("muted")
    model_card.body.addWidget(self.model_dl_status)
    body.addWidget(model_card)
    body.addStretch()
    self._refresh_model_section()
```

Ajouter la méthode helper (compteur) et appeler `_refresh_type_count()` dans `set_type_active` :
```python
def _refresh_type_count(self):
    n = sum(1 for t in self._type_toggles.values() if t.isChecked())
    self.count_badge.setText(f"{n} / {len(_TYPES)} actifs")
```
Modifier `set_type_active` (garder la logique, ajouter le refresh) :
```python
def set_type_active(self, code: str, active: bool):
    self.prefs.entity_overrides[code] = active
    self._refresh_type_count()
    self.on_apply()
```
Ajouter `from PySide6.QtWidgets import QGridLayout` en tête si pas déjà importé (ou garder l'import local ci-dessus).

- [ ] **Step 4: Lancer les tests (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_settings_screen.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py
git commit -m "feat(ui): écran Paramètres cartonné (général, 14 types, modèle)"
```

---

## Task 8: Réécriture de l'écran Règles (liste → table)

**Files:**
- Modify: `anonymator/ui/rules_screen.py` (`__init__` + `_reload_rules`)
- Test: `tests/test_rules_screen.py`

Contrainte : conserver `_on_add_rule_clicked`, `add_rule`, `remove_rule`, `_open_rules_folder`, mapping mode/action. Seuls `__init__` et `_reload_rules` changent (liste → `QTableWidget`).

- [ ] **Step 1: Adapter les tests**

Lire `tests/test_rules_screen.py`. Remplacer les accroches `rules_list` (QListWidget) par la table. Tests attendus :
```python
# extraits clés
def test_add_rule_populates_table(qtbot, tmp_path):
    scr = RulesScreen(tmp_path / "user_rules.json", on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(scr)
    n0 = scr.rules_table.rowCount()
    scr.add_rule(mode="simple", pattern="A#######", action="keep", note="test")
    assert scr.rules_table.rowCount() == n0 + 1
    assert scr.count_badge.text().startswith(str(n0 + 1))

def test_remove_rule_updates_table(qtbot, tmp_path):
    scr = RulesScreen(tmp_path / "user_rules.json", on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(scr)
    scr.add_rule(mode="simple", pattern="FACT.*", action="keep", note="")
    r = scr.user_rules.rules[-1]
    n = scr.rules_table.rowCount()
    scr.remove_rule(r)
    assert scr.rules_table.rowCount() == n - 1
```

- [ ] **Step 2: Lancer les tests (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_rules_screen.py -v`
Expected: FAIL (`rules_table` absent)

- [ ] **Step 3: Réécrire `__init__` et `_reload_rules`**

```python
def __init__(self, rules_path, on_apply, on_back):
    super().__init__()
    from PySide6.QtWidgets import (QTableWidget, QTableWidgetItem, QHeaderView,
                                   QAbstractItemView)
    from anonymator.ui.components.header import HeaderBand
    from anonymator.ui.components.nav_band import NavBand
    from anonymator.ui.components.cards import Card
    self.rules_path = rules_path
    self.on_apply = on_apply
    self.user_rules = UserRules.load(rules_path) if rules_path else UserRules([])

    root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
    root.addWidget(HeaderBand())
    root.addWidget(NavBand("Gestion des règles", "layers", on_home=on_back))
    body = QVBoxLayout(); body.setContentsMargins(40, 24, 40, 16); body.setSpacing(16)
    wrap = QWidget(); wrap.setLayout(body); root.addWidget(wrap)

    title = QLabel("Règles métier"); title.setObjectName("title")
    help_rules = QLabel(
        "Définissez vos propres règles. « Ne jamais masquer » protège une "
        "codification interne (ex. A####### = A + 7 chiffres, FACT.* = "
        "convention de nommage). « Toujours masquer » remplace par "
        "[REGLE-INTERNE]. Mode simple : # = un chiffre, ? = un caractère, "
        "* = n'importe quoi. Mode expert : expression régulière.")
    help_rules.setWordWrap(True); help_rules.setObjectName("muted")
    body.addWidget(title); body.addWidget(help_rules)

    # --- Carte barre d'ajout ---
    add_card = Card("sparkle", "Nouvelle règle")
    add_row = QHBoxLayout()
    self.rule_pattern = QLineEdit(); self.rule_pattern.setPlaceholderText("Motif, ex. A#######")
    self.rule_mode = QComboBox(); self.rule_mode.addItems(["simple", "expert"])
    self.rule_action = QComboBox(); self.rule_action.addItems(["Ne jamais masquer", "Toujours masquer"])
    self.rule_note = QLineEdit(); self.rule_note.setPlaceholderText("Note (optionnel)")
    btn_add_rule = QPushButton("+ Ajouter"); btn_add_rule.setObjectName("primary")
    btn_add_rule.clicked.connect(self._on_add_rule_clicked)
    for w in (self.rule_pattern, self.rule_mode, self.rule_action, self.rule_note, btn_add_rule):
        add_row.addWidget(w)
    add_card.body.addLayout(add_row)
    self.rule_error = QLabel(""); self.rule_error.setObjectName("muted")
    add_card.body.addWidget(self.rule_error)
    body.addWidget(add_card)

    # --- Carte table ---
    table_card = Card("layers", "Règles définies")
    self.count_badge = QLabel(""); self.count_badge.setObjectName("occBadge")
    table_card.head.addWidget(self.count_badge)
    self.rules_table = QTableWidget(0, 5)
    self.rules_table.setHorizontalHeaderLabels(["MOTIF", "MODE", "ACTION", "NOTE", ""])
    self.rules_table.verticalHeader().setVisible(False)
    self.rules_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.rules_table.setSelectionMode(QAbstractItemView.NoSelection)
    hh = self.rules_table.horizontalHeader()
    hh.setSectionResizeMode(0, QHeaderView.Stretch)
    hh.setSectionResizeMode(3, QHeaderView.Stretch)
    for c in (1, 2, 4):
        hh.setSectionResizeMode(c, QHeaderView.ResizeToContents)
    table_card.body.addWidget(self.rules_table)
    body.addWidget(table_card)

    # --- Pied ---
    path_row = QHBoxLayout()
    self.rules_path_label = QLabel(
        f"Fichier des règles : {self.rules_path}" if self.rules_path
        else "Fichier des règles : (non défini)")
    self.rules_path_label.setObjectName("muted"); self.rules_path_label.setWordWrap(True)
    btn_open = QPushButton("Ouvrir le dossier"); btn_open.setObjectName("ghost")
    btn_open.clicked.connect(self._open_rules_folder)
    path_row.addWidget(self.rules_path_label); path_row.addStretch(); path_row.addWidget(btn_open)
    body.addLayout(path_row)
    self._reload_rules()
```

```python
def _reload_rules(self):
    from PySide6.QtWidgets import QTableWidgetItem, QPushButton
    from anonymator.ui.components.rule_action_badge import RuleActionBadge
    from anonymator.ui.icons import icon
    self.rules_table.setRowCount(0)
    for r in self.user_rules.rules:
        row = self.rules_table.rowCount()
        self.rules_table.insertRow(row)
        self.rules_table.setItem(row, 0, QTableWidgetItem(r.pattern))
        mode_lbl = "SIMPLE" if r.mode == "simple" else "EXPERT"
        self.rules_table.setItem(row, 1, QTableWidgetItem(mode_lbl))
        self.rules_table.setCellWidget(row, 2, RuleActionBadge(r.action))
        self.rules_table.setItem(row, 3, QTableWidgetItem(r.note or ""))
        btn = QPushButton(); btn.setObjectName("ghost"); btn.setFixedWidth(34)
        btn.setIcon(icon("trash", "#6B7C72", 16))
        btn.clicked.connect(lambda _=False, rule=r: self.remove_rule(rule))
        self.rules_table.setCellWidget(row, 4, btn)
    self.count_badge.setText(f"{len(self.user_rules.rules)} règles")
    self.rules_table.resizeRowsToContents()
```

Note : `r.action` vaut `"keep"`/`"mask"` (cf. `add_rule`), directement consommé par `RuleActionBadge`. `r.mode` vaut `"simple"`/`"regex"`.

- [ ] **Step 4: Lancer les tests (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_rules_screen.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/rules_screen.py tests/test_rules_screen.py
git commit -m "feat(ui): écran Règles cartonné avec table et badges d'action"
```

---

## Task 9: Réécriture de l'écran À propos

**Files:**
- Modify: `anonymator/ui/about_screen.py`
- Test: `tests/test_about_screen.py`

Contrainte : le contenu reste dérivé de `about.py` (`__version__`, `REPO_URL`). On peut lire directement `__version__` et `REPO_URL` pour composer la vue riche.

- [ ] **Step 1: Adapter les tests**

Lire `tests/test_about_screen.py`. Tests attendus :
```python
from anonymator.ui.about_screen import AboutScreen
from anonymator import __version__

def test_shows_version(qtbot):
    scr = AboutScreen(on_back=lambda: None)
    qtbot.addWidget(scr)
    assert __version__ in scr.version_badge.text()

def test_lists_embedded_components(qtbot):
    scr = AboutScreen(on_back=lambda: None)
    qtbot.addWidget(scr)
    assert "PyMuPDF" in scr._components_text
    assert "GLiNER" in scr._components_text
```

- [ ] **Step 2: Lancer les tests (échec attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_about_screen.py -v`
Expected: FAIL (`version_badge` absent)

- [ ] **Step 3: Réécrire la vue**

```python
# anonymator/ui/about_screen.py
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QScrollArea)
from PySide6.QtGui import QPixmap, QDesktopServices
from PySide6.QtCore import Qt, QUrl
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.components.cards import Card
from anonymator.ui.icons import icon
from anonymator import __version__
from anonymator.ui.about import REPO_URL

_LOGO = Path(__file__).parent / "assets" / "logo.png"


def _badge(text: str, color: str) -> QLabel:
    b = QLabel(text); b.setAlignment(Qt.AlignCenter)
    b.setStyleSheet(f"color: {color}; border: 1px solid {color}; border-radius: 8px;"
                    f"padding: 2px 9px; font-size: 11px; font-weight: 700;")
    return b


class AboutScreen(QWidget):
    def __init__(self, on_back):
        super().__init__()
        self._components_text = "PyMuPDF GLiNER"  # accroche test / résumé
        root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(HeaderBand())
        root.addWidget(NavBand("À propos", "sparkle", on_home=on_back))

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QScrollArea.NoFrame)
        host = QWidget(); body = QVBoxLayout(host)
        body.setContentsMargins(40, 20, 40, 40); body.setSpacing(16)
        scroll.setWidget(host); root.addWidget(scroll)

        # Héros centré
        hero = QVBoxLayout(); hero.setAlignment(Qt.AlignHCenter)
        if _LOGO.exists():
            logo = QLabel(); logo.setAlignment(Qt.AlignHCenter)
            logo.setPixmap(QPixmap(str(_LOGO)).scaledToWidth(180, Qt.SmoothTransformation))
            hero.addWidget(logo)
        name_row = QHBoxLayout(); name_row.setAlignment(Qt.AlignHCenter)
        name = QLabel("Anonymator"); name.setObjectName("title")
        self.version_badge = QLabel(f"v{__version__}"); self.version_badge.setObjectName("occBadge")
        name_row.addWidget(name); name_row.addWidget(self.version_badge)
        hero.addLayout(name_row)
        pitch = QLabel("Anonymisez vos textes et fichiers en local. Protégez les "
                       "données personnelles avant tout partage — sans rien envoyer en ligne.")
        pitch.setObjectName("muted"); pitch.setWordWrap(True); pitch.setAlignment(Qt.AlignHCenter)
        pitch.setMaximumWidth(460)
        hero.addWidget(pitch, alignment=Qt.AlignHCenter)
        body.addLayout(hero)

        # Carte licence
        lic = Card("scale", "Licence & code source")
        r1 = QHBoxLayout()
        r1.addWidget(icon_label("scale"))
        col1 = QVBoxLayout()
        col1.addWidget(_strong("AGPL-3.0")); col1.addWidget(_muted("Logiciel libre — copyleft"))
        r1.addLayout(col1); r1.addStretch()
        lic.body.addLayout(r1)
        gh = QPushButton(f"  Code source sur GitHub — tag v{__version__}")
        gh.setObjectName("secondary"); gh.setIcon(icon("github", "#10331F", 18))
        gh.setCursor(Qt.PointingHandCursor)
        gh.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_URL)))
        lic.body.addWidget(gh)
        body.addWidget(lic)

        # Carte composants
        comp = Card("package", "Composants embarqués")
        for pkg, desc, lbl, col in [
            ("PyMuPDF", "© Artifex Software · lecture & écriture PDF", "AGPL-3.0", "#d62828"),
            ("GLiNER", "urchade/gliner_multi-v2.1 · détection d'entités", "Apache-2.0", "#00965E"),
        ]:
            r = QHBoxLayout()
            r.addWidget(icon_label("package"))
            c = QVBoxLayout(); c.addWidget(_strong(pkg)); c.addWidget(_muted(desc))
            r.addLayout(c); r.addStretch(); r.addWidget(_badge(lbl, col))
            comp.body.addLayout(r)
        body.addWidget(comp)
        body.addStretch()
```

Ajouter en bas du module les helpers utilisés :
```python
def _strong(text: str) -> QLabel:
    l = QLabel(text); l.setStyleSheet("font-weight: 700;"); return l


def _muted(text: str) -> QLabel:
    l = QLabel(text); l.setObjectName("muted"); return l


def icon_label(name: str) -> QLabel:
    l = QLabel(); l.setPixmap(icon(name, "#00965E", 20).pixmap(20, 20)); return l
```

- [ ] **Step 4: Lancer les tests (succès attendu)**

Run: `.venv\Scripts\python -m pytest tests/test_about_screen.py tests/test_about.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/about_screen.py tests/test_about_screen.py
git commit -m "feat(ui): écran À propos cartonné (héros, licence, composants)"
```

---

## Task 10: NavBand sur Accueil / Texte / Fichier / PDF

**Files:**
- Modify: `anonymator/ui/home_screen.py`, `text_screen.py`, `file_screen.py`, `pdf_screen.py`
- Test: `tests/test_home_screen.py`, `tests/test_ui_smoke.py`

Objectif : insérer un `NavBand` cohérent sur les 4 écrans restants. **Lire chaque fichier avant de l'éditer** — les structures diffèrent (Accueil = split hero ; Texte/Fichier/PDF ont un `#ActionBand`).

- [ ] **Step 1: Accueil — envelopper le split sous HeaderBand + NavBand actif**

Dans `home_screen.py`, remplacer le `QHBoxLayout` racine par un `QVBoxLayout` contenant `HeaderBand`, `NavBand("Accueil", "home", on_home=None)`, puis le split actuel (hero + right) dans un `QWidget` interne. Importer `HeaderBand` et `NavBand`. Le reste du contenu (cartes, model_card) est inchangé.

```python
# schéma d'insertion (adapter aux noms locaux)
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
...
root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
root.addWidget(HeaderBand())
root.addWidget(NavBand("Accueil", "home", on_home=None))
split_host = QWidget(); split = QHBoxLayout(split_host)
split.setContentsMargins(0, 0, 0, 0); split.setSpacing(0)
# ... construire hero + right, puis :
split.addWidget(hero, 5); split.addWidget(right, 6)
root.addWidget(split_host)
```

- [ ] **Step 2: Texte / Fichier / PDF — insérer NavBand sous le HeaderBand**

Pour chacun (`text_screen.py`, `file_screen.py`, `pdf_screen.py`) : repérer l'ajout de `HeaderBand()` (ou la barre de tête) au layout racine et insérer juste après :
```python
from anonymator.ui.components.nav_band import NavBand
# titre selon l'écran :
#   Texte   -> NavBand("Texte", "document", on_home=<callback retour accueil>)
#   Fichier -> NavBand("Fichier", "folder", on_home=<callback retour accueil>)
#   PDF     -> NavBand("PDF", "scan", on_home=<callback retour accueil>)
```
Le callback retour accueil est le paramètre déjà reçu par ces écrans (celui branché sur `show_home` dans `MainWindow` — vérifier son nom exact dans chaque `__init__`). Ne pas dupliquer un second retour : si l'écran a déjà un bouton « Accueil » dans son `#ActionBand`, le conserver (il pilote la même action) ou le retirer au profit du NavBand selon rendu — décider à la lecture, garder le comportement.

- [ ] **Step 3: Adapter/compléter les tests**

Ajouter un smoke test vérifiant que chaque écran instancié contient un `NavBand` :
```python
# tests/test_nav_present.py
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.about_screen import AboutScreen
from anonymator.ui.rules_screen import RulesScreen

def test_about_has_navband(qtbot):
    scr = AboutScreen(on_back=lambda: None); qtbot.addWidget(scr)
    assert scr.findChild(NavBand) is not None

def test_rules_has_navband(qtbot, tmp_path):
    scr = RulesScreen(tmp_path / "r.json", on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(scr)
    assert scr.findChild(NavBand) is not None
```
Mettre à jour `tests/test_home_screen.py` / `test_ui_smoke.py` si leurs accroches sur la structure racine cassent.

- [ ] **Step 4: Lancer les tests concernés**

Run: `.venv\Scripts\python -m pytest tests/test_home_screen.py tests/test_ui_smoke.py tests/test_nav_present.py tests/test_main_window_pdf.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/home_screen.py anonymator/ui/text_screen.py anonymator/ui/file_screen.py anonymator/ui/pdf_screen.py tests/test_nav_present.py tests/test_home_screen.py tests/test_ui_smoke.py
git commit -m "feat(ui): bandeau d'onglets sur Accueil, Texte, Fichier et PDF"
```

---

## Task 11: Suite de tests complète + rebuild exe

**Files:** aucun (validation)

- [ ] **Step 1: Lancer toute la suite**

Run: `.venv\Scripts\python -m pytest -q`
Expected: PASS (0 échec). Corriger toute régression (accroches de structure obsolètes) sans changer le comportement.

- [ ] **Step 2: Vérifier le lancement à froid**

Run: `.venv\Scripts\python -m anonymator`
Expected: la fenêtre s'ouvre ; naviguer Accueil → Paramètres / Règles / À propos ; le bandeau d'onglets et les cartes s'affichent. Fermer.

- [ ] **Step 3: Rebuild PyInstaller**

Run: `.venv\Scripts\python -m PyInstaller --noconfirm anonymator.spec`
puis `Copy-Item dist\anonymator\_internal\LICENSE dist\anonymator\LICENSE -Force`
Expected: `dist\anonymator\anonymator.exe` régénéré.

- [ ] **Step 4: Commit final (si ajustements)**

```bash
git add -A
git commit -m "test: adaptation suite UI à la refonte des écrans"
```

---

## Self-Review (couverture spec)

- Nav globale (7 écrans) → Tasks 4, 7, 8, 9, 10 ✔
- Paramètres : carte Général + libellés thème + 14 cartes d'entités + badge compteur + carte modèle → Tasks 3, 5, 7 ✔
- Règles : barre d'ajout + table + badges action + pied → Tasks 6, 8 ✔
- À propos : héros + carte licence (lien GitHub) + carte composants (badges) → Task 9 ✔
- Icônes SVG → Task 1 ✔
- QSS (nav, entity card) → Tasks 4, 5 ✔
- Tests adaptés → chaque task + Task 11 ✔
- Logique métier inchangée → contraintes explicites Tasks 7, 8, 9 ✔
