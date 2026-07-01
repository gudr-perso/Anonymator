# Conformité AGPL & versionnage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mettre Anonymator en conformité AGPL-3.0 (LICENSE, écran « À propos », README) et instaurer une source de vérité de version unique avec procédure de release taggée.

**Architecture:** `__version__` vit à un seul endroit (`anonymator/__init__.py`), lu au runtime sans dépendance git (compatible exe PyInstaller gelé). Un module pur `anonymator/ui/about.py` produit les mentions légales (version + licence + URL source + tag + attributions), rendues dans une section de `SettingsScreen` et testables sans Qt. Le `LICENSE` AGPL-3.0 est embarqué dans le zip via `anonymator.spec`. Un test garde-fou vérifie que `pyproject.toml` et `__version__` ne dérivent pas.

**Tech Stack:** Python 3.11+ (`tomllib` stdlib), PySide6, pytest + pytest-qt (`qtbot`, plateforme offscreen via `tests/conftest.py`), PyInstaller (`anonymator.spec`).

**Constantes de référence (utilisées dans plusieurs tâches) :**
- URL repo : `https://github.com/gudr-perso/Anonymator`
- Version de départ (source de vérité) : `0.1.0` (aligne l'existant `pyproject.toml`)
- SPDX licence : `AGPL-3.0-or-later`

---

### Task 1: Source de vérité `__version__` + garde-fou de synchronisation

**Files:**
- Modify: `anonymator/__init__.py` (actuellement vide)
- Test: `tests/test_version.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_version.py
import re
import tomllib
from pathlib import Path

import anonymator

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def test_version_is_semver():
    assert isinstance(anonymator.__version__, str)
    assert _SEMVER.match(anonymator.__version__), anonymator.__version__


def test_pyproject_version_matches_package():
    root = Path(__file__).resolve().parents[1]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == anonymator.__version__
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_version.py -v`
Expected: FAIL — `AttributeError: module 'anonymator' has no attribute '__version__'`.

- [ ] **Step 3: Write minimal implementation**

Remplacer le contenu de `anonymator/__init__.py` par :

```python
"""Anonymator — anonymisation locale de texte et de fichiers.

Source de vérité unique de la version du paquet. Lue au runtime par l'UI
(écran « À propos ») sans dépendance à git — l'exe PyInstaller gelé n'a pas
accès au dépôt. Ne bumper qu'au moment d'une release (cf. docs/RELEASE.md).
"""

__version__ = "0.1.0"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_version.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add anonymator/__init__.py tests/test_version.py
git commit -m "feat(version): source de verite unique __version__ + garde-fou synchro pyproject"
```

---

### Task 2: Fichier `LICENSE` AGPL-3.0, SPDX dans `pyproject.toml`, embarquage dans le zip

**Files:**
- Create: `LICENSE` (texte intégral AGPL-3.0, ~35 Ko)
- Modify: `pyproject.toml:1-4`
- Modify: `anonymator.spec:8-14` (liste `datas`)
- Test: `tests/test_license_packaging.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_license_packaging.py
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_license_file_present_and_is_agpl():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text
    assert "Version 3" in text
    # Garde-fou volumétrie : le texte intégral fait ~34 Ko, pas un stub.
    assert len(text) > 30_000


def test_pyproject_declares_agpl_spdx():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["license"] == "AGPL-3.0-or-later"


def test_spec_bundles_license_in_zip():
    spec = (ROOT / "anonymator.spec").read_text(encoding="utf-8")
    # LICENSE doit être ajouté aux datas PyInstaller → présent dans le dossier distribué.
    assert "'LICENSE'" in spec
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_license_packaging.py -v`
Expected: FAIL — `FileNotFoundError` sur `LICENSE` (le fichier n'existe pas encore).

- [ ] **Step 3a: Créer le fichier `LICENSE`**

Télécharger le texte canonique officiel de l'AGPL-3.0 depuis gnu.org et l'écrire à la racine :

```bash
curl -fsSL https://www.gnu.org/licenses/agpl-3.0.txt -o LICENSE
```

Vérifier l'intégrité du fichier obtenu :

```bash
head -n 2 LICENSE
wc -c LICENSE
```

Expected :
- `head` affiche `                    GNU AFFERO GENERAL PUBLIC LICENSE` puis `                       Version 3, 19 November 2007`.
- `wc -c` affiche une taille ~34000–35000 octets.

> Si `curl` est indisponible/hors-ligne : copier le texte intégral de l'AGPL-3.0
> depuis https://www.gnu.org/licenses/agpl-3.0.txt dans un fichier `LICENSE` à la
> racine. Ne pas écrire de version abrégée ni de résumé — le texte doit être intégral.

- [ ] **Step 3b: Déclarer la licence SPDX dans `pyproject.toml`**

Dans `pyproject.toml`, ajouter la ligne `license` sous `version` (bloc `[project]`) :

```toml
[project]
name = "anonymator"
version = "0.1.0"
license = "AGPL-3.0-or-later"
requires-python = ">=3.11"
```

- [ ] **Step 3c: Embarquer `LICENSE` dans le zip distribué (`anonymator.spec`)**

Dans `anonymator.spec`, ajouter `LICENSE` à la liste `datas` (il sera copié à la racine du dossier distribué `dist/anonymator/`) :

```python
    datas=[
        ('LICENSE', '.'),
        ('anonymator/config/entities.json', 'anonymator/config'),
        ('anonymator/ui/assets/anonymator.ico', 'anonymator/ui/assets'),
        ('anonymator/ui/assets/logo.png', 'anonymator/ui/assets'),
        ('anonymator/ui/assets/picto.png', 'anonymator/ui/assets'),
        ('anonymator/ui/assets/icons', 'anonymator/ui/assets/icons'),
    ],
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_license_packaging.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add LICENSE pyproject.toml anonymator.spec tests/test_license_packaging.py
git commit -m "feat(licence): LICENSE AGPL-3.0 + SPDX pyproject + embarquage dans le zip"
```

---

### Task 3: Module pur « À propos » (mentions légales testables sans Qt)

**Files:**
- Create: `anonymator/ui/about.py`
- Test: `tests/test_about.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_about.py
import anonymator
from anonymator.ui.about import REPO_URL, about_lines


def test_about_lines_mention_version_and_tag():
    v = anonymator.__version__
    joined = "\n".join(about_lines())
    assert f"Anonymator v{v}" in joined
    # Correspondance AGPL art.6 : le tag exact doit apparaître.
    assert f"tag v{v}" in joined


def test_about_lines_mention_licence_and_source():
    joined = "\n".join(about_lines())
    assert "AGPL-3.0" in joined
    assert REPO_URL in joined


def test_about_lines_attribute_pymupdf_and_gliner():
    joined = "\n".join(about_lines())
    assert "PyMuPDF" in joined and "Artifex" in joined
    assert "GLiNER" in joined and "Apache-2.0" in joined


def test_about_lines_accepts_explicit_version():
    lines = about_lines(version="9.9.9")
    joined = "\n".join(lines)
    assert "Anonymator v9.9.9" in joined
    assert "tag v9.9.9" in joined
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_about.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.ui.about'`.

- [ ] **Step 3: Write minimal implementation**

```python
# anonymator/ui/about.py
"""Mentions légales « À propos » — conformité AGPL-3.0.

Fonction pure : produit les lignes affichées par l'UI à partir de la version.
Aucun accès git ni réseau (compatible exe PyInstaller gelé). La mention du tag
exact satisfait la correspondance « source = binaire » exigée par l'AGPL art. 6.
"""

from anonymator import __version__

REPO_URL = "https://github.com/gudr-perso/Anonymator"


def about_lines(version: str = __version__) -> list[str]:
    return [
        f"Anonymator v{version}",
        f"Licence : AGPL-3.0 — code source : {REPO_URL} (tag v{version})",
        "Embarque PyMuPDF © Artifex Software — AGPL-3.0",
        "Embarque GLiNER (urchade/gliner_multi-v2.1) — Apache-2.0",
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_about.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/about.py tests/test_about.py
git commit -m "feat(about): module pur des mentions legales AGPL (version, source, tag, attributions)"
```

---

### Task 4: Section « À propos » dans `SettingsScreen`

**Files:**
- Modify: `anonymator/ui/settings_screen.py:1-9` (import) et fin de `__init__` (`:88`)
- Test: `tests/test_settings_screen.py` (append)

- [ ] **Step 1: Write the failing test**

Ajouter à la fin de `tests/test_settings_screen.py` :

```python
def test_settings_shows_about_section(qtbot):
    import anonymator
    s = _settings(); qtbot.addWidget(s)
    text = s.about_label.text()
    assert "AGPL-3.0" in text
    assert f"Anonymator v{anonymator.__version__}" in text
    assert "github.com/gudr-perso/Anonymator" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_settings_screen.py::test_settings_shows_about_section -v`
Expected: FAIL — `AttributeError: 'SettingsScreen' object has no attribute 'about_label'`.

- [ ] **Step 3: Write minimal implementation**

Dans `anonymator/ui/settings_screen.py`, ajouter l'import du helper en tête de fichier (après la ligne `from anonymator.ui.download_worker import DownloadWorker`) :

```python
from anonymator.ui.about import about_lines
```

Puis, à la toute fin de `__init__` (juste après `self._refresh_model_section()`, ligne 88), ajouter la section :

```python
        root.addWidget(QLabel("À propos"))
        self.about_label = QLabel("\n".join(about_lines()))
        self.about_label.setObjectName("muted")
        self.about_label.setWordWrap(True)
        root.addWidget(self.about_label)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_settings_screen.py -v`
Expected: PASS (tous les tests du fichier, dont le nouveau).

- [ ] **Step 5: Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_settings_screen.py
git commit -m "feat(ui): section A propos (licence AGPL + source + attributions) dans les Parametres"
```

---

### Task 5: Section « Licence » dans `README.md`

**Files:**
- Modify: `README.md` (ajout d'une section à la fin)
- Test: `tests/test_readme_license.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_readme_license.py
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_licence_section():
    txt = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "## Licence" in txt
    assert "AGPL-3.0" in txt
    assert "https://github.com/gudr-perso/Anonymator" in txt
    # Attribution PyMuPDF requise par la conformité.
    assert "PyMuPDF" in txt and "Artifex" in txt
    # Lien vers le fichier LICENSE.
    assert "LICENSE" in txt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_readme_license.py -v`
Expected: FAIL — `assert "## Licence" in txt` (section absente).

- [ ] **Step 3: Write minimal implementation**

Ajouter à la fin de `README.md` :

```markdown
---

## Licence

Anonymator est distribué sous licence **AGPL-3.0** — voir [LICENSE](LICENSE).

Le code source complet est disponible sur
<https://github.com/gudr-perso/Anonymator>. Chaque version distribuée correspond à
un tag `vX.Y.Z` du dépôt : le binaire livré correspond exactement au source publié
sous ce tag (AGPL art. 6).

Attributions :

- Embarque **PyMuPDF** © Artifex Software — AGPL-3.0.
- Embarque **GLiNER** — modèle `urchade/gliner_multi-v2.1`, Apache-2.0 (usage commercial autorisé).
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_readme_license.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_readme_license.py
git commit -m "docs(readme): section Licence AGPL-3.0 + disponibilite du source + attributions"
```

---

### Task 6: Procédure de release documentée

**Files:**
- Create: `docs/RELEASE.md`

- [ ] **Step 1: Écrire la procédure**

```markdown
# Procédure de release — Anonymator

Objectif : garantir la correspondance AGPL « binaire livré ↔ source publié » sans
incrémenter la version à chaque commit.

## Principes

- **SemVer** `MAJOR.MINOR.PATCH`.
- **Source de vérité unique** : `__version__` dans `anonymator/__init__.py`.
- **Bump uniquement à la release**, jamais par commit.
- **Un tag git `vX.Y.Z`** par commit distribué — le tag est la preuve de
  correspondance source/binaire (AGPL art. 6). Seuls les commits taggés sont distribués.
- L'écran « À propos » lit `__version__` au runtime (aucune dépendance git dans l'exe gelé).

## Règles de bump

- `PATCH` : corrections sans changement de comportement visible.
- `MINOR` : nouvelle fonctionnalité rétro-compatible (ex. support PDF → `MINOR`).
- `MAJOR` : rupture (format de sortie, refonte UI majeure…).

## Flux de release

1. Développement libre sur `main` (commits non versionnés).
2. Bumper la version au même endroit à deux emplacements maintenus synchro (garde-fou
   `tests/test_version.py::test_pyproject_version_matches_package`) :
   - `anonymator/__init__.py` → `__version__ = "X.Y.Z"`
   - `pyproject.toml` → `version = "X.Y.Z"`
3. Vérifier : `python -m pytest tests/test_version.py -v` (doit passer).
4. Commit : `git commit -am "chore(release): vX.Y.Z"`.
5. Tag : `git tag vX.Y.Z` puis `git push origin main --tags`.
6. Build PyInstaller **depuis ce commit taggé** :
   `python -m PyInstaller anonymator.spec` → l'exe affiche `vX.Y.Z` (écran Paramètres →
   « À propos »), le dépôt public contient le source du même tag. ✅ Conformité AGPL.
7. Zipper `dist/anonymator/` (le dossier contient `LICENSE`) → `Anonymator-vX.Y.Z.zip`.

## Builds de développement (optionnel)

Un build hors release ne doit pas être distribué. Pour éviter toute confusion, ne
distribuer que des builds issus d'un tag. La convention `X.Y.Z-dev` reste manuelle
(éditer temporairement `__version__`) — on ne dérive PAS la version depuis git au
runtime, pour rester compatible avec l'exe gelé.

## Validation de conformité (à faire sur la 1re release)

Après une release de test `vX.Y.Z` :
1. Lancer l'exe → Paramètres → « À propos » affiche `vX.Y.Z` et le `tag vX.Y.Z`.
2. `git show vX.Y.Z` → le tag pointe sur le commit buildé.
3. Le dépôt public expose ce tag et le `LICENSE`.
→ Correspondance exe ↔ tag ↔ source publique démontrée.
```

- [ ] **Step 2: Commit**

```bash
git add docs/RELEASE.md
git commit -m "docs(release): procedure de versionnage et release taggee (conformite AGPL)"
```

---

### Task 7: Suite complète + mise à jour du suivi projet

**Files:**
- Modify: `docs/ETAT-PROJET.md` (marquer la conformité AGPL faite)

- [ ] **Step 1: Lancer toute la suite de tests**

Run: `python -m pytest -q`
Expected: PASS (tous les tests, dont les 5 nouveaux fichiers). Aucun échec, aucun test cassé par les modifications de `SettingsScreen`.

- [ ] **Step 2: Mettre à jour `docs/ETAT-PROJET.md`**

Ouvrir `docs/ETAT-PROJET.md`, repérer la ligne du chantier « Conformité AGPL + versionnage » (autour de la ligne 36 / 88) et la marquer comme **faite** : LICENSE AGPL-3.0 à la racine + embarqué, écran « À propos » (Paramètres), README section Licence, `__version__` unique lu par l'UI, garde-fou de synchro, `docs/RELEASE.md`. Ne PAS cocher le critère « release de test `vX.Y.Z` démontrée » tant qu'une vraie release n'a pas été taggée (validation manuelle, cf. `docs/RELEASE.md`).

- [ ] **Step 3: Commit**

```bash
git add docs/ETAT-PROJET.md
git commit -m "docs(suivi): conformite AGPL + versionnage livree (reste : release de test taggee)"
```

---

## Notes de validation manuelle (hors automatisation)

Ces critères d'acceptation de la spec ne sont pas couverts par des tests unitaires et
doivent être validés à la main lors de la première vraie release :

- **`LICENSE` réellement présent dans le zip distribué** : après `PyInstaller`, vérifier
  que `dist/anonymator/LICENSE` existe (Task 2 teste la *déclaration* dans `.spec`, pas
  le build).
- **Correspondance exe ↔ tag ↔ source public** : procédure « Validation de conformité »
  de `docs/RELEASE.md`.

## Points ouverts (de la spec, non tranchés ici)

- Emplacement « À propos » : ce plan le place en section de `SettingsScreen` (choix le
  plus léger, aucun nouveau routage). Un écran dédié reste possible plus tard.
- Licence GLiNER : **tranchée** — le modèle téléchargé `urchade/gliner_multi-v2.1` est
  Apache-2.0 (vérifié sur la fiche HuggingFace, 2026-07-01). Le risque CC-BY-NC de la
  spec concernait les versions v0/v1 antérieures, non utilisées ici. Reste à ré-auditer
  uniquement si l'app change de modèle GLiNER.
- Dépôt de marque « Anonymator » (INPI) : décision business hors code.
- Synchro du tableau des formats README (PDF ❌→✅) : à faire dans le chantier PDF, pas ici.
