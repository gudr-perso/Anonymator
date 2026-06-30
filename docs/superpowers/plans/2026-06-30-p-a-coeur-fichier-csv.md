# P-A — Cœur fichier CSV — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire le cœur non-Qt de la revue fichier : correctif du séparateur CSV, séparation détection/application (`scan_csv`/`apply_csv`), et `FileReviewSession` (état de revue à 4 niveaux).

**Architecture:** Logique 100 % hors Qt, testable en TDD. `Entity` gagne un champ `confirmed` (socle partagé avec P-B). `scan_csv` détecte les entités par cellule (dédupliqué), `apply_csv` masque les retenues et produit le rapport ; l'ancien `anonymize_csv` devient `scan_csv` + `apply_csv` (non-régression). `FileReviewSession` détient l'état activé/désactivé par type/valeur/colonne/cellule et produit le document masqué + le rapport.

**Tech Stack:** Python 3.14, pytest. Réutilise `anonymator.pipeline.detect`, `anonymator.dedup.detect_unique`, `anonymator.anonymize.apply_masking`, `anonymator.report.audit.AuditReport`.

**Référence spec :** [2026-06-30-revue-fichier-coloree-design.md](../specs/2026-06-30-revue-fichier-coloree-design.md) §4, §5, §7.

**Prérequis :** être sur la branche `feat/revue-fichier-coloree`. Lancer les tests via `.venv\Scripts\python.exe -m pytest -q`.

---

## Structure des fichiers (P-A)

```
anonymator/model.py                     MODIFIER : Entity + champ confirmed
anonymator/files/csv_io.py              MODIFIER : sniff_delimiter robuste à la troncature
anonymator/files/anonymize_file.py      MODIFIER : extraire scan_csv / apply_csv
anonymator/core/file_review_session.py  CRÉER : FileReviewSession (non-Qt)
tests/test_model.py                     MODIFIER/CRÉER : champ confirmed
tests/test_csv_io.py                    MODIFIER : non-régression sniff tronqué
tests/test_anonymize_file.py            MODIFIER : équivalence scan+apply / ancien
tests/test_file_review_session.py       CRÉER : préséance 4 niveaux, counts, masked, report
```

---

### Task 0 : `Entity.confirmed`

**Files:**
- Modify: `anonymator/model.py`
- Test: `tests/test_model.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_model.py  (ajouter ; créer le fichier s'il n'existe pas)
from anonymator.model import Entity

def test_entity_confirmed_defaults_true():
    e = Entity("IBAN", "FR76...", 0, 5, "deterministic")
    assert e.confirmed is True

def test_entity_can_be_unconfirmed():
    e = Entity("IBAN", "FR00 0000", 0, 9, "deterministic", confidence=1.0, confirmed=False)
    assert e.confirmed is False
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_model.py -q`
Expected : FAIL (`TypeError: __init__() got an unexpected keyword argument 'confirmed'`).

- [ ] **Step 3 : Implémenter** — ajouter le champ après `confidence` dans `anonymator/model.py`

```python
@dataclass(frozen=True)
class Entity:
    type: str
    value: str
    start: int
    end: int
    source: str
    confidence: float = 1.0
    confirmed: bool = True   # False = format plausible mais validation déterministe KO

    @property
    def length(self) -> int:
        return self.end - self.start

    def __lt__(self, other: "Entity") -> bool:
        return (self.start, self.length) < (other.start, other.length)
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_model.py -q` → PASS. Puis suite complète `.venv\Scripts\python.exe -m pytest -q` → toujours verte (champ optionnel, rétro-compatible).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/model.py tests/test_model.py
git commit -m "feat(model): champ Entity.confirmed (socle validation déterministe)"
```

---

### Task 1 : Correctif `sniff_delimiter` (bug « tout en une colonne »)

**Files:**
- Modify: `anonymator/files/csv_io.py:21-38`
- Test: `tests/test_csv_io.py`

Cause : `read_csv` passe `text[:4096]` à `sniff_delimiter` ; la dernière ligne est coupée en plein milieu, son nombre de `|` diffère, donc `|` est jugé « inconsistant » et on retombe sur `;` par défaut → une seule colonne.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_csv_io.py  (ajouter)
from anonymator.files.csv_io import sniff_delimiter

def test_sniff_ignores_truncated_last_line():
    header = "|".join(f"C{i}" for i in range(18))
    row = "|".join(["x"] * 18)
    text = header + "\n" + "\n".join([row] * 400)   # > 4096 caractères
    sample = text[:4096]                             # coupe la dernière ligne
    assert not sample.endswith("\n")                 # garantit la troncature partielle
    assert sniff_delimiter(sample) == "|"
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_csv_io.py::test_sniff_ignores_truncated_last_line -q`
Expected : FAIL (retourne `";"`).

- [ ] **Step 3 : Implémenter** — au début de `sniff_delimiter`, retirer une dernière ligne partielle

```python
def sniff_delimiter(sample: str) -> str:
    """Choisit le séparateur consistant (même nombre >0 sur chaque ligne non vide).
    Priorité aux séparateurs structurels (;, |, tab) ; la virgule (souvent une
    virgule décimale en français) n'est retenue que si aucun structurel ne convient.
    Défaut ";"."""
    # Un échantillon tronqué (text[:4096]) coupe la dernière ligne en plein milieu :
    # son décompte de séparateurs fausse le test de consistance. On l'écarte.
    if "\n" in sample and not sample.endswith("\n"):
        sample = sample[:sample.rfind("\n")]
    lines = [l for l in sample.splitlines() if l]
    if not lines:
        return ";"

    def best_consistent(candidates):
        best_delim, best_count = None, 0
        for delim in candidates:
            counts = [line.count(delim) for line in lines]
            if all(c == counts[0] for c in counts) and counts[0] > best_count:
                best_delim, best_count = delim, counts[0]
        return best_delim

    return best_consistent(_PRIMARY) or best_consistent(_FALLBACK) or ";"
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_csv_io.py -q` → PASS (dont les tests sniff existants).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/csv_io.py tests/test_csv_io.py
git commit -m "fix(csv_io): sniff ignore la dernière ligne tronquée (bug colonne unique)"
```

---

### Task 2 : Refactor `anonymize_csv` → `scan_csv` + `apply_csv`

**Files:**
- Modify: `anonymator/files/anonymize_file.py:48-80`
- Test: `tests/test_anonymize_file.py`

Objectif : exposer la **détection par cellule** (`scan_csv`) séparément de l'**application** (`apply_csv`), et reconstruire `anonymize_csv` par-dessus → comportement identique (non-régression).

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_anonymize_file.py  (ajouter)
from anonymator.files import csv_io
from anonymator.files.anonymize_file import scan_csv, apply_csv
from anonymator.files.columns import default_maskable_columns
from anonymator.referential import Referential
from anonymator.ner import FakeNer

def _doc(tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    return csv_io.read_csv(src)

def test_scan_csv_maps_cells_to_entities(tmp_path):
    doc = _doc(tmp_path)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    cols = default_maskable_columns(doc.rows, doc.has_header)
    scanned = scan_csv(doc, ner, ref, cols)
    # colonne 0 (Nom), lignes de données 1 et 2
    assert (1, 0) in scanned and scanned[(1, 0)][0].type == "PERSON"
    assert (2, 0) in scanned
    # la colonne Montant (1) n'est pas masquable → absente
    assert all(c == 0 for (_r, c) in scanned)

def test_apply_csv_masks_and_reports(tmp_path):
    doc = _doc(tmp_path)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    cols = default_maskable_columns(doc.rows, doc.has_header)
    scanned = scan_csv(doc, ner, ref, cols)
    masked_doc, report = apply_csv(doc, scanned, ref)
    assert masked_doc.rows[1][0] == "[PERSONNE]"
    assert masked_doc.rows[2][0] == "[PERSONNE]"
    assert {r["type"] for r in report.to_rows()} == {"PERSON"}
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_anonymize_file.py -q`
Expected : FAIL (`ImportError: cannot import name 'scan_csv'`).

- [ ] **Step 3 : Implémenter** — remplacer `anonymize_csv` par trois fonctions dans `anonymator/files/anonymize_file.py`

```python
def scan_csv(doc, ner: NerDetector, ref: Referential,
             cols: set[int]) -> dict[tuple[int, int], list[Entity]]:
    """Détecte les entités par cellule (dédupliqué) sur les colonnes `cols`.
    Clés = (ligne, colonne) ; valeurs = entités détectées dans la cellule.
    Offsets des entités relatifs à la valeur de cellule (cf. dedup.detect_unique)."""
    data_start = 1 if doc.has_header else 0
    values = [doc.rows[r][c]
              for r in range(data_start, len(doc.rows))
              for c in cols if c < len(doc.rows[r])]
    cache = detect_unique(values, lambda v: detect(v, ner, ref))
    result: dict[tuple[int, int], list[Entity]] = {}
    for r in range(data_start, len(doc.rows)):
        for c in cols:
            if c >= len(doc.rows[r]):
                continue
            ents = cache.get(doc.rows[r][c], [])
            if ents:
                result[(r, c)] = ents
    return result


def apply_csv(doc, retained_by_cell: dict[tuple[int, int], list[Entity]],
              ref: Referential) -> tuple["csv_io.CsvDocument", AuditReport]:
    """Masque les entités retenues par cellule et produit le rapport.
    Mute `doc.rows` en place et le retourne."""
    report = AuditReport()
    for (r, c), ents in retained_by_cell.items():
        if not ents:
            continue
        original = doc.rows[r][c]
        location = f"{_column_label(doc, c)} L{r + 1}"
        for e in ents:
            report.add(e.type, e.value, ref.tag_for(e.type), location)
        doc.rows[r][c] = apply_masking(original, ents, ref)
    return doc, report


def anonymize_csv(path: Path, ner: NerDetector, ref: Referential,
                  output_dir: Path, when: datetime,
                  include: set[int] | None = None,
                  exclude: set[int] | None = None) -> FileResult:
    doc = csv_io.read_csv(path)
    cols = set(include) if include is not None else default_maskable_columns(
        doc.rows, doc.has_header)
    if exclude:
        cols -= set(exclude)
    scanned = scan_csv(doc, ner, ref, cols)
    doc, report = apply_csv(doc, scanned, ref)
    out = anonymized_path(path, output_dir, when)
    csv_io.write_csv(doc, out)
    return FileResult(out, report)
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_anonymize_file.py -q` → PASS.
Puis suite complète `.venv\Scripts\python.exe -m pytest -q` → verte (le test existant `test_run_on_csv_writes_output` et tout `anonymize_csv` restent valides : même résultat).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/anonymize_file.py tests/test_anonymize_file.py
git commit -m "refactor(files): scan_csv/apply_csv ; anonymize_csv = scan+apply"
```

---

### Task 3 : `FileReviewSession` — construction, typologies, valeurs, compteurs

**Files:**
- Create: `anonymator/core/file_review_session.py`
- Test: `tests/test_file_review_session.py`

État de revue (non-Qt). L'**état par défaut d'une valeur** suit son `confirmed` : une valeur confirmée est activée (masquée), une valeur non confirmée est désactivée (à cocher pour masquer).

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_file_review_session.py
from anonymator.files import csv_io
from anonymator.files.anonymize_file import scan_csv
from anonymator.files.columns import default_maskable_columns
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.core.file_review_session import FileReviewSession

def _session(tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes(
        "Nom;Montant\nClaire Martin;100,00\nClaire Martin;50,00\nPaul Durand;7,00\n"
        .encode("cp1252"))
    doc = csv_io.read_csv(src)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    cols = default_maskable_columns(doc.rows, doc.has_header)
    scanned = scan_csv(doc, ner, ref, cols)
    return FileReviewSession(doc, scanned, ref, cols)

def test_types_and_values(tmp_path):
    s = _session(tmp_path)
    assert s.types() == ["PERSON"]
    values = dict(s.values_for("PERSON"))      # {valeur: occurrences}
    assert values == {"Claire Martin": 2, "Paul Durand": 1}

def test_count_retained_all_by_default(tmp_path):
    s = _session(tmp_path)
    assert s.count_retained("PERSON") == 3     # 2 + 1 occurrences
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_review_session.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.core.file_review_session`).

- [ ] **Step 3 : Implémenter** `anonymator/core/file_review_session.py`

```python
from anonymator.model import Entity
from anonymator.anonymize import apply_masking
from anonymator.report.audit import AuditReport


class FileReviewSession:
    """État de revue d'un fichier CSV (non-Qt).

    Quatre niveaux de contrôle combinés en ET : colonne incluse, type activé,
    valeur distincte activée, cellule non exclue individuellement. Une valeur
    démarre activée si ses entités sont `confirmed`, désactivée sinon (opt-in)."""

    def __init__(self, doc, scanned: dict[tuple[int, int], list[Entity]],
                 ref, maskable_cols: set[int]):
        self.doc = doc
        self.ref = ref
        self._cells = scanned
        self._columns_enabled: dict[int, bool] = {c: True for c in maskable_cols}
        self._types_enabled: dict[str, bool] = {}
        self._values_enabled: dict[tuple[str, str], bool] = {}
        self._values_count: dict[tuple[str, str], int] = {}
        self._cells_excluded: set[tuple[int, int]] = set()
        for ents in self._cells.values():
            for e in ents:
                self._types_enabled.setdefault(e.type, True)
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                # défaut : confirmé → activé ; non confirmé → désactivé (opt-in)
                self._values_enabled.setdefault(key, e.confirmed)

    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def values_for(self, etype: str) -> list[tuple[str, int]]:
        items = [(v, n) for (t, v), n in self._values_count.items() if t == etype]
        return sorted(items)

    def _cell_retained(self, r: int, c: int) -> list[Entity]:
        if not self._columns_enabled.get(c, False):
            return []
        if (r, c) in self._cells_excluded:
            return []
        out = []
        for e in self._cells.get((r, c), []):
            if not self._types_enabled.get(e.type, True):
                continue
            if not self._values_enabled.get((e.type, e.value), True):
                continue
            out.append(e)
        return out

    def count_retained(self, etype: str) -> int:
        total = 0
        for (r, c) in self._cells:
            total += sum(1 for e in self._cell_retained(r, c) if e.type == etype)
        return total
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_review_session.py -q` → PASS (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/file_review_session.py tests/test_file_review_session.py
git commit -m "feat(core): FileReviewSession — typologies, valeurs, compteurs"
```

---

### Task 4 : `FileReviewSession` — contrôle 4 niveaux, `masked_document`, `report`

**Files:**
- Modify: `anonymator/core/file_review_session.py`
- Test: `tests/test_file_review_session.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_file_review_session.py  (ajouter)
def test_disable_type(tmp_path):
    s = _session(tmp_path)
    s.set_type_enabled("PERSON", False)
    assert s.count_retained("PERSON") == 0

def test_disable_single_value(tmp_path):
    s = _session(tmp_path)
    s.set_value_enabled("PERSON", "Claire Martin", False)
    assert s.count_retained("PERSON") == 1      # seul "Paul Durand" reste

def test_exclude_column(tmp_path):
    s = _session(tmp_path)
    s.set_column_enabled(0, False)
    assert s.count_retained("PERSON") == 0

def test_exclude_single_cell(tmp_path):
    s = _session(tmp_path)
    s.set_cell_excluded(1, 0, True)             # 1re occurrence de Claire Martin
    assert s.count_retained("PERSON") == 2

def test_masked_document_and_report(tmp_path):
    s = _session(tmp_path)
    s.set_value_enabled("PERSON", "Paul Durand", False)
    md = s.masked_document()
    assert md.rows[1][0] == "[PERSONNE]"         # Claire Martin masquée
    assert md.rows[3][0] == "Paul Durand"        # décochée → en clair
    rows = s.report().to_rows()
    assert {r["original"] for r in rows} == {"Claire Martin"}
    # le document original n'est pas muté
    assert s.doc.rows[1][0] == "Claire Martin"
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_review_session.py -q`
Expected : FAIL (`AttributeError: set_type_enabled`).

- [ ] **Step 3 : Implémenter** — ajouter les setters et les producteurs à `FileReviewSession`

```python
    # --- setters ---
    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        self._types_enabled[etype] = enabled

    def set_value_enabled(self, etype: str, value: str, enabled: bool) -> None:
        self._values_enabled[(etype, value)] = enabled

    def set_column_enabled(self, col: int, enabled: bool) -> None:
        self._columns_enabled[col] = enabled

    def set_cell_excluded(self, r: int, c: int, excluded: bool) -> None:
        if excluded:
            self._cells_excluded.add((r, c))
        else:
            self._cells_excluded.discard((r, c))

    def entities_for_cell(self, r: int, c: int) -> list[Entity]:
        """Entités actuellement retenues pour la cellule (pilote le surlignage)."""
        return self._cell_retained(r, c)

    def is_value_enabled(self, etype: str, value: str) -> bool:
        """État de la case d'une valeur distincte (pour cocher l'UI)."""
        return self._values_enabled.get((etype, value), True)

    # --- producteurs ---
    def masked_document(self):
        import copy
        out = copy.deepcopy(self.doc)
        for (r, c) in self._cells:
            ents = self._cell_retained(r, c)
            if ents:
                out.rows[r][c] = apply_masking(out.rows[r][c], ents, self.ref)
        return out

    def report(self) -> AuditReport:
        from anonymator.files.anonymize_file import _column_label
        rep = AuditReport()
        for (r, c) in self._cells:
            for e in self._cell_retained(r, c):
                location = f"{_column_label(self.doc, c)} L{r + 1}"
                rep.add(e.type, e.value, self.ref.tag_for(e.type), location)
        return rep
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_file_review_session.py -q` → PASS (7 tests).
Puis suite complète `.venv\Scripts\python.exe -m pytest -q` → verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/file_review_session.py tests/test_file_review_session.py
git commit -m "feat(core): FileReviewSession — contrôle 4 niveaux, masked_document, report"
```

---

## Auto-revue (P-A vs spec revue fichier)

- §4 archi non-Qt (`FileReviewSession`, `scan_csv`/`apply_csv`) → Tasks 2-4. ✓
- §5 préséance ET des 4 niveaux ; valeur non confirmée désactivée par défaut → Task 3-4 (`confirmed` piloté). ✓
- §7 correctif sniff → Task 1. ✓
- §8 rapport sur retenues uniquement → Task 4 (`report`). ✓
- `Entity.confirmed` socle (partagé P-B) → Task 0. ✓

**Hors P-A (→ P-C) :** vue Qt (tableau paginé, panneau, worker thread), boutons « Analyser et revoir ». **Hors P-A (→ P-B) :** émission des IBAN/NIR `confirmed=False`, secrets, stoplist, overrides — `FileReviewSession` les exploitera automatiquement une fois présents.
