# Uniformisation détection PDF — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Détecter et caviarder de façon cohérente toute occurrence d'une donnée sensible dans un PDF, où qu'elle apparaisse.

**Architecture:** Trois axes greffés au niveau détection (`scan_pdf`), sans toucher l'UI ni la revue : (C) un motif regex d'adresse déterministe, (D) une reconstruction du texte qui garde les phrases contiguës et relègue le texte de marge pivoté, (A) une propagation tout-document qui réplique chaque valeur confirmée à toutes ses occurrences.

**Tech Stack:** Python, PyMuPDF (`fitz`), pytest.

**Réf. spec :** `docs/superpowers/specs/2026-07-01-pdf-detection-uniformisation-design.md`

**Conventions :** tests lancés depuis la racine du repo avec `python -m pytest`. Chaque commit se termine par la ligne `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure

- `anonymator/deterministic.py` — **modifié** : ajout du motif `ADDRESS`.
- `anonymator/files/pdf/extract.py` — **modifié** : réordonnancement des blocs dans `extract_page` + helper `_block_is_vertical`.
- `anonymator/files/pdf/propagate.py` — **créé** : propagation tout-document.
- `anonymator/files/pdf/pdf_io.py` — **modifié** : `scan_pdf` appelle la propagation.
- `tests/test_deterministic.py` — **modifié** : cas ADDRESS.
- `tests/test_pdf_extract.py` — **modifié** : ordre de lecture.
- `tests/pdf_fixtures.py` — **modifié** : fixtures `make_layout_pdf`, `make_repeat_pdf`.
- `tests/test_pdf_propagate.py` — **créé** : propagation (unitaire).
- `tests/test_pdf_io.py` — **modifié** : intégration propagation.

---

## Task 1: C — Adresse déterministe

**Files:**
- Modify: `anonymator/deterministic.py`
- Test: `tests/test_deterministic.py`

- [ ] **Step 1: Write the failing tests**

Ajouter à la fin de `tests/test_deterministic.py` :

```python
def test_detects_address_street_line():
    assert ("ADDRESS", "16 RUE JEROME BONAPARTE") in types_at(
        "16 RUE JEROME BONAPARTE")


def test_detects_address_case_insensitive():
    vals = {v for (t, v) in types_at("12 avenue des Champs") if t == "ADDRESS"}
    assert "12 avenue des Champs" in vals


def test_detects_address_with_bis():
    vals = {v for (t, v) in types_at("5 bis rue du Four") if t == "ADDRESS"}
    assert "5 bis rue du Four" in vals


def test_address_stops_at_newline():
    vals = {v for (t, v) in types_at("16 RUE JEROME BONAPARTE\n91300 MASSY")
            if t == "ADDRESS"}
    assert "16 RUE JEROME BONAPARTE" in vals


def test_postal_city_not_matched_as_address():
    assert all(t != "ADDRESS" for (t, v) in types_at("91300 MASSY"))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_deterministic.py -k address -v`
Expected: FAIL (aucune entité `ADDRESS` produite).

- [ ] **Step 3: Add the ADDRESS pattern**

Dans `anonymator/deterministic.py`, insérer cette entrée dans la liste `_PATTERNS` (juste avant l'entrée `POSTAL_CODE`) :

```python
    (re.compile(
        r"\b\d{1,4}(?:\s?(?:bis|ter|quater))?[,\s]+"
        r"(?:rue|avenue|av|ave|bd|bld|boulevard|impasse|all[ée]e|allee|"
        r"chemin|place|route|rte|quai|cours|passage|square|villa|voie|"
        r"faubourg|fbg|sentier|r[ée]sidence|residence)\b[^\n]*",
        re.IGNORECASE),
     "ADDRESS", None),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_deterministic.py -v`
Expected: PASS (anciens + nouveaux).

- [ ] **Step 5: Commit**

```bash
git add anonymator/deterministic.py tests/test_deterministic.py
git commit -m "feat(detect): motif adresse deterministe (ligne de voie FR)"
```

---

## Task 2: D — Ordre de lecture (léger)

**Files:**
- Modify: `anonymator/files/pdf/extract.py`
- Modify: `tests/pdf_fixtures.py`
- Test: `tests/test_pdf_extract.py`

- [ ] **Step 1: Add the layout fixture**

Ajouter à `tests/pdf_fixtures.py` :

```python
def make_layout_pdf(path: Path) -> Path:
    """Deux colonnes horizontales + un bloc de marge pivoté (vertical)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 120), "Titulaire GUILLAUME DROGLAND", fontsize=11)
    page.insert_text((330, 120), "Montant total", fontsize=11)
    page.insert_text((40, 400), "Vagram Paris Cedex", fontsize=9, rotate=90)
    doc.save(str(path))
    doc.close()
    return path
```

- [ ] **Step 2: Write the failing tests**

Ajouter à `tests/test_pdf_extract.py` (et compléter l'import de fixtures en tête) :

```python
from tests.pdf_fixtures import (make_native_pdf, make_scanned_pdf,
                                make_encrypted_pdf, make_layout_pdf)


def test_block_is_vertical_detects_rotated():
    words = [(0, 0, 5, 40, "Vagram", 0, 0, 0),
             (0, 45, 5, 90, "Paris", 0, 1, 0)]
    assert extract._block_is_vertical(words) is True


def test_block_is_vertical_false_for_normal_text():
    words = [(0, 0, 60, 12, "Titulaire", 0, 0, 0),
             (65, 0, 140, 12, "DROGLAND", 0, 0, 1)]
    assert extract._block_is_vertical(words) is False


def test_extract_page_keeps_phrase_contiguous(tmp_path):
    p = make_layout_pdf(tmp_path / "l.pdf")
    doc = extract.open_document(p)
    pt = extract.extract_page(doc[0], 0)
    doc.close()
    assert "GUILLAUME DROGLAND" in pt.text


def test_extract_page_relegates_vertical_margin(tmp_path):
    p = make_layout_pdf(tmp_path / "l.pdf")
    doc = extract.open_document(p)
    pt = extract.extract_page(doc[0], 0)
    doc.close()
    assert "Vagram" in pt.text
    assert pt.text.index("Titulaire") < pt.text.index("Vagram")
    assert pt.text.index("Montant") < pt.text.index("Vagram")
```

Note : la première ligne remplace l'`import` de fixtures existant en tête de fichier.

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_pdf_extract.py -v`
Expected: FAIL (`_block_is_vertical` inexistant ; marge non reléguée).

- [ ] **Step 4: Implement block reordering**

Dans `anonymator/files/pdf/extract.py`, remplacer la fonction `extract_page` par le bloc suivant (et garder le reste du fichier intact) :

```python
def _block_is_vertical(block_words) -> bool:
    """Vrai si les mots (≥2 car.) du bloc sont majoritairement plus hauts
    que larges — signe d'un texte de marge pivoté."""
    votes = total = 0
    for x0, y0, x1, y1, text, *_ in block_words:
        if len(text) < 2:
            continue
        total += 1
        if (y1 - y0) > (x1 - x0):
            votes += 1
    return total > 0 and votes * 2 > total


def _ordered_words(words):
    """Regroupe par bloc, ordonne les blocs horizontaux haut→bas/gauche→droite,
    relègue les blocs verticaux en fin, conserve (ligne, mot) dans chaque bloc."""
    blocks: dict[int, list] = {}
    for w in words:
        blocks.setdefault(w[5], []).append(w)
    horizontal, vertical = [], []
    for bw in blocks.values():
        y0 = min(w[1] for w in bw)
        x0 = min(w[0] for w in bw)
        (vertical if _block_is_vertical(bw) else horizontal).append((y0, x0, bw))
    horizontal.sort(key=lambda e: (round(e[0] / 10) * 10, e[1]))
    vertical.sort(key=lambda e: (e[1], e[0]))
    ordered: list = []
    for _y, _x, bw in horizontal + vertical:
        ordered.extend(sorted(bw, key=lambda w: (w[6], w[7])))
    return ordered


def extract_page(page: "fitz.Page", page_index: int) -> PageText:
    """Reconstruit le texte plat en ordre de lecture + une WordBox par mot."""
    ordered = _ordered_words(page.get_text("words"))
    parts: list[str] = []
    boxes: list[WordBox] = []
    cursor = 0
    prev_line: tuple[int, int] | None = None
    for x0, y0, x1, y1, text, block, line, _wno in ordered:
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pdf_extract.py -v`
Expected: PASS (anciens tests d'extraction inclus).

- [ ] **Step 6: Commit**

```bash
git add anonymator/files/pdf/extract.py tests/test_pdf_extract.py tests/pdf_fixtures.py
git commit -m "feat(pdf): ordre de lecture — blocs ordonnes, marge verticale releguee"
```

---

## Task 3: A — Module de propagation

**Files:**
- Create: `anonymator/files/pdf/propagate.py`
- Test: `tests/test_pdf_propagate.py`

- [ ] **Step 1: Write the failing tests**

Créer `tests/test_pdf_propagate.py` :

```python
# tests/test_pdf_propagate.py
from anonymator.files.pdf.extract import PageText, WordBox
from anonymator.model import Entity
from anonymator.files.pdf import propagate


def _page(idx, words):
    """PageText jouet : offsets cohérents, rects factices."""
    boxes, parts, cursor = [], [], 0
    for i, w in enumerate(words):
        if i:
            parts.append(" "); cursor += 1
        start = cursor
        parts.append(w); cursor += len(w)
        boxes.append(WordBox(w, (0.0, 0.0, 1.0, 1.0), start, cursor))
    return PageText(idx, "".join(parts), boxes)


def _seed(page, i0, i1, etype, value):
    """Entité 'ner' couvrant les WordBox [i0, i1] de la page."""
    return Entity(etype, value, page.words[i0].char_start,
                  page.words[i1].char_end, "ner", 0.9, True)


def test_propagates_value_to_other_page():
    p0 = _page(0, ["Titulaire", "GUILLAUME", "DROGLAND"])
    p1 = _page(1, ["Client", "GUILLAUME", "DROGLAND", "ici"])
    ent = _seed(p0, 1, 2, "PERSON", "GUILLAUME DROGLAND")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    hits = [e for e in out[1]
            if e.type == "PERSON" and e.value == "GUILLAUME DROGLAND"]
    assert len(hits) == 1
    assert p1.text[hits[0].start:hits[0].end] == "GUILLAUME DROGLAND"
    assert hits[0].source == "propagated"


def test_numeric_only_value_not_propagated():
    p0 = _page(0, ["numero", "16"])
    p1 = _page(1, ["rue", "16", "bis"])
    ent = _seed(p0, 1, 1, "PERSON", "16")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert all(e.value != "16" for e in out[1])


def test_short_single_token_not_propagated():
    p0 = _page(0, ["particule", "Le"])
    p1 = _page(1, ["Le", "grand", "Le"])
    ent = _seed(p0, 1, 1, "PERSON", "Le")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert all(e.value != "Le" for e in out[1])


def test_matches_whole_words_only():
    p0 = _page(0, ["contact", "Martin"])
    p1 = _page(1, ["ecrit", "par", "Martinez"])
    ent = _seed(p0, 1, 1, "PERSON", "Martin")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert all(e.value != "Martin" for e in out[1])


def test_propagation_ignores_case_and_accents():
    p0 = _page(0, ["Client", "GUILLAUME"])
    p1 = _page(1, ["ref", "guillaume"])
    ent = _seed(p0, 1, 1, "PERSON", "GUILLAUME")
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert any(e.value == "GUILLAUME" and e.source == "propagated"
               for e in out[1])


def test_unconfirmed_seed_not_propagated():
    p0 = _page(0, ["ref", "DUPONT"])
    p1 = _page(1, ["ici", "DUPONT"])
    ent = Entity("PERSON", "DUPONT", p0.words[1].char_start,
                 p0.words[1].char_end, "ner", 0.9, False)   # non confirmé
    out = propagate.propagate_across_pages([p0, p1], [[ent], []])
    assert all(e.value != "DUPONT" for e in out[1])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pdf_propagate.py -v`
Expected: FAIL (`propagate` inexistant).

- [ ] **Step 3: Implement the propagation module**

Créer `anonymator/files/pdf/propagate.py` :

```python
# anonymator/files/pdf/propagate.py
from anonymator.model import Entity
from anonymator.textnorm import normalize
from anonymator.merge import merge_entities
from anonymator.files.pdf.extract import PageText

_MIN_SINGLE_TOKEN = 3


def _is_propagatable(value: str) -> bool:
    """Écarte les valeurs risquées : purement numériques, ou token unique
    trop court (fort risque de sur-détection)."""
    tokens = normalize(value).split()
    if not tokens:
        return False
    if "".join(tokens).isdigit():
        return False
    if len(tokens) == 1 and len(tokens[0]) < _MIN_SINGLE_TOKEN:
        return False
    return True


def _collect_targets(per_page_entities: list[list[Entity]]) -> dict[str, tuple[str, str]]:
    """valeur normalisée → (type, valeur canonique). Confirmées seulement.
    La valeur canonique est la première rencontrée (regroupement UI cohérent)."""
    targets: dict[str, tuple[str, str]] = {}
    for entities in per_page_entities:
        for e in entities:
            if not e.confirmed or not _is_propagatable(e.value):
                continue
            targets.setdefault(normalize(e.value), (e.type, e.value))
    return targets


def _find_occurrences(page: PageText, tokens: list[str],
                      etype: str, canonical: str) -> list[Entity]:
    """Repère les suites consécutives de WordBox dont les tokens normalisés
    égalent `tokens`. Match par mot entier (jamais par sous-chaîne)."""
    boxes = page.words
    norm = [normalize(b.text) for b in boxes]
    n = len(tokens)
    out: list[Entity] = []
    i = 0
    while n and i + n <= len(boxes):
        if norm[i:i + n] == tokens:
            out.append(Entity(etype, canonical, boxes[i].char_start,
                              boxes[i + n - 1].char_end, "propagated", 1.0, True))
            i += n
        else:
            i += 1
    return out


def propagate_across_pages(
    pages: list[PageText],
    per_page_entities: list[list[Entity]],
) -> list[list[Entity]]:
    """Réplique chaque valeur sensible confirmée à toutes ses occurrences,
    sur toutes les pages, puis fusionne avec les détections d'origine."""
    targets = _collect_targets(per_page_entities)
    result: list[list[Entity]] = []
    for page, entities in zip(pages, per_page_entities):
        extra: list[Entity] = []
        for key, (etype, canonical) in targets.items():
            extra.extend(_find_occurrences(page, key.split(), etype, canonical))
        result.append(merge_entities(entities + extra))
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_pdf_propagate.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add anonymator/files/pdf/propagate.py tests/test_pdf_propagate.py
git commit -m "feat(pdf): propagation tout-document des valeurs sensibles confirmees"
```

---

## Task 4: Intégration dans `scan_pdf`

**Files:**
- Modify: `anonymator/files/pdf/pdf_io.py`
- Modify: `tests/pdf_fixtures.py`
- Test: `tests/test_pdf_io.py`

- [ ] **Step 1: Add the repeat fixture**

Ajouter à `tests/pdf_fixtures.py` :

```python
def make_repeat_pdf(path: Path) -> Path:
    """Une même phrase présente deux fois, sur deux lignes distinctes."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "GUILLAUME DROGLAND habite ici", fontsize=11)
    page.insert_text((72, 200), "Titulaire GUILLAUME DROGLAND", fontsize=11)
    doc.save(str(path))
    doc.close()
    return path
```

- [ ] **Step 2: Write the failing test**

Ajouter à `tests/test_pdf_io.py` (et compléter l'import de fixtures + `Entity`) :

```python
from tests.pdf_fixtures import (make_native_pdf, make_scanned_pdf,
                                make_repeat_pdf)
from anonymator.model import Entity


class _OnceNer:
    """Ne détecte que la 1re occurrence de la surface (simule un miss GLiNER)."""
    def __init__(self, surface, etype):
        self._s, self._t = surface, etype

    def detect(self, text, labels):
        i = text.find(self._s)
        if i < 0:
            return []
        return [Entity(self._t, self._s, i, i + len(self._s), "ner", 0.9, True)]


def test_scan_pdf_propagates_missed_occurrence(tmp_path):
    src = make_repeat_pdf(tmp_path / "r.pdf")
    pages = pdf_io.scan_pdf(src, _OnceNer("GUILLAUME DROGLAND", "PERSON"), _ref())
    persons = [e for e in pages[0].entities
               if e.type == "PERSON" and e.value == "GUILLAUME DROGLAND"]
    assert len(persons) == 2
```

Note : la première ligne remplace l'`import` de fixtures existant en tête de fichier.

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_pdf_io.py::test_scan_pdf_propagates_missed_occurrence -v`
Expected: FAIL (une seule occurrence sans propagation).

- [ ] **Step 4: Wire propagation into `scan_pdf`**

Dans `anonymator/files/pdf/pdf_io.py`, ajouter l'import du module :

```python
from anonymator.files.pdf import extract, redact, render, propagate
```

Puis remplacer le corps de `scan_pdf` (le `return` final) par :

```python
    per_page = [detect(pt.text, ner, ref) for pt in pages]
    per_page = propagate.propagate_across_pages(pages, per_page)
    return [PageScan(pt.page_index, pt.text, pt.words, ents)
            for pt, ents in zip(pages, per_page)]
```

(Le bloc `doc = extract.open_document(...)` / `ensure_native` / `extract_pages` en amont reste inchangé ; `pages` est la liste de `PageText` déjà extraite.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pdf_io.py -v`
Expected: PASS (anciens + nouveau).

- [ ] **Step 6: Commit**

```bash
git add anonymator/files/pdf/pdf_io.py tests/test_pdf_io.py tests/pdf_fixtures.py
git commit -m "feat(pdf): scan_pdf applique la propagation apres detection"
```

---

## Task 5: Vérification globale

**Files:** aucun (validation).

- [ ] **Step 1: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS — 259 tests d'origine + les nouveaux (adresse, ordre de lecture, propagation, intégration), 0 échec.

- [ ] **Step 2: Si un test hérité casse**

Diagnostiquer avec `python -m pytest <fichier>::<test> -v`. Causes probables : un test supposait l'ancien ordre de lecture (Task 2) ou une entité manquante désormais propagée (Task 4). Corriger l'attente du test si le nouveau comportement est correct, sinon corriger le code. Ne pas laisser de test en échec.

- [ ] **Step 3: Final commit (si corrections en Step 2)**

```bash
git add -A
git commit -m "test: adapte les attentes aux nouvelles regles de detection PDF"
```

---

## Self-Review (fait par l'auteur du plan)

- **Couverture spec** : C (Task 1), D (Task 2), A module (Task 3), intégration A (Task 4), tests des 4 sections + garde-fous + vérif globale (Task 5). ✅
- **Placeholders** : aucun ; tout le code est explicite. ✅
- **Cohérence des types** : `propagate_across_pages(pages, per_page_entities) -> list[list[Entity]]`, `_block_is_vertical(block_words) -> bool`, `Entity(source="propagated")`, `PageText`/`WordBox` — noms alignés entre plan, spec et code existant. ✅
