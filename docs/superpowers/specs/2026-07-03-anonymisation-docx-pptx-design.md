# Design — Anonymisation des fichiers Word (.docx) et PowerPoint (.pptx)

**Date :** 2026-07-03
**Statut :** validé (brainstorming), prêt pour plan d'implémentation

## Objectif

Étendre Anonymator à l'anonymisation des fichiers Office `.docx` et `.pptx`,
en réutilisant au maximum le pipeline existant (détection NER + référentiel,
déduplication, masquage, rapport d'audit) et les patterns de l'application
(dispatch `anonymize_file`, écran Fichier, session de revue).

## Décisions de cadrage

| Axe | Décision |
|---|---|
| Formats v1 | **docx + pptx ensemble** (logique de remap mutualisée) |
| Mode de revue | **Revue par liste d'entités** (type→valeur à cocher), pas de rendu visuel du document |
| Couverture conteneurs | **Cœur + périphérique** (quasi exhaustive) |
| Métadonnées | **Purge systématique** des champs d'identité, tracée dans l'audit |
| Architecture | **Approche C — hybride** : navigation sémantique via python-docx/pptx + module partagé `run_remap` |

### Pourquoi pas de rendu visuel (rappel)

Un `.docx`/`.pptx` ne contient aucune position pixel du texte : c'est Word/PowerPoint
qui calcule la mise en page à l'ouverture. Un rendu fidèle imposerait d'embarquer
un moteur Office (LibreOffice headless, +300–500 Mo, packaging fragile) ou de réécrire
un moteur de mise en page. Rapport valeur/coût défavorable → hors v1. La revue par
liste d'entités donne l'essentiel du contrôle sans rendu.

## Architecture

### Structure des modules

```
anonymator/files/ooxml/
├── __init__.py        # expose COVERAGE (constante périmètre, source de vérité unique)
├── run_remap.py       # cœur partagé : texte plat ↔ runs (testé isolément)
├── metadata.py        # purge docProps (core.xml + app.xml)
├── docx_io.py         # navigation conteneurs Word → list[TextUnit]
└── pptx_io.py         # navigation conteneurs PowerPoint → list[TextUnit]
```

- `docx_io` / `pptx_io` ne connaissent **rien** du NER ni du masquage — uniquement
  « où est le texte ».
- `run_remap` ne connaît **rien** des conteneurs — uniquement « texte plat ↔ runs ».
- Chaque unité est testable indépendamment.

### Concept central : `TextUnit`

Une `TextUnit` = un paragraphe (granularité naturelle pour le NER et le remap). Elle porte :

- `runs` : la liste des runs (objets python-docx/pptx) qui composent le paragraphe ;
- `location` : libellé d'audit lisible (« Corps », « Tableau L2C3 », « En-tête »,
  « Slide 3 / Notes ») ;
- une lecture du texte concaténé et une réécriture des runs.

### Flux de données

1. `docx_io`/`pptx_io` ouvre le fichier → `list[TextUnit]`.
2. `detect_unique()` sur les textes des unités (dédup existante) → `detect()` par texte.
3. Filtrage `confirmed` / revue interactive.
4. Pour chaque unité retenue : `run_remap.apply(unit.runs, entities, ref)`.
5. `metadata.purge()` neutralise les champs d'identité de `docProps`.
6. Sauvegarde via python-docx/pptx → `anonymized_path()`.
7. `AuditReport` alimenté avec les `location` sémantiques.

## Cœur : `run_remap.py`

### Problème

Un paragraphe est fragmenté en runs selon la mise en forme :
`["Contact : ", "Jean ", "Dup", "ont"]`. Le NER détecte « Jean Dupont » sur le texte
concaténé (offsets `[10, 21)`), span à cheval sur 3 runs. Il faut remplacer par
l'étiquette **en préservant la mise en forme** des runs non touchés.

### Algorithme

1. **`build_offsets(runs)`** → texte concaténé + table `[(run_index, char_start, char_end)]`.
   Un run vide compte pour 0 caractère. Fonction pure, symétrique de `pdf/mapping.py`.
2. **`detect()`** sur le texte concaténé → entités à offsets globaux. `merge_entities`
   écarte les chevauchements (déjà appelé par `apply_masking`).
3. **`apply(runs, entities, ref)`** — pour chaque span `[s, e)`, de la **fin vers le début** :
   - trouver les runs recoupant `[s, e)` ;
   - **premier** run recoupé : remplacer sa portion `[s, e)∩run` par l'étiquette complète
     (`ref.tag_for(type)`) → l'étiquette hérite du style de ce run ;
   - runs **suivants** recoupés : supprimer la portion recouverte (chaîne vide) ;
   - runs hors span : inchangés.

### Règle de simplicité (YAGNI)

On **ne fusionne pas** et **ne supprime pas** les runs de l'arbre XML, même devenus
vides — on ne réécrit que `run.text`. Zéro manipulation structurelle = zéro risque
de corrompre le document.

### Cas limites (→ tests)

- span entièrement dans un seul run ;
- span à cheval sur 2 puis 3+ runs ;
- runs vides intercalés ;
- deux entités dans le même paragraphe (ordre fin→début) ;
- entité en tout début / toute fin de paragraphe.

### Hors périmètre v1 (limites documentées)

- texte dans les champs calculés / insertions automatiques (`w:fldSimple`, field codes) ;
- équations ;
- texte à l'intérieur d'images (pas d'OCR) ;
- données de graphiques liées à un fichier externe.

## Carte de couverture des conteneurs

### docx (`docx_io`)

| Conteneur | Localisation audit | Note |
|---|---|---|
| Corps | `Corps` | paragraphes de `document.body` |
| Tableaux | `Tableau L{r}C{c}` | récursion cellules ; tableaux imbriqués |
| En-têtes / pieds | `En-tête` / `Pied` | par section |
| Notes bas de page / fin | `Note {n}` | parties `footnotes`/`endnotes` |
| Commentaires | `Commentaire {n}` | partie `comments` |
| Suivi des modifications | inclus | `w:ins`/`w:del` traités comme runs |
| Zones de texte / SmartArt | `Zone de texte` | text-boxes dans shapes ; SmartArt = drawing `dgm` |

### pptx (`pptx_io`)

| Conteneur | Localisation audit | Note |
|---|---|---|
| Shapes de slide | `Slide {n}` | text frames |
| Groupes | `Slide {n}` | **récursion obligatoire** dans `GroupShape` |
| Tableaux | `Slide {n} / Tableau L{r}C{c}` | |
| Notes | `Slide {n} / Notes` | notes slide |
| Zones de texte / SmartArt | `Slide {n} / Zone de texte` | |

### Réserve technique

python-docx expose corps/tableaux/en-têtes/sections ; commentaires, notes, SmartArt
et certaines zones de texte demandent parfois de descendre au XML de la partie
(via `element`/`part`). Encapsulé dans `docx_io`, c'est la zone la plus densément testée.
Idem `Company`/`Manager` (`app.xml`), non exposés par `core_properties`.

## Purge des métadonnées (`metadata.py`)

Neutralisation (valeur → vide) des champs d'identité, pour les deux formats :

- `docProps/core.xml` : `author`/`creator`, `last_modified_by`, `title`, `keywords`,
  `subject`/`comments`, `category` ;
- `docProps/app.xml` : `Company`, `Manager`.

Chaque champ purgé non vide est consigné dans l'audit :
`location = "Métadonnées / {champ}"`.

## Intégration UI

### `OoxmlReviewSession` (dans `core/`)

Calquée sur l'interface de `FileReviewSession` mais **sans logique colonnes/cellules** :
clé = index de `TextUnit`. Même API consommée par l'arbre UI :
`types()`, `values_for(type)`, `count_retained(type)`,
`is_type_enabled`/`set_type_enabled`, `is_value_enabled`/`set_value_enabled`, `report()`.
Même règle opt-in (`confirmed` → coché par défaut). → l'arbre « Entités détectées »
fonctionne sans modification.

### Workers

`OoxmlScanWorker` (miroir de `FileScanWorker`) : construit le détecteur dans le thread,
émet `(text_units, scanned)`. L'application finale (run_remap + purge + save) est
synchrone au clic « Anonymiser » (léger, pas de modèle requis), comme la session CSV.

### Adaptations `FileScreen`

- filtre `QFileDialog` et libellés : ajout `*.docx *.pptx` ;
- `load_path` : docx/pptx → pas de grille de lignes, active « Analyser », préview dédiée ;
- `analyze()` : branche docx/pptx vers `OoxmlScanWorker` → `OoxmlReviewSession` ;
- **préview gauche réutilisée** : `QTableWidget` à 2 colonnes — `Emplacement` (la `location`)
  + `Texte extrait` — surlignage des cellules contenant des entités retenues ; pagination réutilisée.

### Affichage du périmètre (exigence ferme)

Sous la carte « Entités détectées », un encart `PerimetreCard` en deux blocs, **visible avant application** :

- ✅ **Traité** : corps, tableaux, en-têtes/pieds, notes, commentaires, zones de texte
  + **purge des métadonnées** (auteur, société…).
- ⚠️ **Non traité — à vérifier manuellement** : champs calculés / insertions automatiques,
  équations, **texte dans les images (pas d'OCR)**, données de graphiques liées à un fichier externe.

Le texte provient d'une constante unique `ooxml.COVERAGE` (source de vérité partagée
UI ↔ doc), pour éviter tout décalage entre ce que l'app annonce et ce qu'elle fait.

## Stratégie de test

- **`run_remap` (priorité 1)** : tests unitaires purs, fixtures de runs en mémoire,
  cas limites ci-dessus ; vérifie texte concaténé, offsets, styles préservés.
- **`docx_io` / `pptx_io`** : documents fabriqués par programme couvrant chaque conteneur ;
  assert `TextUnit` + `location`.
- **`metadata`** : champs renseignés → vides après purge + entrées d'audit.
- **Intégration bout-en-bout** : anonymiser un `.docx` et un `.pptx`, **rouvrir** le
  fichier produit, vérifier entités masquées, mise en forme préservée, métadonnées vides,
  `AuditReport` cohérent, cohérence globale (même valeur → même étiquette entre conteneurs).
- **Non-régression dispatch** : `anonymize_file` route `.docx`/`.pptx` ; format inconnu inchangé.
- Fixtures programmatiques dans `tests/ooxml_fixtures.py` (pattern `tests/pdf_fixtures.py`).

## Dépendances & packaging

- `requirements.txt` : `python-docx>=1.1`, `python-pptx>=0.6.23` (pures-Python, MIT,
  compatibles AGPL).
- `anonymator.spec` : vérifier au build les gabarits par défaut chargés en package data ;
  ajouter si besoin `datas` via `collect_data_files('docx')` / `collect_data_files('pptx')`.
  Test de fumée sur l'exe PyInstaller.

## Ce qui est explicitement hors périmètre v1

- rendu visuel fidèle du document ;
- OCR du texte dans les images ;
- champs calculés, équations, graphiques liés à des données externes ;
- sélection fine de conteneurs par l'utilisateur (tout est traité ; l'utilisateur
  décoche au niveau type/valeur).
