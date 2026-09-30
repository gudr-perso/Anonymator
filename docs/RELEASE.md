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

---

# Historique des versions et composants embarqués

`requirements.txt` n'exprime que des minima (`>=`) : deux builds d'un même tag ne
sont pas garantis identiques. Cette section est donc le **seul enregistrement de
ce qui a réellement été livré** — état du modèle et des composants tiers au
moment du gel, version par version.

Régénérer l'inventaire de l'environnement courant :
`.venv/Scripts/python -m pip list --format=freeze`

## v0.9.1 — 2026-09-30

Correctif de caviardage sur les images, **remplace la v0.9.0** (dont les archives
n'ont pas été diffusées). Tout le contenu de la v0.9.0 part avec celle-ci.

- **Caviardage mot à mot au lieu de la ligne entière.** Masquer un nom effaçait
  toute la phrase qui l'entourait — « Pour toute question, notre comptable
  *[nom]* reste joignable au *[numéro]* » disparaissait en bloc — et masquer un
  IBAN emportait le mot « IBAN : » avec lui. Le résultat restait sûr, mais
  illisible bien au-delà du nécessaire.

  Cause : RapidOCR rend par défaut **une boîte par ligne**, là où PyMuPDF rend
  une boîte par **mot** côté PDF. `layout.py` prenait chaque boîte pour un mot,
  donc un « mot » faisait 457 px de large. La granularité du rectangle est la
  granularité du caviardage : le défaut ne se voit pas en lisant le code, mais
  saute aux yeux sur l'image produite.

  Le moteur sait découper (`return_word_box`) ; on l'exploite, avec repli sur la
  boîte de ligne quand un mot n'a pas la sienne — caviarder trop large reste
  sûr, perdre la zone ne l'est pas. Sur l'image de démonstration, le téléphone
  passe d'**un rectangle de 222 px à cinq de 16 à 24 px**, et les libellés
  « SIRET : » et « IBAN : » restent lisibles.

- **Image de démonstration** `exemples/capture_mail_demo.png` : une capture
  d'écran de messagerie à données fictives, dans l'univers de `clients_demo.csv`.
  Elle est conçue pour montrer les deux moitiés du travail — les règles seules y
  trouvent e-mail, téléphone, IBAN et SIRET **sans le modèle GLiNER**, mais ni la
  signature manuscrite ni la pastille d'initiales ne sont détectées : il faut les
  tracer à la main. Régénérable par `scripts/make_demo_image.py`, dont les
  données fictives restent lisibles plutôt qu'enfouies dans un binaire.

**Tests** : 826 verts, 7 d'intégration désélectionnés. Un test épingle la
granularité : au-delà de 120 px pour un rectangle de téléphone, la régression
est revenue.

## v0.9.0 — 2026-09-30 (jamais diffusée)

Nouveau **mode Image**, et **quatre correctifs de détection** qui réparent de
vraies fuites. Ces correctifs touchent **tous les formats** — texte, CSV, XLSX,
PDF, Word, PowerPoint — et non le seul mode Image.

> **Mise à jour recommandée à tous les utilisateurs.** Trois des quatre
> correctifs concernent des données qui restaient **en clair** dans un fichier
> présenté comme anonymisé. Les archives `v0.8.1` et antérieures portent ces
> défauts.

### Correctifs de détection

- **IBAN et NIR séparés par des espaces insécables** : les validateurs ne
  retiraient que l'espace simple. Un numéro contenant un insécable, une
  tabulation ou un saut de ligne était déclaré invalide, classé « non confirmé »,
  donc **non masqué par défaut**. L'insécable est courant en Word et en PDF
  français : le cas n'avait rien d'exotique. `vat_fr_is_plausible` normalisait
  déjà tous les blancs dans le même fichier — ces deux validateurs étaient les
  exceptions.
- **Motif IBAN glouton** : une suite de groupes séparés par un blanc *optionnel*
  pouvait absorber le mot voisin (« FR76 … 189 SIRET » lu d'un bloc), ce qui
  cassait la clé de contrôle et produisait le même effet. Avant de renoncer, la
  détection retente désormais sur le plus long préfixe valide ; elle ne masque
  jamais moins qu'avant.
- **Motif téléphone traversant une tabulation ou un saut de ligne** : dans un FEC
  lu en `.txt`, il soudait la fin d'une colonne au début de la suivante et
  **fabriquait** de faux numéros, masquant des montants ou des dates. Séparateurs
  internes désormais explicites (espace, insécable, insécable fine).
- **SIRET écrit par groupes** (`404 833 048 00022`) : non détecté, seule la forme
  collée l'était. Détection ajoutée **avec contexte obligatoire**, comme pour le
  SIREN groupé — hors contexte, la suite de chiffres ne se distingue pas d'un
  montant et la masquer rendrait un FEC illisible.

### Mode Image

Ouvrir une capture d'écran, un scan ou une photo (`.png`, `.jpg`, `.bmp`, `.tif`,
`.webp`), voir les zones que la reconnaissance de texte **propose**, les valider
ou les décocher, **tracer à la souris** ce qu'elle a manqué, puis enregistrer une
image dont les pixels sont **détruits** et les métadonnées EXIF purgées.

- **Aucun téléchargement, aucun appel réseau** : les modèles OCR sont embarqués
  dans l'exécutable. Un test coupe la socket pendant une lecture pour le garantir.
- **La revue est obligatoire par construction** : aucun chemin ne mène à un
  fichier de sortie sans être passé par elle.
- **La promesse est prudente** : l'application propose, l'utilisateur valide. Elle
  ne prétend pas avoir tout vu. L'encart « périmètre » de l'écran liste ce qui
  reste hors de portée — écriture manuscrite, texte trop petit ou flou, visages,
  plaques, codes-barres, et les mises en page en colonnes.
- `.heic` (photo iPhone) non supporté : message clair, aucun plantage.

### Sous le capot

La couche de texte positionné (`WordBox`, `PageText`, `PageScan`, mapping
entité→rectangles, propagation) sort du dossier `pdf/` vers
`anonymator/files/textlayer.py`, où elle ne dépend plus d'aucun format : un PDF
natif l'extrait, un OCR la reconstruit. `PdfReviewSession` devient
`SpatialReviewSession`, `PdfCanvas` devient `SpatialCanvas`. Les anciens modules
ré-exportent : aucun appelant ne change.

### Composants embarqués — ajouts

| Composant | Rôle | Licence |
|---|---|---|
| `rapidocr` 3.9.2 | reconnaissance de texte dans les images | Apache-2.0 |
| Modèles PP-OCRv6 (~32 Mo) | détection, reconnaissance, orientation | Apache-2.0 (amont PaddleOCR) |
| `opencv-python-headless` | traitement d'image pour l'OCR | Apache-2.0 |
| `shapely`, `pyclipper`, `omegaconf`, `antlr4-python3-runtime` | géométrie et configuration | BSD-3-Clause / MIT |

⚠️ Contrairement au modèle GLiNER, **téléchargé** au premier lancement, les modèles
PP-OCR sont **redistribués** dans l'exécutable. Le texte de leur licence est fourni
dans `third-party-licenses/Apache-2.0.txt`.

⚠️ **OpenCV** : `rapidocr` déclare `opencv_python`, la variante qui embarque ses
propres plugins Qt et entre en conflit avec PySide6 sous PyInstaller. Les deux
variantes écrivent le **même dossier `cv2`** et ne cohabitent pas. Après
`pip install -r requirements.txt`, vérifier et corriger :
`pip uninstall -y opencv_python` puis
`pip install --force-reinstall --no-deps opencv-python-headless`.

**Tests** : 820 verts, 4 d'intégration désélectionnés (GLiNER, et pour l'OCR :
lecture réelle, restitution des accents, **verrou réseau**).

**Poids** : le dossier distribué passe de 723,1 à **872,0 Mo** non compressés ; l'archive
`.zip` de 275,7 à **346,2 Mo** (**+70,5 Mo** compressés), identique pour les deux éditions.

**Build du 2026-09-30**, depuis le commit taggé `v0.9.0` : les deux marques construites,
`LICENSE` et `exemples/` présents à la racine du dossier distribué, les trois modèles ONNX
dans `_internal/`, **une seule variante d'OpenCV** embarquée, et les deux exécutables
lancés avec succès (fenêtres « CAP'nonyme » et « Cum'Anonyme », aucun crash log).

## v0.8.1 — 2026-09-22

Correctif d'affichage, **remplace la v0.8.0** (dont les archives n'ont pas été
diffusées).

- **Invitation à s'enregistrer, édition CUMA** : le premier paragraphe était
  coupé en haut et en bas. Le titre « Bienvenue dans Cum'Anonyme », plus large
  que les paragraphes, élargissait le dialogue ; la hauteur du paragraphe était
  alors calculée pour cette largeur (2 lignes) au lieu de sa largeur réelle
  (3 lignes). Test ajouté pour les deux éditions.
- Espace insécable dans « (1 minute) ».

**Tests** : 715 verts, 1 d'intégration désélectionné. Composants embarqués
identiques à la v0.8.0 (même environnement de build).

## v0.8.0 — 2026-09-22

Release **fonctionnelle** : invitation à s'enregistrer. Le traitement des
fichiers est strictement inchangé — mêmes entrées, mêmes sorties qu'en v0.7.0.

### Invitation à s'enregistrer

- Au **premier lancement**, un dialogue propose de s'enregistrer : « M'enregistrer »,
  « Plus tard », « Ne plus demander ». Jamais bloquant ; une seule relance, au
  5ᵉ lancement, puis plus rien. Les installations existantes le verront au
  premier lancement de la v0.8.0.
- « M'enregistrer » ouvre le **formulaire Notion de l'édition** dans le
  navigateur par défaut. **L'application n'effectue aucun appel réseau** : la
  promesse « aucune donnée ne quitte votre machine » reste vraie telle quelle
  (garde-fou : `tests/test_registration.py` vérifie qu'aucune bibliothèque
  réseau n'est importée).
- **Un formulaire par édition** (`Brand.form_url`) : CAP'nonyme et Cum'Anonyme
  ne partagent pas leur formulaire. Une édition sans formulaire n'affiche ni
  l'invitation ni le bouton « Nous contacter ».
- Choix mémorisé dans `preferences.json` (`registration`, `launch_count`).

Pourquoi une invitation et pas un enregistrement obligatoire : sous AGPL-3.0,
toute restriction supplémentaire peut être retirée par n'importe quel
destinataire (art. 7 et 10). Un blocage ne gênerait que les utilisateurs de
bonne foi.

**Tests** : 713 verts, 1 d'intégration désélectionné.

### Composants embarqués

Relevé de l'environnement de build, 2026-09-22 (PC de build différent de celui
de la v0.6.0 ; pas de relevé pour la v0.7.0).

| Composant | Version | Écart vs v0.6.0 |
|---|---|---|
| Python | 3.14.3 | 3.14.6 |
| gliner | 0.2.28 | = |
| torch | 2.13.0 | = |
| transformers | 5.13.1 | = |
| tokenizers | 0.22.2 | = |
| huggingface_hub | 1.29.0 | 1.25.1 |
| onnxruntime | 1.29.0 | 1.28.0 |
| numpy | 2.5.2 | 2.5.1 |
| PySide6 / shiboken6 | 6.11.2 | 6.11.1 |
| pymupdf | 1.28.2 | 1.28.0 |
| openpyxl | 3.1.5 | = |
| python-docx | 1.2.0 | = |
| python-pptx | 1.0.2 | = |
| xlsxwriter | 3.2.9 | = |
| truststore | 0.10.4 | = |
| PyInstaller | 6.22.2 (hooks-contrib 2026.7) | 6.21.0 (2026.6) |

Modèle inchangé : `urchade/gliner_multi-v2.1`, Apache-2.0, téléchargé au
premier lancement.

## v0.6.0 — 2026-09-02

Release de **correction**, issue d'une revue de code systématique du paquet
`anonymator`. Le moteur de détection est inchangé ; ce qui change, c'est ce qui
lui est effectivement soumis, et ce qui est réellement écrit dans le fichier de
sortie. La version mineure est justifiée par l'élargissement du périmètre docx.

Absorbe la `v0.5.2` (build macOS), bumpée mais **jamais taggée ni diffusée**.

### Fuites de données corrigées

- **Liens hypertexte Word** — le texte d'un `<w:hyperlink>` n'était jamais
  analysé (`Paragraph.runs` n'expose que les runs enfants directs). Word créant
  un lien dès qu'une adresse e-mail est saisie, ces adresses ressortaient en
  clair du document « anonymisé », sans apparaître au rapport d'audit.
- **Contrôles de contenu Word** — les paragraphes d'un `<w:sdt>` (champs de
  formulaire, modèles) échappaient à `container.paragraphs` : jamais analysés.
- **Métadonnées du classeur** — le `.xlsx` de sortie conservait auteur, titre et
  sujet d'origine. C'était le seul format sans purge (docx/pptx et PDF
  l'avaient déjà). Un titre comme « Paie 2026 » en dit parfois plus que le
  contenu.
- **En-têtes de 1re page et de pages paires** — seul le jeu normal était traité.

### Corruptions de fichier de sortie corrigées

- **Second enregistrement** — les sessions classeur et document masquent un
  objet ouvert *en place* : réenregistrer après avoir décoché une valeur
  réappliquait les offsets d'origine sur un texte déjà masqué
  (« [PERSONNE] » → « [PERSONNE]NNE] »), silencieusement. Les deux sessions
  rendent désormais leur état d'origine avant chaque passage.
- **Cellules fusionnées (Word)** — `row.cells` rend le même objet pour chaque
  colonne d'une fusion : la cellule était masquée deux fois, avec le même effet.
  Le parcours docx se fait maintenant sur l'arbre XML, ce qui règle du même coup
  les liens hypertexte et les contrôles de contenu.
- **CSV à virgules** — le séparateur était deviné en comptant les caractères de
  la ligne brute, guillemets compris. Un fichier `nom,adresse,ville` contenant
  `"Dupont, Jean"` était relu en **une seule colonne**, puis réécrit avec des
  guillemets doublés. La détection s'appuie désormais sur `csv.reader`, donc sur
  le parseur qui lira le fichier pour de bon.

### Robustesse

- **Fermeture pendant le téléchargement du modèle** — `quit()` + `wait()` sur un
  thread bloqué dans `snapshot_download` gelait la fenêtre jusqu'au bout des
  ~2,2 Go. Annulation coopérative, vue au paquet suivant.
- **Encodage** — `detect_encoding` pouvait renvoyer `cp1252` sur des octets que
  cp1252 ne décode pas (0x81, 0x8D, 0x8F, 0x90, 0x9D) ; repli sur `latin-1`, et
  un CSV illisible se dit sur l'écran Fichier au lieu de remonter en « Erreur
  inattendue ».
- **Bascule « Première ligne = en-têtes » (CSV)** — le dialogue annonçait une
  relance d'analyse qui n'avait pas lieu. La revue disparaissait sans être
  refaite et l'enregistrement repartait en détection automatique : une colonne
  forcée à la main n'était alors pas masquée du tout.
- **Sélection manuelle (écran Texte)** — `add_manual` remettait à zéro toutes
  les cases de la revue.

**Tests** : 637 verts (615 en v0.5.1), dont 15 qui échouent sur le code d'avant.

### Repris de la v0.5.2, jamais diffusée

- **Build macOS (Apple Silicon)** — bundle `.app`, `scripts/build.sh`,
  `scripts/make_icns.sh` et workflow CI sur runner `macos-14` arm64
  (cf. « Build macOS » plus haut). Jamais exécuté à ce jour : PoC à lancer.
- **Environnement de build rafraîchi** — `.venv` reconstruit, exécution sous
  **Python 3.14.6**.
- **Correspondance source/binaire rétablie** — les archives v0.5.1 diffusées
  avaient été construites hors du commit taggé. Les archives v0.6.0 doivent être
  buildées depuis le tag `v0.6.0` (AGPL art. 6, cf. « Principes »).

### Modèle de détection — inchangé

| | |
|---|---|
| Modèle | `urchade/gliner_multi-v2.1` |
| Licence | Apache-2.0 |
| Poids | 2 311 737 240 octets (~2,2 Go) |
| Distribution | téléchargé au premier lancement, **jamais embarqué** dans l'archive |

Le modèle est le même depuis la première version dotée de GLiNER : ni le dépôt,
ni le poids relevé (`MODEL_DOWNLOAD_SIZE_BYTES`, `anonymator/core/model_status.py`)
n'ont bougé.

⚠️ En revanche **sa pile d'exécution évolue** (`gliner`, `transformers`, `torch`,
`tokenizers`). À poids de modèle constants, une détection peut donc différer
d'une version à l'autre. Le test d'intégration sur modèle réel
(`pytest -m integration`) n'ayant jamais été lancé, cette non-régression
**n'est pas vérifiée**.

### Composants embarqués

Relevé de l'environnement de build, 2026-09-01.

| Composant | Version | Rôle |
|---|---|---|
| Python | 3.14.6 | interpréteur gelé |
| gliner | 0.2.28 | chargement et inférence du modèle NER |
| torch | 2.13.0 | runtime du modèle |
| transformers | 5.13.1 | backbone et tokenisation |
| tokenizers | 0.22.2 | tokenisation (binding Rust) |
| huggingface_hub | 1.25.1 | téléchargement du modèle au 1er lancement |
| onnxruntime | 1.28.0 | dépendance gliner |
| numpy | 2.5.1 | calcul |
| PySide6 / shiboken6 | 6.11.1 | interface Qt |
| pymupdf | 1.28.0 | lecture et rédaction PDF |
| openpyxl | 3.1.5 | xlsx |
| python-docx | 1.2.0 | docx |
| python-pptx | 1.0.2 | pptx |
| xlsxwriter | 3.2.9 | écriture xlsx |
| truststore | 0.10.4 | certificats du magasin système |
| PyInstaller | 6.21.0 (hooks-contrib 2026.6) | gel de l'exécutable |

**Tests** : 637 verts, 1 d'intégration désélectionné, sur cette pile.

### Écart de pile mesuré avec la v0.5.1 diffusée

Versions relues directement dans `CAPnonyme-v0.5.1.zip` (archive du 2026-07-30,
celle qui a été diffusée) : `torch 2.13.0`, `transformers 5.13.1`,
`numpy 2.5.1`, `tokenizers 0.22.2`, `huggingface_hub 1.25.1` — **identiques à
la v0.6.0**.

Seuls ces composants sont lisibles dans l'archive gelée : PyInstaller ne conserve
les `dist-info` que pour les paquets dont un hook réclame les métadonnées.
`gliner`, `PySide6` et `pymupdf` n'y figurent pas et leur version en v0.5.1 n'a
pas pu être établie.

**Piste ouverte** : figer les versions (`requirements.lock`) pour rendre les
builds d'un même tag reproductibles. En l'état, ils ne le sont pas.

## Versions antérieures

Pas d'inventaire des composants avant la v0.6.0 : l'historique fonctionnel est
porté par les tags `v0.2.0` → `v0.5.1` et le journal git.
