# Marques verrouillées CAP / CUMA — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produire deux exécutables (CAP'nonyme / Cum'Anonyme) figés chacun dans son thème et son nom, tout en gardant un build dev non verrouillé.

**Architecture :** Une notion de « marque » (surcouche du thème) est figée au démarrage par un module d'entrée dédié (`brands/cap.py`, `brands/cuma.py`) qui appelle `lock_brand()` avant `main()`. En mode verrouillé, l'UI lit le thème et le nom depuis la marque (pas depuis les préférences) et masque le sélecteur de thème. Le `.spec` PyInstaller et un script PowerShell sont paramétrés par la variable d'environnement de build `ANONYMATOR_BUILD_BRAND`.

**Tech Stack :** Python 3, PySide6, pytest / pytest-qt, PyInstaller, PowerShell.

**Référence conception :** `docs/superpowers/specs/2026-07-05-marques-cap-cuma-design.md`

---

## Structure des fichiers

**Créés :**
- `anonymator/brand.py` — modèle `Brand`, dict `BRANDS`, état actif, `lock_brand` / `active_brand` / `is_locked` / `reset_brand`, et `build_target` (mapping build).
- `anonymator/brands/__init__.py` — paquet vide.
- `anonymator/brands/cap.py` — entrée verrouillée CAP.
- `anonymator/brands/cuma.py` — entrée verrouillée CUMA.
- `tests/test_brand.py` — tests du module marque.
- `scripts/build.ps1` — build + zip par marque.

**Modifiés :**
- `anonymator/ui/main_window.py` — titre + thème effectif depuis la marque.
- `anonymator/ui/components/header.py` — nom du bandeau depuis la marque.
- `anonymator/ui/about.py` — nom produit dans les mentions.
- `anonymator/ui/about_screen.py` — nom produit dans le héros.
- `anonymator/ui/settings_screen.py` — sélecteur de thème masqué si verrouillé.
- `anonymator.spec` — script d'entrée / nom d'exe / icône paramétrés.
- `tests/test_settings_screen.py` — cas verrouillé/non verrouillé.

**Convention projet :** encodage source UTF-8, tests via `.venv\Scripts\python.exe -m pytest`. L'état global de marque est réinitialisé en fin de test (`reset_brand()`), sur le modèle de `set_active_theme(DEFAULT_THEME)` déjà utilisé dans `tests/test_main_window_theme.py`.

---

### Task 1 : Module `brand.py`

**Files:**
- Create: `anonymator/brand.py`
- Test: `tests/test_brand.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

```python
# tests/test_brand.py
from anonymator.brand import (
    Brand, BRANDS, lock_brand, reset_brand, active_brand, is_locked, build_target,
)


def teardown_function():
    reset_brand()   # isole l'état global entre les tests


def test_default_is_dev_unlocked():
    reset_brand()
    b = active_brand()
    assert b.key == "dev"
    assert b.locked is False
    assert is_locked() is False
    assert b.product_name == "Anonymator"
    assert b.theme is None


def test_lock_cap_forces_theme_and_name():
    lock_brand("cap")
    b = active_brand()
    assert b.theme == "cap"
    assert b.product_name == "CAP'nonyme"
    assert b.exe_name == "capnonyme"
    assert is_locked() is True


def test_lock_cuma_forces_theme_and_name():
    lock_brand("cuma")
    b = active_brand()
    assert b.theme == "cuma"
    assert b.product_name == "Cum'Anonyme"
    assert b.exe_name == "cumanonyme"
    assert is_locked() is True


def test_reset_returns_to_dev():
    lock_brand("cap")
    reset_brand()
    assert active_brand().key == "dev"


def test_build_target_maps_brand_to_entry_and_name():
    assert build_target("cap") == (
        "anonymator/brands/cap.py", "capnonyme", "anonymator.ico")
    assert build_target("cuma") == (
        "anonymator/brands/cuma.py", "cumanonyme", "anonymator.ico")


def test_build_target_unknown_falls_back_to_dev():
    assert build_target("dev") == (
        "anonymator/__main__.py", "anonymator", "anonymator.ico")
    assert build_target("nimportequoi") == (
        "anonymator/__main__.py", "anonymator", "anonymator.ico")
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

Run: `.venv\Scripts\python.exe -m pytest tests/test_brand.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.brand'`

- [ ] **Step 3 : Écrire l'implémentation minimale**

```python
# anonymator/brand.py
"""Marque de distribution — surcouche du thème.

Une « marque » fige, pour un exécutable diffusé, le thème imposé, le nom de
produit affiché et le nom du fichier exe. Le mode dev (défaut) n'est pas
verrouillé : le thème vient des préférences et le sélecteur de thème reste
visible dans les réglages.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Brand:
    key: str
    theme: str | None       # None en dev : le thème vient des préférences
    product_name: str       # nom affiché (titre, en-tête, à propos)
    exe_name: str           # nom du fichier exe / dossier dist
    icon: str               # fichier .ico dans anonymator/ui/assets
    locked: bool


BRANDS = {
    "cuma": Brand("cuma", "cuma", "Cum'Anonyme", "cumanonyme", "anonymator.ico", True),
    "cap":  Brand("cap",  "cap",  "CAP'nonyme",  "capnonyme",  "anonymator.ico", True),
}

DEV_BRAND = Brand("dev", None, "Anonymator", "anonymator", "anonymator.ico", False)

_active = DEV_BRAND


def lock_brand(key: str) -> None:
    """Fige la marque active. À appeler AVANT de construire la fenêtre."""
    global _active
    _active = BRANDS[key]


def reset_brand() -> None:
    """Rétablit le mode dev non verrouillé (isolation des tests)."""
    global _active
    _active = DEV_BRAND


def active_brand() -> Brand:
    return _active


def is_locked() -> bool:
    return _active.locked


def build_target(build_brand: str) -> tuple[str, str, str]:
    """(script d'entrée, nom d'exe, icône) pour un build PyInstaller.

    `build_brand` ∈ {"cap", "cuma", "dev"} ; toute valeur inconnue → dev.
    Lu par `anonymator.spec` depuis la variable d'env ANONYMATOR_BUILD_BRAND.
    """
    b = BRANDS.get(build_brand)
    if b is not None:
        return (f"anonymator/brands/{b.key}.py", b.exe_name, b.icon)
    return ("anonymator/__main__.py", DEV_BRAND.exe_name, DEV_BRAND.icon)
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run: `.venv\Scripts\python.exe -m pytest tests/test_brand.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5 : Commit**

```bash
git add anonymator/brand.py tests/test_brand.py
git commit -m "feat(brand): module marque (surcouche thème) + mapping build"
```

---

### Task 2 : Modules d'entrée par marque

**Files:**
- Create: `anonymator/brands/__init__.py`
- Create: `anonymator/brands/cap.py`
- Create: `anonymator/brands/cuma.py`
- Test: `tests/test_brand_entrypoints.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

```python
# tests/test_brand_entrypoints.py
from unittest.mock import patch
from anonymator.brand import active_brand, reset_brand


def teardown_function():
    reset_brand()


def test_cap_entry_locks_cap_then_calls_main():
    import anonymator.brands.cap as entry
    with patch("anonymator.brands.cap.main", return_value=0) as m:
        rc = entry.run()
    assert rc == 0
    assert m.called
    assert active_brand().key == "cap"


def test_cuma_entry_locks_cuma_then_calls_main():
    import anonymator.brands.cuma as entry
    with patch("anonymator.brands.cuma.main", return_value=0) as m:
        rc = entry.run()
    assert rc == 0
    assert m.called
    assert active_brand().key == "cuma"
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

Run: `.venv\Scripts\python.exe -m pytest tests/test_brand_entrypoints.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.brands'`

- [ ] **Step 3 : Créer le paquet et les entrées**

```python
# anonymator/brands/__init__.py
```

(fichier vide)

```python
# anonymator/brands/cap.py
"""Point d'entrée verrouillé — marque CAP (CAP'nonyme)."""
from anonymator.brand import lock_brand
from anonymator.__main__ import main


def run() -> int:
    lock_brand("cap")
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
```

```python
# anonymator/brands/cuma.py
"""Point d'entrée verrouillé — marque CUMA (Cum'Anonyme)."""
from anonymator.brand import lock_brand
from anonymator.__main__ import main


def run() -> int:
    lock_brand("cuma")
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run: `.venv\Scripts\python.exe -m pytest tests/test_brand_entrypoints.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5 : Commit**

```bash
git add anonymator/brands/ tests/test_brand_entrypoints.py
git commit -m "feat(brand): points d'entrée verrouillés CAP et CUMA"
```

---

### Task 3 : Titre + thème effectif dans `MainWindow`

**Files:**
- Modify: `anonymator/ui/main_window.py`
- Test: `tests/test_main_window_theme.py`

- [ ] **Step 1 : Ajouter les tests du verrou (échec attendu)**

Ajouter ces deux tests à la fin de `tests/test_main_window_theme.py` :

```python
def test_locked_brand_forces_theme_ignoring_prefs(qtbot, tmp_path):
    """Un exe verrouillé CUMA ignore un preferences.json portant 'cap'."""
    from anonymator.brand import lock_brand, reset_brand
    prefs = tmp_path / "preferences.json"
    prefs.write_text('{"theme": "cap"}', encoding="utf-8")
    try:
        lock_brand("cuma")
        w = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs)
        qtbot.addWidget(w)
        assert active_theme() == "cuma"
        assert w.windowTitle() == "Cum'Anonyme"
    finally:
        reset_brand()
        set_active_theme(DEFAULT_THEME)


def test_dev_brand_uses_prefs_theme_and_default_title(qtbot, tmp_path):
    from anonymator.brand import reset_brand
    prefs = tmp_path / "preferences.json"
    prefs.write_text('{"theme": "cap"}', encoding="utf-8")
    try:
        reset_brand()
        w = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs)
        qtbot.addWidget(w)
        assert active_theme() == "cap"
        assert w.windowTitle() == "Anonymator"
    finally:
        set_active_theme(DEFAULT_THEME)
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main_window_theme.py -v`
Expected: FAIL — `test_locked_brand_forces_theme_ignoring_prefs` : `active_theme() == "cap"` au lieu de `"cuma"` (le verrou n'est pas encore lu).

- [ ] **Step 3 : Router titre et thème par la marque**

Dans `anonymator/ui/main_window.py`, ajouter l'import après la ligne `from anonymator.ui.theme import ...` :

```python
from anonymator.brand import active_brand
```

Remplacer la ligne du titre (`self.setWindowTitle("Anonymator")`) par :

```python
        self.setWindowTitle(active_brand().product_name)
```

Ajouter cette méthode dans la classe (par ex. juste avant `_apply_theme`) :

```python
    def _effective_theme(self) -> str:
        """Thème réellement appliqué : celui de la marque si verrouillée,
        sinon la préférence utilisateur (mode dev)."""
        b = active_brand()
        return b.theme if b.locked else self.prefs.theme
```

Remplacer la ligne `set_active_theme(self.prefs.theme)` du `__init__` par :

```python
        set_active_theme(self._effective_theme())   # avant de construire la couche peinte/icônes
```

Remplacer le corps de `_apply_theme` par :

```python
    def _apply_theme(self):
        theme = self._effective_theme()
        set_active_theme(theme)
        self.setStyleSheet(build_qss(theme))
```

Remplacer la 1re ligne de `_apply_prefs` (`theme_changed = self.prefs.theme != active_theme()`) par :

```python
        theme_changed = self._effective_theme() != active_theme()
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv\Scripts\python.exe -m pytest tests/test_main_window_theme.py -v`
Expected: PASS (4 tests — les 2 existants + les 2 nouveaux)

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/main_window.py tests/test_main_window_theme.py
git commit -m "feat(brand): titre et thème de MainWindow pilotés par la marque"
```

---

### Task 4 : Nom produit dans l'en-tête

**Files:**
- Modify: `anonymator/ui/components/header.py`
- Test: `tests/test_header_brand.py`

- [ ] **Step 1 : Écrire le test qui échoue**

```python
# tests/test_header_brand.py
from anonymator.brand import lock_brand, reset_brand
from anonymator.ui.components.header import HeaderBand


def teardown_function():
    reset_brand()


def _label_texts(widget):
    from PySide6.QtWidgets import QLabel
    return [c.text() for c in widget.findChildren(QLabel)]


def test_header_shows_dev_name_by_default(qtbot):
    reset_brand()
    h = HeaderBand(); qtbot.addWidget(h)
    assert "Anonymator" in _label_texts(h)


def test_header_shows_brand_name_when_locked(qtbot):
    lock_brand("cap")
    h = HeaderBand(); qtbot.addWidget(h)
    assert "CAP'nonyme" in _label_texts(h)
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv\Scripts\python.exe -m pytest tests/test_header_brand.py -v`
Expected: FAIL — `test_header_shows_brand_name_when_locked` : `"CAP'nonyme"` absent (l'en-tête affiche encore « Anonymator » en dur).

- [ ] **Step 3 : Router le nom de l'en-tête**

Dans `anonymator/ui/components/header.py`, ajouter l'import :

```python
from anonymator.brand import active_brand
```

Remplacer la ligne `name = QLabel("Anonymator"); name.setStyleSheet("font-weight: 700;")` par :

```python
        name = QLabel(active_brand().product_name); name.setStyleSheet("font-weight: 700;")
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv\Scripts\python.exe -m pytest tests/test_header_brand.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/header.py tests/test_header_brand.py
git commit -m "feat(brand): nom de l'en-tête piloté par la marque"
```

---

### Task 5 : Nom produit dans « À propos »

**Files:**
- Modify: `anonymator/ui/about.py`
- Modify: `anonymator/ui/about_screen.py`
- Test: `tests/test_about.py`

- [ ] **Step 1 : Ajouter le test verrouillé (échec attendu)**

Ajouter à la fin de `tests/test_about.py` :

```python
def test_about_lines_use_brand_product_name():
    from anonymator.brand import lock_brand, reset_brand
    try:
        lock_brand("cuma")
        joined = "\n".join(about_lines(version="1.2.3"))
        assert "Cum'Anonyme v1.2.3" in joined
    finally:
        reset_brand()
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv\Scripts\python.exe -m pytest tests/test_about.py -v`
Expected: FAIL — `test_about_lines_use_brand_product_name` : la 1re ligne dit encore « Anonymator v1.2.3 ».

- [ ] **Step 3 : Router le nom produit**

Dans `anonymator/ui/about.py`, ajouter l'import :

```python
from anonymator.brand import active_brand
```

Remplacer la 1re entrée de la liste `about_lines` (`f"Anonymator v{version}",`) par :

```python
        f"{active_brand().product_name} v{version}",
```

Dans `anonymator/ui/about_screen.py`, ajouter l'import après `from anonymator import __version__` :

```python
from anonymator.brand import active_brand
```

Remplacer la ligne `name = QLabel("Anonymator"); name.setObjectName("title")` par :

```python
        name = QLabel(active_brand().product_name); name.setObjectName("title")
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv\Scripts\python.exe -m pytest tests/test_about.py -v`
Expected: PASS (5 tests — les 4 existants restent verts car en dev le nom vaut « Anonymator »)

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/about.py anonymator/ui/about_screen.py tests/test_about.py
git commit -m "feat(brand): nom produit dans les mentions À propos"
```

---

### Task 6 : Masquer le sélecteur de thème si verrouillé

**Files:**
- Modify: `anonymator/ui/settings_screen.py`
- Test: `tests/test_settings_screen.py`

- [ ] **Step 1 : Ajouter les tests (échec attendu)**

Ajouter à la fin de `tests/test_settings_screen.py` :

```python
def test_theme_selector_hidden_when_brand_locked(qtbot):
    from anonymator.brand import lock_brand, reset_brand
    try:
        lock_brand("cap")
        s = _settings(); qtbot.addWidget(s)
        assert not hasattr(s, "theme_box")
    finally:
        reset_brand()


def test_theme_selector_present_in_dev(qtbot):
    from anonymator.brand import reset_brand
    reset_brand()
    s = _settings(); qtbot.addWidget(s)
    assert hasattr(s, "theme_box")
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv\Scripts\python.exe -m pytest tests/test_settings_screen.py -v`
Expected: FAIL — `test_theme_selector_hidden_when_brand_locked` : `theme_box` existe encore en mode verrouillé.

- [ ] **Step 3 : Conditionner la sous-section thème**

Dans `anonymator/ui/settings_screen.py`, ajouter l'import après la ligne `from anonymator.ui.theme import ...` :

```python
from anonymator.brand import is_locked
```

Remplacer ce bloc (construction de la carte Général, sélecteur inclus) :

```python
        general = Card("palette", "Général")
        general.body.addWidget(QLabel("Thème de l'application"))
        self.theme_box = QComboBox()
        self.theme_box.addItems([THEME_LABELS[k] for k in ("cuma", "cap")])
        self.theme_box.setCurrentText(label_for_theme(prefs.theme))
        self.theme_box.currentTextChanged.connect(
            lambda lbl: self.select_theme(theme_for_label(lbl)))
        general.body.addWidget(self.theme_box)
        general.body.addWidget(QLabel("Dossier de sortie"))
```

par :

```python
        general = Card("palette", "Général")
        if not is_locked():
            general.body.addWidget(QLabel("Thème de l'application"))
            self.theme_box = QComboBox()
            self.theme_box.addItems([THEME_LABELS[k] for k in ("cuma", "cap")])
            self.theme_box.setCurrentText(label_for_theme(prefs.theme))
            self.theme_box.currentTextChanged.connect(
                lambda lbl: self.select_theme(theme_for_label(lbl)))
            general.body.addWidget(self.theme_box)
        general.body.addWidget(QLabel("Dossier de sortie"))
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv\Scripts\python.exe -m pytest tests/test_settings_screen.py -v`
Expected: PASS (tous — les tests existants tournent en dev, `theme_box` présent)

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py
git commit -m "feat(brand): masque le sélecteur de thème en mode verrouillé"
```

---

### Task 7 : Paramétrer `anonymator.spec`

**Files:**
- Modify: `anonymator.spec`

Non testable unitairement (script PyInstaller) — validé par le build dev en Task 8.

- [ ] **Step 1 : Lire la marque de build en tête du `.spec`**

Dans `anonymator.spec`, juste après `from PyInstaller.utils.hooks import collect_data_files`, ajouter :

```python
import os
from anonymator.brand import build_target

# Marque de build (packaging, PAS runtime) : cap | cuma | dev (défaut).
_BUILD_BRAND = os.environ.get('ANONYMATOR_BUILD_BRAND', 'dev')
_ENTRY, _EXE_NAME, _ICON = build_target(_BUILD_BRAND)
```

- [ ] **Step 2 : Utiliser l'entrée paramétrée dans `Analysis`**

Remplacer la 1re ligne de `Analysis(` (`    ['anonymator/__main__.py'],`) par :

```python
    [_ENTRY],
```

- [ ] **Step 3 : Paramétrer nom d'exe et icône**

Dans l'appel `EXE(`, remplacer `    name='anonymator',` par :

```python
    name=_EXE_NAME,
```

et remplacer `    icon='anonymator/ui/assets/anonymator.ico',` par :

```python
    icon=f'anonymator/ui/assets/{_ICON}',
```

Dans l'appel `COLLECT(`, remplacer `    name='anonymator',` par :

```python
    name=_EXE_NAME,
```

- [ ] **Step 4 : Vérification statique (compilation Python du spec)**

Run: `.venv\Scripts\python.exe -c "import ast; ast.parse(open('anonymator.spec', encoding='utf-8').read()); print('spec OK')"`
Expected: `spec OK`

- [ ] **Step 5 : Commit**

```bash
git add anonymator.spec
git commit -m "build: spec paramétré par ANONYMATOR_BUILD_BRAND"
```

---

### Task 8 : Script de build `scripts/build.ps1`

**Files:**
- Create: `scripts/build.ps1`

- [ ] **Step 1 : Écrire le script**

```powershell
# scripts/build.ps1
# Build + zip d'une (ou des) marque(s) Anonymator.
#   .\scripts\build.ps1 cap | cuma | dev | all
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('cap', 'cuma', 'dev', 'all')]
    [string]$Brand
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
$spec = Join-Path $root 'anonymator.spec'

# Version lue depuis anonymator/__init__.py (source de vérité unique)
$initPy = Join-Path $root 'anonymator\__init__.py'
$version = (Select-String -Path $initPy -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value

$meta = @{
    cap  = @{ exe = 'capnonyme';  zip = "CAPnonyme-v$version.zip" }
    cuma = @{ exe = 'cumanonyme'; zip = "CumAnonyme-v$version.zip" }
    dev  = @{ exe = 'anonymator'; zip = $null }
}
$targets = if ($Brand -eq 'all') { @('cap', 'cuma') } else { @($Brand) }

foreach ($b in $targets) {
    Write-Host "== Build $b (v$version) =="
    $env:ANONYMATOR_BUILD_BRAND = $b
    & $python -m PyInstaller --noconfirm $spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller a echoue pour la marque '$b'" }

    $zip = $meta[$b].zip
    if ($zip) {
        $distDir = Join-Path $root "dist\$($meta[$b].exe)"
        $zipPath = Join-Path $root "dist\$zip"
        if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
        Compress-Archive -Path $distDir -DestinationPath $zipPath
        Write-Host "Zip cree : $zipPath"
    }
}
Remove-Item Env:\ANONYMATOR_BUILD_BRAND -ErrorAction SilentlyContinue
Write-Host "Termine."
```

- [ ] **Step 2 : Build dev de bout en bout (vérifie le spec paramétré)**

Run: `powershell -ExecutionPolicy Bypass -File scripts\build.ps1 dev`
Expected: PyInstaller termine sans erreur ; le dossier `dist\anonymator\` existe et contient `anonymator.exe`. (Pas de zip pour dev.)

- [ ] **Step 3 : Build CAP + zip**

Run: `powershell -ExecutionPolicy Bypass -File scripts\build.ps1 cap`
Expected: `dist\capnonyme\capnonyme.exe` existe ; `dist\CAPnonyme-v0.4.0.zip` créé.

- [ ] **Step 4 : Vérifier le verrou à l'exécution**

Lancer `dist\capnonyme\capnonyme.exe` : la fenêtre s'ouvre en thème **bleu (CAP)**, le titre et l'en-tête affichent **CAP'nonyme**, et l'écran « Détection & masquage » **n'affiche pas** le sélecteur de thème. Fermer.

- [ ] **Step 5 : Commit**

```bash
git add scripts/build.ps1
git commit -m "build: script build.ps1 (build + zip par marque)"
```

---

### Task 9 : Vérification globale de non-régression

**Files:** aucun (validation).

- [ ] **Step 1 : Suite de tests complète**

Run: `.venv\Scripts\python.exe -m pytest -q`
Expected: PASS sur l'ensemble (aucune régression ; `test_entrypoint.py` et `test_about.py` restent verts car le mode dev conserve le nom « Anonymator »).

- [ ] **Step 2 : Lancement dev**

Run: `.venv\Scripts\python.exe -m anonymator`
Expected: fenêtre « Anonymator », sélecteur de thème présent dans les réglages, bascule CUMA/CAP fonctionnelle. Fermer.

- [ ] **Step 3 : Commit éventuel des ajustements**

Si des correctifs ont été nécessaires :

```bash
git add -A
git commit -m "test: verrouillage marques — non-régression"
```
```
