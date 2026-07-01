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
2. Bumper la version aux deux emplacements maintenus synchro (garde-fou
   `tests/test_version.py::test_pyproject_version_matches_package`) :
   - `anonymator/__init__.py` → `__version__ = "X.Y.Z"`
   - `pyproject.toml` → `version = "X.Y.Z"`
3. Vérifier : `.venv/Scripts/python -m pytest tests/test_version.py -v` (doit passer).
4. Commit : `git commit -am "chore(release): vX.Y.Z"`.
5. Tag : `git tag vX.Y.Z` puis `git push origin main --tags`.
6. Build PyInstaller **depuis ce commit taggé** :
   `.venv/Scripts/python -m PyInstaller anonymator.spec` → l'exe affiche `vX.Y.Z`
   (écran Paramètres → « À propos »), le dépôt public contient le source du même tag.
   ✅ Conformité AGPL.
7. **Layout PyInstaller 6** : les `datas` (dont `LICENSE`) sont placés dans
   `dist/anonymator/_internal/`, pas à la racine du dossier. Le `LICENSE` est donc
   bien distribué (`_internal/LICENSE`). Pour le rendre visible à côté de l'exe,
   le copier à la racine avant de zipper :
   `cp dist/anonymator/_internal/LICENSE dist/anonymator/LICENSE`.
8. Zipper `dist/anonymator/` (contient `anonymator.exe` + `LICENSE` racine + `_internal/`)
   → `Anonymator-vX.Y.Z.zip`.

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
4. Vérifier que le `LICENSE` AGPL existe bien dans le dossier distribué :
   `dist/anonymator/_internal/LICENSE` (embarqué par le `.spec`) et, après copie,
   `dist/anonymator/LICENSE` (visible à côté de l'exe).
