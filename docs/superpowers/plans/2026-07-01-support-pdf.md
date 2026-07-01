# Support PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter le support des fichiers `.pdf` à Anonymator, avec deux modes de sortie — rédaction juridique (destruction réelle du texte via PyMuPDF) et extraction texte anonymisée (.txt) — sur un écran PDF dédié offrant revue visuelle et sélection de zone manuelle.

**Architecture :** Tout le code PyMuPDF est isolé dans `anonymator/files/pdf/` (aucun autre module ne l'importe). Le moteur de détection ne change pas : `detect()`/`apply_masking()` travaillent sur du texte plat + offsets ; le sous-package PDF ne fait que **traduire** entre « texte plat » et « géométrie de page ». L'état de revue vit dans `PdfReviewSession` (core, non-Qt), miroir de `FileReviewSession` indexé par `(page, rect)`. L'UI (`PdfScreen` dédié + `PdfCanvas` QGraphicsView) réutilise le panneau latéral d'entités, le pattern worker/busy et la pagination de `FileScreen`.

**Tech Stack :** Python, PyMuPDF (`fitz`), PySide6 (QGraphicsView), pytest + pytest-qt. Fixtures PDF générées **par code** (aucun binaire dans le repo).

---

## Décisions verrouillées pour ce plan

- **Écran PDF dédié** (`PdfScreen`), pas d'extension de `FileScreen`. `FileScreen` reste `.txt/.csv/.xlsx`.
- **Sélection de zone manuelle incluse en v1** : l'utilisateur peut tracer un rectangle sur le canevas pour caviarder un tampon/signature non détecté.
- **`render.py` renvoie des octets PNG** (pas de `QImage`) → la couche `files/pdf/` reste sans dépendance Qt et testable seule ; la conversion PNG→`QPixmap` se fait dans `PdfCanvas`. (Le spec laissait le choix du widget ouvert ; ce choix garde l'isolation.)
- **Seuil natif/scanné** : `MIN_CHARS_PER_PAGE = 10` caractères extractibles par page (constante documentée, ajustable).
- **Rendu** : `RENDER_ZOOM = 2.0`. En coordonnées scène du canevas, 1 point PDF = `zoom` pixels. Overlay (points → scène) : `× zoom`. Manuel (scène → points) : `/ zoom`.

## File Structure

Nouveau sous-package `anonymator/files/pdf/` (PyMuPDF isolé) :

| Fichier | Responsabilité unique |
|---|---|
| `anonymator/files/pdf/__init__.py` | Marqueur de package (vide). |
| `anonymator/files/pdf/extract.py` | Ouvre le PDF, classe natif/scanné, extrait mots+boîtes → `PageText` (texte plat + `WordBox` avec offsets). Exceptions `ScannedPdfNotSupported`, `EncryptedPdfError`, `CorruptPdfError`. |
| `anonymator/files/pdf/mapping.py` | Le pont : entité `[s,e)` → rectangles des mots qui recoupent. Cœur logique, sans Qt ni I/O. |
| `anonymator/files/pdf/redact.py` | `redact_page` (add_redact_annot + apply_redactions), `purge_metadata`, `save_redacted`. Destruction réelle. |
| `anonymator/files/pdf/render.py` | `render_page(page, zoom)` → octets PNG. |
| `anonymator/files/pdf/pdf_io.py` | Orchestration : `scan_pdf`, `anonymize_pdf_text`, `anonymize_pdf_redact`, `render_page_at`. `PageScan` dataclass. Miroir de `scan_csv`/`apply_csv`. |
| `anonymator/core/pdf_review_session.py` | `PdfReviewSession` (non-Qt) : niveaux type/valeur/exclusion + rects manuels ; produit rects retenus par page + `report()`. |
| `anonymator/ui/pdf_scan_worker.py` | `PdfScanWorker(QThread)` : scan threadé (copie de `FileScanWorker`). |
| `anonymator/ui/pdf_canvas.py` | `PdfCanvas(QGraphicsView)` : image de page + overlays + tracé rubber-band manuel. `scene_rect_to_points` (helper pur). |
| `anonymator/ui/pdf_screen.py` | `PdfScreen(QWidget)` dédié : canevas + panneau latéral réutilisé + pagination + 2 boutons de mode. |

Fichiers modifiés : `anonymator/ui/main_window.py`, `anonymator/ui/home_screen.py`, `requirements.txt`, `anonymator.spec`, `README.md`.

Fichiers de test créés : un par module de logique + `tests/test_pdf_screen.py`. Helper de fixtures : `tests/pdf_fixtures.py`.

---

## Task 0 : Dépendance PyMuPDF

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1 : Ajouter PyMuPDF à `requirements.txt`**

Ajouter la ligne (après `openpyxl>=3.1`) :

```
pymupdf>=1.24
```

- [ ] **Step 2 : Installer dans le venv**

Run: `.venv/Scripts/python -m pip install "pymupdf>=1.24"`
Expected: `Successfully installed pymupdf-<version>`

- [ ] **Step 3 : Vérifier l'import**

Run: `.venv/Scripts/python -c "import fitz; print(fitz.__doc__)"`
Expected: une ligne mentionnant PyMuPDF/MuPDF (pas d'`ImportError`).

- [ ] **Step 4 : Commit**

```bash
git add requirements.txt
git commit -m "build: ajoute PyMuPDF (support PDF)"
```

---

## Task 1 : Helper de fixtures PDF (générées par code)

**Files:**
- Create: `tests/pdf_fixtures.py`
- Test: `tests/test_pdf_fixtures.py`

- [ ] **Step 1 : Écrire le test des fixtures**

```python
# tests/test_pdf_fixtures.py
import fitz
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf, make_encrypted_pdf


def test_native_pdf_has_extractable_text(tmp_path):
    p = tmp_path / "n.pdf"
    make_native_pdf(p, "Contact Claire Martin ici")
    doc = fitz.open(str(p))
    assert "Claire Martin" in doc[0].get_text()
    doc.close()


def test_scanned_pdf_has_no_text(tmp_path):
    p = tmp_path / "s.pdf"
    make_scanned_pdf(p)
    doc = fitz.open(str(p))
    assert doc[0].get_text().strip() == ""
    doc.close()


def test_encrypted_pdf_needs_pass(tmp_path):
    p = tmp_path / "e.pdf"
    make_encrypted_pdf(p, "secret")
    doc = fitz.open(str(p))
    assert doc.needs_pass is True
    doc.close()
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_fixtures.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tests.pdf_fixtures'`

- [ ] **Step 3 : Écrire le helper**

```python
# tests/pdf_fixtures.py
from pathlib import Path
import fitz


def make_native_pdf(path: Path, text: str = "Contact Claire Martin claire@example.com",
                    title: str = "", author: str = "") -> Path:
    """PDF natif : une page avec du texte sélectionnable à (72, 72)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text, fontsize=12)
    if title or author:
        doc.set_metadata({"title": title, "author": author})
    doc.save(str(path))
    doc.close()
    return path


def make_scanned_pdf(path: Path) -> Path:
    """PDF « scanné » : une page avec seulement une image, aucune couche texte."""
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 200, 200))
    pix.clear_with(220)
    page.insert_image(fitz.Rect(50, 50, 250, 250), pixmap=pix)
    doc.save(str(path))
    doc.close()
    return path


def make_encrypted_pdf(path: Path, password: str = "secret") -> Path:
    """PDF chiffré (mot de passe utilisateur)."""
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "secret content", fontsize=12)
    doc.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256,
             owner_pw=password, user_pw=password)
    doc.close()
    return path
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_fixtures.py -v`
Expected: 3 passed

- [ ] **Step 5 : Commit**

```bash
git add tests/pdf_fixtures.py tests/test_pdf_fixtures.py
git commit -m "test: fixtures PDF générées par code (natif/scanné/chiffré)"
```

---

## Task 2 : `extract.py` — ouverture, classification, extraction

**Files:**
- Create: `anonymator/files/pdf/__init__.py` (vide)
- Create: `anonymator/files/pdf/extract.py`
- Test: `tests/test_pdf_extract.py`

- [ ] **Step 1 : Créer le marqueur de package**

Créer `anonymator/files/pdf/__init__.py` **vide**.

- [ ] **Step 2 : Écrire les tests d'extraction**

```python
# tests/test_pdf_extract.py
import pytest
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf, make_encrypted_pdf
from anonymator.files.pdf import extract
from anonymator.files.pdf.extract import (
    ScannedPdfNotSupported, EncryptedPdfError, CorruptPdfError)


def test_open_native_pdf(tmp_path):
    p = make_native_pdf(tmp_path / "n.pdf", "Bonjour Claire Martin")
    doc = extract.open_document(p)
    assert doc.page_count == 1
    doc.close()


def test_open_encrypted_raises(tmp_path):
    p = make_encrypted_pdf(tmp_path / "e.pdf")
    with pytest.raises(EncryptedPdfError):
        extract.open_document(p)


def test_open_corrupt_raises(tmp_path):
    p = tmp_path / "bad.pdf"
    p.write_bytes(b"%PDF-1.4 this is not a real pdf")
    with pytest.raises(CorruptPdfError):
        extract.open_document(p)


def test_ensure_native_accepts_text_pdf(tmp_path):
    p = make_native_pdf(tmp_path / "n.pdf", "Un texte bien present ici")
    doc = extract.open_document(p)
    extract.ensure_native(doc)   # ne lève pas
    doc.close()


def test_ensure_native_rejects_scanned(tmp_path):
    p = make_scanned_pdf(tmp_path / "s.pdf")
    doc = extract.open_document(p)
    with pytest.raises(ScannedPdfNotSupported):
        extract.ensure_native(doc)
    doc.close()


def test_extract_page_flat_text_and_boxes(tmp_path):
    p = make_native_pdf(tmp_path / "n.pdf", "Bonjour Claire Martin")
    doc = extract.open_document(p)
    pt = extract.extract_page(doc[0], 0)
    doc.close()
    assert "Claire" in pt.text and "Martin" in pt.text
    assert pt.words, "au moins un mot"
    # les offsets pointent vers le bon fragment de texte plat
    w = pt.words[0]
    assert pt.text[w.char_start:w.char_end] == w.text
    # boîtes non vides
    x0, y0, x1, y1 = w.rect
    assert x1 > x0 and y1 > y0


def test_extract_pages_returns_one_per_page(tmp_path):
    p = make_native_pdf(tmp_path / "n.pdf", "Page unique de test")
    doc = extract.open_document(p)
    pages = extract.extract_pages(doc)
    doc.close()
    assert len(pages) == 1
    assert pages[0].page_index == 0
```

- [ ] **Step 3 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_extract.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.files.pdf.extract'`

- [ ] **Step 4 : Écrire `extract.py`**

```python
# anonymator/files/pdf/extract.py
from dataclasses import dataclass
from pathlib import Path
import fitz

MIN_CHARS_PER_PAGE = 10   # < ce seuil de caractères extractibles / page → scanné


class ScannedPdfNotSupported(Exception):
    pass


class EncryptedPdfError(Exception):
    pass


class CorruptPdfError(Exception):
    pass


@dataclass
class WordBox:
    text: str
    rect: tuple[float, float, float, float]   # (x0, y0, x1, y1) en points PDF
    char_start: int                            # offset inclusif dans le texte plat
    char_end: int                              # offset exclusif


@dataclass
class PageText:
    page_index: int
    text: str                # texte plat reconstruit en ordre de lecture
    words: list[WordBox]


def open_document(path: Path) -> "fitz.Document":
    try:
        doc = fitz.open(str(path))
    except Exception as exc:   # noqa: BLE001 — traduit en erreur métier claire
        raise CorruptPdfError("Fichier PDF illisible ou endommagé") from exc
    if doc.needs_pass:
        doc.close()
        raise EncryptedPdfError("PDF protégé par mot de passe : non supporté")
    return doc


def ensure_native(doc: "fitz.Document") -> None:
    """Lève ScannedPdfNotSupported si aucune page n'a de couche texte."""
    for page in doc:
        if len(page.get_text().strip()) >= MIN_CHARS_PER_PAGE:
            return
    raise ScannedPdfNotSupported(
        "PDF scanné : reconnaissance de texte (OCR) non supportée pour l'instant")


def extract_page(page: "fitz.Page", page_index: int) -> PageText:
    """Reconstruit le texte plat en ordre de lecture + une WordBox par mot."""
    words = page.get_text("words")            # (x0,y0,x1,y1, mot, bloc, ligne, n°mot)
    words.sort(key=lambda w: (w[5], w[6], w[7]))
    parts: list[str] = []
    boxes: list[WordBox] = []
    cursor = 0
    prev_line: tuple[int, int] | None = None
    for x0, y0, x1, y1, text, block, line, _wno in words:
        line_key = (block, line)
        if prev_line is not None and line_key != prev_line:
            parts.append("\n"); cursor += 1
        elif parts:
            parts.append(" "); cursor += 1
        start = cursor
        parts.append(text); cursor += len(text)
        boxes.append(WordBox(text, (x0, y0, x1, y1), start, cursor))
        prev_line = line_key
    return PageText(page_index, "".join(parts), boxes)


def extract_pages(doc: "fitz.Document") -> list[PageText]:
    return [extract_page(page, i) for i, page in enumerate(doc)]
```

- [ ] **Step 5 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_extract.py -v`
Expected: 7 passed

- [ ] **Step 6 : Commit**

```bash
git add anonymator/files/pdf/__init__.py anonymator/files/pdf/extract.py tests/test_pdf_extract.py
git commit -m "feat(pdf): extract — ouverture, classification natif/scanné, mots+boîtes"
```

---

## Task 3 : `mapping.py` — le pont offset → rectangles (cœur logique)

**Files:**
- Create: `anonymator/files/pdf/mapping.py`
- Test: `tests/test_pdf_mapping.py`

- [ ] **Step 1 : Écrire les tests du pont**

```python
# tests/test_pdf_mapping.py
from anonymator.model import Entity
from anonymator.files.pdf.extract import WordBox, PageText
from anonymator.files.pdf import mapping


def _page():
    # texte plat : "Bonjour Claire Martin"  (offsets 0..21)
    #               0......7......14
    return PageText(0, "Bonjour Claire Martin", [
        WordBox("Bonjour", (10, 10, 60, 20), 0, 7),
        WordBox("Claire", (62, 10, 100, 20), 8, 14),
        WordBox("Martin", (102, 10, 150, 20), 15, 21),
    ])


def test_single_word_entity_maps_to_its_rect():
    pt = _page()
    ent = Entity("PERSON", "Claire", 8, 14, "ner")
    rects = mapping.rects_for_entity(pt, ent)
    assert rects == [(62, 10, 100, 20)]


def test_multi_word_entity_maps_to_all_intersecting_rects():
    pt = _page()
    ent = Entity("PERSON", "Claire Martin", 8, 21, "ner")
    rects = mapping.rects_for_entity(pt, ent)
    assert (62, 10, 100, 20) in rects and (102, 10, 150, 20) in rects
    assert len(rects) == 2


def test_partial_overlap_still_selects_word():
    pt = _page()
    # entité couvrant "laire" (déborde à l'intérieur du mot Claire)
    ent = Entity("X", "laire", 9, 14, "ner")
    rects = mapping.rects_for_entity(pt, ent)
    assert rects == [(62, 10, 100, 20)]


def test_unmappable_entity_returns_empty():
    pt = _page()
    ent = Entity("X", "zzz", 100, 103, "ner")   # hors de tout mot
    assert mapping.rects_for_entity(pt, ent) == []


def test_rects_for_entities_aggregates():
    pt = _page()
    ents = [Entity("PERSON", "Bonjour", 0, 7, "ner"),
            Entity("PERSON", "Martin", 15, 21, "ner")]
    rects = mapping.rects_for_entities(pt, ents)
    assert (10, 10, 60, 20) in rects and (102, 10, 150, 20) in rects
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_mapping.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.files.pdf.mapping'`

- [ ] **Step 3 : Écrire `mapping.py`**

```python
# anonymator/files/pdf/mapping.py
from anonymator.model import Entity
from anonymator.files.pdf.extract import PageText, WordBox

Rect = tuple[float, float, float, float]


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

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_mapping.py -v`
Expected: 5 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/pdf/mapping.py tests/test_pdf_mapping.py
git commit -m "feat(pdf): mapping — pont entité[s,e) → rectangles (multi-lignes)"
```

---

## Task 4 : `redact.py` — destruction réelle + purge métadonnées

**Files:**
- Create: `anonymator/files/pdf/redact.py`
- Test: `tests/test_pdf_redact.py`

- [ ] **Step 1 : Écrire les tests (dont le test pivot de destruction)**

```python
# tests/test_pdf_redact.py
import fitz
from tests.pdf_fixtures import make_native_pdf
from anonymator.files.pdf import extract, mapping, redact
from anonymator.model import Entity


def test_redaction_really_destroys_text(tmp_path):
    """Test pivot : après rédaction, get_text() ne contient plus la valeur."""
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin fin")
    doc = extract.open_document(src)
    pt = extract.extract_page(doc[0], 0)
    ent = Entity("PERSON", "Claire Martin", pt.text.index("Claire"),
                 pt.text.index("Claire") + len("Claire Martin"), "ner")
    rects = mapping.rects_for_entity(pt, ent)
    redact.redact_page(doc[0], rects)
    out = tmp_path / "out.pdf"
    redact.save_redacted(doc, out)
    doc.close()

    check = fitz.open(str(out))
    assert "Claire Martin" not in check[0].get_text()
    assert "Contact" in check[0].get_text()   # le reste survit
    check.close()


def test_purge_metadata_clears_title_and_author(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte", title="Secret", author="Alice")
    doc = extract.open_document(src)
    redact.purge_metadata(doc)
    out = tmp_path / "out.pdf"
    redact.save_redacted(doc, out)
    doc.close()

    check = fitz.open(str(out))
    meta = check.metadata
    check.close()
    assert not meta.get("title") and not meta.get("author")
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_redact.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.files.pdf.redact'`

- [ ] **Step 3 : Écrire `redact.py`**

```python
# anonymator/files/pdf/redact.py
from pathlib import Path
import fitz

Rect = tuple[float, float, float, float]


def redact_page(page: "fitz.Page", rects: list[Rect]) -> None:
    """Marque chaque rectangle pour rédaction puis applique — destruction réelle
    du texte dans le flux du PDF (pas un simple masque visuel)."""
    for r in rects:
        page.add_redact_annot(fitz.Rect(*r), fill=(0, 0, 0))
    page.apply_redactions()


def purge_metadata(doc: "fitz.Document") -> None:
    """Vide les métadonnées document et le bloc XML (XMP)."""
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:   # noqa: BLE001 — absent sur certains PDF, sans gravité
        pass


def save_redacted(doc: "fitz.Document", out_path: Path) -> None:
    """Sauvegarde avec nettoyage (garbage collection des objets orphelins)."""
    doc.save(str(out_path), garbage=4, deflate=True, clean=True)
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_redact.py -v`
Expected: 2 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/pdf/redact.py tests/test_pdf_redact.py
git commit -m "feat(pdf): redact — destruction reelle (apply_redactions) + purge metadonnees"
```

---

## Task 5 : `render.py` — rendu de page en PNG

**Files:**
- Create: `anonymator/files/pdf/render.py`
- Test: `tests/test_pdf_render.py`

- [ ] **Step 1 : Écrire les tests de rendu**

```python
# tests/test_pdf_render.py
from tests.pdf_fixtures import make_native_pdf
from anonymator.files.pdf import extract, render


def test_render_page_returns_png_bytes(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "un texte a rendre")
    doc = extract.open_document(src)
    png = render.render_page(doc[0])
    doc.close()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"   # signature PNG
    assert len(png) > 100


def test_render_zoom_increases_size(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "un texte a rendre")
    doc = extract.open_document(src)
    small = render.render_page(doc[0], zoom=1.0)
    big = render.render_page(doc[0], zoom=3.0)
    doc.close()
    assert len(big) > len(small)
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.files.pdf.render'`

- [ ] **Step 3 : Écrire `render.py`**

```python
# anonymator/files/pdf/render.py
import fitz

RENDER_ZOOM = 2.0   # 1 point PDF = RENDER_ZOOM pixels dans l'image rendue


def render_page(page: "fitz.Page", zoom: float = RENDER_ZOOM) -> bytes:
    """Rend la page en image PNG (octets). Pas de Qt ici : la conversion en
    QPixmap se fait dans la couche UI (PdfCanvas)."""
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return pix.tobytes("png")
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_render.py -v`
Expected: 2 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/pdf/render.py tests/test_pdf_render.py
git commit -m "feat(pdf): render — page vers PNG (octets, sans Qt)"
```

---

## Task 6 : `pdf_io.py` — orchestration + mode texte + mode rédaction

**Files:**
- Create: `anonymator/files/pdf/pdf_io.py`
- Test: `tests/test_pdf_io.py`

- [ ] **Step 1 : Écrire les tests d'orchestration**

```python
# tests/test_pdf_io.py
from datetime import datetime
import fitz
import pytest
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.pdf import pdf_io
from anonymator.files.pdf.extract import ScannedPdfNotSupported


def _ref():
    return Referential.load_default()


def test_scan_pdf_returns_pagescan_with_entities(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    pages = pdf_io.scan_pdf(src, FakeNer({"Claire Martin": "PERSON"}), _ref())
    assert len(pages) == 1
    ps = pages[0]
    assert ps.page_index == 0
    assert any(e.type == "PERSON" and e.value == "Claire Martin" for e in ps.entities)
    assert ps.words   # les boîtes sont conservées pour le mapping


def test_scan_pdf_rejects_scanned(tmp_path):
    src = make_scanned_pdf(tmp_path / "s.pdf")
    with pytest.raises(ScannedPdfNotSupported):
        pdf_io.scan_pdf(src, FakeNer({}), _ref())


def test_anonymize_pdf_text_writes_masked_txt(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    res = pdf_io.anonymize_pdf_text(src, FakeNer({"Claire Martin": "PERSON"}),
                                    _ref(), tmp_path, datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".txt"
    out = res.output_path.read_text(encoding="utf-8")
    assert "[PERSONNE]" in out and "Claire Martin" not in out


def test_anonymize_pdf_redact_destroys_and_saves(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    pages = pdf_io.scan_pdf(src, FakeNer({"Claire Martin": "PERSON"}), _ref())
    ps = pages[0]
    from anonymator.files.pdf import mapping
    ent = next(e for e in ps.entities if e.value == "Claire Martin")
    rects = mapping.rects_for_entity(_page_text(ps), ent)
    out = pdf_io.anonymize_pdf_redact(src, {0: rects}, tmp_path,
                                      datetime(2026, 1, 2, 3, 4, 5))
    assert out.suffix == ".pdf"
    check = fitz.open(str(out))
    assert "Claire Martin" not in check[0].get_text()
    check.close()


def _page_text(ps):
    """Reconstruit un PageText à partir d'un PageScan pour appeler mapping."""
    from anonymator.files.pdf.extract import PageText
    return PageText(ps.page_index, ps.text, ps.words)


def test_render_page_at_returns_png(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "un texte")
    png = pdf_io.render_page_at(src, 0)
    assert png[:4] == b"\x89PNG"
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_io.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.files.pdf.pdf_io'`

- [ ] **Step 3 : Écrire `pdf_io.py`**

```python
# anonymator/files/pdf/pdf_io.py
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.model import Entity
from anonymator.pipeline import detect
from anonymator.anonymize import apply_masking
from anonymator.report.audit import AuditReport
from anonymator.output_naming import anonymized_path
from anonymator.files import txt_io
from anonymator.files.anonymize_file import FileResult
from anonymator.files.pdf import extract, redact, render
from anonymator.files.pdf.extract import WordBox

Rect = tuple[float, float, float, float]


@dataclass
class PageScan:
    page_index: int
    text: str
    words: list[WordBox]
    entities: list[Entity]


def scan_pdf(path: Path, ner: NerDetector, ref: Referential) -> list[PageScan]:
    """Extrait chaque page (texte plat + boîtes) et détecte les entités.
    Lève ScannedPdfNotSupported / EncryptedPdfError / CorruptPdfError."""
    doc = extract.open_document(path)
    try:
        extract.ensure_native(doc)
        pages = extract.extract_pages(doc)
    finally:
        doc.close()
    return [PageScan(pt.page_index, pt.text, pt.words, detect(pt.text, ner, ref))
            for pt in pages]


def anonymize_pdf_text(path: Path, ner: NerDetector, ref: Referential,
                       output_dir: Path, when: datetime) -> FileResult:
    """Mode extraction : texte plat de toutes les pages → pipeline texte → .txt."""
    doc = extract.open_document(path)
    try:
        extract.ensure_native(doc)
        pages = extract.extract_pages(doc)
    finally:
        doc.close()
    text = "\n\n".join(p.text for p in pages)
    ents = [e for e in detect(text, ner, ref) if e.confirmed]
    report = AuditReport()
    for e in ents:
        report.add(e.type, e.value, ref.tag_for(e.type), "pdf")
    masked = apply_masking(text, ents, ref)
    out = anonymized_path(path.with_suffix(".txt"), output_dir, when)
    txt_io.write_text(masked, "utf-8", out)
    return FileResult(out, report)


def anonymize_pdf_redact(path: Path, rects_by_page: dict[int, list[Rect]],
                         output_dir: Path, when: datetime) -> Path:
    """Mode rédaction : caviarde les rectangles retenus par page, purge les
    métadonnées, sauvegarde. L'original n'est jamais modifié."""
    doc = extract.open_document(path)
    try:
        for i, page in enumerate(doc):
            rects = rects_by_page.get(i, [])
            if rects:
                redact.redact_page(page, rects)
        redact.purge_metadata(doc)
        out = anonymized_path(path, output_dir, when)
        redact.save_redacted(doc, out)
    finally:
        doc.close()
    return out


def render_page_at(path: Path, page_index: int,
                   zoom: float = render.RENDER_ZOOM) -> bytes:
    """Rend une page en PNG (pour l'aperçu de revue)."""
    doc = extract.open_document(path)
    try:
        return render.render_page(doc[page_index], zoom=zoom)
    finally:
        doc.close()
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_io.py -v`
Expected: 5 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/pdf/pdf_io.py tests/test_pdf_io.py
git commit -m "feat(pdf): pdf_io — scan + mode texte + mode redaction + rendu"
```

---

## Task 7 : `PdfReviewSession` — état de revue (core, non-Qt)

**Files:**
- Create: `anonymator/core/pdf_review_session.py`
- Test: `tests/test_pdf_review_session.py`

Note : l'API expose délibérément les **mêmes noms de méthodes** que `FileReviewSession` (`types`, `total_occurrences`, `values_for`, `count_retained`, `is_type_enabled`, `set_type_enabled`, `is_value_enabled`, `set_value_enabled`) pour que le panneau latéral de l'UI soit réutilisé sans modification.

- [ ] **Step 1 : Écrire les tests de session**

```python
# tests/test_pdf_review_session.py
from anonymator.referential import Referential
from anonymator.model import Entity
from anonymator.files.pdf.extract import WordBox
from anonymator.files.pdf.pdf_io import PageScan
from anonymator.core.pdf_review_session import PdfReviewSession


def _pagescan():
    words = [
        WordBox("Bonjour", (10, 10, 60, 20), 0, 7),
        WordBox("Claire", (62, 10, 100, 20), 8, 14),
        WordBox("Martin", (102, 10, 150, 20), 15, 21),
    ]
    ents = [Entity("PERSON", "Claire Martin", 8, 21, "ner")]
    return PageScan(0, "Bonjour Claire Martin", words, ents)


def _session():
    return PdfReviewSession([_pagescan()], Referential.load_default())


def test_types_and_values():
    s = _session()
    assert s.types() == ["PERSON"]
    assert s.values_for("PERSON") == [("Claire Martin", 1)]
    assert s.total_occurrences() == 1


def test_retained_rects_by_page_default():
    s = _session()
    rects = s.retained_rects_by_page()
    assert set(rects.keys()) == {0}
    assert (62, 10, 100, 20) in rects[0] and (102, 10, 150, 20) in rects[0]


def test_disabling_type_removes_rects():
    s = _session()
    s.set_type_enabled("PERSON", False)
    assert s.retained_rects_by_page().get(0, []) == []
    assert s.count_retained("PERSON") == 0


def test_disabling_value_removes_rects():
    s = _session()
    s.set_value_enabled("PERSON", "Claire Martin", False)
    assert s.retained_rects_by_page().get(0, []) == []


def test_unconfirmed_entity_starts_disabled():
    words = [WordBox("FR76", (10, 10, 40, 20), 0, 4)]
    ents = [Entity("IBAN", "FR76", 0, 4, "deterministic", confirmed=False)]
    s = PdfReviewSession([PageScan(0, "FR76", words, ents)],
                         Referential.load_default())
    assert s.is_value_enabled("IBAN", "FR76") is False
    assert s.retained_rects_by_page().get(0, []) == []


def test_manual_rects_added_to_retained():
    s = _session()
    s.add_manual_rect(0, (200, 200, 260, 230))
    rects = s.retained_rects_by_page()[0]
    assert (200, 200, 260, 230) in rects
    assert s.manual_rects(0) == [(200, 200, 260, 230)]


def test_clear_manual_rects():
    s = _session()
    s.add_manual_rect(0, (200, 200, 260, 230))
    s.clear_manual_rects(0)
    assert s.manual_rects(0) == []


def test_occurrence_exclusion():
    s = _session()
    s.set_occurrence_excluded(0, 0, True)
    assert s.retained_rects_by_page().get(0, []) == []


def test_report_lists_entities_and_manual_zones():
    s = _session()
    s.add_manual_rect(0, (200, 200, 260, 230))
    rows = s.report().to_rows()
    kinds = {r["type"] for r in rows}
    assert "PERSON" in kinds and "ZONE" in kinds


def test_retained_entity_rects_carries_type_for_overlay():
    s = _session()
    overlay = s.retained_entity_rects(0)
    assert all(len(item) == 2 for item in overlay)     # (rect, type)
    assert any(t == "PERSON" for _rect, t in overlay)
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_review_session.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.core.pdf_review_session'`

- [ ] **Step 3 : Écrire `pdf_review_session.py`**

```python
# anonymator/core/pdf_review_session.py
from dataclasses import dataclass, field
from anonymator.model import Entity
from anonymator.report.audit import AuditReport
from anonymator.files.pdf import mapping
from anonymator.files.pdf.extract import PageText
from anonymator.files.pdf.pdf_io import PageScan

Rect = tuple[float, float, float, float]
_MANUAL_TYPE = "ZONE"
_MANUAL_TAG = "[ZONE]"


@dataclass
class _Occ:
    page: int
    entity: Entity
    rects: list[Rect]


class PdfReviewSession:
    """État de revue d'un PDF (non-Qt). Miroir de FileReviewSession, indexé par
    (page, rect). Trois niveaux combinés en ET : type activé, valeur distincte
    activée, occurrence non exclue individuellement. Plus des rects manuels."""

    def __init__(self, pages: list[PageScan], ref):
        self.ref = ref
        self._occs: list[_Occ] = []
        self._types_enabled: dict[str, bool] = {}
        self._values_enabled: dict[tuple[str, str], bool] = {}
        self._values_count: dict[tuple[str, str], int] = {}
        self._excluded: set[int] = set()                 # indices dans self._occs
        self._manual: dict[int, list[Rect]] = {}
        for ps in pages:
            page_text = PageText(ps.page_index, ps.text, ps.words)
            for e in ps.entities:
                rects = mapping.rects_for_entity(page_text, e)
                self._occs.append(_Occ(ps.page_index, e, rects))
                self._types_enabled.setdefault(e.type, True)
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                self._values_enabled.setdefault(key, e.confirmed)

    # --- lecture (API identique à FileReviewSession) ---
    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def total_occurrences(self) -> int:
        return sum(self._values_count.values())

    def values_for(self, etype: str) -> list[tuple[str, int]]:
        items = [(v, n) for (t, v), n in self._values_count.items() if t == etype]
        return sorted(items)

    def _occ_retained(self, i: int) -> bool:
        occ = self._occs[i]
        if i in self._excluded:
            return False
        if not self._types_enabled.get(occ.entity.type, True):
            return False
        if not self._values_enabled.get((occ.entity.type, occ.entity.value), True):
            return False
        return True

    def count_retained(self, etype: str) -> int:
        return sum(1 for i, occ in enumerate(self._occs)
                   if occ.entity.type == etype and self._occ_retained(i))

    def is_type_enabled(self, etype: str) -> bool:
        return self._types_enabled.get(etype, True)

    def is_value_enabled(self, etype: str, value: str) -> bool:
        return self._values_enabled.get((etype, value), True)

    # --- écriture ---
    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        self._types_enabled[etype] = enabled

    def set_value_enabled(self, etype: str, value: str, enabled: bool) -> None:
        self._values_enabled[(etype, value)] = enabled

    def set_occurrence_excluded(self, page: int, occ_index: int, excluded: bool) -> None:
        """Exclut une occurrence individuelle. occ_index = index dans occurrences()."""
        if excluded:
            self._excluded.add(occ_index)
        else:
            self._excluded.discard(occ_index)

    # --- rects manuels ---
    def add_manual_rect(self, page: int, rect: Rect) -> None:
        self._manual.setdefault(page, []).append(rect)

    def manual_rects(self, page: int) -> list[Rect]:
        return list(self._manual.get(page, []))

    def clear_manual_rects(self, page: int) -> None:
        self._manual.pop(page, None)

    # --- producteurs ---
    def occurrences(self, page: int) -> list[tuple[int, Entity]]:
        """(occ_index global, entité) des occurrences de la page — pour l'UI."""
        return [(i, occ.entity) for i, occ in enumerate(self._occs)
                if occ.page == page]

    def retained_entity_rects(self, page: int) -> list[tuple[Rect, str]]:
        """(rect, type) des entités retenues sur la page (overlays colorés)."""
        out: list[tuple[Rect, str]] = []
        for i, occ in enumerate(self._occs):
            if occ.page == page and self._occ_retained(i):
                for r in occ.rects:
                    out.append((r, occ.entity.type))
        return out

    def retained_rects_by_page(self) -> dict[int, list[Rect]]:
        """Tous les rectangles à caviarder par page (entités retenues + manuels)."""
        result: dict[int, list[Rect]] = {}
        for i, occ in enumerate(self._occs):
            if self._occ_retained(i):
                result.setdefault(occ.page, []).extend(occ.rects)
        for page, rects in self._manual.items():
            result.setdefault(page, []).extend(rects)
        return result

    def report(self) -> AuditReport:
        rep = AuditReport()
        for i, occ in enumerate(self._occs):
            if self._occ_retained(i):
                rep.add(occ.entity.type, occ.entity.value,
                        self.ref.tag_for(occ.entity.type), f"page {occ.page + 1}")
        for page, rects in self._manual.items():
            for _r in rects:
                rep.add(_MANUAL_TYPE, "(zone manuelle)", _MANUAL_TAG,
                        f"page {page + 1}")
        return rep
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_review_session.py -v`
Expected: 10 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/pdf_review_session.py tests/test_pdf_review_session.py
git commit -m "feat(pdf): PdfReviewSession — niveaux type/valeur/exclusion + zones manuelles"
```

---

## Task 8 : `PdfScanWorker` — scan threadé

**Files:**
- Create: `anonymator/ui/pdf_scan_worker.py`
- Test: `tests/test_pdf_scan_worker.py`

- [ ] **Step 1 : Écrire le test du worker**

```python
# tests/test_pdf_scan_worker.py
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.pdf_scan_worker import PdfScanWorker


def test_scan_worker_emits_pages(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    worker = PdfScanWorker(src, FakeNer({"Claire Martin": "PERSON"}),
                           Referential.load_default())
    with qtbot.waitSignal(worker.scan_finished, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    pages = blocker.args[0]
    assert pages and pages[0].entities


def test_scan_worker_emits_error_on_scanned(qtbot, tmp_path):
    src = make_scanned_pdf(tmp_path / "s.pdf")
    worker = PdfScanWorker(src, FakeNer({}), Referential.load_default())
    with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    assert "OCR" in blocker.args[0] or "scann" in blocker.args[0].lower()
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_scan_worker.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.ui.pdf_scan_worker'`

- [ ] **Step 3 : Écrire `pdf_scan_worker.py`**

```python
# anonymator/ui/pdf_scan_worker.py
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from anonymator.files.pdf.pdf_io import scan_pdf


class PdfScanWorker(QThread):
    scan_finished = Signal(object)   # list[PageScan]
    error = Signal(str)

    def __init__(self, path: Path, ner, ref):
        super().__init__()
        self._path, self._ner, self._ref = path, ner, ref

    def run(self):
        try:
            self.scan_finished.emit(scan_pdf(self._path, self._ner, self._ref))
        except Exception as exc:   # noqa: BLE001 — remonté à l'UI via error
            self.error.emit(str(exc))
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_scan_worker.py -v`
Expected: 2 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/pdf_scan_worker.py tests/test_pdf_scan_worker.py
git commit -m "feat(pdf): PdfScanWorker — scan threade (miroir FileScanWorker)"
```

---

## Task 9 : `PdfCanvas` — canevas image + overlays + tracé manuel

**Files:**
- Create: `anonymator/ui/pdf_canvas.py`
- Test: `tests/test_pdf_canvas.py`

- [ ] **Step 1 : Écrire les tests du canevas**

```python
# tests/test_pdf_canvas.py
from tests.pdf_fixtures import make_native_pdf
from anonymator.files.pdf import pdf_io
from anonymator.ui.pdf_canvas import PdfCanvas, scene_rect_to_points


def test_scene_to_points_divides_by_zoom_and_orders():
    # scène (20,40)->(60,80) à zoom 2 → points (10,20)->(30,40)
    assert scene_rect_to_points(60, 80, 20, 40, 2.0) == (10.0, 20.0, 30.0, 40.0)


def test_set_page_loads_pixmap(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.set_page(png, zoom=2.0)
    assert c.has_page() is True


def test_set_overlays_draws_items(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.set_page(png, zoom=2.0)
    c.set_overlays([((10, 10, 50, 20), "PERSON")], [(60, 60, 90, 80)])
    assert c.overlay_count() == 2   # 1 entité + 1 zone manuelle


def test_draw_mode_emits_points(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "du texte a afficher")
    png = pdf_io.render_page_at(src, 0)
    c = PdfCanvas(); qtbot.addWidget(c)
    c.set_page(png, zoom=2.0)
    c.set_draw_mode(True)
    captured = {}
    c.manual_rect_drawn.connect(lambda r: captured.setdefault("r", r))
    c._finish_manual((20, 40), (60, 80))   # helper interne : coords scène
    assert captured["r"] == (10.0, 20.0, 30.0, 40.0)
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_canvas.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.ui.pdf_canvas'`

- [ ] **Step 3 : Écrire `pdf_canvas.py`**

```python
# anonymator/ui/pdf_canvas.py
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PySide6.QtGui import QImage, QPixmap, QColor, QPen, QBrush
from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from anonymator.ui.colors import color_for

Rect = tuple[float, float, float, float]


def scene_rect_to_points(x0: float, y0: float, x1: float, y1: float,
                         zoom: float) -> Rect:
    """Convertit un rectangle en coordonnées scène (pixels) vers des points PDF,
    en normalisant l'ordre des coins."""
    return (min(x0, x1) / zoom, min(y0, y1) / zoom,
            max(x0, x1) / zoom, max(y0, y1) / zoom)


class PdfCanvas(QGraphicsView):
    """Affiche une page rendue + overlays de rectangles. En mode tracé, un
    glisser produit un rectangle manuel (émis en points PDF)."""

    manual_rect_drawn = Signal(tuple)   # (x0, y0, x1, y1) en points PDF

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setRenderHints(self.renderHints())
        self._zoom = 2.0
        self._pixmap_item = None
        self._overlay_items: list[QGraphicsRectItem] = []
        self._draw_mode = False
        self._origin: QPointF | None = None
        self._rubber: QGraphicsRectItem | None = None

    def has_page(self) -> bool:
        return self._pixmap_item is not None

    def overlay_count(self) -> int:
        return len(self._overlay_items)

    def set_draw_mode(self, on: bool) -> None:
        self._draw_mode = on
        self.setCursor(Qt.CrossCursor if on else Qt.ArrowCursor)

    def set_page(self, png: bytes, zoom: float) -> None:
        self._zoom = zoom
        self._scene.clear()
        self._overlay_items = []
        self._rubber = None
        img = QImage.fromData(png, "PNG")
        self._pixmap_item = self._scene.addPixmap(QPixmap.fromImage(img))
        self._scene.setSceneRect(self._pixmap_item.boundingRect())

    def set_overlays(self, entity_rects: list[tuple[Rect, str]],
                     manual_rects: list[Rect]) -> None:
        for item in self._overlay_items:
            self._scene.removeItem(item)
        self._overlay_items = []
        for rect, etype in entity_rects:
            self._add_overlay(rect, QColor(color_for(etype)), dashed=False)
        for rect in manual_rects:
            self._add_overlay(rect, QColor("#20202A"), dashed=True)

    def _add_overlay(self, rect: Rect, color: QColor, dashed: bool) -> None:
        x0, y0, x1, y1 = (v * self._zoom for v in rect)
        item = QGraphicsRectItem(QRectF(x0, y0, x1 - x0, y1 - y0))
        pen = QPen(color); pen.setWidth(2)
        if dashed:
            pen.setStyle(Qt.DashLine)
        item.setPen(pen)
        fill = QColor(color); fill.setAlpha(70)
        item.setBrush(QBrush(fill))
        self._scene.addItem(item)
        self._overlay_items.append(item)

    # --- tracé manuel ---
    def mousePressEvent(self, event):
        if self._draw_mode and event.button() == Qt.LeftButton and self.has_page():
            self._origin = self.mapToScene(event.position().toPoint())
            self._rubber = QGraphicsRectItem()
            pen = QPen(QColor("#20202A")); pen.setStyle(Qt.DashLine); pen.setWidth(2)
            self._rubber.setPen(pen)
            self._scene.addItem(self._rubber)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._rubber is not None and self._origin is not None:
            cur = self.mapToScene(event.position().toPoint())
            self._rubber.setRect(QRectF(self._origin, cur).normalized())
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._rubber is not None and self._origin is not None:
            cur = self.mapToScene(event.position().toPoint())
            self._scene.removeItem(self._rubber)
            self._rubber = None
            self._finish_manual((self._origin.x(), self._origin.y()),
                                (cur.x(), cur.y()))
            self._origin = None
            return
        super().mouseReleaseEvent(event)

    def _finish_manual(self, p0: tuple[float, float],
                       p1: tuple[float, float]) -> None:
        pts = scene_rect_to_points(p0[0], p0[1], p1[0], p1[1], self._zoom)
        # ignore les tracés dégénérés (clic sans glisser)
        if pts[2] - pts[0] < 1 or pts[3] - pts[1] < 1:
            return
        self.manual_rect_drawn.emit(pts)
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_canvas.py -v`
Expected: 4 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/pdf_canvas.py tests/test_pdf_canvas.py
git commit -m "feat(pdf): PdfCanvas — image de page + overlays + trace manuel (rubber-band)"
```

---

## Task 10 : `PdfScreen` — écran dédié (canevas + panneau + 2 modes)

**Files:**
- Create: `anonymator/ui/pdf_screen.py`
- Test: `tests/test_pdf_screen.py`

- [ ] **Step 1 : Écrire les tests d'écran**

```python
# tests/test_pdf_screen.py
from datetime import datetime
from unittest.mock import patch
import fitz
from tests.pdf_fixtures import make_native_pdf, make_scanned_pdf
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.pdf_screen import PdfScreen


def _screen(mapping=None, out=None):
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer(mapping or {}))
    prefs = Preferences(output_dir=str(out)) if out else Preferences()
    return PdfScreen(ref, loader, prefs, on_back=lambda: None)


def test_load_enables_analyze(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.btn_review.isEnabled() is True


def test_analyze_builds_session_and_side(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.count_retained("PERSON") == 1
    assert s.side.topLevelItemCount() == 1


def test_redact_run_writes_destroyed_pdf(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    res = s.run_redact(when=datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".pdf"
    check = fitz.open(str(res.output_path))
    assert "Claire Martin" not in check[0].get_text()
    check.close()


def test_text_run_writes_masked_txt(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src))
    res = s.run_text(when=datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".txt"
    out = res.output_path.read_text(encoding="utf-8")
    assert "[PERSONNE]" in out and "Claire Martin" not in out


def test_manual_rect_added_to_session(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s._on_manual_rect((300.0, 300.0, 360.0, 330.0))
    assert (300.0, 300.0, 360.0, 330.0) in s.session.manual_rects(0)


def test_scanned_pdf_shows_error(qtbot, tmp_path):
    src = make_scanned_pdf(tmp_path / "s.pdf")
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    with patch("anonymator.ui.pdf_screen.QMessageBox.warning") as warn:
        s.analyze()
        qtbot.waitUntil(lambda: warn.called, timeout=5000)
    assert warn.called
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_screen.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.ui.pdf_screen'`

- [ ] **Step 3 : Écrire `pdf_screen.py`**

```python
# anonymator/ui/pdf_screen.py
from datetime import datetime
from pathlib import Path
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QFileDialog, QMessageBox, QTreeWidget,
                               QTreeWidgetItem, QHeaderView)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from anonymator.files.pdf import pdf_io
from anonymator.files.pdf.extract import (
    ScannedPdfNotSupported, EncryptedPdfError, CorruptPdfError)
from anonymator.files.pdf.render import RENDER_ZOOM
from anonymator.output_naming import anonymized_path
from anonymator.files.anonymize_file import FileResult
from anonymator.core.pdf_review_session import PdfReviewSession
from anonymator.ui.pdf_scan_worker import PdfScanWorker
from anonymator.ui.pdf_canvas import PdfCanvas
from anonymator.ui.colors import color_for
from anonymator.ui.icons import icon
from anonymator.ui.components.header import HeaderBand
from anonymator.ui.components.cards import Card
from anonymator.ui.components.banner import ModelBanner
from anonymator.core.model_status import is_model_available
from anonymator.ner import NullNer


class PdfScreen(QWidget):
    def __init__(self, ref, loader, prefs, on_back, on_request_model=None):
        super().__init__()
        self.ref, self.loader, self.prefs = ref, loader, prefs
        self.on_request_model = on_request_model
        self.path: Path | None = None
        self.session: PdfReviewSession | None = None
        self.page = 0
        self._page_count = 0
        self._busy = False
        self._degraded = False
        self._worker: PdfScanWorker | None = None
        self._png_cache: dict[int, bytes] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0); root.setSpacing(0)
        root.addWidget(HeaderBand())
        self.banner = ModelBanner(on_install=self._request_model)
        root.addWidget(self.banner)

        # ---- barre d'action ----
        bar = QHBoxLayout(); bar.setContentsMargins(18, 14, 18, 8); bar.setSpacing(12)
        self._file_ic = QLabel(); self._file_ic.setPixmap(icon("document", "#00965E").pixmap(22, 22))
        info_col = QVBoxLayout(); info_col.setSpacing(1)
        self.name_label = QLabel("Aucun PDF"); self.name_label.setObjectName("fileName")
        self.meta_label = QLabel("Importez un fichier .pdf natif (texte sélectionnable)")
        self.meta_label.setObjectName("fileMeta")
        info_col.addWidget(self.name_label); info_col.addWidget(self.meta_label)
        bar.addWidget(self._file_ic); bar.addLayout(info_col); bar.addStretch()

        self.btn_open = QPushButton("  Ouvrir"); self.btn_open.setObjectName("ghost")
        self.btn_open.setIcon(icon("folder", "#00965E")); self.btn_open.clicked.connect(self._open)
        self.btn_review = QPushButton("  Analyser"); self.btn_review.setObjectName("primary")
        self.btn_review.setIcon(icon("scan", "white"))
        self.btn_review.setEnabled(False); self.btn_review.clicked.connect(self.analyze)
        self.btn_zone = QPushButton("  Zone manuelle"); self.btn_zone.setObjectName("ghost")
        self.btn_zone.setCheckable(True); self.btn_zone.setIcon(icon("scan", "#6B7C72"))
        self.btn_zone.toggled.connect(self._toggle_zone)
        self.btn_redact = QPushButton("  Caviarder (PDF)"); self.btn_redact.setObjectName("info")
        self.btn_redact.setIcon(icon("shield", "white")); self.btn_redact.clicked.connect(self._redact_clicked)
        self.btn_text = QPushButton("  Extraire en .txt"); self.btn_text.setObjectName("ghost")
        self.btn_text.setIcon(icon("document", "#6B7C72")); self.btn_text.clicked.connect(self._text_clicked)
        self.btn_back = QPushButton("  Accueil"); self.btn_back.setObjectName("ghost")
        self.btn_back.setIcon(icon("home", "#6B7C72")); self.btn_back.clicked.connect(on_back)
        for b in (self.btn_open, self.btn_review, self.btn_zone,
                  self.btn_redact, self.btn_text, self.btn_back):
            bar.addWidget(b)
        root.addLayout(bar)

        # ---- corps : canevas (gauche) + entités (droite) ----
        self.canvas = PdfCanvas()
        self.canvas.manual_rect_drawn.connect(self._on_manual_rect)
        canvas_card = Card("document", "Aperçu de la page")
        canvas_card.body.addWidget(self.canvas)

        self.side = QTreeWidget()
        self.side.setHeaderHidden(True); self.side.setColumnCount(2)
        self.side.setRootIsDecorated(True)
        self.side.header().setStretchLastSection(False)
        self.side.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.side.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.side.itemChanged.connect(self._on_side_changed)
        ent_card = Card("shield", "Entités détectées")
        hint = QLabel("Décochez pour conserver en clair. Bouton « Zone manuelle » "
                      "pour caviarder un tampon/signature non détecté.")
        hint.setObjectName("hint"); hint.setWordWrap(True)
        ent_card.body.addWidget(hint); ent_card.body.addWidget(self.side)
        self.side.hide()

        body = QHBoxLayout(); body.setContentsMargins(18, 0, 18, 8); body.setSpacing(12)
        body.addWidget(canvas_card, 3); body.addWidget(ent_card, 2)
        root.addLayout(body, 1)

        # ---- pagination ----
        self.pager = QHBoxLayout(); self.pager.setContentsMargins(18, 6, 18, 14)
        self.btn_prev = QPushButton("‹ Précédent"); self.btn_prev.setObjectName("pager")
        self.btn_prev.clicked.connect(lambda: self._go(self.page - 1))
        self.lbl_page = QLabel(""); self.lbl_page.setObjectName("pageInfo")
        self.lbl_page.setAlignment(Qt.AlignCenter)
        self.btn_next = QPushButton("Suivant ›"); self.btn_next.setObjectName("pager")
        self.btn_next.clicked.connect(lambda: self._go(self.page + 1))
        self.pager.addWidget(self.btn_prev); self.pager.addStretch()
        self.pager.addWidget(self.lbl_page); self.pager.addStretch()
        self.pager.addWidget(self.btn_next)
        self.pager_widget = QWidget(); self.pager_widget.setLayout(self.pager); self.pager_widget.hide()
        root.addWidget(self.pager_widget)

    # ---------- ouverture ----------
    def _open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un PDF", "", "PDF (*.pdf)")
        if path:
            self.load_path(path)

    def load_path(self, path: str):
        self.path = Path(path)
        self.session = None
        self._png_cache = {}
        self.side.hide(); self.pager_widget.hide()
        self.btn_zone.setChecked(False)
        self.btn_review.setEnabled(self.path.suffix.lower() == ".pdf")
        self.name_label.setText(self.path.name)
        self.meta_label.setText("Fichier PDF — cliquez « Analyser »")

    # ---------- analyse ----------
    def analyze(self):
        if self._worker and self._worker.isRunning():
            return
        if not self.path:
            return
        self._degraded = not (self.loader.has_detector() or is_model_available())
        ner = NullNer() if self._degraded else self.loader.get()
        self._set_busy(True)
        self._worker = PdfScanWorker(self.path, ner, self.ref)
        self._worker.scan_finished.connect(self._on_scanned)
        self._worker.error.connect(self._on_scan_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _set_busy(self, busy: bool):
        self._busy = busy
        for b in (self.btn_review, self.btn_redact, self.btn_text, self.btn_open):
            b.setEnabled(not busy)
        self.setCursor(Qt.BusyCursor if busy else Qt.ArrowCursor)

    def _on_scan_error(self, msg):
        self._set_busy(False)
        QMessageBox.warning(self, "PDF non exploitable", msg)

    def _on_scanned(self, pages):
        self.session = PdfReviewSession(pages, self.ref)
        self._page_count = len(pages)
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        self.page = 0
        self._build_side()
        self.side.show()
        self.pager_widget.setVisible(self._page_count > 1)
        self._render_page()

    # ---------- panneau latéral (même structure que FileScreen) ----------
    def _build_side(self):
        bold = QFont(); bold.setBold(True)
        self.side.blockSignals(True); self.side.clear()
        for t in self.session.types():
            top = QTreeWidgetItem([t, f"×{self.session.count_retained(t)}"])
            top.setForeground(0, QColor(color_for(t)))
            top.setForeground(1, QColor("#6B7C72"))
            top.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
            top.setFont(0, bold)
            top.setData(0, Qt.UserRole, ("type", t, None))
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable)
            top.setCheckState(0, Qt.Checked if self.session.is_type_enabled(t) else Qt.Unchecked)
            for value, n in self.session.values_for(t):
                child = QTreeWidgetItem([value, f"×{n}"])
                child.setForeground(1, QColor("#9aa8a0"))
                child.setTextAlignment(1, Qt.AlignRight | Qt.AlignVCenter)
                child.setData(0, Qt.UserRole, ("value", t, value))
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Checked if self.session.is_value_enabled(t, value) else Qt.Unchecked)
                top.addChild(child)
            self.side.addTopLevelItem(top)
        self.side.expandAll()
        self.side.blockSignals(False)

    def _on_side_changed(self, item, _col):
        if self.session is None:
            return
        kind, etype, value = item.data(0, Qt.UserRole)
        checked = item.checkState(0) == Qt.Checked
        if kind == "type":
            self.session.set_type_enabled(etype, checked)
        else:
            self.session.set_value_enabled(etype, value, checked)
        self._refresh_counts()
        self._render_page()

    def _refresh_counts(self):
        for i in range(self.side.topLevelItemCount()):
            top = self.side.topLevelItem(i)
            _, t, _ = top.data(0, Qt.UserRole)
            top.setText(1, f"×{self.session.count_retained(t)}")

    # ---------- rendu page + overlays ----------
    def _png_for(self, page_index: int) -> bytes:
        if page_index not in self._png_cache:
            self._png_cache[page_index] = pdf_io.render_page_at(self.path, page_index)
        return self._png_cache[page_index]

    def _render_page(self):
        if self.session is None:
            return
        self.canvas.set_page(self._png_for(self.page), RENDER_ZOOM)
        self.canvas.set_overlays(self.session.retained_entity_rects(self.page),
                                 self.session.manual_rects(self.page))
        self.lbl_page.setText(f"Page {self.page + 1} / {self._page_count}")
        self.btn_prev.setEnabled(self.page > 0)
        self.btn_next.setEnabled(self.page < self._page_count - 1)

    def _go(self, page: int):
        self.page = max(0, min(page, self._page_count - 1))
        self._render_page()

    # ---------- zone manuelle ----------
    def _toggle_zone(self, on: bool):
        self.canvas.set_draw_mode(on)

    def _on_manual_rect(self, rect: tuple):
        if self.session is not None:
            self.session.add_manual_rect(self.page, rect)
            self._render_page()

    # ---------- exécution ----------
    def run_redact(self, when: datetime | None = None) -> FileResult | None:
        if self.session is None or not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        rects = self.session.retained_rects_by_page()
        out = pdf_io.anonymize_pdf_redact(self.path, rects, out_dir, when)
        return FileResult(out, self.session.report())

    def run_text(self, when: datetime | None = None) -> FileResult | None:
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        try:
            ner = self.loader.get()
            return pdf_io.anonymize_pdf_text(self.path, ner, self.ref, out_dir, when)
        except (ScannedPdfNotSupported, EncryptedPdfError, CorruptPdfError) as e:
            QMessageBox.warning(self, "PDF non exploitable", str(e))
            return None

    def _redact_clicked(self):
        if self.session is None:
            QMessageBox.information(self, "Analysez d'abord",
                                    "Cliquez « Analyser » avant de caviarder.")
            return
        confirm = QMessageBox.question(
            self, "Confirmer la rédaction",
            "La rédaction détruit définitivement les données sélectionnées "
            "dans le PDF de sortie. Continuer ?")
        if confirm != QMessageBox.Yes:
            return
        res = self.run_redact()
        if res is not None:
            QMessageBox.information(self, "PDF caviardé",
                                    f"Fichier enregistré :\n{res.output_path}")

    def _text_clicked(self):
        if not self.path:
            QMessageBox.information(self, "Aucun PDF", "Ouvrez d'abord un PDF.")
            return
        res = self.run_text()
        if res is not None:
            QMessageBox.information(self, "Texte extrait",
                                    f"Fichier enregistré :\n{res.output_path}")

    def _request_model(self):
        if self.on_request_model is not None:
            self.on_request_model()

    def hide_degraded(self):
        self._degraded = False
        self.banner.setVisible(False)
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_pdf_screen.py -v`
Expected: 6 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/pdf_screen.py tests/test_pdf_screen.py
git commit -m "feat(pdf): PdfScreen dedie — canevas + panneau reutilise + modes redaction/texte + zone manuelle"
```

---

## Task 11 : Câblage application (`main_window` + `home_screen`)

**Files:**
- Modify: `anonymator/ui/main_window.py`
- Modify: `anonymator/ui/home_screen.py`
- Test: `tests/test_main_window_pdf.py`

- [ ] **Step 1 : Écrire le test de câblage**

```python
# tests/test_main_window_pdf.py
from unittest.mock import patch
from anonymator.ui.main_window import MainWindow


def test_main_window_has_pdf_screen(qtbot, tmp_path):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        w = MainWindow(prefs_path=tmp_path / "p.json")
        qtbot.addWidget(w)
    assert hasattr(w, "pdf_screen")
    w.show_pdf()
    assert w.stack.currentWidget() is w.pdf_screen


def test_apply_prefs_updates_pdf_ref(qtbot, tmp_path):
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        w = MainWindow(prefs_path=tmp_path / "p.json")
        qtbot.addWidget(w)
    sentinel = object()
    w.ref = sentinel
    with patch.object(w, "_build_ref", return_value=sentinel):
        w._apply_prefs()
    assert w.pdf_screen.ref is sentinel


def test_home_has_pdf_card(qtbot):
    from anonymator.ui.home_screen import HomeScreen
    calls = {}
    h = HomeScreen(lambda: None, lambda: None, lambda: None,
                   on_pdf=lambda: calls.setdefault("pdf", True))
    qtbot.addWidget(h)
    h.btn_pdf.click()
    assert calls.get("pdf") is True
```

- [ ] **Step 2 : Lancer pour vérifier l'échec**

Run: `.venv/Scripts/python -m pytest tests/test_main_window_pdf.py -v`
Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute 'pdf_screen'` (et `HomeScreen` n'accepte pas `on_pdf`)

- [ ] **Step 3a : Ajouter la NavCard PDF à `home_screen.py`**

Modifier la signature du constructeur (ligne 36-37) :

```python
    def __init__(self, on_text, on_file, on_settings,
                 model_available: bool = True, on_download=None, on_dismiss=None,
                 on_pdf=None):
```

Puis, dans le bloc des NavCards (après `self.btn_file = NavCard(...)`, avant `self.btn_settings`), ajouter la carte PDF et l'inclure dans la boucle d'ajout :

```python
        self.btn_file = NavCard("folder", "Importer un fichier",
                                ".txt, .csv ou .xlsx", on_click=on_file)
        self.btn_pdf = NavCard("document", "Importer un PDF",
                               "Caviarder ou extraire (PDF natifs)", on_click=on_pdf)
        self.btn_settings = NavCard("settings", "Paramètres",
                                    "Règles de détection & masquage", on_click=on_settings)
        for c in (self.btn_text, self.btn_file, self.btn_pdf, self.btn_settings):
            rv.addWidget(c)
```

- [ ] **Step 3b : Câbler `PdfScreen` dans `main_window.py`**

Ajouter l'import (après l'import de `FileScreen`, ligne 11) :

```python
from anonymator.ui.pdf_screen import PdfScreen
```

Dans `__init__`, après la création de `self.file_screen` (ligne 41-43), ajouter :

```python
        self.pdf_screen = PdfScreen(self.ref, self.loader, self.prefs,
                                    self.show_home, on_request_model=self._request_model)
```

Ajouter `self.pdf_screen` au tuple des widgets empilés (ligne 46) :

```python
        for w in (self.home, self.text_screen, self.file_screen,
                  self.pdf_screen, self.settings_screen):
            self.stack.addWidget(w)
```

Passer `on_pdf` à `HomeScreen` (ligne 36-38) :

```python
        self.home = HomeScreen(self.show_text, self.show_file, self.show_settings,
                               model_available=is_model_available(),
                               on_download=self._request_model,
                               on_pdf=self.show_pdf)
```

Dans `_apply_prefs` (après `self.file_screen.ref = self.ref`, ligne 67) :

```python
        self.pdf_screen.ref = self.ref
```

Dans `_on_model_ready` (après `self.file_screen.hide_degraded()`, ligne 76) :

```python
        self.pdf_screen.hide_degraded()
```

Ajouter la méthode de navigation (à côté de `show_file`, ligne 96-97) :

```python
    def show_pdf(self):
        self.stack.setCurrentWidget(self.pdf_screen)
```

- [ ] **Step 4 : Lancer pour vérifier le succès**

Run: `.venv/Scripts/python -m pytest tests/test_main_window_pdf.py -v`
Expected: 3 passed

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/main_window.py anonymator/ui/home_screen.py tests/test_main_window_pdf.py
git commit -m "feat(pdf): cablage app — carte accueil + PdfScreen dans MainWindow"
```

---

## Task 12 : Packaging (spec PyInstaller + README)

**Files:**
- Modify: `anonymator.spec`
- Modify: `README.md`

- [ ] **Step 1 : Ajouter les hidden imports PDF à `anonymator.spec`**

Dans la liste `hiddenimports=[...]`, ajouter (après `'anonymator.files.txt_io',`) :

```python
        'anonymator.files.pdf.extract',
        'anonymator.files.pdf.mapping',
        'anonymator.files.pdf.redact',
        'anonymator.files.pdf.render',
        'anonymator.files.pdf.pdf_io',
        'anonymator.core.pdf_review_session',
        'anonymator.ui.pdf_scan_worker',
        'anonymator.ui.pdf_canvas',
        'anonymator.ui.pdf_screen',
        'fitz',
        'pymupdf',
```

- [ ] **Step 2 : Mettre à jour le tableau des formats du `README.md`**

Remplacer la ligne (README.md:52) :

```
| `.pdf` | ❌ Non supporté en v1 |
```

par :

```
| `.pdf` | ✅ PDF natifs : caviardage (destruction réelle) ou extraction .txt. Scannés (image seule) non supportés. |
```

Puis remplacer la ligne du tableau des erreurs (README.md:71) :

```
| `.pdf` refusé | Non supporté en v1 |
```

par :

```
| `.pdf` scanné (image seule) | OCR non supporté en v1 — message clair, aucun plantage |
```

- [ ] **Step 3 : Vérifier la suite complète**

Run: `.venv/Scripts/python -m pytest -q`
Expected: tous les tests passent (194 existants + les nouveaux tests PDF), 1 deselected (intégration GLiNER).

- [ ] **Step 4 : Commit**

```bash
git add anonymator.spec README.md
git commit -m "build(pdf): hidden imports PyInstaller + README formats (.pdf actif)"
```

---

## Notes d'intégration & risques

- **Build PyInstaller (à valider manuellement)** : PyMuPDF embarque MuPDF via son propre hook `pyinstaller-hooks-contrib`. Après ce plan, refaire un build (`.venv/Scripts/pyinstaller anonymator.spec`) et vérifier qu'un `.pdf` s'ouvre dans l'exe. Si `fitz` ne se charge pas, ajouter `--collect-all pymupdf` ou un hook. Hors périmètre des tests automatisés.
- **Conformité AGPL** : PyMuPDF est AGPL-3.0. Le spec [conformité AGPL](../specs/2026-07-01-conformite-agpl-design.md) doit être implémenté **avant de distribuer** un exe embarquant PyMuPDF (LICENSE AGPL, écran « À propos », `__version__`). Ce plan livre la fonctionnalité ; la distribution reste bloquée tant que la conformité n'est pas faite.
- **Seuil natif/scanné** (`MIN_CHARS_PER_PAGE = 10`) : à recalibrer si de vrais PDF natifs pauvres en texte sont rejetés à tort. Documenté dans `extract.py`.
- **PDF mixtes** (certaines pages scannées) : v1 accepte le doc dès qu'**une** page a du texte ; les pages sans texte ne produisent aucune entité et ne sont pas caviardées (pas de plantage). Amélioration (avertissement explicite par page) remise à plus tard.

---

## Self-Review (effectuée)

**Couverture du spec :** extract/classify (T2) · pont offset→rects multi-lignes (T3) · destruction réelle + purge métadonnées (T4, test pivot) · rendu aperçu (T5) · orchestration + mode texte + mode rédaction (T6) · `PdfReviewSession` non-Qt (T7) · `PdfScanWorker` (T8) · canevas + overlays + **zone manuelle** (T9, décision v1) · **écran dédié** (T10, décision v1) · câblage app (T11) · packaging requirements/spec/README/filtre QFileDialog (T0+T12). Gestion d'erreurs scanné/chiffré/corrompu couverte (T2 + T8 + T10). Entité non mappable → liste vide sans blocage (T3). Tous les cas du tableau §5 du spec sont adressés.

**Cohérence des types :** `WordBox`/`PageText` (extract) → `mapping` → `PageScan` (pdf_io) → `PdfReviewSession`. `PdfReviewSession` expose les mêmes noms de méthodes que `FileReviewSession` (`types`, `count_retained`, `values_for`, `is_type_enabled`, `set_type_enabled`, `is_value_enabled`, `set_value_enabled`) → le panneau latéral est réutilisé à l'identique. `Rect = tuple[float,float,float,float]` utilisé de bout en bout. `RENDER_ZOOM` défini dans `render.py`, réimporté par `pdf_screen`. `FileResult` réutilisé pour les deux modes.
