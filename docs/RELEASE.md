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

## Build macOS (Apple Silicon)

### Contraintes

- **PyInstaller ne cross-compile pas** : le `.app` doit être construit *sur* macOS.
  Le workflow `.github/workflows/build-macos.yml` s'en charge sur un runner
  `macos-14` (arm64), ce qui évite d'avoir à posséder un Mac.
- **arm64 uniquement** : PyTorch ne publie plus de wheels macOS x86_64 depuis la
  2.3. Supporter les Macs Intel impliquerait de figer `torch<=2.2` et un build
  séparé — hors périmètre. Cible = macOS 11+ sur puce Apple (M1 et plus).
- **`universal2` est hors d'atteinte** pour la même raison.

### Procédure

Lancer le workflow `build-macos` (onglet Actions → *Run workflow*, choix de la
marque), ou pousser un tag `vX.Y.Z` — le workflow construit alors `all`
(cap + cuma). Les archives sont publiées en artefacts de run.

Sur un Mac local, l'équivalent de `scripts/build.ps1` est :

```bash
./scripts/build.sh cap    # ou cuma | dev | all
```

Il régénère l'icône `.icns` (`scripts/make_icns.sh`, non versionnée), lance
PyInstaller, puis assemble `dist/<Produit>-vX.Y.Z-macOS-arm64.zip` contenant le
`.app`, le `LICENSE` et les `exemples/`.

Deux différences de fond avec Windows :

- le `.spec` ajoute un bloc `BUNDLE` sur macOS — sans lui, PyInstaller ne produit
  qu'un binaire Unix nu, non lançable depuis le Finder ;
- l'archivage utilise `ditto` et non `zip` : le `.app` contient des liens
  symboliques (frameworks Qt) et une signature que `zip` détruit. Pour la même
  raison, `LICENSE` et `exemples/` sont placés **à côté** du bundle et jamais
  à l'intérieur — toute modification postérieure au build invaliderait sa
  signature.

### Gatekeeper

Le `.app` est signé *ad hoc* par PyInstaller (obligatoire sur arm64 pour qu'il
s'exécute), mais **ni signé Developer ID, ni notarisé** : pas de compte Apple
Developer pour l'instant. La diffusion visée est restreinte (quelques postes
identifiés), ce qui rend l'abonnement à 99 $/an difficile à justifier.

Conséquence : **dès que le `.app` est transféré** — pCloud, mail, clé USB,
artefact GitHub — macOS pose un drapeau de quarantaine et bloque l'ouverture
avec un message trompeur (« l'app est endommagée »). C'est le parcours normal,
pas un cas limite.

La procédure de déblocage voyage donc **avec l'application** : `scripts/build.sh`
écrit un `LISEZ-MOI.txt` à la racine de l'archive, à côté du `.app` et du
`LICENSE`. Il est rédigé pour une utilisatrice non développeuse et contient la
commande exacte, nom d'application substitué :

```bash
xattr -dr com.apple.quarantine /Applications/CAPnonyme.app
```

Cette notice est générée, pas recopiée : le nom de produit vient de
`product_name()` et la taille du modèle de `MODEL_DOWNLOAD_SIZE`
(`anonymator/core/model_status.py`), pour qu'elle ne puisse pas diverger du code.

**Seuil de bascule** : si la diffusion s'élargit au-delà de quelques personnes,
ou si demander un passage par le Terminal devient intenable, il faudra un compte
Apple Developer, un certificat *Developer ID Application*, `codesign` avec
hardened runtime et une notarisation (`notarytool submit` + `stapler staple`) —
automatisables dans le même workflow, certificat stocké en secret de dépôt.

La conformité AGPL est inchangée : même tag, même source, `LICENSE` présent à la
racine de l'archive.
