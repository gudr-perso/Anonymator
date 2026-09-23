# Design — Anonymisation des images (socle OCR + fichiers image en entrée)

**Date :** 2026-09-23
**Statut :** validé (brainstorming), prêt pour plan d'implémentation
**Version de départ :** `0.8.1`

## Objectif

Permettre à l'utilisateur de déposer une image (`.png`, `.jpg`…), de voir les données
personnelles qu'elle contient, d'en caviarder le contenu — automatiquement par OCR,
manuellement au rectangle, ou les deux — et d'obtenir une image de sortie dont les
pixels sont **réellement détruits** et les métadonnées EXIF purgées.

Le socle produit au passage les briques (OCR, caviardage pixel) dont dépendent les
lots ultérieurs du programme « image ».

## Cadrage : ce lot dans le programme

« Anonymiser les images » recouvre quatre chantiers indépendants. Ils ont été
identifiés ensemble, mais ne sont pas spécifiés ensemble.

| # | Sous-projet | Statut |
|---|---|---|
| **0** | **Socle image** — OCR + caviardage pixel + purge EXIF | **ce document** |
| **2** | **Fichiers image en entrée** — écran, session de revue, sortie | **ce document** |
| 1 | PDF scannés (page sans couche texte) | plus tard — réutilisera le socle |
| 3 | Images incrustées dans `.docx` / `.pptx` / `.xlsx` / `.pdf` | plus tard — le plus lourd |
| 4 | Visages, plaques d'immatriculation | non planifié — autre modèle, autre nature de donnée |

Le lot 3 est celui qui comble le trou le plus dangereux (l'utilisateur croit son
`.docx` anonymisé alors qu'une capture d'écran y expose des noms), mais il suppose
le socle acquis et éprouvé. Le lot 2 le précède parce qu'il valide le socle sur un
cas simple, avec un résultat immédiatement visible.

## Décisions de cadrage

| Axe | Décision |
|---|---|
| Moteur OCR | **RapidOCR** (PP-OCRv6 en ONNX), derrière un protocole `OcrEngine` |
| Modèles | **Embarqués** dans la wheel (32 Mo) — aucun téléchargement, jamais |
| Types d'image visés | Captures d'écran, scans, **photos au téléphone**, graphiques exportés |
| Modes | **OCR + revue visuelle + tracé manuel de rectangles**, combinables |
| Promesse | « l'application **propose**, vous validez » — jamais « tout a été vu » |
| Revue | **Obligatoire**, comme en PDF avant destruction |
| Sortie | Image caviardée, même format, `<nom>_ano_AAAAMMJJHHMMSS.<ext>` |
| Export `.txt` | **Hors périmètre** de ce lot |
| EXIF | Orientation **appliquée**, puis purge totale, tracée dans l'audit |
| Entrée UI | Nouvelle `NavCard` « Importer une image », comme « Importer un PDF » |

### Pourquoi le tracé manuel est dans ce lot, et non « plus tard »

Les photos au téléphone font partie du périmètre assumé. Sur ce terrain, aucun OCR
n'atteint un taux de rappel qui autoriserait à écrire « images traitées » dans la
`PerimetreCard`. Or `anonymator/files/ooxml/__init__.py` pose la règle du projet :

> « Annoncer plus que ce que le code fait est pire que ne rien annoncer : cela
> transforme une lacune en fausse assurance. »

Sans tracé manuel, l'utilisateur qui constate un nom raté par l'OCR n'a aucun recours :
il voit le défaut sans pouvoir le corriger. Avec le tracé, la fonction reste utile même
quand l'OCR échoue complètement, et la promesse redevient tenable. Ce n'est donc pas un
confort : c'est ce qui rend le lot livrable sans mentir.

Coût réel faible : la capacité **existe déjà** côté PDF (`PdfReviewSession.add_manual_rect`,
`PdfCanvas.set_draw_mode`), couverte par 9 tests répartis sur `test_pdf_review_session.py`,
`test_pdf_canvas.py` et `test_pdf_screen.py`. Il s'agit de la généraliser, pas de l'écrire.

## Choix du moteur OCR

Trois options ont été comparées : OCR natif de l'OS (`Windows.Media.Ocr` / Vision),
RapidOCR, EasyOCR sur torch.

**RapidOCR retenu** : une seule implémentation pour Windows et macOS (l'OCR natif en
imposerait deux, au résultat non reproductible d'une machine à l'autre), détection en
quadrilatères orientés — ce qu'exigent les photos de travers et les étiquettes de
graphiques —, wheels pip pures sans binaire externe à embarquer.

### Mesures effectuées le 2026-09-23

| Élément | Mesure |
|---|---|
| `onnxruntime` | **déjà embarqué** — `dist/capnonyme/_internal/onnxruntime/capi/onnxruntime.dll` = 18 Mo, tiré par `gliner`. Coût marginal nul. |
| Modèles | **32 Mo dans la wheel** : `PP-OCRv6_det_small.onnx` 9,93 Mo + `PP-OCRv6_rec_small.onnx` 21,23 Mo + `ch_ppocr_mobile_v2.0_cls_mobile.onnx` 0,59 Mo |
| Wheel `rapidocr` 3.9.2 | 27 Mo |
| Dépendances ajoutées | 11 paquets : `omegaconf`, `antlr4-python3-runtime`, `opencv-python`, `pyclipper`, `shapely`, `six`, `colorlog`, `requests`, `charset-normalizer`, `urllib3` |
| Déjà présents | `Pillow` 12.3.0, `numpy` 2.5.2, `onnxruntime` 1.29.0 |
| Coût estimé dans le zip | **+80 à 110 Mo** sur ~289 Mo actuels — **à mesurer au premier build** |

### Deux pièges de packaging

1. **`opencv-python` embarque ses propres plugins Qt** et entre en conflit avec PySide6
   sous PyInstaller. Imposer **`opencv-python-headless`** dans `requirements.txt`.
2. **`rapidocr/default_models.yaml` pointe vers ModelScope** (hébergeur externe) pour
   tout modèle alternatif. Les modèles par défaut sont locaux, mais un basculement
   déclencherait un appel réseau. Verrouiller la configuration sur les modèles
   embarqués **et le vérifier par un test**, sinon la promesse « aucun appel réseau en
   usage normal » saute en silence.

## Licences

Vérifié le 2026-09-23 auprès du dépôt amont (`RapidAI/RapidOCR`).

| Élément | Licence | Compatible AGPL-3.0 |
|---|---|---|
| Code RapidOCR | Apache-2.0, © 2021 RapidOCR Authors | oui (sens unique Apache-2.0 → AGPL-3.0) |
| Modèles PP-OCR redistribués | Apache-2.0, amont PaddleOCR | oui — **aucune clause non-commerciale** |
| 11 dépendances | Apache-2.0 / BSD-3-Clause / MIT | oui, toutes permissives |

**Obligation nouvelle, à ne pas découvrir au build.** `third-party-licenses/README.md`
note que les poids GLiNER sont *téléchargés*, donc non redistribués. Ici c'est l'inverse :
les 32 Mo de modèles partent **dans l'exécutable**. Redistribuer un artefact Apache-2.0
impose de joindre le texte de la licence et les notices d'attribution. Or le dossier ne
contient aujourd'hui que `GPL-3.0.txt` et `LGPL-3.0.txt`.

À faire dans ce lot :

- ajouter `third-party-licenses/Apache-2.0.txt` ;
- ajouter au tableau du `README.md` de ce dossier les lignes `rapidocr` (OCR) et
  `opencv-python-headless` / `shapely` / `pyclipper` ;
- mentionner explicitement que **les modèles PP-OCR sont redistribués** dans l'exécutable,
  contrairement au modèle GLiNER.

## Architecture

### Refactor préalable — sortir du dossier `pdf/` ce qui n'est pas PDF

`WordBox` et `PageText` sont définis dans `anonymator/files/pdf/extract.py`, **qui
importe `fitz`**. En l'état, la chaîne image tirerait PyMuPDF sans jamais s'en servir.

Or ces types ne doivent rien au PDF. Vérification faite fichier par fichier :
`mapping.py`, `propagate.py`, `PageScan` (`pdf_io.py:22`) et `PdfReviewSession`
n'importent **aucun** symbole PyMuPDF.

```
anonymator/files/textlayer.py     (nouveau)
├── WordBox, PageText, PageScan   # dataclasses de la couche de texte positionné
├── mapping   -> fusionné         # rects_for_entity / rects_for_entities
└── propagate -> fusionné         # propagation d'une valeur confirmée
```

`anonymator/files/pdf/extract.py` et `pdf_io.py` ré-exportent ces symboles : aucun
appelant existant ne change. Refactor mécanique, déjà couvert par les tests en place.
Il porte aussi un sens : « couche de texte positionné » est un concept du domaine,
pas un détail de format.

**Même logique côté session.** `PdfReviewSession` est déjà générique — elle ne manipule
que `PageScan`, `Entity` et `Rect`. Son seul point PDF-spécifique est la sauvegarde.
Elle est renommée `SpatialReviewSession` (`core/spatial_review_session.py`), la
sauvegarde devient le point de spécialisation, et `PdfReviewSession` reste un alias.
Alternative écartée : dupliquer 170 lignes de session et leur couverture de test.

### Modules neufs

```
anonymator/files/image/
├── __init__.py    # COVERAGE_IMAGE — périmètre, source de vérité unique
├── image_io.py    # décodage Pillow, orientation EXIF, ré-encodage, purge EXIF
├── ocr.py         # protocole OcrEngine + FakeOcr + RapidOcrEngine (import paresseux)
├── layout.py      # boîtes OCR -> texte plat en ordre de lecture + WordBox
└── redact.py      # écrasement des pixels + ré-encodage
```

`ocr.py` est calqué sur `anonymator/ner.py` : un protocole, un *fake* pour les tests,
une implémentation réelle à import paresseux. Conséquence directe : **la suite de tests
tourne hors-ligne**, sans charger onnxruntime ni les 32 Mo de modèles.

Aucun de ces modules ne connaît Qt. `image_io` et `redact` ne connaissent ni le NER ni
le référentiel — uniquement « où sont les pixels ».

### UI

```
anonymator/ui/image_screen.py        # écran, calqué sur pdf_screen
anonymator/ui/image_scan_worker.py   # QThread, calqué sur pdf_scan_worker
anonymator/ui/pdf_canvas.py          # généralisé : zoom natif 1.0, pas de RENDER_ZOOM
```

`PdfCanvas` affiche déjà une image avec overlays, zoom et mode tracé. Le seul point à
généraliser est le facteur de rendu : le PDF rend ses pages à `RENDER_ZOOM = 2.0`
(points → pixels), une image est déjà en pixels, donc facteur 1.0. Le canvas devient
`SpatialCanvas`, `PdfCanvas` reste un alias.

Nouvelle `NavCard` « Importer une image » dans `home_screen.py`, après « Importer un PDF ».

## Flux de données

| # | Étape | Code |
|---|---|---|
| 1 | Décodage Pillow, **application** de l'orientation EXIF, conversion RGB. Une seule « page », index 0 | neuf, court |
| 2 | `RapidOcrEngine.read()` → quadrilatères + texte + confiance | neuf |
| 3 | `layout.py` : regroupement en lignes, ordre de lecture, texte plat, `WordBox` avec `char_start` / `char_end` | **neuf — le cœur** |
| 4 | `chunking.detect_long(text, ner, ref)` | existant — le piège GLiNER des ~384 tokens est déjà traité |
| 5 | `mapping.rects_for_entities()` | existant, zéro ligne neuve |
| 6 | `propagate` : une valeur confirmée une fois est retrouvée partout ailleurs dans l'image | existant |
| 7 | Revue : overlays, cases à cocher, tracé manuel (`ZONE` → `[ZONE]`) | existant, généralisé |
| 8 | Écrasement des pixels retenus + ré-encodage sans EXIF | neuf, court |
| 9 | `output_naming.py` | existant |

**Quadrilatères réduits à leur rectangle englobant.** `Rect` est un 4-uple dans tout le
code existant, et un englobant déborde toujours un peu : en caviardage, déborder est sûr,
rogner ne l'est pas.

**Ordre de lecture (étape 3).** Les boîtes sont groupées en lignes par chevauchement
vertical, puis triées de gauche à droite dans chaque ligne, les lignes de haut en bas.
Le texte plat joint les mots par une espace et les lignes par un saut de ligne. C'est ce
texte qui alimente GLiNER : sa qualité conditionne la détection des noms.

## Périmètre et promesse

`anonymator/files/image/__init__.py` expose `COVERAGE_IMAGE`, sur le modèle exact de
`COVERAGE_DOCX` : source de vérité unique partagée entre la `PerimetreCard`, la
documentation et un test de non-régression sur fichier piégé.

**Traité**

- Texte lu par l'OCR, proposé à la validation
- Zones tracées manuellement par l'utilisateur
- Destruction réelle des pixels (pas un calque)
- Purge des métadonnées EXIF (GPS, appareil, auteur, date)

**Non traité**

- Texte que l'OCR n'a pas lu — écriture manuscrite, texte trop petit, flou, contre-jour
- Visages, plaques d'immatriculation, signatures manuscrites
- Texte dans une langue non latine
- Codes-barres et QR codes

**Formulation imposée.** L'écran dit que l'application **propose** des zones et que
l'utilisateur **valide**. Il ne dit jamais que l'image « a été analysée » au sens où
tout aurait été vu.

**GLiNER est moins bon ici, et il faut le dire.** Un texte reconstitué depuis des boîtes
est pauvre en ponctuation et en contexte, or GLiNER vit du contexte : un nom isolé dans
une cellule de tableau capturé sera moins bien reconnu que le même nom dans une phrase.
Les détecteurs déterministes (e-mail, IBAN, téléphone, SIREN/SIRET, NIR) gardent en
revanche toute leur force, puisqu'ils reposent sur des motifs et des sommes de contrôle.

## Erreurs et cas limites

| Cas | Comportement |
|---|---|
| Format non supporté (`.heic`, `.avif`, `.svg`) | Message clair, aucun plantage — doctrine du PDF scanné |
| Image corrompue / illisible | Erreur métier dédiée, comme `CorruptPdfError` |
| Image sans aucun texte détecté | L'écran s'ouvre normalement, zéro entité, tracé manuel disponible |
| Image très grande (> 4000 px) | Redimensionnement pour l'OCR, **caviardage aux coordonnées d'origine** |
| OCR indisponible (dépendance absente) | Mode dégradé : tracé manuel seul, bannière — calqué sur le mode dégradé GLiNER |
| Image animée (`.gif`, `.webp` animé) | Première image seule, avertissement explicite |

**Formats acceptés :** `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tif`, `.tiff`, `.webp` (via Pillow).
`.heic` — format natif des photos iPhone — est **hors périmètre** de ce lot : Pillow ne le
décode pas sans `pillow-heif`. Windows convertit généralement en JPEG à l'import, le cas
devrait donc rester marginal ; si le terrain dit le contraire, `pillow-heif` est un ajout
isolé (licence à vérifier à ce moment-là).

## Tests

| Test | Ce qu'il protège |
|---|---|
| `FakeOcr` sur toute la chaîne | La suite reste **hors-ligne et rapide**, sans onnxruntime ni modèles |
| « le caviardage détruit » | Relire l'image de sortie, vérifier que la zone est uniforme |
| « aucun accès réseau » | Couper la socket pendant un OCR réel — protège la promesse produit |
| « orientation avant purge » | Une image `Orientation=6` ressort droite **et** sans EXIF |
| « périmètre tenu » | Une image piégée par élément annoncé, sur le modèle de `tests/test_perimetre_tenu.py` |
| Ordre de lecture | Boîtes en désordre → texte plat attendu (multi-colonnes, multi-lignes) |
| Coordonnées après redimensionnement | Une image > 4000 px est caviardée au bon endroit |
| Intégration, moteur réel | Marqué et **désélectionné par défaut**, comme celui de GLiNER |

Les 721 tests existants doivent rester verts après le refactor `textlayer` /
`SpatialReviewSession` — c'est le critère d'acceptation de la première tâche.

## Risques

| Risque | Gravité | Traitement |
|---|---|---|
| **Qualité OCR inconnue sur les photos réelles** | **élevée** | Banc de mesure en **première tâche**, sur des images fournies par l'utilisateur, **avant** de construire l'écran. Si le rappel est trop faible, le tracé manuel reste livrable seul. |
| Poids du zip (~289 Mo + 80/110) | moyenne | Mesurer au premier build. Options de repli : modèles `small` déjà retenus, `--exclude` PyInstaller, détection seule sans classification d'orientation |
| Conflit Qt `opencv-python` / PySide6 | moyenne | `opencv-python-headless` imposé, validé par un lancement de l'exe, pas seulement par les tests |
| Fuite réseau via ModelScope | moyenne | Configuration verrouillée + test socket |
| Régression du refactor PDF | faible | Alias de compatibilité + les 721 tests existants |

## Hors périmètre de ce lot

- PDF scannés (lot 1), images incrustées dans les documents (lot 3), visages et plaques (lot 4)
- Export `.txt` du texte anonymisé d'une image
- OCR de l'écriture manuscrite
- `.heic`, `.avif`, `.svg`
- Traitement par lot de plusieurs images

## Ordre d'implémentation suggéré

1. **Banc de mesure OCR** — RapidOCR sur un échantillon d'images réelles : rappel, temps, poids. Décision *go / no-go* sur le moteur.
2. **Refactor** `textlayer.py` + `SpatialReviewSession` + `SpatialCanvas`, à comportement constant, 721 tests verts.
3. **Socle** `files/image/` avec `FakeOcr`, en TDD.
4. **`RapidOcrEngine`** réel, verrou réseau, test d'intégration marqué.
5. **Écran et worker**, `NavCard`, `PerimetreCard`.
6. **Licences**, `requirements.txt`, build des deux marques, mesure du zip.
7. **Documentation** utilisateur (neutre par édition) et `README.md`.
