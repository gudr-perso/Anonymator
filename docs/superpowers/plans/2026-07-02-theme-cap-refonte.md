# Refonte du thème CAP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre le thème CAP entièrement bleu (charte CAP) en calquant la structure du thème CUMA, sans jamais modifier le rendu de CUMA.

**Architecture:** Le style vit dans deux couches — QSS (déjà pilotée par thème) et couche peinte/icônes (codée en dur en vert CUMA). On introduit un **thème actif** dans `theme.py` que la couche peinte/icônes lit à l'exécution. Toutes les valeurs CUMA (existantes + nouveaux tokens) sont figées sur le rendu actuel. Le changement de thème dans les Paramètres reconstruit la pile d'écrans (différé) pour tout recolorer.

**Tech Stack:** Python, PySide6 (Qt), pytest + pytest-qt (fixture `qtbot`, plateforme Qt `offscreen` via `tests/conftest.py`).

**Encodage :** fichiers source en UTF-8, fins de ligne LF (comportement actuel du repo). Lancer les tests avec `python -m pytest` depuis la racine.

---

## Contexte de référence (ne pas modifier CUMA)

Charte CAP (pièce jointe) :

| Nom | Hex |
|---|---|
| cap-navy | `#050c3f` |
| cap-navy-lift | `#0a1556` |
| cap-navy-deep | `#030826` |
| cap-orange | `#f36100` |
| cap-orange-bright | `#ff7a1f` |
| cap-cyan | `#138fdb` |
| cap-cyan-light | `#2aa6e8` |

Spec complète : `docs/superpowers/specs/2026-07-02-theme-cap-refonte-design.md`.

## Structure des fichiers

- `anonymator/ui/theme.py` — jeu de tokens `cuma`/`cap` + accesseur de thème actif. **Cœur du changement.**
- `anonymator/ui/components/grid.py` — `paint_grid` lit le thème actif.
- `anonymator/ui/components/toggle.py` — couleurs on/off depuis le thème actif.
- `anonymator/ui/home_screen.py` — héros navy, texte blanc, logo CAP.
- `anonymator/ui/components/{cards,header,nav_band}.py`, `about_screen.py`, `file_screen.py`, `pdf_screen.py`, `text_screen.py`, `components/rule_action_badge.py` — icônes/badges via tokens.
- `anonymator/ui/main_window.py` — pose le thème actif avant de construire les écrans + reconstruit au changement de thème.
- `anonymator/ui/assets/logo-cap.png` — copie de `cap-logo-trans.png`.
- Tests : `tests/test_theme.py`, `tests/test_components.py`, nouveau `tests/test_theme_active.py`.

---

## Task 1 : `theme.py` — nouveaux tokens + accesseur de thème actif

**Files:**
- Modify: `anonymator/ui/theme.py:1-16` (dict `THEMES`) et fin de fichier
- Test: `tests/test_theme.py`

- [ ] **Step 1 : Écrire les tests de non-régression (garde-fou CUMA) + accesseur**

Ajouter à la fin de `tests/test_theme.py` :

```python
def test_cuma_tokens_are_frozen():
    """Garde-fou : CUMA ne doit jamais bouger (rendu identique au pixel)."""
    from anonymator.ui.theme import THEMES
    assert THEMES["cuma"] == {
        "primary": "#31B700", "action": "#00965E", "dark": "#063b27",
        "accent": "#E8621A", "accent_hover": "#C9500F", "bg": "#FFFFFF",
        "text": "#10331F", "bg_hero": "#E8F3EA", "surface": "#FFFFFF",
        "surface_alt": "#F3FAF4", "border": "#E2E8E4", "text_muted": "#6B7C72",
        "info": "#4FA8D8", "info_hover": "#3D93C2",
        "grid_bg": "#E8F3EA", "grid_line": "#E1EBE3",
        "hero_text": "#10331F", "hero_muted": "#6B7C72",
        "toggle_off": "#C7D2CC", "logo": "logo.png",
    }


def test_cap_has_same_keys_as_cuma():
    from anonymator.ui.theme import THEMES
    assert set(THEMES["cap"]) == set(THEMES["cuma"])


def test_active_theme_getset():
    from anonymator.ui.theme import (
        set_active_theme, active_theme, DEFAULT_THEME)
    try:
        set_active_theme("cap")
        assert active_theme() == "cap"
        set_active_theme("inconnu")          # retombe sur le défaut
        assert active_theme() == DEFAULT_THEME
    finally:
        set_active_theme(DEFAULT_THEME)


def test_color_reads_active_theme():
    from anonymator.ui.theme import set_active_theme, color, DEFAULT_THEME
    try:
        set_active_theme("cap")
        assert color("action") == "#138fdb"
        assert color("grid_bg") == "#0a1556"
        assert color("action", "cuma") == "#00965E"   # override explicite
    finally:
        set_active_theme(DEFAULT_THEME)
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

Run: `python -m pytest tests/test_theme.py -q`
Expected: FAIL (`KeyError`/`ImportError` : nouveaux tokens et `set_active_theme`/`color` absents).

- [ ] **Step 3 : Réécrire `THEMES` + ajouter l'accesseur dans `theme.py`**

Remplacer le bloc `DEFAULT_THEME = "cuma"` … `THEMES = { … }` (lignes 1-16) par :

```python
DEFAULT_THEME = "cuma"

THEMES = {
    "cuma": {"primary": "#31B700", "action": "#00965E", "dark": "#063b27",
             "accent": "#E8621A", "accent_hover": "#C9500F", "bg": "#FFFFFF",
             "text": "#10331F",
             "bg_hero": "#E8F3EA", "surface": "#FFFFFF", "surface_alt": "#F3FAF4",
             "border": "#E2E8E4", "text_muted": "#6B7C72",
             "info": "#4FA8D8", "info_hover": "#3D93C2",
             "grid_bg": "#E8F3EA", "grid_line": "#E1EBE3",
             "hero_text": "#10331F", "hero_muted": "#6B7C72",
             "toggle_off": "#C7D2CC", "logo": "logo.png"},
    "cap":  {"primary": "#2aa6e8", "action": "#138fdb", "dark": "#050c3f",
             "accent": "#f36100", "accent_hover": "#d15400", "bg": "#FFFFFF",
             "text": "#050c3f",
             "bg_hero": "#0a1556", "surface": "#FFFFFF", "surface_alt": "#EEF5FB",
             "border": "#DCE6F0", "text_muted": "#64748B",
             "info": "#2aa6e8", "info_hover": "#138fdb",
             "grid_bg": "#0a1556", "grid_line": "#1e2a63",
             "hero_text": "#FFFFFF", "hero_muted": "rgba(255,255,255,0.82)",
             "toggle_off": "#C3CCE0", "logo": "logo-cap.png"},
}
```

Puis ajouter, **juste après** le dict `THEMES` (avant `THEME_LABELS`) :

```python
_active_theme = DEFAULT_THEME


def set_active_theme(name: str) -> None:
    """Positionne le thème lu par la couche peinte / icônes."""
    global _active_theme
    _active_theme = name if name in THEMES else DEFAULT_THEME


def active_theme() -> str:
    return _active_theme


def tokens(theme: str | None = None) -> dict:
    return THEMES.get(theme or _active_theme, THEMES[DEFAULT_THEME])


def color(role: str, theme: str | None = None) -> str:
    """Couleur d'un rôle dans le thème actif (ou `theme` si précisé)."""
    return tokens(theme)[role]
```

Note : `build_qss` utilise `str.format(**tokens)` ; le `_TEMPLATE` ne référence qu'un sous-ensemble des clés, les tokens supplémentaires sont ignorés sans erreur.

- [ ] **Step 4 : Lancer les tests, vérifier qu'ils passent**

Run: `python -m pytest tests/test_theme.py -q`
Expected: PASS (tous, y compris les tests préexistants).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/theme.py tests/test_theme.py
git commit -m "feat(theme): tokens étendus + accesseur de thème actif (CUMA figé)"
```

---

## Task 2 : `grid.py` — quadrillage piloté par le thème actif

**Files:**
- Modify: `anonymator/ui/components/grid.py` (intégralité)
- Test: `tests/test_theme_active.py` (nouveau)

- [ ] **Step 1 : Écrire le test**

Créer `tests/test_theme_active.py` :

```python
from anonymator.ui.theme import set_active_theme, DEFAULT_THEME
from anonymator.ui.components.grid import grid_colors


def test_grid_colors_follow_active_theme():
    try:
        set_active_theme("cuma")
        assert grid_colors() == ("#E8F3EA", "#E1EBE3")
        set_active_theme("cap")
        assert grid_colors() == ("#0a1556", "#1e2a63")
    finally:
        set_active_theme(DEFAULT_THEME)
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

Run: `python -m pytest tests/test_theme_active.py -q`
Expected: FAIL (`ImportError: cannot import name 'grid_colors'`).

- [ ] **Step 3 : Réécrire `grid.py`**

Remplacer tout le contenu de `anonymator/ui/components/grid.py` par :

```python
from PySide6.QtGui import QPainter, QPen, QColor
from anonymator.ui.theme import color

# Fond quadrillé identique au panneau gauche de l'accueil (HeroPanel).
# Les couleurs sont désormais lues dans le thème actif (cf. theme.py).
GRID_STEP = 26


def grid_colors() -> tuple[str, str]:
    """(fond, ligne) du quadrillage pour le thème actif."""
    return color("grid_bg"), color("grid_line")


def paint_grid(widget, bg: str | None = None, line: str | None = None,
               step: int = GRID_STEP) -> None:
    """Peint un fond + une grille de cadrage légère sur *widget*.

    Sans argument, lit le thème actif (`grid_bg`/`grid_line`). À appeler depuis
    le paintEvent d'un QWidget dont l'objectName porte le même fond en QSS."""
    if bg is None:
        bg = color("grid_bg")
    if line is None:
        line = color("grid_line")
    p = QPainter(widget)
    p.fillRect(widget.rect(), QColor(bg))
    pen = QPen(QColor(line)); pen.setWidth(1)
    p.setPen(pen)
    w, h = widget.width(), widget.height()
    x = step
    while x < w:
        p.drawLine(x, 0, x, h); x += step
    y = step
    while y < h:
        p.drawLine(0, y, w, y); y += step
    p.end()
```

- [ ] **Step 4 : Lancer le test, vérifier qu'il passe**

Run: `python -m pytest tests/test_theme_active.py -q`
Expected: PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/grid.py tests/test_theme_active.py
git commit -m "feat(theme): paint_grid lit le thème actif (grid_bg/grid_line)"
```

---

## Task 3 : Écrans Fichier / PDF / Texte — fond quadrillé via le thème

**Files:**
- Modify: `anonymator/ui/file_screen.py:8,37`
- Modify: `anonymator/ui/pdf_screen.py:9,33`
- Modify: `anonymator/ui/text_screen.py:21,34`

Ces trois écrans importent `GRID_BG` (supprimé en Task 2) pour poser le fond QSS. On bascule sur `color("grid_bg")`.

- [ ] **Step 1 : `file_screen.py`**

Ligne 8, remplacer :
```python
from anonymator.ui.components.grid import paint_grid, GRID_BG
```
par :
```python
from anonymator.ui.components.grid import paint_grid
from anonymator.ui.theme import color
```
Ligne 37, remplacer :
```python
        self.setStyleSheet(f"#FileBg {{ background: {GRID_BG}; }}")
```
par :
```python
        self.setStyleSheet(f"#FileBg {{ background: {color('grid_bg')}; }}")
```

- [ ] **Step 2 : `pdf_screen.py`**

Ligne 9, remplacer :
```python
from anonymator.ui.components.grid import paint_grid, GRID_BG
```
par :
```python
from anonymator.ui.components.grid import paint_grid
from anonymator.ui.theme import color
```
Ligne 33, remplacer :
```python
        self.setStyleSheet(f"#PdfBg {{ background: {GRID_BG}; }}")
```
par :
```python
        self.setStyleSheet(f"#PdfBg {{ background: {color('grid_bg')}; }}")
```

- [ ] **Step 3 : `text_screen.py`**

Ligne 21, remplacer :
```python
from anonymator.ui.components.grid import paint_grid, GRID_BG
```
par :
```python
from anonymator.ui.components.grid import paint_grid
from anonymator.ui.theme import color
```
Ligne 34, remplacer :
```python
        self.setStyleSheet(f"#TextBg {{ background: {GRID_BG}; }}")
```
par :
```python
        self.setStyleSheet(f"#TextBg {{ background: {color('grid_bg')}; }}")
```

Note : si `text_screen.py` importe déjà `color` (voir Task 6bis plus bas), ne pas dupliquer l'import.

- [ ] **Step 4 : Vérifier qu'aucune référence à `GRID_BG` ne subsiste**

Run: `git grep -n "GRID_BG\|GRID_LINE" -- anonymator/`
Expected: aucune sortie.

- [ ] **Step 5 : Lancer les tests d'écrans**

Run: `python -m pytest tests/test_text_screen.py tests/test_ui_smoke.py -q`
Expected: PASS.

- [ ] **Step 6 : Commit**

```bash
git add anonymator/ui/file_screen.py anonymator/ui/pdf_screen.py anonymator/ui/text_screen.py
git commit -m "feat(theme): fonds Fichier/PDF/Texte via color('grid_bg')"
```

---

## Task 4 : `toggle.py` — pastille on/off via le thème actif

**Files:**
- Modify: `anonymator/ui/components/toggle.py:5-6,20-31`
- Test: `tests/test_components.py`

- [ ] **Step 1 : Écrire le test**

Ajouter à la fin de `tests/test_components.py` :

```python
from anonymator.ui.theme import set_active_theme, DEFAULT_THEME
from anonymator.ui.components.toggle import ToggleSwitch as _Toggle


def test_toggle_track_color_follows_theme(qtbot):
    from anonymator.ui.theme import color
    try:
        set_active_theme("cap")
        t = _Toggle(); qtbot.addWidget(t)
        t.setChecked(True)
        assert t.track_color() == color("action")   # cyan en CAP
        t.setChecked(False)
        assert t.track_color() == color("toggle_off")
    finally:
        set_active_theme(DEFAULT_THEME)
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

Run: `python -m pytest tests/test_components.py::test_toggle_track_color_follows_theme -q`
Expected: FAIL (`AttributeError: 'ToggleSwitch' object has no attribute 'track_color'`).

- [ ] **Step 3 : Modifier `toggle.py`**

Supprimer les lignes 5-6 :
```python
_ON = "#00965E"
_OFF = "#C7D2CC"
```
Ajouter l'import en tête (après les imports Qt existants) :
```python
from anonymator.ui.theme import color
```
Remplacer le corps de `paintEvent` (lignes 20-31) par une version qui délègue à `track_color()` :
```python
    def track_color(self) -> str:
        return color("action") if self.isChecked() else color("toggle_off")

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor(self.track_color()))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(self.rect(), 12, 12)
        d = 18
        x = self.width() - d - 3 if self.isChecked() else 3
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(x, 3, d, d)
        p.end()
```

- [ ] **Step 4 : Lancer les tests**

Run: `python -m pytest tests/test_components.py -q`
Expected: PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/toggle.py tests/test_components.py
git commit -m "feat(theme): toggle on/off via color('action')/color('toggle_off')"
```

---

## Task 5 : Icônes & badges des composants via le thème actif

Remplacer les littéraux verts/orange codés en dur par des appels `color(...)`. Ces appels s'exécutent à la construction des widgets ⇒ ils prennent le thème actif (posé par `main_window`, cf. Task 7).

**Files:**
- Modify: `anonymator/ui/components/cards.py:3,13,25,29,50,55`
- Modify: `anonymator/ui/components/header.py:2,11`
- Modify: `anonymator/ui/components/nav_band.py:3,20,29`
- Modify: `anonymator/ui/components/rule_action_badge.py:2,17-18`

- [ ] **Step 1 : `cards.py`**

Après `from anonymator.ui.icons import icon` (ligne 3), ajouter :
```python
from anonymator.ui.theme import color
```
Ligne 13 : `icon(icon_name, "#00965E")` → `icon(icon_name, color("action"))`
Ligne 25 (signature `StatCard`) : `accent: str = "#00965E"` → `accent: str | None = None`
Dans `StatCard.__init__`, juste avant la ligne 29 (`ic = QLabel()...`), ajouter :
```python
        if accent is None:
            accent = color("action")
```
Ligne 50 : `icon(icon_name, "#00965E")` → `icon(icon_name, color("action"))`
Ligne 55 : `icon("chevron-right", "#6B7C72")` → `icon("chevron-right", color("text_muted"))`

- [ ] **Step 2 : `header.py` — icône + étiquette réseau pilotée par le thème**

Cette étape touche aussi `theme.py` (nouveau token `header_tag`) et `tests/test_theme.py`.

D'abord, ajouter le token `header_tag` aux **deux** thèmes dans `anonymator/ui/theme.py` :
- dans `THEMES["cuma"]`, ajouter `"header_tag": "RÉSEAU CUMA"` ;
- dans `THEMES["cap"]`, ajouter `"header_tag": ""` (chaîne vide → étiquette masquée).

Mettre à jour le garde-fou `tests/test_theme.py::test_cuma_tokens_are_frozen` : ajouter
`"header_tag": "RÉSEAU CUMA",` dans le dict attendu (sinon le test échoue, ce qui est
normal — c'est le garde-fou qui signale l'évolution volontaire de CUMA).

Ajouter un test dans `tests/test_theme.py` :
```python
def test_cap_header_tag_is_empty():
    from anonymator.ui.theme import THEMES
    assert THEMES["cap"]["header_tag"] == ""
    assert THEMES["cuma"]["header_tag"] == "RÉSEAU CUMA"
```

Puis réécrire `anonymator/ui/components/header.py` en entier :
```python
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from anonymator.ui.icons import icon
from anonymator.ui.theme import color


class HeaderBand(QFrame):
    """Bandeau d'en-tête : logo + nom de l'app + étiquette réseau (thème)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBand")
        row = QHBoxLayout(self)
        logo = QLabel(); logo.setPixmap(icon("shield", color("primary")).pixmap(20, 20))
        name = QLabel("Anonymator"); name.setStyleSheet("font-weight: 700;")
        row.addWidget(logo); row.addWidget(name)
        tag = color("header_tag")
        if tag:                                  # masqué (avec le séparateur) si vide
            sep = QLabel("|"); sep.setObjectName("muted")
            net = QLabel(tag); net.setObjectName("muted")
            net.setStyleSheet("font-weight: 700; letter-spacing: 1px;")
            row.addWidget(sep); row.addWidget(net)
        row.addStretch()
```

Vérifier après coup : `python -m pytest tests/test_theme.py -q` (garde-fou + nouveau test passent).

- [ ] **Step 3 : `nav_band.py`**

Après `from anonymator.ui.icons import icon` (ligne 3), ajouter :
```python
from anonymator.ui.theme import color
```
Ligne 20 : `icon("home", "#6B7C72", 18)` → `icon("home", color("text_muted"), 18)`
Ligne 29 : `icon(icon_name, "#00965E", 18)` → `icon(icon_name, color("action"), 18)`

- [ ] **Step 4 : `rule_action_badge.py`**

Après `from anonymator.ui.icons import icon` (ligne 2), ajouter :
```python
from anonymator.ui.theme import color
```
Remplacer les attributs de classe (lignes 17-18) :
```python
    _KEEP = "#00965E"
    _MASK = "#E8621A"
```
par une résolution dans `__init__`. Supprimer ces deux lignes, et remplacer, dans `__init__`, la ligne :
```python
        self.color = self._KEEP if keep else self._MASK
```
par :
```python
        self.color = color("action") if keep else color("accent")
```

- [ ] **Step 5 : Lancer les tests concernés**

Run: `python -m pytest tests/test_components.py tests/test_ui_smoke.py -q`
Expected: PASS.

- [ ] **Step 6 : Commit**

```bash
git add anonymator/ui/components/cards.py anonymator/ui/components/header.py anonymator/ui/components/nav_band.py anonymator/ui/components/rule_action_badge.py
git commit -m "feat(theme): icônes/badges des composants via color(...)"
```

---

## Task 6 : Icônes des écrans About / Fichier / PDF / Texte via le thème

**Files:**
- Modify: `anonymator/ui/about_screen.py:13,30,79`
- Modify: `anonymator/ui/file_screen.py:60,323`
- Modify: `anonymator/ui/pdf_screen.py:54,218`
- Modify: `anonymator/ui/text_screen.py:50-51`

- [ ] **Step 1 : `about_screen.py`**

Ajouter en tête (près des autres imports `from anonymator.ui...`) :
```python
from anonymator.ui.theme import color
```
Ligne 13 : `_LOGO = Path(__file__).parent / "assets" / "logo.png"` → à remplacer par une résolution dynamique. Supprimer la constante `_LOGO` et, à l'endroit où elle est utilisée dans `AboutScreen.__init__` (chercher `_LOGO`), utiliser :
```python
        logo_path = Path(__file__).parent / "assets" / color("logo")
```
puis remplacer les usages de `_LOGO` par `logo_path`.
Ligne 30 (`_icon_label`) : `icon(name, "#00965E", 20)` → `icon(name, color("action"), 20)`
Ligne 79 : `icon("github", "#10331F", 18)` → `icon("github", color("text"), 18)`
Laisser inchangées les couleurs de `EMBEDDED_COMPONENTS` (`#d62828`, `#00965E`) et `#9a031e` : ce sont des couleurs de contenu par composant/licence, pas du chrome de thème.

- [ ] **Step 2 : `file_screen.py`**

Si `color` n'est pas déjà importé (il l'est après Task 3), s'assurer de `from anonymator.ui.theme import color`.
Ligne 60 : `icon("document", "#00965E")` → `icon("document", color("action"))`
Ligne 323 : `QColor("#6B7C72")` → `QColor(color("text_muted"))`

- [ ] **Step 3 : `pdf_screen.py`**

`color` est importé après Task 3.
Ligne 54 : `icon("document", "#00965E")` → `icon("document", color("action"))`
Ligne 218 : `QColor("#6B7C72")` → `QColor(color("text_muted"))`

- [ ] **Step 4 : `text_screen.py`**

`color` est importé après Task 3.
Lignes 50-51 : les `StatCard(..., "#E8621A")` et `StatCard(..., "#9a031e")` — remplacer **uniquement** le `#E8621A` (accent de thème) :
```python
        self.stat_keep = StatCard("document", "Conservées", color("accent"))
```
Laisser `self.stat_risk = StatCard("alert", "Niveau de risque", "#9a031e")` inchangé (rouge « risque », couleur sémantique hors thème).

- [ ] **Step 5 : Vérifier qu'aucun vert de thème codé en dur ne subsiste dans le chrome**

Run: `git grep -n "#00965E\|#31B700" -- anonymator/ui`
Expected: seules restent les occurrences **de contenu** volontairement conservées (`EMBEDDED_COMPONENTS` de `about_screen.py`). Aucune dans un `icon(...)` de chrome.

- [ ] **Step 6 : Lancer les tests**

Run: `python -m pytest tests/test_about.py tests/test_text_screen.py tests/test_ui_smoke.py -q`
Expected: PASS.

- [ ] **Step 7 : Commit**

```bash
git add anonymator/ui/about_screen.py anonymator/ui/file_screen.py anonymator/ui/pdf_screen.py anonymator/ui/text_screen.py
git commit -m "feat(theme): icônes des écrans About/Fichier/PDF/Texte via color(...)"
```

---

## Task 7 : Logo CAP + héros navy dans `home_screen.py`

**Files:**
- Create: `anonymator/ui/assets/logo-cap.png` (copie binaire)
- Modify: `anonymator/ui/home_screen.py:1-11,19,21-34,62-63,66-76`

- [ ] **Step 1 : Copier le logo CAP dans les assets**

```bash
cp "C:/_pCloud/__CAP Consulting/logos/cap-logo-trans.png" "anonymator/ui/assets/logo-cap.png"
```
Vérifier : `ls -la anonymator/ui/assets/logo-cap.png` (fichier non vide, ~273 Ko).

- [ ] **Step 2 : Rendre le héros piloté par le thème actif**

Dans `home_screen.py`, remplacer les lignes 1-11 :
```python
from pathlib import Path
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtCore import Qt
from anonymator.ui.components.cards import NavCard
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand

_HERO_BG = "#E8F3EA"
_GRID = "#E1EBE3"
_LOGO = Path(__file__).parent / "assets" / "logo.png"
```
par :
```python
from pathlib import Path
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap
from PySide6.QtCore import Qt
from anonymator.ui.components.cards import NavCard
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.nav_band import NavBand
from anonymator.ui.theme import color

_ASSETS = Path(__file__).parent / "assets"
```

Remplacer la ligne 19 (`self.setStyleSheet(f"#Hero {{ background: {_HERO_BG}; }}")`) par :
```python
        self.setStyleSheet(f"#Hero {{ background: {color('grid_bg')}; }}")
```

Remplacer le `paintEvent` de `HeroPanel` (lignes 21-34) par :
```python
    def paintEvent(self, _event):
        p = QPainter(self)
        bg, grid = color("grid_bg"), color("grid_line")
        p.fillRect(self.rect(), QColor(bg))
        pen = QPen(QColor(grid)); pen.setWidth(1)
        p.setPen(pen)
        step = 26
        w, h = self.width(), self.height()
        x = step
        while x < w:
            p.drawLine(x, 0, x, h); x += step
        y = step
        while y < h:
            p.drawLine(0, y, w, y); y += step
        p.end()
```

- [ ] **Step 3 : Logo + textes du héros pilotés par le thème**

Dans `HomeScreen.__init__`, remplacer le bloc logo (lignes 57-63) :
```python
        has_logo = _LOGO.exists()
        if has_logo:
            logo = QLabel()
            logo.setPixmap(QPixmap(str(_LOGO)).scaledToWidth(250, Qt.SmoothTransformation))
        else:
            logo = QLabel("CUMA"); logo.setObjectName("title")
            logo.setStyleSheet("color: #31B700; font-size: 34px; font-weight: 800;")
```
par :
```python
        logo_path = _ASSETS / color("logo")
        has_logo = logo_path.exists()
        if has_logo:
            logo = QLabel()
            logo.setPixmap(QPixmap(str(logo_path)).scaledToWidth(250, Qt.SmoothTransformation))
        else:
            logo = QLabel("CUMA"); logo.setObjectName("title")
            logo.setStyleSheet(
                f"color: {color('primary')}; font-size: 34px; font-weight: 800;")
```

Remplacer les lignes 64-69 (titre + sous-titre) :
```python
        title = QLabel("Anonymisez.\nPartagez l'essentiel.")
        title.setObjectName("title")
        sub = QLabel("Protégez noms, adresses et coordonnées avant tout partage. "
                     "Traitement 100% local, aucune donnée envoyée.")
        sub.setObjectName("muted"); sub.setWordWrap(True)
        sub.setStyleSheet("color:#6B7C72; font-size:16px; line-height:140%;")
```
par (le héros est sombre en CAP ⇒ textes lus dans le thème) :
```python
        title = QLabel("Anonymisez.\nPartagez l'essentiel.")
        title.setObjectName("title")
        title.setStyleSheet(f"color: {color('hero_text')};")
        sub = QLabel("Protégez noms, adresses et coordonnées avant tout partage. "
                     "Traitement 100% local, aucune donnée envoyée.")
        sub.setWordWrap(True)
        sub.setStyleSheet(
            f"color:{color('hero_muted')}; font-size:16px; line-height:140%;")
```
Note : le `setStyleSheet` sur `#title` prime sur la règle QSS globale `QLabel#title` (couleur `text`), ce qui donne le blanc voulu en CAP et laisse CUMA identique (même valeur `#10331F`).

Dans le repli sans logo (lignes 73-76), remplacer la couleur codée en dur du pied :
```python
            foot = QLabel("la puissance du <span style='color:#E8621A;font-weight:700'>groupe</span>")
```
par :
```python
            foot = QLabel("la puissance du "
                          f"<span style='color:{color('accent')};font-weight:700'>groupe</span>")
```

- [ ] **Step 4 : Carte d'invitation modèle — teinte via `action`**

Remplacer les lignes 97-99 :
```python
        self.model_card.setStyleSheet(
            "#modelInvite { background: rgba(0, 150, 94, 0.08); "
            "border: 1px solid rgba(0, 150, 94, 0.45); border-radius: 10px; }")
```
par un calcul RGBA depuis `action` (ajouter le helper en tête de fichier, après les imports) :
```python
def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"
```
et le `setStyleSheet` :
```python
        act = color("action")
        self.model_card.setStyleSheet(
            f"#modelInvite {{ background: {_rgba(act, 0.08)}; "
            f"border: 1px solid {_rgba(act, 0.45)}; border-radius: 10px; }}")
```

- [ ] **Step 5 : Test — logo et couleurs du héros suivent le thème**

Ajouter à `tests/test_theme_active.py` :
```python
def test_home_logo_filename_follows_theme():
    from anonymator.ui.theme import color, set_active_theme, DEFAULT_THEME
    try:
        set_active_theme("cuma")
        assert color("logo") == "logo.png"
        set_active_theme("cap")
        assert color("logo") == "logo-cap.png"
    finally:
        set_active_theme(DEFAULT_THEME)


def test_home_screen_builds_under_cap(qtbot):
    from anonymator.ui.theme import set_active_theme, DEFAULT_THEME
    from anonymator.ui.home_screen import HomeScreen
    try:
        set_active_theme("cap")
        s = HomeScreen(lambda: None, lambda: None, lambda: None)
        qtbot.addWidget(s)
        assert s is not None
    finally:
        set_active_theme(DEFAULT_THEME)
```

- [ ] **Step 6 : Lancer les tests**

Run: `python -m pytest tests/test_theme_active.py tests/test_ui_smoke.py -q`
Expected: PASS.

- [ ] **Step 7 : Commit**

```bash
git add anonymator/ui/assets/logo-cap.png anonymator/ui/home_screen.py tests/test_theme_active.py
git commit -m "feat(theme): héros navy + texte blanc + logo CAP en thème CAP"
```

---

## Task 8 : `main_window.py` — poser le thème actif + reconstruire au changement

**Files:**
- Modify: `anonymator/ui/main_window.py:8,38-65,76-85`

- [ ] **Step 1 : Imports**

Ligne 8, remplacer :
```python
from anonymator.ui.theme import build_qss
```
par :
```python
from anonymator.ui.theme import build_qss, set_active_theme, active_theme
```
Ajouter aux imports Qt (ligne 4 zone) :
```python
from PySide6.QtCore import QTimer
```

- [ ] **Step 2 : Factoriser la construction des écrans + poser le thème avant**

Dans `__init__`, remplacer le bloc lignes 38-65 :
```python
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings,
                               model_available=is_model_available(),
                               on_download=self._request_model,
                               on_pdf=self.show_pdf,
                               on_rules=self.show_rules, on_about=self.show_about)
        self.text_screen = TextScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_request_model=self._request_model)
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_text_review=self._review_text,
                                      on_request_model=self._request_model)
        self.pdf_screen = PdfScreen(self.ref, self.loader, self.prefs,
                                    self.show_home, on_request_model=self._request_model)
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        self.rules_screen = RulesScreen(self.rules_path, self._apply_prefs, self.show_home)
        self.about_screen = AboutScreen(self.show_home)
        for w in (self.home, self.text_screen, self.file_screen,
                  self.pdf_screen, self.settings_screen,
                  self.rules_screen, self.about_screen):
            self.stack.addWidget(w)

        self.settings_screen.model_ready.connect(self._on_model_ready)

        self.show_home()
        self._apply_theme()
```
par :
```python
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        set_active_theme(self.prefs.theme)   # avant de construire la couche peinte/icônes
        self._build_screens()
        self.show_home()
        self._apply_theme()

    def _build_screens(self):
        """(Re)construit tous les écrans avec le thème actif courant."""
        while self.stack.count():
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()

        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings,
                               model_available=is_model_available(),
                               on_download=self._request_model,
                               on_pdf=self.show_pdf,
                               on_rules=self.show_rules, on_about=self.show_about)
        self.text_screen = TextScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_request_model=self._request_model)
        self.file_screen = FileScreen(self.ref, self.loader, self.prefs,
                                      self.show_home, on_text_review=self._review_text,
                                      on_request_model=self._request_model)
        self.pdf_screen = PdfScreen(self.ref, self.loader, self.prefs,
                                    self.show_home, on_request_model=self._request_model)
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home)
        self.rules_screen = RulesScreen(self.rules_path, self._apply_prefs, self.show_home)
        self.about_screen = AboutScreen(self.show_home)
        for w in (self.home, self.text_screen, self.file_screen,
                  self.pdf_screen, self.settings_screen,
                  self.rules_screen, self.about_screen):
            self.stack.addWidget(w)

        self.settings_screen.model_ready.connect(self._on_model_ready)
```

- [ ] **Step 3 : `_apply_theme` pose le thème actif ; `_apply_prefs` reconstruit si le thème change**

Remplacer `_apply_theme` (lignes 76-77) :
```python
    def _apply_theme(self):
        self.setStyleSheet(build_qss(self.prefs.theme))
```
par :
```python
    def _apply_theme(self):
        set_active_theme(self.prefs.theme)
        self.setStyleSheet(build_qss(self.prefs.theme))
```

Remplacer `_apply_prefs` (lignes 79-85) :
```python
    def _apply_prefs(self):
        self.prefs.save(self.prefs_path)
        self.ref = self._build_ref()
        self.text_screen.ref = self.ref
        self.file_screen.ref = self.ref
        self.pdf_screen.ref = self.ref
        self._apply_theme()
```
par :
```python
    def _apply_prefs(self):
        theme_changed = self.prefs.theme != active_theme()
        self.prefs.save(self.prefs_path)
        self.ref = self._build_ref()
        self.text_screen.ref = self.ref
        self.file_screen.ref = self.ref
        self.pdf_screen.ref = self.ref
        self._apply_theme()
        if theme_changed:
            # reconstruire hors du callback du combo (évite de détruire le
            # settings_screen dont le signal est en cours d'exécution)
            QTimer.singleShot(0, self._retheme)

    def _retheme(self):
        self._build_screens()
        self.show_home()
```

- [ ] **Step 4 : Test — construction sous CAP et bascule de thème**

Ajouter `tests/test_main_window_theme.py` :
```python
from pathlib import Path
from anonymator.ui.main_window import MainWindow
from anonymator.ui.theme import active_theme, set_active_theme, DEFAULT_THEME


def test_mainwindow_sets_active_theme_from_prefs(qtbot, tmp_path):
    prefs = tmp_path / "preferences.json"
    prefs.write_text('{"theme": "cap"}', encoding="utf-8")
    try:
        w = MainWindow(prefs_path=prefs); qtbot.addWidget(w)
        assert active_theme() == "cap"
    finally:
        set_active_theme(DEFAULT_THEME)


def test_theme_switch_rebuilds_and_updates_active(qtbot, tmp_path):
    prefs = tmp_path / "preferences.json"
    prefs.write_text('{"theme": "cuma"}', encoding="utf-8")
    try:
        w = MainWindow(prefs_path=prefs); qtbot.addWidget(w)
        assert active_theme() == "cuma"
        w.prefs.theme = "cap"
        w._apply_prefs()
        assert active_theme() == "cap"
        w._retheme()   # exécuter le rebuild différé de façon synchrone
        assert w.stack.count() == 7
    finally:
        set_active_theme(DEFAULT_THEME)
```
Note : si le constructeur `MainWindow` exige un `ModelLoader`, passer `MainWindow(loader=ModelLoader(), prefs_path=prefs)` en s'inspirant de `tests/test_ui_smoke.py`. Vérifier la signature réelle avant d'écrire l'appel.

- [ ] **Step 5 : Lancer les tests**

Run: `python -m pytest tests/test_main_window_theme.py tests/test_ui_smoke.py -q`
Expected: PASS.

- [ ] **Step 6 : Commit**

```bash
git add anonymator/ui/main_window.py tests/test_main_window_theme.py
git commit -m "feat(theme): pose le thème actif au démarrage + reconstruit au changement"
```

---

## Task 9 : Vérification finale (suite complète + rendu)

- [ ] **Step 1 : Suite complète**

Run: `python -m pytest -q`
Expected: PASS (aucune régression).

- [ ] **Step 2 : Garde-fou CUMA rétabli**

Run: `python -m pytest tests/test_theme.py::test_cuma_tokens_are_frozen -q`
Expected: PASS — confirme que CUMA n'a pas bougé.

- [ ] **Step 3 : Vérif manuelle (lancer l'app)**

Lancer l'application (`python -m anonymator`), puis :
- Paramètres → thème **CUMA** : accueil vert pâle, quadrillage vert, onglets/pastilles verts, icônes vertes, CTA orange — **identique à avant**.
- Paramètres → thème **CAP** : accueil **navy foncé**, titre/sous-titre **blancs**, **logo CAP**, quadrillage navy éclairci ; onglets soulignés et pastilles on/off en **cyan** ; CTA en **orange** charte ; écrans Texte/Fichier/PDF sur fond navy quadrillé.
- **Point de contrôle lisibilité** : sur les écrans Texte/Fichier/PDF en CAP, repérer tout libellé/texte gris posé **directement** sur le fond navy (hors carte blanche). Si trouvé, le repasser en clair via `color("hero_text")`/`color("hero_muted")` dans le fichier d'écran concerné, ajouter/ajuster le test de smoke correspondant, puis committer.

- [ ] **Step 4 : Commit éventuel des corrections de lisibilité**

```bash
git add -A
git commit -m "fix(theme): lisibilité des textes hors carte sur fond navy (CAP)"
```

---

## Notes hors périmètre (à confirmer avec l'utilisateur, pas dans ce plan)

- Couleurs de contenu conservées volontairement : badges de licence `EMBEDDED_COMPONENTS` (`#d62828`, `#00965E`) et rouge « risque » `#9a031e` — sémantiques, indépendantes du thème.
