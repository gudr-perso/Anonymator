# Anonymisation des images — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre d'ouvrir une image, d'y caviarder les données personnelles (proposées par OCR, complétées à la main au rectangle), et d'enregistrer une image dont les pixels sont réellement détruits et les métadonnées EXIF purgées.

**Architecture:** L'OCR n'est pas une nouvelle chaîne, c'est une nouvelle **source**. Il produit le même contrat que `files/pdf/extract.py` — un texte plat en ordre de lecture plus une `WordBox` par mot — donc `detect_long`, `mapping`, `propagate`, la session de revue et le canvas se rebranchent sans modification. Un refactor préalable sort ces briques du dossier `pdf/`, où elles sont retenues par un import `fitz` dont elles n'ont pas besoin.

**Tech Stack:** Python 3.14, Pillow, RapidOCR (ONNX, modèles PP-OCRv6 embarqués), onnxruntime (déjà présent via `gliner`), PySide6, pytest.

**Spec :** [`docs/superpowers/specs/2026-09-23-anonymisation-images-design.md`](../specs/2026-09-23-anonymisation-images-design.md)

**Branche :** `feat/anonymisation-images` (déjà créée, porte la spec)

---

## Avant de commencer

```bash
cd /c/_pCloud/Extensions/anonymise
git status
./.venv/Scripts/python -m pytest -q
```

Attendu : branche `feat/anonymisation-images`, `721 passed, 1 deselected`.

Ce nombre est le filet du plan : **il ne doit jamais baisser**. Les tâches 2 à 5 sont des refactors à comportement constant — elles ajoutent 0 test et gardent les 721.

## Carte des fichiers

| Fichier | Responsabilité | Tâche |
|---|---|---|
| `scripts/ocr_bench.py` | Banc de mesure OCR, hors package | 1 |
| `anonymator/files/textlayer.py` | **Créé** — `WordBox`, `PageText`, `PageScan`, `rects_for_entity/ies`, propagation | 2, 3 |
| `anonymator/files/pdf/extract.py` | Ré-exporte depuis `textlayer` | 2 |
| `anonymator/files/pdf/mapping.py` | Ré-exporte depuis `textlayer` | 2 |
| `anonymator/files/pdf/propagate.py` | Ré-exporte depuis `textlayer` | 3 |
| `anonymator/files/pdf/pdf_io.py` | Ré-exporte `PageScan` | 2 |
| `anonymator/core/spatial_review_session.py` | **Créé** — `SpatialReviewSession` (ex-`PdfReviewSession`) | 4 |
| `anonymator/core/pdf_review_session.py` | Alias de compatibilité | 4 |
| `anonymator/ui/spatial_canvas.py` | **Créé** — `SpatialCanvas` (ex-`PdfCanvas`) | 5 |
| `anonymator/ui/pdf_canvas.py` | Alias de compatibilité | 5 |
| `anonymator/files/image/ocr.py` | **Créé** — `OcrBox`, protocole `OcrEngine`, `FakeOcr`, `RapidOcrEngine` | 6, 12 |
| `anonymator/files/image/layout.py` | **Créé** — boîtes OCR → `PageText` en ordre de lecture | 7 |
| `anonymator/files/image/image_io.py` | **Créé** — décodage, EXIF, purge, encodage, orchestration | 8, 11 |
| `anonymator/files/image/redact.py` | **Créé** — écrasement des pixels | 9 |
| `anonymator/files/image/__init__.py` | **Créé** — `COVERAGE_IMAGE` | 10 |
| `anonymator/files/coverage.py` | **Créé** — registre `COVERAGE_BY_FORMAT` unifié | 10 |
| `anonymator/ui/components/perimetre_card.py` | Lit le registre unifié | 10 |
| `anonymator/ui/image_scan_worker.py` | **Créé** — QThread d'analyse | 15 |
| `anonymator/ui/image_screen.py` | **Créé** — écran de revue image | 16 |
| `anonymator/ui/home_screen.py` | `NavCard` « Importer une image » | 17 |
| `anonymator/ui/main_window.py` | Routage `show_image` | 17 |
| `requirements.txt`, `anonymator.spec`, `third-party-licenses/` | Packaging et licences | 14, 18 |
| `README.md`, `docs/ETAT-PROJET.md` | Documentation | 19 |

---

# PHASE 0 — Décision sur le moteur

## Task 1 : Banc de mesure OCR (porte GO / NO-GO)

**Pourquoi d'abord.** Deux inconnues peuvent tuer le choix RapidOCR, et aucune ne se lève en lisant du code :

1. **Les accents français.** La wheel ne contient **aucun dictionnaire de caractères** et la config par défaut est `lang_type: "ch"`. Si `Éléonore`, `Châteauneuf` ou `Gaëtan` reviennent sans accents ou mutilés, la détection de noms s'effondre — et le modèle `latin` de rechange n'est **pas** dans la wheel, ce qui entrerait en conflit avec la règle « zéro réseau ».
2. **Le rappel sur photo au téléphone**, qui conditionne la formulation du périmètre.

**Files:**
- Create: `scripts/ocr_bench.py`
- Create: `scripts/bench_images/` (jeu d'images, **non versionné** — ajouter au `.gitignore`)

> **✅ Fait le 2026-09-23 — critère n°1 tranché, GO.** Les accents sont restitués :
> 5 lignes sur 5 exactes au caractère près (`Éléonore Châteauneuf habite à Nîmes`,
> `Gaëtan Dupré - facture de 1 250,50 €`, `François Maître, 12 rue de l'Église`),
> scores 0,98 à 1,00. Le modèle `latin` de rechange n'est **pas** nécessaire.
> Détail dans la spec, § « Résultat du test des accents ». **Les steps 1, 2 et 5
> ci-dessous sont soldés ; restent les steps 3, 4 et 6** — la mesure du rappel sur
> de vraies images, qui ne décide plus du moteur mais alimente la rédaction du
> périmètre (tâche 10) et le besoin d'un indicateur de progression (tâche 16).

- [ ] **Step 1 : Installer RapidOCR dans le venv** *(fait)*

```bash
cd /c/_pCloud/Extensions/anonymise
./.venv/Scripts/python -m pip install rapidocr
./.venv/Scripts/python -m pip uninstall -y opencv_python
./.venv/Scripts/python -m pip install --force-reinstall --no-deps opencv-python-headless
./.venv/Scripts/python -c "from rapidocr import RapidOCR; print('import OK')"
```

Attendu : `import OK`.

⚠️ **Les trois commandes sont nécessaires, dans cet ordre.** `rapidocr` déclare
`opencv_python` — la variante complète, qui embarque ses propres plugins Qt et entre
en conflit avec PySide6 sous PyInstaller. Demander `opencv-python-headless` en même
temps ne suffit pas : pip installe **les deux**. Et comme elles écrivent le même
dossier `cv2`, désinstaller la complète efface aussi le headless — d'où la
réinstallation forcée en troisième commande.

- [ ] **Step 2 : Écrire le banc**

Créer `scripts/ocr_bench.py` :

```python
"""Banc de mesure OCR — hors package, jamais importé par l'application.

Usage : ./.venv/Scripts/python scripts/ocr_bench.py scripts/bench_images
Produit un rapport texte : par image, temps, nombre de boîtes, texte reconnu.
"""
import sys
import time
from pathlib import Path

from PIL import Image
import numpy as np
from rapidocr import RapidOCR

ACCENTS = "éèêëàâçùûôîïÉÈÀÇ"


def run(folder: Path) -> None:
    engine = RapidOCR()
    suffixes = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
    images = sorted(p for p in folder.iterdir() if p.suffix.lower() in suffixes)
    if not images:
        print(f"Aucune image dans {folder}")
        return
    for path in images:
        img = Image.open(path).convert("RGB")
        arr = np.array(img)
        t0 = time.perf_counter()
        res = engine(arr)
        elapsed = time.perf_counter() - t0
        txts = list(res.txts or ())
        joined = " ".join(txts)
        found = sorted({c for c in joined if c in ACCENTS})
        print(f"\n=== {path.name} ({img.width}x{img.height}) ===")
        print(f"  temps      : {elapsed:.2f} s")
        print(f"  boites     : {len(txts)}")
        print(f"  accents    : {''.join(found) if found else 'AUCUN'}")
        print(f"  texte      : {joined[:400]}")


if __name__ == "__main__":
    run(Path(sys.argv[1] if len(sys.argv) > 1 else "scripts/bench_images"))
```

- [ ] **Step 3 : Constituer le jeu d'images**

```bash
mkdir -p scripts/bench_images
echo "scripts/bench_images/" >> .gitignore
```

Y déposer **au minimum 8 images** couvrant les quatre cas du périmètre :

| Cas | Nombre | Doit contenir |
|---|---|---|
| Capture d'écran | 2 | Un nom **accentué** (`Éléonore Dupré`), un e-mail, un IBAN |
| Scan de document | 2 | Une facture ou un courrier avec nom et adresse |
| Photo au téléphone | 2 | Le même document photographié de biais, éclairage inégal |
| Graphique exporté | 2 | Des étiquettes, dont une verticale |

**Au moins une image doit contenir `Éléonore Châteauneuf Gaëtan` en clair** : c'est le test des accents.

- [ ] **Step 4 : Lancer le banc**

```bash
./.venv/Scripts/python scripts/ocr_bench.py scripts/bench_images
```

- [ ] **Step 5 : Trancher — GO / NO-GO**

Critères d'acceptation, à évaluer dans cet ordre :

| # | Critère | Seuil | Si échec |
|---|---|---|---|
| 1 | ~~**Accents français** restitués~~ | ✅ **TRANCHÉ le 2026-09-23 : GO** — 5/5 lignes exactes | — |
| 2 | Rappel sur capture d'écran | ≥ 95 % des mots lisibles | NO-GO moteur — reprendre le comparatif de la spec (OCR natif OS / EasyOCR) |
| 3 | Rappel sur scan | ≥ 85 % | Acceptable, à refléter dans le périmètre |
| 4 | Rappel sur photo | ≥ 50 % | En dessous, la spec tient quand même : le tracé manuel reste livrable. **Le noter dans le périmètre**, ne pas bloquer. |
| 5 | Temps sur une image 2000 px | < 10 s | Au-delà, prévoir un indicateur de progression dans l'écran (tâche 16) |

- [ ] **Step 6 : Consigner le résultat et committer**

Ajouter les chiffres mesurés dans la spec, section « Mesures effectuées », sous un titre `### Résultats du banc (tâche 1)`.

```bash
git add scripts/ocr_bench.py .gitignore docs/superpowers/specs/2026-09-23-anonymisation-images-design.md
git commit -m "chore(ocr): banc de mesure RapidOCR et resultats"
```

> **Porte.** Ne pas enchaîner sur la tâche 2 avant que le critère 1 soit tranché. Les critères 3 et 4 n'arrêtent rien : ils alimentent la rédaction du périmètre en tâche 10.

---

# PHASE 1 — Refactor à comportement constant

Les quatre tâches qui suivent ne changent **aucun** comportement. Critère de sortie unique et identique pour chacune : `721 passed, 1 deselected`.

## Task 2 : Extraire `textlayer.py` — dataclasses et mapping

**Files:**
- Create: `anonymator/files/textlayer.py`
- Modify: `anonymator/files/pdf/extract.py` (retirer les dataclasses, ré-exporter)
- Modify: `anonymator/files/pdf/mapping.py` (devient un ré-export)
- Modify: `anonymator/files/pdf/pdf_io.py` (retirer `PageScan`, ré-exporter)
- Test: `tests/test_textlayer.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_textlayer.py` :

```python
from anonymator.files.textlayer import (
    WordBox, PageText, PageScan, rects_for_entity, rects_for_entities)
from anonymator.model import Entity


def _page():
    return PageText(0, "Jean Dupont paie", [
        WordBox("Jean", (0.0, 0.0, 10.0, 5.0), 0, 4),
        WordBox("Dupont", (11.0, 0.0, 25.0, 5.0), 5, 11),
        WordBox("paie", (26.0, 0.0, 34.0, 5.0), 12, 16),
    ])


def test_rects_for_entity_couvre_les_mots_recoupes():
    ent = Entity("PERSON", "Jean Dupont", 0, 11, "ner")
    assert rects_for_entity(_page(), ent) == [
        (0.0, 0.0, 10.0, 5.0), (11.0, 0.0, 25.0, 5.0)]


def test_rects_for_entities_dedoublonne():
    e1 = Entity("PERSON", "Jean", 0, 4, "ner")
    e2 = Entity("PERSON", "Jean", 0, 4, "ner")
    assert rects_for_entities(_page(), [e1, e2]) == [(0.0, 0.0, 10.0, 5.0)]


def test_textlayer_n_importe_pas_pymupdf():
    import anonymator.files.textlayer as m
    assert "fitz" not in getattr(m, "__dict__", {})


def test_page_scan_est_une_dataclass_pure():
    scan = PageScan(0, "abc", [], [])
    assert (scan.page_index, scan.text, scan.words, scan.entities) == (0, "abc", [], [])
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

```bash
./.venv/Scripts/python -m pytest tests/test_textlayer.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.files.textlayer'`.

- [ ] **Step 3 : Créer `anonymator/files/textlayer.py`**

Le contenu est **déplacé à l'identique** depuis `pdf/extract.py` (dataclasses), `pdf/pdf_io.py` (`PageScan`) et `pdf/mapping.py` (fonctions) :

```python
# anonymator/files/textlayer.py
"""Couche de texte positionné : un texte plat en ordre de lecture, plus la
boîte de chaque mot. Concept du domaine, indépendant du format source — un PDF
natif l'extrait, un OCR la reconstruit depuis une image.

Aucun import de PyMuPDF ni de Pillow ici : ce module ne sait pas d'où vient la
page, seulement comment la décrire."""
from dataclasses import dataclass

from anonymator.model import Entity

Rect = tuple[float, float, float, float]


@dataclass
class WordBox:
    text: str
    rect: Rect          # (x0, y0, x1, y1) dans l'unité de la source
    char_start: int     # offset inclusif dans le texte plat
    char_end: int       # offset exclusif


@dataclass
class PageText:
    page_index: int
    text: str           # texte plat reconstruit en ordre de lecture
    words: list[WordBox]


@dataclass
class PageScan:
    page_index: int
    text: str
    words: list[WordBox]
    entities: list[Entity]


def _intersects(word: WordBox, start: int, end: int) -> bool:
    """Vrai si la plage de caractères du mot recoupe [start, end)."""
    return word.char_start < end and start < word.char_end


def rects_for_entity(page: PageText, entity: Entity) -> list[Rect]:
    """Rectangles de tous les mots dont la plage recoupe [entity.start, entity.end).
    Une entité multi-lignes produit naturellement plusieurs rectangles."""
    return [w.rect for w in page.words
            if _intersects(w, entity.start, entity.end)]


def rects_for_entities(page: PageText, entities: list[Entity]) -> list[Rect]:
    out: list[Rect] = []
    for e in entities:
        for r in rects_for_entity(page, e):
            if r not in out:
                out.append(r)
    return out
```

- [ ] **Step 4 : Faire de `pdf/mapping.py` un ré-export**

Remplacer **tout** le contenu de `anonymator/files/pdf/mapping.py` par :

```python
# anonymator/files/pdf/mapping.py
"""Compatibilité : le mapping vit désormais dans anonymator.files.textlayer,
qui ne dépend d'aucun format. Ce module reste le point d'entrée historique."""
from anonymator.files.textlayer import (  # noqa: F401
    Rect, rects_for_entity, rects_for_entities)
```

- [ ] **Step 5 : Retirer les dataclasses de `pdf/extract.py`**

Dans `anonymator/files/pdf/extract.py`, supprimer les définitions `@dataclass class WordBox` et `@dataclass class PageText` (lignes 21-32) ainsi que `from dataclasses import dataclass`, et ajouter juste après `import fitz` :

```python
from anonymator.files.textlayer import WordBox, PageText  # noqa: F401
```

Le reste du fichier (`open_document`, `ensure_native`, `extract_page`, `extract_pages`) ne change pas.

- [ ] **Step 6 : Retirer `PageScan` de `pdf/pdf_io.py`**

Dans `anonymator/files/pdf/pdf_io.py`, supprimer le bloc `@dataclass class PageScan` (lignes 21-26) et remplacer la ligne `from anonymator.files.pdf.extract import WordBox` par :

```python
from anonymator.files.textlayer import WordBox, PageScan  # noqa: F401
```

- [ ] **Step 7 : Lancer toute la suite**

```bash
./.venv/Scripts/python -m pytest -q
```

Attendu : `725 passed, 1 deselected` (721 + les 4 nouveaux de `test_textlayer.py`).

- [ ] **Step 8 : Committer**

```bash
git add anonymator/files/textlayer.py anonymator/files/pdf/extract.py anonymator/files/pdf/mapping.py anonymator/files/pdf/pdf_io.py tests/test_textlayer.py
git commit -m "refactor(textlayer): sortir WordBox/PageText/PageScan et le mapping du dossier pdf"
```

## Task 3 : Déplacer la propagation dans `textlayer.py`

**Files:**
- Modify: `anonymator/files/textlayer.py` (ajouter la propagation)
- Modify: `anonymator/files/pdf/propagate.py` (devient un ré-export)
- Test: `tests/test_textlayer.py` (compléter)

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à la fin de `tests/test_textlayer.py` :

```python
def test_propagation_retrouve_une_valeur_confirmee_sur_une_autre_page():
    from anonymator.files.textlayer import propagate_across_pages
    p0 = PageText(0, "Jean Dupont", [
        WordBox("Jean", (0.0, 0.0, 10.0, 5.0), 0, 4),
        WordBox("Dupont", (11.0, 0.0, 25.0, 5.0), 5, 11),
    ])
    p1 = PageText(1, "vu Jean Dupont ici", [
        WordBox("vu", (0.0, 0.0, 4.0, 5.0), 0, 2),
        WordBox("Jean", (5.0, 0.0, 15.0, 5.0), 3, 7),
        WordBox("Dupont", (16.0, 0.0, 30.0, 5.0), 8, 14),
        WordBox("ici", (31.0, 0.0, 37.0, 5.0), 15, 18),
    ])
    confirmee = Entity("PERSON", "Jean Dupont", 0, 11, "ner")
    result = propagate_across_pages([p0, p1], [[confirmee], []])
    assert [e.value for e in result[1]] == ["Jean Dupont"]
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

```bash
./.venv/Scripts/python -m pytest tests/test_textlayer.py -q
```

Attendu : `ImportError: cannot import name 'propagate_across_pages'`.

- [ ] **Step 3 : Déplacer le code**

Copier **à l'identique** tout le contenu de `anonymator/files/pdf/propagate.py` (sauf sa ligne d'en-tête et ses imports) à la fin de `anonymator/files/textlayer.py`, et compléter les imports en tête de `textlayer.py` :

```python
from anonymator.textnorm import normalize
from anonymator.merge import merge_entities
```

- [ ] **Step 4 : Faire de `pdf/propagate.py` un ré-export**

Remplacer **tout** le contenu de `anonymator/files/pdf/propagate.py` par :

```python
# anonymator/files/pdf/propagate.py
"""Compatibilité : la propagation vit désormais dans anonymator.files.textlayer.
Elle ne dépend d'aucun format — seulement de WordBox et d'Entity."""
from anonymator.files.textlayer import propagate_across_pages  # noqa: F401
```

- [ ] **Step 5 : Lancer toute la suite**

```bash
./.venv/Scripts/python -m pytest -q
```

Attendu : `726 passed, 1 deselected`.

- [ ] **Step 6 : Committer**

```bash
git add anonymator/files/textlayer.py anonymator/files/pdf/propagate.py tests/test_textlayer.py
git commit -m "refactor(textlayer): deplacer la propagation hors du dossier pdf"
```

## Task 4 : `PdfReviewSession` → `SpatialReviewSession`

La classe est déjà générique : elle ne manipule que `PageScan`, `Entity` et `Rect`, et une image est simplement une liste d'une seule page. Aucune logique ne change — seulement le nom et le module.

**Files:**
- Create: `anonymator/core/spatial_review_session.py`
- Modify: `anonymator/core/pdf_review_session.py` (devient un alias)
- Test: `tests/test_spatial_review_session.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_spatial_review_session.py` :

```python
from anonymator.core.spatial_review_session import SpatialReviewSession
from anonymator.files.textlayer import PageScan, WordBox
from anonymator.model import Entity
from anonymator.referential import Referential


def test_session_accepte_une_page_unique():
    page = PageScan(0, "Jean Dupont", [
        WordBox("Jean", (0.0, 0.0, 10.0, 5.0), 0, 4),
        WordBox("Dupont", (11.0, 0.0, 25.0, 5.0), 5, 11),
    ], [Entity("PERSON", "Jean Dupont", 0, 11, "ner")])
    s = SpatialReviewSession([page], Referential.load_default())
    assert s.types() == ["PERSON"]
    assert len(s.retained_rects_by_page()[0]) == 2


def test_pdf_review_session_reste_un_alias():
    from anonymator.core.pdf_review_session import PdfReviewSession
    assert PdfReviewSession is SpatialReviewSession
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

```bash
./.venv/Scripts/python -m pytest tests/test_spatial_review_session.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.core.spatial_review_session'`.

- [ ] **Step 3 : Déplacer le fichier et renommer la classe**

```bash
git mv anonymator/core/pdf_review_session.py anonymator/core/spatial_review_session.py
```

Dans `anonymator/core/spatial_review_session.py` :
- renommer `class PdfReviewSession` en `class SpatialReviewSession` ;
- remplacer les imports de tête par :

```python
from anonymator.files.textlayer import PageText, PageScan, rects_for_entity
```

- remplacer l'unique appel `mapping.rects_for_entity(page_text, e)` par `rects_for_entity(page_text, e)` ;
- dans la docstring de classe, remplacer « État de revue d'un PDF » par « État de revue d'une source spatiale (PDF ou image) ».

- [ ] **Step 4 : Recréer `pdf_review_session.py` comme alias**

Créer `anonymator/core/pdf_review_session.py` :

```python
# anonymator/core/pdf_review_session.py
"""Compatibilité : la session de revue spatiale est générique (PDF ou image)
et vit dans anonymator.core.spatial_review_session."""
from anonymator.core.spatial_review_session import (  # noqa: F401
    SpatialReviewSession, Rect)

PdfReviewSession = SpatialReviewSession
```

- [ ] **Step 5 : Lancer toute la suite**

```bash
./.venv/Scripts/python -m pytest -q
```

Attendu : `728 passed, 1 deselected`.

- [ ] **Step 6 : Committer**

```bash
git add anonymator/core/spatial_review_session.py anonymator/core/pdf_review_session.py tests/test_spatial_review_session.py
git commit -m "refactor(session): PdfReviewSession devient SpatialReviewSession"
```

## Task 5 : `PdfCanvas` → `SpatialCanvas`

Le canvas accepte déjà un facteur de rendu (`set_page(png, zoom)`). Une image se charge avec `zoom=1.0`. Seuls le nom de la classe et celui du convertisseur de coordonnées portent une marque PDF.

**Files:**
- Create: `anonymator/ui/spatial_canvas.py`
- Modify: `anonymator/ui/pdf_canvas.py` (devient un alias)
- Test: `tests/test_spatial_canvas.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_spatial_canvas.py` :

```python
from anonymator.ui.spatial_canvas import SpatialCanvas, scene_rect_to_source


def test_conversion_de_coordonnees_a_zoom_1():
    assert scene_rect_to_source(10.0, 20.0, 30.0, 40.0, 1.0) == (10.0, 20.0, 30.0, 40.0)


def test_conversion_normalise_l_ordre_des_coins():
    assert scene_rect_to_source(30.0, 40.0, 10.0, 20.0, 1.0) == (10.0, 20.0, 30.0, 40.0)


def test_pdf_canvas_reste_un_alias():
    from anonymator.ui.pdf_canvas import PdfCanvas
    assert PdfCanvas is SpatialCanvas
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

```bash
./.venv/Scripts/python -m pytest tests/test_spatial_canvas.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.ui.spatial_canvas'`.

- [ ] **Step 3 : Déplacer et renommer**

```bash
git mv anonymator/ui/pdf_canvas.py anonymator/ui/spatial_canvas.py
```

Dans `anonymator/ui/spatial_canvas.py` :
- renommer `def scene_rect_to_points` en `def scene_rect_to_source` (son paramètre `zoom` et son corps ne changent pas) ;
- renommer `class PdfCanvas` en `class SpatialCanvas` ;
- mettre à jour l'unique appel dans `_finish_manual`.

- [ ] **Step 4 : Recréer `pdf_canvas.py` comme alias**

Créer `anonymator/ui/pdf_canvas.py` :

```python
# anonymator/ui/pdf_canvas.py
"""Compatibilité : le canevas est générique (page PDF rendue ou image) et vit
dans anonymator.ui.spatial_canvas."""
from anonymator.ui.spatial_canvas import (  # noqa: F401
    SpatialCanvas, scene_rect_to_source, Rect)

PdfCanvas = SpatialCanvas
scene_rect_to_points = scene_rect_to_source
```

- [ ] **Step 5 : Corriger l'import de l'écran PDF**

Dans `anonymator/ui/pdf_screen.py`, remplacer l'import de `PdfCanvas` par :

```python
from anonymator.ui.spatial_canvas import SpatialCanvas
```

et remplacer l'unique instanciation `PdfCanvas()` par `SpatialCanvas()`.

- [ ] **Step 6 : Lancer toute la suite**

```bash
./.venv/Scripts/python -m pytest -q
```

Attendu : `731 passed, 1 deselected`.

- [ ] **Step 7 : Committer**

```bash
git add anonymator/ui/spatial_canvas.py anonymator/ui/pdf_canvas.py anonymator/ui/pdf_screen.py tests/test_spatial_canvas.py
git commit -m "refactor(ui): PdfCanvas devient SpatialCanvas"
```

---

# PHASE 2 — Socle image (hors ligne, avec `FakeOcr`)

## Task 6 : Protocole `OcrEngine` et `FakeOcr`

Calqué sur `anonymator/ner.py` : un protocole, un *fake* pour les tests, l'implémentation réelle plus tard (tâche 12) à import paresseux.

**Files:**
- Create: `anonymator/files/image/__init__.py` (vide pour l'instant, complété en tâche 10)
- Create: `anonymator/files/image/ocr.py`
- Test: `tests/test_image_ocr.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_image_ocr.py` :

```python
from PIL import Image
from anonymator.files.image.ocr import OcrBox, FakeOcr, NullOcr


def _img():
    return Image.new("RGB", (100, 50), (255, 255, 255))


def test_fake_ocr_rend_les_boites_fournies():
    boxes = [OcrBox("Jean", (0.0, 0.0, 10.0, 5.0), 0.9)]
    assert FakeOcr(boxes).read(_img()) == boxes


def test_null_ocr_ne_rend_rien():
    assert NullOcr().read(_img()) == []


def test_ocr_box_expose_un_rectangle_englobant():
    quad = [[10, 4], [30, 2], [31, 12], [11, 14]]
    box = OcrBox.from_quad("Dupont", quad, 0.8)
    assert box.rect == (10.0, 2.0, 31.0, 14.0)
    assert box.text == "Dupont"
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

```bash
./.venv/Scripts/python -m pytest tests/test_image_ocr.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.files.image'`.

- [ ] **Step 3 : Créer le paquet et le module**

```bash
mkdir -p anonymator/files/image
touch anonymator/files/image/__init__.py
```

Créer `anonymator/files/image/ocr.py` :

```python
# anonymator/files/image/ocr.py
"""Moteur OCR derrière un protocole, sur le modèle de anonymator/ner.py.

Le protocole permet trois choses : tester toute la chaîne hors ligne avec
FakeOcr, offrir un mode dégradé avec NullOcr (tracé manuel seul), et changer de
moteur sans toucher au reste du code."""
from dataclasses import dataclass
from typing import Protocol

Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class OcrBox:
    text: str
    rect: Rect          # rectangle englobant, en pixels de l'image source
    confidence: float

    @classmethod
    def from_quad(cls, text: str, quad, confidence: float) -> "OcrBox":
        """Réduit un quadrilatère (4 coins) à son rectangle englobant.

        Un englobant déborde toujours un peu : en caviardage, déborder est sûr,
        rogner ne l'est pas."""
        xs = [float(p[0]) for p in quad]
        ys = [float(p[1]) for p in quad]
        return cls(text, (min(xs), min(ys), max(xs), max(ys)), float(confidence))


class OcrEngine(Protocol):
    def read(self, image) -> list[OcrBox]: ...


class FakeOcr:
    """Moteur déterministe pour les tests : rend les boîtes qu'on lui donne."""
    def __init__(self, boxes: list[OcrBox]):
        self._boxes = list(boxes)

    def read(self, image) -> list[OcrBox]:
        return list(self._boxes)


class NullOcr:
    """Moteur vide : aucune lecture. Sert le mode dégradé (dépendance OCR
    absente) — le tracé manuel de zones reste disponible."""
    def read(self, image) -> list[OcrBox]:
        return []
```

- [ ] **Step 4 : Lancer le test, vérifier qu'il passe**

```bash
./.venv/Scripts/python -m pytest tests/test_image_ocr.py -q
```

Attendu : `3 passed`.

- [ ] **Step 5 : Committer**

```bash
git add anonymator/files/image/ tests/test_image_ocr.py
git commit -m "feat(image): protocole OcrEngine, FakeOcr et NullOcr"
```

## Task 7 : `layout.py` — ordre de lecture

C'est le seul module délicat du lot. Il transforme une liste de boîtes en désordre en un texte plat cohérent, sur lequel GLiNER travaillera.

**Files:**
- Create: `anonymator/files/image/layout.py`
- Test: `tests/test_image_layout.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `tests/test_image_layout.py` :

```python
from anonymator.files.image.layout import page_from_boxes
from anonymator.files.image.ocr import OcrBox


def test_boites_en_desordre_sont_remises_en_ordre_de_lecture():
    boxes = [
        OcrBox("monde", (60.0, 0.0, 110.0, 20.0), 0.9),
        OcrBox("suite", (0.0, 40.0, 50.0, 60.0), 0.9),
        OcrBox("Bonjour", (0.0, 0.0, 50.0, 20.0), 0.9),
    ]
    page = page_from_boxes(boxes)
    assert page.text == "Bonjour monde\nsuite"


def test_les_offsets_pointent_sur_le_bon_mot():
    boxes = [
        OcrBox("Jean", (0.0, 0.0, 40.0, 20.0), 0.9),
        OcrBox("Dupont", (45.0, 0.0, 100.0, 20.0), 0.9),
    ]
    page = page_from_boxes(boxes)
    assert page.text == "Jean Dupont"
    w = page.words[1]
    assert page.text[w.char_start:w.char_end] == "Dupont"
    assert w.rect == (45.0, 0.0, 100.0, 20.0)


def test_deux_lignes_sont_separees_par_un_saut_de_ligne():
    boxes = [
        OcrBox("haut", (0.0, 0.0, 40.0, 20.0), 0.9),
        OcrBox("bas", (0.0, 100.0, 40.0, 120.0), 0.9),
    ]
    assert page_from_boxes(boxes).text == "haut\nbas"


def test_boites_de_hauteurs_inegales_sur_la_meme_ligne_restent_groupees():
    # Un titre en gras et un mot plus petit alignés : chevauchement vertical
    # majoritaire -> même ligne.
    boxes = [
        OcrBox("TOTAL", (0.0, 0.0, 60.0, 30.0), 0.9),
        OcrBox("42", (70.0, 5.0, 90.0, 25.0), 0.9),
    ]
    assert page_from_boxes(boxes).text == "TOTAL 42"


def test_page_vide():
    page = page_from_boxes([])
    assert page.text == ""
    assert page.words == []
    assert page.page_index == 0
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_layout.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.files.image.layout'`.

- [ ] **Step 3 : Implémenter**

Créer `anonymator/files/image/layout.py` :

```python
# anonymator/files/image/layout.py
"""Reconstruit une couche de texte positionné depuis des boîtes OCR.

L'OCR rend des boîtes sans ordre garanti. GLiNER, lui, se nourrit du contexte :
la qualité de ce texte plat conditionne directement la détection des noms. On
regroupe donc les boîtes en lignes, puis on lit gauche→droite, haut→bas —
exactement ce que fait extract_page() côté PDF."""
from anonymator.files.image.ocr import OcrBox
from anonymator.files.textlayer import PageText, WordBox

# Deux boîtes appartiennent à la même ligne si leur chevauchement vertical
# dépasse cette fraction de la plus petite des deux hauteurs. Assez bas pour
# tolérer des tailles de police inégales, assez haut pour ne pas fusionner
# deux lignes voisines serrées.
_LINE_OVERLAP_RATIO = 0.5


def _same_line(a: OcrBox, b: OcrBox) -> bool:
    top = max(a.rect[1], b.rect[1])
    bottom = min(a.rect[3], b.rect[3])
    overlap = bottom - top
    if overlap <= 0:
        return False
    shortest = min(a.rect[3] - a.rect[1], b.rect[3] - b.rect[1])
    return shortest > 0 and overlap / shortest >= _LINE_OVERLAP_RATIO


def _group_lines(boxes: list[OcrBox]) -> list[list[OcrBox]]:
    """Regroupe en lignes, puis trie chaque ligne gauche→droite et les lignes
    haut→bas."""
    lines: list[list[OcrBox]] = []
    for box in sorted(boxes, key=lambda b: (b.rect[1], b.rect[0])):
        for line in lines:
            if _same_line(line[0], box):
                line.append(box)
                break
        else:
            lines.append([box])
    for line in lines:
        line.sort(key=lambda b: b.rect[0])
    lines.sort(key=lambda line: min(b.rect[1] for b in line))
    return lines


def page_from_boxes(boxes: list[OcrBox], page_index: int = 0) -> PageText:
    """Texte plat en ordre de lecture + une WordBox par boîte OCR."""
    parts: list[str] = []
    words: list[WordBox] = []
    cursor = 0
    for line_no, line in enumerate(_group_lines(boxes)):
        for word_no, box in enumerate(line):
            if line_no or word_no:
                parts.append("\n" if word_no == 0 else " ")
                cursor += 1
            start = cursor
            parts.append(box.text)
            cursor += len(box.text)
            words.append(WordBox(box.text, box.rect, start, cursor))
    return PageText(page_index, "".join(parts), words)
```

- [ ] **Step 4 : Lancer les tests, vérifier qu'ils passent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_layout.py -q
```

Attendu : `5 passed`.

- [ ] **Step 5 : Committer**

```bash
git add anonymator/files/image/layout.py tests/test_image_layout.py
git commit -m "feat(image): reconstruction de l'ordre de lecture depuis les boites OCR"
```

## Task 8 : `image_io.py` — décodage, orientation EXIF, purge

**Files:**
- Create: `anonymator/files/image/image_io.py`
- Test: `tests/test_image_io.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `tests/test_image_io.py` :

```python
import pytest
from PIL import Image
from anonymator.files.image import image_io


def test_formats_supportes_contient_les_extensions_attendues():
    assert ".png" in image_io.SUPPORTED_SUFFIXES
    assert ".jpg" in image_io.SUPPORTED_SUFFIXES
    assert ".heic" not in image_io.SUPPORTED_SUFFIXES


def test_format_non_supporte_leve_une_erreur_metier(tmp_path):
    p = tmp_path / "photo.heic"
    p.write_bytes(b"pas une image")
    with pytest.raises(image_io.UnsupportedImageFormat):
        image_io.load_image(p)


def test_fichier_corrompu_leve_une_erreur_metier(tmp_path):
    p = tmp_path / "casse.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n corrompu")
    with pytest.raises(image_io.CorruptImageError):
        image_io.load_image(p)


def test_chargement_rend_une_image_rgb(tmp_path):
    p = tmp_path / "gris.png"
    Image.new("L", (10, 10), 128).save(p)
    assert image_io.load_image(p).mode == "RGB"


def test_orientation_exif_est_appliquee_avant_la_purge(tmp_path):
    # Orientation=6 => rotation de 90° ; une image 20x10 doit ressortir 10x20.
    p = tmp_path / "tournee.jpg"
    img = Image.new("RGB", (20, 10), (10, 20, 30))
    exif = img.getexif()
    exif[274] = 6                      # 274 = tag Orientation
    img.save(p, exif=exif)
    loaded = image_io.load_image(p)
    assert loaded.size == (10, 20)


def test_une_image_animee_est_reduite_a_sa_premiere_vue(tmp_path):
    p = tmp_path / "anime.webp"
    v1 = Image.new("RGB", (10, 10), (255, 0, 0))
    v2 = Image.new("RGB", (10, 10), (0, 0, 255))
    v1.save(p, save_all=True, append_images=[v2], duration=100, loop=0)
    loaded = image_io.load_image(p)
    assert loaded.size == (10, 10)
    assert loaded.getpixel((5, 5)) == (255, 0, 0)


def test_enregistrement_ne_conserve_aucune_metadonnee(tmp_path):
    src = tmp_path / "avec_exif.jpg"
    img = Image.new("RGB", (10, 10), (1, 2, 3))
    exif = img.getexif()
    exif[271] = "MarqueAppareil"       # 271 = Make
    img.save(src, exif=exif)
    out = tmp_path / "sortie.jpg"
    image_io.save_image(image_io.load_image(src), out)
    assert dict(Image.open(out).getexif()) == {}
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_io.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.files.image.image_io'`.

- [ ] **Step 3 : Implémenter**

Créer `anonymator/files/image/image_io.py` :

```python
# anonymator/files/image/image_io.py
"""Entrées/sorties image : décodage, orientation, purge des métadonnées.

Ce module ne connaît ni le NER ni le référentiel — uniquement les pixels."""
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

SUPPORTED_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"})


class UnsupportedImageFormat(Exception):
    pass


class CorruptImageError(Exception):
    pass


def load_image(path: Path) -> Image.Image:
    """Décode l'image, applique l'orientation EXIF et normalise en RGB.

    L'orientation est APPLIQUÉE ici, avant toute purge : purger d'abord ferait
    ressortir l'image tournée, puisque le visualiseur n'aurait plus le tag pour
    la redresser."""
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise UnsupportedImageFormat(
            f"Format non supporté : {path.suffix}. "
            f"Formats acceptés : {', '.join(sorted(SUPPORTED_SUFFIXES))}")
    try:
        img = Image.open(path)
        img.load()
    except UnidentifiedImageError as exc:
        raise CorruptImageError("Image illisible ou endommagée") from exc
    except OSError as exc:
        raise CorruptImageError("Image illisible ou endommagée") from exc
    return ImageOps.exif_transpose(img).convert("RGB")


def strip_metadata(img: Image.Image) -> Image.Image:
    """Rend une copie ne portant que les pixels : ni EXIF, ni ICC, ni commentaire.

    On reconstruit l'image depuis son tampon brut — recopier l'objet Pillow
    traînerait son dictionnaire `info`."""
    return Image.frombytes(img.mode, img.size, img.tobytes())


def save_image(img: Image.Image, out_path: Path) -> Path:
    """Écrit l'image sans aucune métadonnée. L'original n'est jamais modifié."""
    clean = strip_metadata(img)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    clean.save(out_path)
    return out_path
```

- [ ] **Step 4 : Lancer les tests, vérifier qu'ils passent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_io.py -q
```

Attendu : `7 passed`.

- [ ] **Step 5 : Committer**

```bash
git add anonymator/files/image/image_io.py tests/test_image_io.py
git commit -m "feat(image): decodage, orientation EXIF appliquee et purge des metadonnees"
```

## Task 9 : `redact.py` — le caviardage détruit vraiment

**Files:**
- Create: `anonymator/files/image/redact.py`
- Test: `tests/test_image_redact.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `tests/test_image_redact.py` :

```python
from PIL import Image
from anonymator.files.image.redact import redact_image


def test_la_zone_caviardee_est_uniforme():
    img = Image.new("RGB", (100, 50), (255, 255, 255))
    img.putpixel((20, 20), (255, 0, 0))     # un pixel à détruire
    out = redact_image(img, [(10.0, 10.0, 40.0, 40.0)])
    zone = out.crop((10, 10, 40, 40))
    assert zone.getextrema() == ((0, 0), (0, 0), (0, 0))


def test_le_reste_de_l_image_est_intact():
    img = Image.new("RGB", (100, 50), (255, 255, 255))
    out = redact_image(img, [(10.0, 10.0, 40.0, 40.0)])
    assert out.getpixel((80, 25)) == (255, 255, 255)


def test_l_image_source_n_est_pas_modifiee():
    img = Image.new("RGB", (100, 50), (255, 255, 255))
    redact_image(img, [(10.0, 10.0, 40.0, 40.0)])
    assert img.getpixel((20, 20)) == (255, 255, 255)


def test_un_rectangle_deborde_est_ramene_dans_l_image():
    img = Image.new("RGB", (100, 50), (255, 255, 255))
    out = redact_image(img, [(-20.0, -20.0, 500.0, 500.0)])
    assert out.getextrema() == ((0, 0), (0, 0), (0, 0))


def test_aucun_rectangle_rend_une_copie_identique():
    img = Image.new("RGB", (10, 10), (7, 8, 9))
    assert list(redact_image(img, []).getdata()) == list(img.getdata())
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_redact.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.files.image.redact'`.

- [ ] **Step 3 : Implémenter**

Créer `anonymator/files/image/redact.py` :

```python
# anonymator/files/image/redact.py
"""Caviardage destructif d'une image.

Les pixels sont ÉCRASÉS dans le tampon, jamais recouverts par un calque : une
forme dessinée par-dessus se retire, un pixel noirci ne se retrouve pas."""
from PIL import Image, ImageDraw

Rect = tuple[float, float, float, float]

FILL = (0, 0, 0)


def redact_image(img: Image.Image, rects: list[Rect]) -> Image.Image:
    """Rend une copie dont chaque rectangle est écrasé en noir opaque.
    L'image reçue n'est pas modifiée."""
    out = img.convert("RGB").copy()
    if not rects:
        return out
    draw = ImageDraw.Draw(out)
    width, height = out.size
    for x0, y0, x1, y1 in rects:
        left = max(0, int(min(x0, x1)))
        top = max(0, int(min(y0, y1)))
        right = min(width, int(round(max(x0, x1))))
        bottom = min(height, int(round(max(y0, y1))))
        if right > left and bottom > top:
            draw.rectangle([left, top, right - 1, bottom - 1], fill=FILL)
    return out
```

- [ ] **Step 4 : Lancer les tests, vérifier qu'ils passent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_redact.py -q
```

Attendu : `5 passed`.

- [ ] **Step 5 : Committer**

```bash
git add anonymator/files/image/redact.py tests/test_image_redact.py
git commit -m "feat(image): caviardage destructif par ecrasement des pixels"
```

## Task 10 : Périmètre image et registre unifié

**Files:**
- Modify: `anonymator/files/image/__init__.py`
- Create: `anonymator/files/coverage.py`
- Modify: `anonymator/ui/components/perimetre_card.py`
- Test: `tests/test_image_coverage.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `tests/test_image_coverage.py` :

```python
from anonymator.files import coverage
from anonymator.files.image import COVERAGE_IMAGE


def test_le_registre_expose_les_formats_documentaires_et_l_image():
    assert set(coverage.COVERAGE_BY_FORMAT) >= {"docx", "pptx", "xlsx", "image"}


def test_le_perimetre_image_annonce_ses_limites():
    non = " ".join(COVERAGE_IMAGE["non_traite"]).lower()
    assert "manuscrit" in non
    assert "visage" in non


def test_le_perimetre_image_ne_promet_pas_l_exhaustivite():
    traite = " ".join(COVERAGE_IMAGE["traite"]).lower()
    assert "propos" in traite        # « proposé à la validation »
    assert "analysé" not in traite


def test_la_carte_perimetre_accepte_le_format_image():
    from anonymator.ui.components.perimetre_card import PerimetreCard
    card = PerimetreCard("image")
    assert "manuscrit" in card.rendered_text().lower()
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_coverage.py -q
```

Attendu : `ImportError: cannot import name 'COVERAGE_IMAGE'`.

- [ ] **Step 3 : Écrire le périmètre**

Remplacer le contenu de `anonymator/files/image/__init__.py` par :

```python
# Périmètre de l'anonymisation d'une image — source de vérité unique partagée
# entre l'UI (PerimetreCard), la documentation et les tests.
#
# Même règle que pour les documents : un élément ne figure en « traité » que si
# un test le vérifie. Ici s'ajoute une contrainte propre à l'OCR — il rate. La
# formulation dit donc que l'application PROPOSE et que l'utilisateur VALIDE ;
# elle ne dit jamais que l'image « a été analysée ».

COVERAGE_IMAGE = {
    "traite": [
        "Texte lu par la reconnaissance de caractères, proposé à votre validation",
        "Zones que vous tracez vous-même à la souris",
        "Destruction réelle des pixels (la zone noircie est irrécupérable)",
        "Purge des métadonnées EXIF (position GPS, appareil, auteur, date)",
    ],
    "non_traite": [
        "Texte que la reconnaissance n'a pas lu : écriture manuscrite, "
        "caractères trop petits, flou, contre-jour",
        "Visages, plaques d'immatriculation, signatures manuscrites",
        "Texte dans une écriture non latine",
        "Codes-barres et QR codes",
    ],
}
```

- [ ] **Step 4 : Créer le registre unifié**

Créer `anonymator/files/coverage.py` :

```python
# anonymator/files/coverage.py
"""Registre des périmètres par format.

Chaque famille de formats définit son propre périmètre au plus près de son
code ; ce module les rassemble pour l'UI, qui n'a pas à savoir d'où ils
viennent."""
from anonymator.files import ooxml
from anonymator.files.image import COVERAGE_IMAGE

COVERAGE_BY_FORMAT = {
    **ooxml.COVERAGE_BY_FORMAT,
    "image": COVERAGE_IMAGE,
}
```

- [ ] **Step 5 : Brancher la carte sur le registre**

Dans `anonymator/ui/components/perimetre_card.py` :
- remplacer `from anonymator.files import ooxml` par `from anonymator.files import coverage as coverage_registry` ;
- dans `set_format`, remplacer la ligne de résolution par :

```python
        coverage = coverage_registry.COVERAGE_BY_FORMAT.get(
            fmt, coverage_registry.COVERAGE_BY_FORMAT["docx"])
```

- [ ] **Step 6 : Lancer toute la suite**

```bash
./.venv/Scripts/python -m pytest -q
```

Attendu : `755 passed, 1 deselected` (les tests existants de `PerimetreCard` doivent rester verts).

- [ ] **Step 7 : Committer**

```bash
git add anonymator/files/image/__init__.py anonymator/files/coverage.py anonymator/ui/components/perimetre_card.py tests/test_image_coverage.py
git commit -m "feat(image): perimetre image et registre de couverture unifie"
```

## Task 11 : Orchestration — `scan_image` et `anonymize_image_redact`

Miroir de `scan_pdf` / `anonymize_pdf_redact`. Ces deux fonctions vivent dans `image_io.py`, comme leurs homologues vivent dans `pdf_io.py`.

**Files:**
- Modify: `anonymator/files/image/image_io.py`
- Test: `tests/test_image_scan.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `tests/test_image_scan.py` :

```python
from datetime import datetime

from PIL import Image

from anonymator.files.image import image_io
from anonymator.files.image.ocr import FakeOcr, OcrBox
from anonymator.ner import FakeNer
from anonymator.referential import Referential


def _image(tmp_path):
    p = tmp_path / "capture.png"
    Image.new("RGB", (200, 100), (255, 255, 255)).save(p)
    return p


def _ocr():
    return FakeOcr([
        OcrBox("Contact", (0.0, 0.0, 50.0, 20.0), 0.9),
        OcrBox("jean@exemple.fr", (55.0, 0.0, 180.0, 20.0), 0.9),
    ])


def test_scan_image_rend_une_page_unique_avec_ses_entites(tmp_path):
    pages = image_io.scan_image(_image(tmp_path), _ocr(), FakeNer({}), Referential.load_default())
    assert len(pages) == 1
    page = pages[0]
    assert page.page_index == 0
    assert page.text == "Contact jean@exemple.fr"
    assert [e.type for e in page.entities] == ["EMAIL"]


def test_les_rectangles_de_l_entite_pointent_sur_la_bonne_boite(tmp_path):
    from anonymator.files.textlayer import PageText, rects_for_entity
    page = image_io.scan_image(_image(tmp_path), _ocr(), FakeNer({}), Referential.load_default())[0]
    pt = PageText(0, page.text, page.words)
    assert rects_for_entity(pt, page.entities[0]) == [(55.0, 0.0, 180.0, 20.0)]


def test_anonymize_image_redact_ecrit_un_fichier_horodate(tmp_path):
    src = _image(tmp_path)
    out_dir = tmp_path / "sortie"
    out = image_io.anonymize_image_redact(
        src, [(0.0, 0.0, 50.0, 20.0)], out_dir, datetime(2026, 9, 23, 14, 30, 0))
    assert out.name == "capture_ano_20260923143000.png"
    assert out.parent == out_dir


def test_le_fichier_de_sortie_a_bien_ses_pixels_detruits(tmp_path):
    src = _image(tmp_path)
    out = image_io.anonymize_image_redact(
        src, [(10.0, 10.0, 40.0, 40.0)], tmp_path / "s", datetime(2026, 9, 23))
    assert Image.open(out).crop((10, 10, 40, 40)).getextrema() == (
        (0, 0), (0, 0), (0, 0))


def test_l_original_n_est_jamais_modifie(tmp_path):
    src = _image(tmp_path)
    avant = src.read_bytes()
    image_io.anonymize_image_redact(
        src, [(0.0, 0.0, 200.0, 100.0)], tmp_path / "s", datetime(2026, 9, 23))
    assert src.read_bytes() == avant
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_scan.py -q
```

Attendu : `AttributeError: module 'anonymator.files.image.image_io' has no attribute 'scan_image'`.

- [ ] **Step 3 : Implémenter**

Ajouter à la fin de `anonymator/files/image/image_io.py` — et compléter ses imports de tête :

```python
from datetime import datetime

from anonymator.core.chunking import detect_long
from anonymator.files.image.layout import page_from_boxes
from anonymator.files.image.redact import redact_image
from anonymator.files.textlayer import PageScan
from anonymator.ner import NerDetector
from anonymator.output_naming import anonymized_path
from anonymator.referential import Referential

Rect = tuple[float, float, float, float]
```

```python
def scan_image(path: Path, ocr, ner: NerDetector,
               ref: Referential) -> list[PageScan]:
    """Lit l'image, reconstruit sa couche de texte et y détecte les entités.

    Rend une liste d'une seule page, pour que la session de revue spatiale —
    écrite pour le PDF multi-pages — s'applique sans cas particulier.

    Lève UnsupportedImageFormat / CorruptImageError."""
    img = load_image(path)
    page = page_from_boxes(ocr.read(img))
    entities = detect_long(page.text, ner, ref)
    return [PageScan(page.page_index, page.text, page.words, entities)]


def anonymize_image_redact(path: Path, rects: list[Rect], output_dir: Path,
                           when: datetime) -> Path:
    """Caviarde les rectangles retenus, purge les métadonnées, enregistre.
    L'original n'est jamais modifié."""
    img = load_image(path)
    out = anonymized_path(path, output_dir, when)
    return save_image(redact_image(img, rects), out)
```

- [ ] **Step 4 : Lancer les tests, vérifier qu'ils passent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_scan.py -q
```

Attendu : `5 passed`.

- [ ] **Step 5 : Lancer toute la suite**

```bash
./.venv/Scripts/python -m pytest -q
```

Attendu : `760 passed, 1 deselected`.

- [ ] **Step 6 : Committer**

```bash
git add anonymator/files/image/image_io.py tests/test_image_scan.py
git commit -m "feat(image): orchestration scan_image et anonymize_image_redact"
```

---

# PHASE 3 — Moteur réel

## Task 12 : `RapidOcrEngine` avec modèles verrouillés

**Files:**
- Modify: `anonymator/files/image/ocr.py`
- Test: `tests/test_image_ocr_rapid.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `tests/test_image_ocr_rapid.py` :

```python
import pytest
from PIL import Image

from anonymator.files.image import ocr as ocr_mod


class _FausseSortie:
    boxes = [[[10, 4], [30, 2], [31, 12], [11, 14]]]
    txts = ("Dupont",)
    scores = (0.87,)


class _FauxMoteur:
    def __init__(self, *a, **k):
        self.params = k.get("params")

    def __call__(self, arr):
        return _FausseSortie()


def test_l_adaptateur_convertit_les_quadrilateres_en_rectangles(monkeypatch):
    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _FauxMoteur)
    engine = ocr_mod.RapidOcrEngine()
    boxes = engine.read(Image.new("RGB", (50, 20), (255, 255, 255)))
    assert len(boxes) == 1
    assert boxes[0].text == "Dupont"
    assert boxes[0].rect == (10.0, 2.0, 31.0, 14.0)
    assert boxes[0].confidence == pytest.approx(0.87)


def test_une_sortie_vide_ne_casse_rien(monkeypatch):
    class _Vide:
        boxes = None
        txts = None
        scores = None

    class _Moteur(_FauxMoteur):
        def __call__(self, arr):
            return _Vide()

    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _Moteur)
    assert ocr_mod.RapidOcrEngine().read(
        Image.new("RGB", (10, 10), (0, 0, 0))) == []


def test_une_grande_image_est_reduite_mais_les_boites_reviennent_a_l_echelle(
        monkeypatch):
    """Une image de 8000 px est réduite avant l'OCR : les coordonnées rendues
    doivent être celles de l'IMAGE D'ORIGINE, sinon le caviardage tombe à côté."""
    vues = {}

    class _Moteur(_FauxMoteur):
        def __call__(self, arr):
            vues["taille"] = (arr.shape[1], arr.shape[0])
            return _FausseSortie()

    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _Moteur)
    engine = ocr_mod.RapidOcrEngine()
    boxes = engine.read(Image.new("RGB", (8000, 4000), (255, 255, 255)))
    facteur = 8000 / ocr_mod.MAX_SIDE
    assert vues["taille"] == (ocr_mod.MAX_SIDE, ocr_mod.MAX_SIDE // 2)
    # La boîte fictive (10,2)-(31,14) doit être remise a l'echelle d'origine.
    assert boxes[0].rect == pytest.approx(
        (10 * facteur, 2 * facteur, 31 * facteur, 14 * facteur))


def test_une_petite_image_n_est_pas_redimensionnee(monkeypatch):
    vues = {}

    class _Moteur(_FauxMoteur):
        def __call__(self, arr):
            vues["taille"] = (arr.shape[1], arr.shape[0])
            return _FausseSortie()

    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _Moteur)
    boxes = ocr_mod.RapidOcrEngine().read(Image.new("RGB", (50, 20), (0, 0, 0)))
    assert vues["taille"] == (50, 20)
    assert boxes[0].rect == (10.0, 2.0, 31.0, 14.0)


def test_les_modeles_sont_verrouilles_sur_les_fichiers_embarques(monkeypatch):
    captured = {}

    class _Moteur(_FauxMoteur):
        def __init__(self, *a, **k):
            captured.update(k.get("params") or {})

    monkeypatch.setattr(ocr_mod, "_load_rapidocr", lambda: _Moteur)
    ocr_mod.RapidOcrEngine()
    for key in ("Det.model_path", "Rec.model_path", "Cls.model_path"):
        assert key in captured, f"{key} doit etre impose"
        assert str(captured[key]).endswith(".onnx")
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_ocr_rapid.py -q
```

Attendu : `AttributeError: module 'anonymator.files.image.ocr' has no attribute '_load_rapidocr'`.

- [ ] **Step 3 : Implémenter**

Ajouter à la fin de `anonymator/files/image/ocr.py` :

```python
def _load_rapidocr():
    """Import paresseux : charger RapidOCR tire onnxruntime et 32 Mo de modèles.
    Isolé dans une fonction pour être remplaçable en test."""
    from rapidocr import RapidOCR
    return RapidOCR


def _bundled_model_paths() -> dict[str, str]:
    """Chemins des trois modèles livrés dans la wheel.

    On les impose explicitement : laissés à null, les paramètres Det/Rec/Cls
    font résoudre le modèle par default_models.yaml, qui pointe vers un
    hébergeur externe. L'application promet « aucun appel réseau en usage
    normal » — ce verrou est ce qui tient la promesse."""
    import rapidocr

    models = Path(rapidocr.__file__).parent / "models"
    return {
        "Det.model_path": str(models / "PP-OCRv6_det_small.onnx"),
        "Rec.model_path": str(models / "PP-OCRv6_rec_small.onnx"),
        "Cls.model_path": str(models / "ch_ppocr_mobile_v2.0_cls_mobile.onnx"),
    }


# Côté le plus long au-delà duquel on réduit l'image avant l'OCR. RapidOCR
# redimensionne déjà en interne (Global.max_side_len), mais sans contrat
# documenté sur le remappage des boîtes : on maîtrise donc l'échelle nous-mêmes,
# et on remet les coordonnées à l'échelle de l'image d'origine. Une erreur ici
# ne se verrait pas en détection — elle ferait caviarder à côté.
MAX_SIDE = 2000


class RapidOcrEngine:
    """Adaptateur autour de RapidOCR (ONNX). Importé paresseusement."""

    def __init__(self, text_score: float = 0.5):
        params = _bundled_model_paths()
        params["Global.text_score"] = text_score
        self._engine = _load_rapidocr()(params=params)

    def read(self, image) -> list[OcrBox]:
        import numpy as np

        img = image.convert("RGB")
        scale = 1.0
        longest = max(img.size)
        if longest > MAX_SIDE:
            scale = longest / MAX_SIDE
            img = img.resize((max(1, round(img.width / scale)),
                              max(1, round(img.height / scale))))
        result = self._engine(np.array(img))
        quads = result.boxes if result.boxes is not None else []
        txts = result.txts or ()
        scores = result.scores or ()
        boxes = [OcrBox.from_quad(t, q, s)
                 for q, t, s in zip(quads, txts, scores)]
        if scale == 1.0:
            return boxes
        return [OcrBox(b.text,
                       tuple(v * scale for v in b.rect),
                       b.confidence)
                for b in boxes]
```

Compléter les imports de tête de `ocr.py` :

```python
from pathlib import Path
```

- [ ] **Step 4 : Lancer les tests, vérifier qu'ils passent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_ocr_rapid.py -q
```

Attendu : `5 passed`.

- [ ] **Step 5 : Committer**

```bash
git add anonymator/files/image/ocr.py tests/test_image_ocr_rapid.py
git commit -m "feat(image): adaptateur RapidOCR avec modeles embarques imposes"
```

## Task 13 : Le verrou réseau, prouvé

**Files:**
- Test: `tests/test_image_ocr_integration.py`
- Modify: `pyproject.toml` (déclarer le marqueur si absent)

- [ ] **Step 1 : Vérifier la déclaration du marqueur d'intégration**

```bash
grep -n "markers" pyproject.toml
```

Si `markers` n'est pas déclaré, ajouter à `pyproject.toml` :

```toml
[tool.pytest.ini_options]
markers = ["integration: nécessite les modèles réels (désélectionné par défaut)"]
addopts = "-m 'not integration'"
```

- [ ] **Step 2 : Écrire le test d'intégration**

Créer `tests/test_image_ocr_integration.py` :

```python
"""Tests du moteur OCR réel. Désélectionnés par défaut :
    ./.venv/Scripts/python -m pytest -m integration -q
"""
import socket

import pytest
from PIL import Image, ImageDraw

pytestmark = pytest.mark.integration


def _image_avec_texte(text: str) -> Image.Image:
    img = Image.new("RGB", (600, 120), (255, 255, 255))
    ImageDraw.Draw(img).text((20, 40), text, fill=(0, 0, 0))
    return img


def test_aucun_acces_reseau_pendant_un_ocr(monkeypatch):
    """Le socle promet « aucun appel réseau en usage normal ». On coupe la
    socket : si RapidOCR tente de télécharger un modèle, le test tombe."""
    def _interdit(*a, **k):
        raise AssertionError("acces reseau pendant l'OCR")

    monkeypatch.setattr(socket, "socket", _interdit)
    monkeypatch.setattr(socket, "create_connection", _interdit)

    from anonymator.files.image.ocr import RapidOcrEngine
    RapidOcrEngine().read(_image_avec_texte("Dupont"))


def test_les_accents_francais_sont_restitues():
    """Critère d'acceptation n°1 du banc de mesure (tâche 1), figé en test."""
    from anonymator.files.image.ocr import RapidOcrEngine
    boxes = RapidOcrEngine().read(_image_avec_texte("Eleonore Chateauneuf"))
    lu = " ".join(b.text for b in boxes)
    assert "leonore" in lu.lower()
```

> Le second test utilise une police par défaut sans accents garantis : il vérifie
> la lecture de base. La **preuve des accents** reste celle du banc de mesure de
> la tâche 1, sur de vraies images. Si le banc a montré un échec des accents et
> qu'un modèle `latin` a dû être vendorisé, remplacer ici le texte par
> `"Éléonore Châteauneuf"` et l'assertion par `assert "Éléonore" in lu`.

- [ ] **Step 3 : Lancer le test d'intégration**

```bash
./.venv/Scripts/python -m pytest -m integration tests/test_image_ocr_integration.py -q
```

Attendu : `2 passed`. **Si le premier test échoue**, c'est que le verrou de la tâche 12 ne tient pas : reprendre `_bundled_model_paths()` avant d'aller plus loin.

- [ ] **Step 4 : Vérifier que la suite normale les ignore**

```bash
./.venv/Scripts/python -m pytest -q
```

Attendu : `765 passed, 3 deselected`.

- [ ] **Step 5 : Committer**

```bash
git add tests/test_image_ocr_integration.py pyproject.toml
git commit -m "test(image): verrou reseau et lecture reelle, marques integration"
```

## Task 14 : Dépendances et licences

**Files:**
- Modify: `requirements.txt`
- Create: `third-party-licenses/Apache-2.0.txt`
- Modify: `third-party-licenses/README.md`
- Test: `tests/test_licences_tierces.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Créer `tests/test_licences_tierces.py` :

```python
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = RACINE / "third-party-licenses"


def test_le_texte_apache_est_fourni():
    texte = (DOSSIER / "Apache-2.0.txt").read_text(encoding="utf-8")
    assert "Apache License" in texte
    assert "Version 2.0" in texte


def test_le_tableau_cite_rapidocr():
    readme = (DOSSIER / "README.md").read_text(encoding="utf-8")
    assert "rapidocr" in readme.lower()


def test_la_redistribution_des_modeles_ocr_est_annoncee():
    readme = (DOSSIER / "README.md").read_text(encoding="utf-8")
    assert "PP-OCR" in readme
    assert "redistribu" in readme.lower()
```

- [ ] **Step 2 : Lancer le test, vérifier qu'il échoue**

```bash
./.venv/Scripts/python -m pytest tests/test_licences_tierces.py -q
```

Attendu : `FileNotFoundError` sur `Apache-2.0.txt`.

- [ ] **Step 3 : Ajouter les dépendances**

Ajouter à `requirements.txt`, après la ligne `pymupdf>=1.24` :

```
# OCR des images.
#
# ATTENTION opencv : rapidocr declare `opencv_python`, la variante complete, qui
# embarque ses propres plugins Qt et entre en conflit avec PySide6 sous
# PyInstaller. Les deux variantes ecrivent le MEME dossier cv2 et ne peuvent pas
# cohabiter. Un `pip install -r requirements.txt` installe donc la complete, puis
# la headless par-dessus : l'ordre du fichier ne suffit pas a garantir le
# resultat. Apres installation, verifier et corriger si besoin :
#     pip uninstall -y opencv_python
#     pip install --force-reinstall --no-deps opencv-python-headless
#     pip list | grep -i opencv     # doit ne montrer QUE opencv-python-headless
rapidocr>=3.9
opencv-python-headless>=4.10
```

> Vérifié le 2026-09-23 : RapidOCR fonctionne à l'identique avec le seul headless
> (5/5 lignes exactes sur le test des accents) et les 721 tests restent verts.

- [ ] **Step 4 : Récupérer le texte de la licence**

```bash
curl -sSL https://www.apache.org/licenses/LICENSE-2.0.txt -o third-party-licenses/Apache-2.0.txt
head -3 third-party-licenses/Apache-2.0.txt
```

Attendu : les premières lignes de l'Apache License, Version 2.0.

- [ ] **Step 5 : Compléter le tableau d'attribution**

Dans `third-party-licenses/README.md`, ajouter au tableau des licences permissives :

```markdown
| RapidOCR (`rapidocr`) | reconnaissance de texte dans les images | Apache-2.0 |
| OpenCV (`opencv-python-headless`) | traitement d'image pour l'OCR | Apache-2.0 |
| `shapely`, `pyclipper` | géométrie des boîtes de texte | BSD-3-Clause / MIT |
```

Puis, juste sous la note existante concernant GLiNER, ajouter :

```markdown
> **Les modèles OCR, eux, sont redistribués.** Contrairement au modèle GLiNER
> téléchargé au premier lancement, les trois modèles PP-OCR (PaddleOCR, Apache-2.0,
> ~32 Mo) sont embarqués dans l'exécutable. Le texte complet de leur licence est
> fourni dans [`Apache-2.0.txt`](Apache-2.0.txt).
```

- [ ] **Step 6 : Lancer les tests, vérifier qu'ils passent**

```bash
./.venv/Scripts/python -m pytest tests/test_licences_tierces.py -q
```

Attendu : `3 passed`.

- [ ] **Step 7 : Committer**

```bash
git add requirements.txt third-party-licenses/ tests/test_licences_tierces.py
git commit -m "chore(licences): rapidocr et modeles PP-OCR redistribues, texte Apache-2.0"
```

---

# PHASE 4 — Interface

## Task 15 : Worker d'analyse

**Files:**
- Create: `anonymator/ui/image_scan_worker.py`
- Test: `tests/test_image_scan_worker.py`

- [ ] **Step 1 : Lire le worker PDF pour en suivre exactement le patron**

```bash
cat anonymator/ui/pdf_scan_worker.py
```

- [ ] **Step 2 : Écrire le test qui échoue**

Créer `tests/test_image_scan_worker.py` :

```python
from PIL import Image

from anonymator.files.image.ocr import FakeOcr, OcrBox
from anonymator.ner import FakeNer
from anonymator.referential import Referential
from anonymator.ui.image_scan_worker import ImageScanWorker


def _image(tmp_path):
    p = tmp_path / "capture.png"
    Image.new("RGB", (200, 100), (255, 255, 255)).save(p)
    return p


def test_le_worker_emet_les_pages_analysees(tmp_path, qtbot):
    ocr = FakeOcr([OcrBox("jean@exemple.fr", (0.0, 0.0, 120.0, 20.0), 0.9)])
    w = ImageScanWorker(_image(tmp_path), ocr, FakeNer({}), Referential.load_default())
    with qtbot.waitSignal(w.scanned, timeout=5000) as blocker:
        w.run()
    pages = blocker.args[0]
    assert len(pages) == 1
    assert [e.type for e in pages[0].entities] == ["EMAIL"]


def test_le_worker_emet_une_erreur_metier_lisible(tmp_path, qtbot):
    p = tmp_path / "photo.heic"
    p.write_bytes(b"pas une image")
    w = ImageScanWorker(p, FakeOcr([]), FakeNer({}), Referential.load_default())
    with qtbot.waitSignal(w.failed, timeout=5000) as blocker:
        w.run()
    assert "Format non supporté" in blocker.args[0]
```

- [ ] **Step 3 : Lancer le test, vérifier qu'il échoue**

```bash
./.venv/Scripts/python -m pytest tests/test_image_scan_worker.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.ui.image_scan_worker'`.

- [ ] **Step 4 : Implémenter**

Créer `anonymator/ui/image_scan_worker.py` :

```python
# anonymator/ui/image_scan_worker.py
"""Analyse d'une image dans un fil séparé : l'OCR peut prendre plusieurs
secondes sur une photo, l'interface ne doit pas geler."""
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from anonymator.files.image import image_io


class ImageScanWorker(QObject):
    scanned = Signal(list)      # list[PageScan]
    failed = Signal(str)        # message métier, affichable tel quel

    def __init__(self, path: Path, ocr, ner, ref, parent=None):
        super().__init__(parent)
        self._path = Path(path)
        self._ocr = ocr
        self._ner = ner
        self._ref = ref

    def run(self) -> None:
        try:
            pages = image_io.scan_image(
                self._path, self._ocr, self._ner, self._ref)
        except (image_io.UnsupportedImageFormat,
                image_io.CorruptImageError) as exc:
            self.failed.emit(str(exc))
            return
        except Exception as exc:                       # noqa: BLE001
            self.failed.emit(f"Analyse impossible : {exc}")
            return
        self.scanned.emit(pages)
```

- [ ] **Step 5 : Lancer les tests, vérifier qu'ils passent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_scan_worker.py -q
```

Attendu : `2 passed`.

- [ ] **Step 6 : Committer**

```bash
git add anonymator/ui/image_scan_worker.py tests/test_image_scan_worker.py
git commit -m "feat(ui): worker d'analyse d'image"
```

## Task 16 : Écran Image

> **Indicateur de progression : décidé, à faire.** Le test du 2026-09-23 a mesuré
> **4,4 s** sur une image nette de 900 px de large, chargement des modèles compris —
> et une photo au téléphone est plusieurs fois plus grande. Au-delà d'une seconde
> sans retour visuel, l'utilisateur croit l'application figée. L'analyse doit donc
> tourner dans un **vrai QThread** (pas un `run()` appelé directement, qui gèlerait
> la fenêtre) et l'écran afficher un état d'attente explicite pendant ce temps.

**Files:**
- Create: `anonymator/ui/image_screen.py`
- Test: `tests/test_image_screen.py`

- [ ] **Step 1 : Lire l'écran PDF, qui sert de modèle**

```bash
cat anonymator/ui/pdf_screen.py
```

Points à reprendre tels quels : la construction du panneau latéral (`_build_side`), le branchement des cases à cocher (`_on_side_changed`), le bouton de tracé de zone (`_toggle_zone`, `_on_manual_rect`), les raccourcis de zoom. Points à **retirer** : la pagination (une image n'a qu'une page), le mode extraction `.txt` (hors périmètre), le rendu par `render_page_at`.

- [ ] **Step 2 : Écrire les tests qui échouent**

Créer `tests/test_image_screen.py` :

```python
from datetime import datetime

from PIL import Image

from anonymator.files.image.ocr import FakeOcr, OcrBox
from anonymator.ner import FakeNer
from anonymator.referential import Referential
from anonymator.ui.image_screen import ImageScreen


class _Loader:
    ner = FakeNer({})
    available = True


def _ecran(qtbot):
    screen = ImageScreen(Referential.load_default(), _Loader(), prefs=None, on_back=lambda: None)
    qtbot.addWidget(screen)
    return screen


def _image(tmp_path):
    p = tmp_path / "capture.png"
    Image.new("RGB", (200, 100), (255, 255, 255)).save(p)
    return p


def test_l_ecran_affiche_la_carte_perimetre_image(qtbot):
    assert "manuscrit" in _ecran(qtbot).perimetre.rendered_text().lower()


def test_apres_analyse_les_entites_sont_listees(qtbot, tmp_path):
    screen = _ecran(qtbot)
    screen.ocr = FakeOcr([OcrBox("jean@exemple.fr", (0.0, 0.0, 120.0, 20.0), 0.9)])
    screen.load_path(str(_image(tmp_path)))
    screen.analyze()
    qtbot.waitUntil(lambda: screen.session is not None, timeout=5000)
    assert screen.session.types() == ["EMAIL"]


def test_une_zone_tracee_a_la_main_est_retenue(qtbot, tmp_path):
    screen = _ecran(qtbot)
    screen.ocr = FakeOcr([])
    screen.load_path(str(_image(tmp_path)))
    screen.analyze()
    qtbot.waitUntil(lambda: screen.session is not None, timeout=5000)
    screen._on_manual_rect((5.0, 5.0, 25.0, 25.0))
    assert screen.session.manual_rects(0) == [(5.0, 5.0, 25.0, 25.0)]


def test_l_enregistrement_produit_une_image_caviardee(qtbot, tmp_path):
    screen = _ecran(qtbot)
    screen.ocr = FakeOcr([])
    screen.load_path(str(_image(tmp_path)))
    screen.analyze()
    qtbot.waitUntil(lambda: screen.session is not None, timeout=5000)
    screen._on_manual_rect((10.0, 10.0, 40.0, 40.0))
    out = screen.run_redact(tmp_path / "sortie", datetime(2026, 9, 23, 14, 0, 0))
    assert Image.open(out).crop((10, 10, 40, 40)).getextrema() == (
        (0, 0), (0, 0), (0, 0))
```

- [ ] **Step 3 : Lancer les tests, vérifier qu'ils échouent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_screen.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.ui.image_screen'`.

- [ ] **Step 4 : Implémenter**

Créer `anonymator/ui/image_screen.py`. Squelette imposé — le détail du style suit `pdf_screen.py` :

```python
# anonymator/ui/image_screen.py
"""Écran de revue d'une image.

L'OCR PROPOSE des zones, l'utilisateur VALIDE et complète à la souris. La revue
est obligatoire : aucun chemin ne mène à l'enregistrement sans passer par elle."""
from datetime import datetime
from io import BytesIO
from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFileDialog, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt

from anonymator.core.spatial_review_session import SpatialReviewSession
from anonymator.files.image import image_io
from anonymator.files.image.ocr import NullOcr
from anonymator.ui.components.perimetre_card import PerimetreCard
from anonymator.ui.image_scan_worker import ImageScanWorker
from anonymator.ui.spatial_canvas import SpatialCanvas

_FILTRE = "Images (*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp)"


class ImageScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back, on_request_model=None):
        super().__init__()
        self.ref = ref
        self.loader = loader
        self.prefs = prefs
        self.path: Path | None = None
        self.session: SpatialReviewSession | None = None
        self.ocr = NullOcr()          # remplacé par RapidOcrEngine au chargement

        root = QVBoxLayout(self)
        self.btn_open = QPushButton("Ouvrir une image…")
        self.btn_open.clicked.connect(self._open)
        self.btn_analyze = QPushButton("Analyser")
        self.btn_analyze.clicked.connect(self.analyze)
        self.btn_zone = QPushButton("Tracer une zone")
        self.btn_zone.setCheckable(True)
        self.btn_zone.toggled.connect(self._toggle_zone)
        self.btn_save = QPushButton("Caviarder et enregistrer")
        self.btn_save.clicked.connect(self._save_clicked)
        self.btn_back = QPushButton("Retour")
        self.btn_back.clicked.connect(on_back)

        bar = QHBoxLayout()
        for b in (self.btn_open, self.btn_analyze, self.btn_zone,
                  self.btn_save, self.btn_back):
            bar.addWidget(b)
        root.addLayout(bar)

        self.canvas = SpatialCanvas()
        self.canvas.manual_rect_drawn.connect(self._on_manual_rect)
        self.side = QTreeWidget()
        self.side.setHeaderLabels(["Type / valeur", "Nb"])
        self.side.itemChanged.connect(self._on_side_changed)
        self.perimetre = PerimetreCard("image")
        self.status = QLabel("")

        body = QHBoxLayout()
        body.addWidget(self.canvas, 3)
        right = QVBoxLayout()
        right.addWidget(self.side, 2)
        right.addWidget(self.perimetre)
        body.addLayout(right, 2)
        root.addLayout(body)
        root.addWidget(self.status)

    # --- chargement ---
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir une image", "", _FILTRE)
        if path:
            self.load_path(path)

    def load_path(self, path: str) -> None:
        self.path = Path(path)
        self.session = None
        self.side.clear()
        try:
            img = image_io.load_image(self.path)
        except (image_io.UnsupportedImageFormat,
                image_io.CorruptImageError) as exc:
            self.status.setText(str(exc))
            return
        buf = BytesIO()
        img.save(buf, format="PNG")
        self.canvas.set_page(buf.getvalue(), 1.0)   # une image est déjà en pixels
        self.status.setText(f"{self.path.name} — {img.width}x{img.height}")

    # --- analyse ---
    def analyze(self) -> None:
        if self.path is None:
            return
        self.status.setText("Analyse en cours…")
        worker = ImageScanWorker(self.path, self.ocr, self.loader.ner, self.ref)
        worker.scanned.connect(self._on_scanned)
        worker.failed.connect(self.status.setText)
        worker.run()

    def _on_scanned(self, pages) -> None:
        self.session = SpatialReviewSession(pages, self.ref)
        self._build_side()
        self._refresh_overlays()
        self.status.setText(
            f"{self.session.total_occurrences()} zone(s) proposée(s) — "
            f"vérifiez, décochez, complétez à la souris.")

    # --- panneau latéral ---
    def _build_side(self) -> None:
        self.side.blockSignals(True)
        self.side.clear()
        for etype in self.session.types():
            parent = QTreeWidgetItem([etype, ""])
            parent.setFlags(parent.flags() | Qt.ItemIsUserCheckable)
            parent.setCheckState(
                0, Qt.Checked if self.session.is_type_enabled(etype) else Qt.Unchecked)
            for value, count in self.session.values_for(etype):
                child = QTreeWidgetItem([value, str(count)])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(
                    0, Qt.Checked
                    if self.session.is_value_enabled(etype, value) else Qt.Unchecked)
                parent.addChild(child)
            self.side.addTopLevelItem(parent)
        self.side.expandAll()
        self.side.blockSignals(False)

    def _on_side_changed(self, item, _col) -> None:
        if self.session is None:
            return
        checked = item.checkState(0) == Qt.Checked
        if item.parent() is None:
            self.session.set_type_enabled(item.text(0), checked)
        else:
            self.session.set_value_enabled(
                item.parent().text(0), item.text(0), checked)
        self._refresh_overlays()

    def _refresh_overlays(self) -> None:
        # Ordre des paramètres : (entités retenues, zones manuelles, non confirmées)
        self.canvas.set_overlays(
            self.session.retained_entity_rects(0),
            self.session.manual_rects(0),
            self.session.unconfirmed_entity_rects(0))

    # --- zones manuelles ---
    def _toggle_zone(self, on: bool) -> None:
        self.canvas.set_draw_mode(on)

    def _on_manual_rect(self, rect: tuple) -> None:
        if self.session is None:
            return
        self.session.add_manual_rect(0, rect)
        self._refresh_overlays()

    # --- enregistrement ---
    def run_redact(self, output_dir: Path,
                   when: datetime | None = None) -> Path | None:
        if self.session is None or self.path is None:
            return None
        rects = self.session.retained_rects_by_page().get(0, [])
        return image_io.anonymize_image_redact(
            self.path, rects, Path(output_dir), when or datetime.now())

    def _save_clicked(self) -> None:
        if self.session is None:
            self.status.setText("Analysez l'image avant de l'enregistrer.")
            return
        out_dir = getattr(self.prefs, "output_dir", None) or self.path.parent
        out = self.run_redact(Path(out_dir))
        self.status.setText(f"Enregistré : {out}")
```

> **Attention à l'ordre des paramètres de `set_overlays`** : la signature est
> `set_overlays(entity_rects, manual_rects, unconfirmed_rects=None)` — les zones
> manuelles viennent **avant** les non confirmées. Inverser les deux ne lève
> aucune erreur : les overlays s'affichent simplement avec le mauvais style.

- [ ] **Step 5 : Lancer les tests, vérifier qu'ils passent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_screen.py -q
```

Attendu : `5 passed`.

- [ ] **Step 6 : Committer**

```bash
git add anonymator/ui/image_screen.py tests/test_image_screen.py
git commit -m "feat(ui): ecran de revue d'image avec tracage manuel"
```

## Task 17 : Point d'entrée et routage

**Files:**
- Modify: `anonymator/ui/home_screen.py`
- Modify: `anonymator/ui/main_window.py`
- Test: `tests/test_image_navigation.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Créer `tests/test_image_navigation.py` :

```python
from anonymator.ui.main_window import MainWindow


def test_l_accueil_propose_une_tuile_image(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    assert "image" in w.home.btn_image.text().lower()


def test_la_tuile_mene_a_l_ecran_image(qtbot):
    w = MainWindow()
    qtbot.addWidget(w)
    w.show_image()
    assert w.stack.currentWidget() is w.image_screen
```

- [ ] **Step 2 : Lancer les tests, vérifier qu'ils échouent**

```bash
./.venv/Scripts/python -m pytest tests/test_image_navigation.py -q
```

Attendu : `AttributeError: 'HomeScreen' object has no attribute 'btn_image'`.

- [ ] **Step 3 : Ajouter la tuile d'accueil**

Dans `anonymator/ui/home_screen.py` :
- ajouter `on_image=None` à la signature de `__init__` ;
- après la création de `self.btn_pdf`, ajouter :

```python
        self.btn_image = NavCard("document", "Importer une image",
                                 "Caviarder une capture, un scan, une photo",
                                 on_click=on_image)
```

- ajouter `self.btn_image` à la boucle `for c in (...)`, juste après `self.btn_pdf`.

- [ ] **Step 4 : Router depuis la fenêtre principale**

Dans `anonymator/ui/main_window.py` :
- importer l'écran : `from anonymator.ui.image_screen import ImageScreen` ;
- après la création de `self.pdf_screen`, ajouter :

```python
        self.image_screen = ImageScreen(self.ref, self.loader, self.prefs,
                                        self.show_home)
```

- ajouter `self.image_screen` à la liste des écrans empilés dans le `stack` ;
- ajouter `on_image=self.show_image` à la construction de `HomeScreen` ;
- ajouter la méthode, à côté de `show_pdf` :

```python
    def show_image(self):
        self.stack.setCurrentWidget(self.image_screen)
```

- dans la méthode qui propage le référentiel (`self.pdf_screen.ref = self.ref`), ajouter `self.image_screen.ref = self.ref`.

- [ ] **Step 5 : Brancher le moteur OCR réel**

Toujours dans `main_window.py`, après la création de `self.image_screen` :

```python
        try:
            from anonymator.files.image.ocr import RapidOcrEngine
            self.image_screen.ocr = RapidOcrEngine()
        except Exception:                                    # noqa: BLE001
            pass    # mode dégradé : NullOcr, le tracé manuel reste disponible
```

- [ ] **Step 6 : Lancer toute la suite**

```bash
./.venv/Scripts/python -m pytest -q
```

Attendu : `777 passed, 3 deselected`.

- [ ] **Step 7 : Lancer l'application et vérifier à l'œil**

```bash
./.venv/Scripts/python -m anonymator
```

Vérifier : la tuile « Importer une image » est présente ; ouvrir une image du banc ; les zones proposées s'affichent ; tracer une zone à la souris ; enregistrer ; ouvrir le fichier produit et constater que les zones sont noires.

- [ ] **Step 8 : Committer**

```bash
git add anonymator/ui/home_screen.py anonymator/ui/main_window.py tests/test_image_navigation.py
git commit -m "feat(ui): tuile d'accueil et routage vers l'ecran image"
```

---

# PHASE 5 — Packaging et documentation

## Task 18 : Build des deux marques et mesure du poids

**Files:**
- Modify: `anonymator.spec`

- [ ] **Step 1 : Déclarer les modèles et le module dans le spec PyInstaller**

Dans `anonymator.spec`, ajouter aux `hiddenimports` :

```python
    'rapidocr',
    'onnxruntime',
```

et, pour embarquer les modèles, ajouter aux `datas` :

```python
import rapidocr as _rapidocr
from pathlib import Path as _Path
_models = _Path(_rapidocr.__file__).parent / "models"
datas += [(str(p), "rapidocr/models") for p in _models.glob("*.onnx")]
```

> `excludes` contient déjà `scipy`, qui n'est **pas** une dépendance de RapidOCR :
> le laisser tel quel.

- [ ] **Step 2 : Mesurer le poids avant**

```bash
ls -la dist/*.zip | tail -4
```

Noter la taille des archives `v0.8.1`.

- [ ] **Step 3 : Builder les deux marques**

```bash
pwsh -File scripts/build.ps1 all
```

⚠️ **Ne pas rediriger la sortie avec `2>&1`** : PyInstaller écrit ses `INFO` sur stderr, PowerShell les transforme en erreurs et le `$ErrorActionPreference = 'Stop'` du script avorte le build dès la première ligne. Compter ~4 min par marque.

- [ ] **Step 4 : Mesurer et comparer**

```bash
ls -la dist/*.zip | tail -4
find dist/capnonyme/_internal -iname "*.onnx" -exec ls -lh {} \;
```

Attendu : les trois `.onnx` présents, croissance des archives dans la fourchette annoncée par la spec (**+80 à 110 Mo**). Si la croissance dépasse nettement, chercher ce qui a été embarqué en trop (`opencv-python` complet au lieu du `headless` ?) avant de continuer.

- [ ] **Step 5 : Valider l'exécutable, pas seulement les tests**

```bash
./dist/capnonyme/capnonyme.exe
```

C'est **le** test du conflit Qt : `opencv-python` et PySide6 embarquent chacun des plugins Qt, et le conflit ne se voit qu'au lancement de l'exe, jamais en test. Dérouler : ouvrir une image, analyser, tracer une zone, enregistrer.

- [ ] **Step 6 : Consigner la mesure et committer**

Reporter la taille mesurée dans la spec, section « Mesures effectuées ».

```bash
git add anonymator.spec docs/superpowers/specs/2026-09-23-anonymisation-images-design.md
git commit -m "build(image): embarquer rapidocr et les modeles PP-OCR"
```

## Task 19 : Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/ETAT-PROJET.md`

- [ ] **Step 1 : Compléter le tableau des formats du README**

Dans `README.md`, ajouter au tableau « Formats supportés » :

```markdown
| `.png` `.jpg` `.bmp` `.tif` `.webp` | ✅ Texte reconnu par OCR **proposé** à votre validation, plus les zones que vous tracez vous-même. Pixels réellement détruits, métadonnées EXIF purgées. `.heic` non supporté. |
```

- [ ] **Step 2 : Documenter le mode Image**

Dans `README.md`, après la section « Mode Fichier », ajouter :

```markdown
### Mode Image

1. Cliquer **Importer une image** sur l'écran d'accueil.
2. Cliquer **Ouvrir une image…** → sélectionner un `.png`, `.jpg`, `.bmp`, `.tif` ou `.webp`.
3. Cliquer **Analyser** → les zones de texte reconnues et contenant des données
   personnelles sont **proposées**, surlignées sur l'image.
4. Décocher les zones à **ne pas** masquer.
5. **La reconnaissance de caractères n'est pas infaillible** — surtout sur une photo.
   Relire l'image et, pour tout ce qu'elle a manqué, cliquer **Tracer une zone**
   puis dessiner un rectangle à la souris.
6. Cliquer **Caviarder et enregistrer** → les pixels des zones retenues sont
   **détruits** (non récupérables) et les métadonnées EXIF supprimées.
7. L'original n'est **jamais modifié**.
```

- [ ] **Step 3 : Ajouter la limite connue**

Dans `README.md`, tableau « Problèmes connus » :

```markdown
| Nom manqué sur une photo | La reconnaissance de caractères échoue sur le flou, le contre-jour et l'écriture manuscrite. Tracer la zone manuellement. |
| Image `.heic` (photo iPhone) | Format non supporté — la convertir en `.jpg` avant import |
```

- [ ] **Step 4 : Mettre à jour l'état du projet**

Dans `docs/ETAT-PROJET.md` :
- ajouter une ligne au tableau des étapes : `| **Anonymisation des images** (OCR + tracé manuel) | ✅ **Fait** |` ;
- corriger le nombre de tests (la valeur affichée, `637`, était **déjà périmée** avant ce chantier : la suite en comptait 721 au démarrage) ;
- ajouter aux décisions verrouillées :

```markdown
- **Images** : OCR **RapidOCR** (modèles PP-OCR Apache-2.0 **embarqués**, aucun téléchargement),
  revue **obligatoire**, **tracé manuel** de zones complémentaire — la promesse est
  « l'application propose, vous validez », jamais « tout a été vu ». Caviardage par
  **écrasement des pixels**, purge EXIF avec **orientation appliquée avant purge**.
  Couche de texte positionné mutualisée dans `files/textlayer.py` (PDF et image).
```

- [ ] **Step 5 : Vérifier et committer**

```bash
./.venv/Scripts/python -m pytest -q
git add README.md docs/ETAT-PROJET.md
git commit -m "docs(image): mode Image dans le README et etat du projet"
```

---

## Sortie de chantier

- [ ] `./.venv/Scripts/python -m pytest -q` → **777 passed, 3 deselected**
- [ ] `./.venv/Scripts/python -m pytest -m integration -q` → tests OCR réels verts, **dont le verrou réseau**
- [ ] Les deux exes se lancent et déroulent le scénario image de bout en bout
- [ ] Croissance du zip mesurée et consignée dans la spec
- [ ] `third-party-licenses/` complété, redistribution des modèles annoncée
- [ ] Fusion dans `main` via le skill `superpowers:finishing-a-development-branch`

> **Non couvert par ce plan, par décision de la spec :** PDF scannés (lot 1), images
> incrustées dans les documents (lot 3), visages et plaques (lot 4), export `.txt`
> depuis une image, `.heic`, traitement par lot.
