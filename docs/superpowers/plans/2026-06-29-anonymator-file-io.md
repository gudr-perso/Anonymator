# Anonymator — Plan 2 : E/S fichiers (txt / csv / xlsx) + rapport d'audit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Anonymiser des fichiers `.txt`, `.csv` et `.xlsx` en réutilisant le moteur du Plan 1, en préservant la structure/l'encodage, avec sélection de colonnes et rapport d'audit — le tout testable sans UI.

**Architecture:** Le cœur (Plan 1) détecte la PII dans une **chaîne**. Le mode fichier applique ce cœur **cellule par cellule** : on collecte les valeurs texte uniques, on détecte une seule fois par valeur (dédup), puis on masque chaque cellule via `apply_masking`. CSV/TXT sont ré-émis avec mêmes séparateur/encodage ; XLSX est édité **en place** via openpyxl (on ne touche que `.value` des cellules chaîne, jamais les formules/nombres/styles). Un rapport d'audit agrège les remplacements.

**Tech Stack:** Python 3.11+, pytest, openpyxl ; réutilise `anonymator.pipeline`, `anonymator.anonymize`, `anonymator.dedup`, `anonymator.referential`, `anonymator.ner` du Plan 1.

**Référence spec :** [2026-06-29-anonymator-design.md](../specs/2026-06-29-anonymator-design.md) — §6 (mode fichier), §7 (rapport), §9.1 (nommage sortie).

---

## Pré-requis (déjà livrés par le Plan 1)
- `pipeline.detect(text, ner, ref) -> list[Entity]`
- `anonymize.apply_masking(text, entities, ref) -> str` (fusionne en interne, sûr sur entrées non fusionnées)
- `dedup.detect_unique(values, detect) -> dict[str, list[Entity]]` (offsets relatifs à la valeur)
- `referential.Referential.load_default()`
- `ner.FakeNer(mapping)` (tests) / `ner.GlinerDetector` (prod)
- `model.Entity`

## Structure des fichiers (Plan 2)

```
anonymator/output_naming.py        <nom>_ano_AAAAMMJJHHMMSS.<ext>
anonymator/files/__init__.py
anonymator/files/encoding.py       détection encodage (utf-8 / cp1252)
anonymator/files/columns.py        classification cellule "structurée" + colonnes masquables (règle D)
anonymator/files/csv_io.py         sniff séparateur + lecture/écriture CSV préservante
anonymator/files/txt_io.py         lecture/écriture texte
anonymator/files/xlsx_io.py        anonymisation xlsx en place (openpyxl)
anonymator/files/anonymize_file.py orchestrateur CSV + dispatcher par extension
anonymator/report/__init__.py
anonymator/report/audit.py         AuditReport : agrégation + export CSV/JSON
tests/...                          un fichier de test par module
```

---

### Task 0 : Dépendance openpyxl + packages

**Files:** Modify `requirements.txt` ; Create `anonymator/files/__init__.py`, `anonymator/report/__init__.py`.

- [ ] **Step 1 : Ajouter openpyxl à `requirements.txt`** (garder les lignes existantes)

```
gliner>=0.2.13
openpyxl>=3.1
pytest>=8.0
```

- [ ] **Step 2 : Installer openpyxl** (léger, pas de souci pCloud)

Run : `.venv/Scripts/python -m pip install "openpyxl>=3.1"`
Expected : installation OK.

- [ ] **Step 3 : Créer les packages**

`anonymator/files/__init__.py` et `anonymator/report/__init__.py` : fichiers vides.

- [ ] **Step 4 : Vérifier la suite existante**

Run : `.venv/Scripts/python -m pytest -q`
Expected : tous verts (43 passed, 1 deselected).

- [ ] **Step 5 : Commit**

```bash
git add requirements.txt anonymator/files/__init__.py anonymator/report/__init__.py
git commit -m "chore: dépendance openpyxl + packages files/report"
```

---

### Task 1 : Nommage du fichier de sortie

**Files:** Create `anonymator/output_naming.py` ; Test `tests/test_output_naming.py`.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_output_naming.py
from datetime import datetime
from pathlib import Path
from anonymator.output_naming import anonymized_path

def test_builds_suffixed_name_in_output_dir():
    src = Path("C:/data/balance_2026.csv")
    out = anonymized_path(src, Path("D:/sorties"), datetime(2026, 6, 24, 17, 18, 0))
    assert out == Path("D:/sorties/balance_2026_ano_20260624171800.csv")

def test_preserves_multidot_stem_and_extension():
    src = Path("/x/616870200FEC20231231.csv")
    out = anonymized_path(src, Path("/out"), datetime(2026, 1, 2, 3, 4, 5))
    assert out.name == "616870200FEC20231231_ano_20260102030405.csv"
```

- [ ] **Step 2 : Run → FAIL** : `.venv/Scripts/python -m pytest tests/test_output_naming.py -q`

- [ ] **Step 3 : Implémenter**

```python
# anonymator/output_naming.py
from datetime import datetime
from pathlib import Path

def anonymized_path(source: Path, output_dir: Path, when: datetime) -> Path:
    stamp = when.strftime("%Y%m%d%H%M%S")
    return output_dir / f"{source.stem}_ano_{stamp}{source.suffix}"
```

- [ ] **Step 4 : Run → PASS** (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/output_naming.py tests/test_output_naming.py
git commit -m "feat: nommage horodaté du fichier de sortie"
```

---

### Task 2 : Détection d'encodage

**Files:** Create `anonymator/files/encoding.py` ; Test `tests/test_encoding.py`.

**Approche :** essayer UTF-8 strict ; en cas d'échec, retomber sur **cp1252** (Windows-1252, surensemble de Latin-1) — les exports comptables FR observés sont en cp1252.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_encoding.py
from anonymator.files.encoding import detect_encoding

def test_detects_utf8():
    assert detect_encoding("Société".encode("utf-8")) == "utf-8"

def test_falls_back_to_cp1252_for_latin1_bytes():
    # "Société" en cp1252 n'est pas de l'UTF-8 valide
    assert detect_encoding("Société".encode("cp1252")) == "cp1252"

def test_pure_ascii_is_utf8():
    assert detect_encoding(b"Banque Credit Agricole") == "utf-8"
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/files/encoding.py
def detect_encoding(data: bytes) -> str:
    try:
        data.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"
```

- [ ] **Step 4 : Run → PASS** (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/encoding.py tests/test_encoding.py
git commit -m "feat: détection d'encodage (utf-8 / cp1252)"
```

---

### Task 3 : Sniff du séparateur CSV

**Files:** Create `anonymator/files/csv_io.py` ; Test `tests/test_csv_sniff.py`.

**Constaté :** FEC en `|`, grand livre en `;`. On limite le sniff à un jeu de séparateurs plausibles.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_csv_sniff.py
from anonymator.files.csv_io import sniff_delimiter

def test_sniffs_semicolon():
    sample = "10121000;Libellé;20,00;0,00\n10131000;Autre;2,00;0,00\n"
    assert sniff_delimiter(sample) == ";"

def test_sniffs_pipe():
    sample = "ANC|A nouveaux|1284|20230101|Texte\nANC|A nouveaux|1284|20230102|Autre\n"
    assert sniff_delimiter(sample) == "|"

def test_defaults_to_semicolon_when_ambiguous():
    assert sniff_delimiter("valeur_unique_sans_separateur\n") == ";"
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** (début de `csv_io.py`)

```python
# anonymator/files/csv_io.py
import csv

_CANDIDATES = [";", "|", ",", "\t"]

def sniff_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="".join(_CANDIDATES))
        return dialect.delimiter
    except csv.Error:
        # ambigu / une seule colonne : compter les candidats, défaut ";"
        counts = {d: sample.count(d) for d in _CANDIDATES}
        best = max(counts, key=counts.get)
        return best if counts[best] > 0 else ";"
```

- [ ] **Step 4 : Run → PASS** (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/csv_io.py tests/test_csv_sniff.py
git commit -m "feat: sniff du séparateur CSV (;|,tab, défaut ;)"
```

---

### Task 4 : Classification des colonnes (règle D)

**Files:** Create `anonymator/files/columns.py` ; Test `tests/test_columns.py`.

**Règle :** une cellule est « structurée » (non-texte) si elle ne contient **aucune lettre** (montants, dates, n° de compte, vide). Une colonne est **masquable** si au moins une de ses cellules de données contient une lettre. L'orchestrateur applique ensuite les surcharges utilisateur (inclure/exclure).

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_columns.py
from anonymator.files.columns import looks_structured, default_maskable_columns

def test_looks_structured_true_for_numbers_dates_empty():
    assert looks_structured("       1284")
    assert looks_structured("15866,00")
    assert looks_structured("20230101")
    assert looks_structured("")
    assert looks_structured("51211000")

def test_looks_structured_false_when_has_letter():
    assert not looks_structured("Banque Crédit Agricole")
    assert not looks_structured("A.N. au 01/01/2023")

def test_default_maskable_columns_skips_header_and_numeric_cols():
    rows = [
        ["CompteNum", "CompteLib", "Debit"],     # en-tête
        ["10131000", "CS appelé", "0,00"],
        ["51211000", "Banque CRCA", "9702,88"],
    ]
    cols = default_maskable_columns(rows, has_header=True)
    assert cols == {1}      # seule la colonne "CompteLib" a des lettres

def test_default_maskable_columns_without_header():
    rows = [["10121000", "CS appelé", "20,00"], ["16423000", "", "2173,39"]]
    assert default_maskable_columns(rows, has_header=False) == {1}
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/files/columns.py
def looks_structured(value: str) -> bool:
    """Vrai si la valeur ne contient aucune lettre (nombre, date, code, vide)."""
    return not any(ch.isalpha() for ch in value)

def default_maskable_columns(rows: list[list[str]], has_header: bool) -> set[int]:
    data = rows[1:] if has_header else rows
    width = max((len(r) for r in rows), default=0)
    maskable: set[int] = set()
    for col in range(width):
        for row in data:
            if col < len(row) and not looks_structured(row[col]):
                maskable.add(col)
                break
    return maskable
```

- [ ] **Step 4 : Run → PASS** (4 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/columns.py tests/test_columns.py
git commit -m "feat: classification colonnes masquables (règle D)"
```

---

### Task 5 : Lecture / écriture CSV préservante

**Files:** Modify `anonymator/files/csv_io.py` ; Test `tests/test_csv_io.py`.

On lit en un `CsvDocument` (lignes + séparateur + encodage + en-tête + fin de ligne) et on ré-écrit à l'identique sur les cellules non modifiées.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_csv_io.py
from pathlib import Path
from anonymator.files.csv_io import read_csv, write_csv

def test_roundtrip_preserves_rows_delimiter_encoding(tmp_path):
    src = tmp_path / "in.csv"
    src.write_bytes("10131000;CS appelé;2,00\n51211000;Banque CRCA;9702,88\n"
                    .encode("cp1252"))
    doc = read_csv(src)
    assert doc.delimiter == ";"
    assert doc.encoding == "cp1252"
    assert doc.rows[0] == ["10131000", "CS appelé", "2,00"]
    out = tmp_path / "out.csv"
    write_csv(doc, out)
    # ré-écriture fidèle (mêmes octets décodés)
    assert read_csv(out).rows == doc.rows
    assert out.read_bytes().decode("cp1252").count(";") == 4

def test_read_detects_header(tmp_path):
    src = tmp_path / "h.csv"
    src.write_bytes("JournalCode|JournalLib|Debit\nANC|A nouveaux|0,00\n"
                    .encode("utf-8"))
    doc = read_csv(src)
    assert doc.delimiter == "|"
    assert doc.has_header is True
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** (ajouter à `csv_io.py`)

```python
# anonymator/files/csv_io.py  (ajouts)
import io
from dataclasses import dataclass
from pathlib import Path
from anonymator.files.encoding import detect_encoding

@dataclass
class CsvDocument:
    rows: list[list[str]]
    delimiter: str
    encoding: str
    has_header: bool
    line_terminator: str

def read_csv(path: Path) -> CsvDocument:
    data = path.read_bytes()
    encoding = detect_encoding(data)
    text = data.decode(encoding)
    line_terminator = "\r\n" if "\r\n" in text else "\n"
    sample = text[:4096]
    delimiter = sniff_delimiter(sample)
    try:
        has_header = csv.Sniffer().has_header(sample)
    except csv.Error:
        has_header = False
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    rows = [row for row in reader]
    return CsvDocument(rows, delimiter, encoding, has_header, line_terminator)

def write_csv(doc: CsvDocument, path: Path) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=doc.delimiter,
                        lineterminator=doc.line_terminator,
                        quoting=csv.QUOTE_MINIMAL)
    writer.writerows(doc.rows)
    path.write_bytes(buffer.getvalue().encode(doc.encoding))
```

- [ ] **Step 4 : Run → PASS** (2 tests). Puis suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/csv_io.py tests/test_csv_io.py
git commit -m "feat: lecture/écriture CSV préservante (séparateur, encodage, EOL)"
```

---

### Task 6 : Rapport d'audit

**Files:** Create `anonymator/report/audit.py` ; Test `tests/test_audit.py`.

Agrège les remplacements par `(type, valeur_originale)` : compteur d'occurrences + emplacements. Export CSV et JSON.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_audit.py
import json
from pathlib import Path
from anonymator.report.audit import AuditReport

def test_aggregates_by_type_and_value():
    rep = AuditReport()
    rep.add("PERSON", "Claire Martin", "[PERSONNE]", "CompAuxLib L2")
    rep.add("PERSON", "Claire Martin", "[PERSONNE]", "CompAuxLib L9")
    rep.add("EMAIL", "c@x.fr", "[EMAIL]", "EcritureLib L2")
    rows = rep.to_rows()
    person = next(r for r in rows if r["original"] == "Claire Martin")
    assert person["type"] == "PERSON"
    assert person["tag"] == "[PERSONNE]"
    assert person["occurrences"] == 2
    assert person["locations"] == "CompAuxLib L2; CompAuxLib L9"

def test_export_json_and_csv(tmp_path):
    rep = AuditReport()
    rep.add("EMAIL", "c@x.fr", "[EMAIL]", "texte")
    j = tmp_path / "r.json"
    rep.export_json(j)
    data = json.loads(j.read_text(encoding="utf-8"))
    assert data[0]["original"] == "c@x.fr"
    c = tmp_path / "r.csv"
    rep.export_csv(c)
    content = c.read_text(encoding="utf-8")
    assert "type" in content and "c@x.fr" in content
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/report/audit.py
import csv
import json
from pathlib import Path

class AuditReport:
    def __init__(self):
        # clé (type, original) -> {tag, occurrences, locations[]}
        self._entries: dict[tuple[str, str], dict] = {}

    def add(self, etype: str, original: str, tag: str, location: str) -> None:
        key = (etype, original)
        entry = self._entries.setdefault(
            key, {"tag": tag, "occurrences": 0, "locations": []})
        entry["occurrences"] += 1
        entry["locations"].append(location)

    def to_rows(self) -> list[dict]:
        rows = []
        for (etype, original), e in self._entries.items():
            rows.append({
                "type": etype,
                "original": original,
                "tag": e["tag"],
                "occurrences": e["occurrences"],
                "locations": "; ".join(e["locations"]),
            })
        return rows

    def export_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_rows(), ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def export_csv(self, path: Path) -> None:
        rows = self.to_rows()
        fields = ["type", "original", "tag", "occurrences", "locations"]
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
```

- [ ] **Step 4 : Run → PASS** (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/report/audit.py tests/test_audit.py
git commit -m "feat: rapport d'audit (agrégation + export CSV/JSON)"
```

---

### Task 7 : Orchestrateur CSV (lire → colonnes → dédup → masquer → écrire + rapport)

**Files:** Create `anonymator/files/anonymize_file.py` ; Test `tests/test_anonymize_csv.py`.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_anonymize_csv.py
from datetime import datetime
from pathlib import Path
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.anonymize_file import anonymize_csv

def test_masks_text_columns_writes_new_file_and_report(tmp_path):
    src = tmp_path / "fec.csv"
    src.write_bytes(
        ("CompteNum;CompAuxLib;Debit\n"
         "41100000;Claire Martin;100,00\n"
         "41100000;Claire Martin;50,00\n").encode("cp1252"))
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    result = anonymize_csv(src, ner, ref, tmp_path,
                           when=datetime(2026, 6, 24, 17, 18, 0))
    # nouveau fichier suffixé, original intact
    assert result.output_path.name == "fec_ano_20260624171800.csv"
    assert src.read_bytes().decode("cp1252").count("Claire Martin") == 2
    out_text = result.output_path.read_bytes().decode("cp1252")
    assert "Claire Martin" not in out_text
    assert out_text.count("[PERSONNE]") == 2
    # colonnes numériques préservées
    assert "41100000" in out_text and "100,00" in out_text
    # rapport
    rows = result.report.to_rows()
    person = next(r for r in rows if r["original"] == "Claire Martin")
    assert person["occurrences"] == 2

def test_column_overrides_exclude(tmp_path):
    src = tmp_path / "x.csv"
    src.write_bytes("Nom;Note\nClaire Martin;RAS Claire Martin\n".encode("cp1252"))
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    # exclure la colonne 1 ("Note") → seul "Nom" masqué
    result = anonymize_csv(src, ner, ref, tmp_path,
                           when=datetime(2026, 1, 1, 0, 0, 0), exclude={1})
    out = result.output_path.read_bytes().decode("cp1252")
    assert out == "Nom;Note\n[PERSONNE];RAS Claire Martin\n"
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

```python
# anonymator/files/anonymize_file.py
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.pipeline import detect
from anonymator.anonymize import apply_masking
from anonymator.dedup import detect_unique
from anonymator.report.audit import AuditReport
from anonymator.output_naming import anonymized_path
from anonymator.files import csv_io
from anonymator.files.columns import default_maskable_columns

@dataclass
class FileResult:
    output_path: Path
    report: AuditReport

def _column_label(doc, col: int) -> str:
    if doc.has_header and doc.rows and col < len(doc.rows[0]):
        return doc.rows[0][col]
    return f"col{col}"

def anonymize_csv(path: Path, ner: NerDetector, ref: Referential,
                  output_dir: Path, when: datetime,
                  include: set[int] | None = None,
                  exclude: set[int] | None = None) -> FileResult:
    doc = csv_io.read_csv(path)
    cols = set(include) if include is not None else default_maskable_columns(
        doc.rows, doc.has_header)
    if exclude:
        cols -= set(exclude)

    data_start = 1 if doc.has_header else 0
    # 1) collecter les valeurs texte uniques des colonnes retenues
    values = [doc.rows[r][c]
              for r in range(data_start, len(doc.rows))
              for c in cols if c < len(doc.rows[r])]
    cache = detect_unique(values, lambda v: detect(v, ner, ref))

    # 2) masquer cellule par cellule + alimenter le rapport
    report = AuditReport()
    for r in range(data_start, len(doc.rows)):
        for c in cols:
            if c >= len(doc.rows[r]):
                continue
            original = doc.rows[r][c]
            ents = cache.get(original, [])
            if not ents:
                continue
            location = f"{_column_label(doc, c)} L{r + 1}"
            for e in ents:
                report.add(e.type, e.value, ref.tag_for(e.type), location)
            doc.rows[r][c] = apply_masking(original, ents, ref)

    out = anonymized_path(path, output_dir, when)
    csv_io.write_csv(doc, out)
    return FileResult(out, report)
```

- [ ] **Step 4 : Run → PASS** (2 tests). Puis suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/anonymize_file.py tests/test_anonymize_csv.py
git commit -m "feat: anonymisation CSV (colonnes, dédup, masquage, rapport)"
```

---

### Task 8 : Anonymisation TXT

**Files:** Modify `anonymator/files/anonymize_file.py` ; Create `anonymator/files/txt_io.py` ; Test `tests/test_anonymize_txt.py`.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_anonymize_txt.py
from datetime import datetime
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.anonymize_file import anonymize_txt

def test_masks_whole_text_file(tmp_path):
    src = tmp_path / "note.txt"
    src.write_bytes("Contact Claire Martin au 06 12 34 56 78.".encode("cp1252"))
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    res = anonymize_txt(src, ner, ref, tmp_path,
                        when=datetime(2026, 6, 24, 17, 18, 0))
    out = res.output_path.read_bytes().decode("cp1252")
    assert out == "Contact [PERSONNE] au [TEL]."
    assert res.output_path.name == "note_ano_20260624171800.txt"
    assert {r["type"] for r in res.report.to_rows()} == {"PERSON", "PHONE"}
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

`anonymator/files/txt_io.py` :
```python
from pathlib import Path
from anonymator.files.encoding import detect_encoding

def read_text(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    enc = detect_encoding(data)
    return data.decode(enc), enc

def write_text(text: str, encoding: str, path: Path) -> None:
    path.write_bytes(text.encode(encoding))
```

Ajouter à `anonymize_file.py` :
```python
from anonymator.files import txt_io

def anonymize_txt(path: Path, ner: NerDetector, ref: Referential,
                  output_dir: Path, when: datetime) -> FileResult:
    text, encoding = txt_io.read_text(path)
    ents = detect(text, ner, ref)
    report = AuditReport()
    for e in ents:
        report.add(e.type, e.value, ref.tag_for(e.type), "texte")
    masked = apply_masking(text, ents, ref)
    out = anonymized_path(path, output_dir, when)
    txt_io.write_text(masked, encoding, out)
    return FileResult(out, report)
```

- [ ] **Step 4 : Run → PASS** (1 test). Puis suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/txt_io.py anonymator/files/anonymize_file.py tests/test_anonymize_txt.py
git commit -m "feat: anonymisation TXT (texte intégral + rapport)"
```

> Note : le **chunking du texte très long** (spec §9) n'est pas traité ici ; le pipeline étant sans état, il se branchera en amont (découpe + recalage d'offsets) au moment de l'UI (Plan 3). À documenter comme limite connue.

---

### Task 9 : Anonymisation XLSX en place (openpyxl)

**Files:** Create `anonymator/files/xlsx_io.py` ; Modify `anonymator/files/anonymize_file.py` ; Test `tests/test_anonymize_xlsx.py`.

**Principe :** charger le classeur, parcourir **tous les onglets**, ne traiter que les cellules **chaîne** (`cell.data_type == "s"`) — ce qui **exclut nativement** nombres, dates et **formules** (`data_type == "f"`). On ne touche que `.value`, donc styles/formules/mise en forme sont préservés. Sauvegarde dans un nouveau fichier.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_anonymize_xlsx.py
from datetime import datetime
import openpyxl
from openpyxl.styles import Font
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.anonymize_file import anonymize_xlsx

def _make_book(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Balance"
    ws["A1"] = "Libellé"; ws["B1"] = "Montant"
    ws["A1"].font = Font(bold=True)
    ws["A2"] = "Claire Martin"; ws["B2"] = 100
    ws["B3"] = "=B2*2"          # formule : ne doit pas être touchée
    ws2 = wb.create_sheet("Tiers")
    ws2["A1"] = "Fournisseur Claire Martin"
    wb.save(path)

def test_masks_string_cells_all_sheets_preserves_formatting(tmp_path):
    src = tmp_path / "bal.xlsx"
    _make_book(src)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    res = anonymize_xlsx(src, ner, ref, tmp_path,
                         when=datetime(2026, 6, 24, 17, 18, 0))
    assert res.output_path.name == "bal_ano_20260624171800.xlsx"

    wb = openpyxl.load_workbook(res.output_path)
    ws = wb["Balance"]
    assert ws["A2"].value == "[PERSONNE]"      # nom masqué
    assert ws["B2"].value == 100               # nombre intact
    assert ws["B3"].value == "=B2*2"           # formule intacte
    assert ws["A1"].font.bold is True          # mise en forme préservée
    assert ws["A1"].value == "Libellé"         # en-tête (pas de PII) intact
    assert wb["Tiers"]["A1"].value == "Fournisseur [PERSONNE]"  # 2e onglet traité
    # original intact
    assert openpyxl.load_workbook(src)["Balance"]["A2"].value == "Claire Martin"
    assert any(r["original"] == "Claire Martin" for r in res.report.to_rows())
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter**

`anonymator/files/xlsx_io.py` :
```python
from datetime import datetime
from pathlib import Path
import openpyxl
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.pipeline import detect
from anonymator.anonymize import apply_masking
from anonymator.dedup import detect_unique
from anonymator.report.audit import AuditReport
from anonymator.output_naming import anonymized_path

def anonymize_workbook(path: Path, ner: NerDetector, ref: Referential,
                       output_dir: Path, when: datetime):
    wb = openpyxl.load_workbook(path)
    # 1) collecter les valeurs texte uniques (cellules chaîne, hors formules)
    string_cells = []  # (sheet_title, coordinate, value)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.data_type == "s" and isinstance(cell.value, str):
                    string_cells.append((ws.title, cell.coordinate, cell.value))
    cache = detect_unique([v for _, _, v in string_cells],
                          lambda v: detect(v, ner, ref))

    # 2) masquer + rapport
    report = AuditReport()
    for sheet_title, coord, value in string_cells:
        ents = cache.get(value, [])
        if not ents:
            continue
        location = f"{sheet_title}!{coord}"
        for e in ents:
            report.add(e.type, e.value, ref.tag_for(e.type), location)
        wb[sheet_title][coord] = apply_masking(value, ents, ref)

    out = anonymized_path(path, output_dir, when)
    wb.save(out)
    return out, report
```

Ajouter à `anonymize_file.py` :
```python
from anonymator.files import xlsx_io

def anonymize_xlsx(path: Path, ner: NerDetector, ref: Referential,
                   output_dir: Path, when: datetime) -> FileResult:
    out, report = xlsx_io.anonymize_workbook(path, ner, ref, output_dir, when)
    return FileResult(out, report)
```

- [ ] **Step 4 : Run → PASS** (1 test). Puis suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/xlsx_io.py anonymator/files/anonymize_file.py tests/test_anonymize_xlsx.py
git commit -m "feat: anonymisation XLSX en place (openpyxl, tous onglets, formats préservés)"
```

---

### Task 10 : Dispatcher par extension + refus des formats non supportés

**Files:** Modify `anonymator/files/anonymize_file.py` ; Test `tests/test_dispatch.py`.

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_dispatch.py
from datetime import datetime
import pytest
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.anonymize_file import anonymize_file, UnsupportedFormat

def test_dispatches_by_extension(tmp_path):
    src = tmp_path / "n.txt"
    src.write_bytes("Claire Martin".encode("cp1252"))
    ref = Referential.load_default(); ner = FakeNer({"Claire Martin": "PERSON"})
    res = anonymize_file(src, ner, ref, tmp_path, when=datetime(2026, 1, 1))
    assert res.output_path.suffix == ".txt"

def test_rejects_pdf(tmp_path):
    src = tmp_path / "doc.pdf"
    src.write_bytes(b"%PDF-1.7")
    ref = Referential.load_default(); ner = FakeNer({})
    with pytest.raises(UnsupportedFormat) as exc:
        anonymize_file(src, ner, ref, tmp_path, when=datetime(2026, 1, 1))
    assert ".pdf" in str(exc.value).lower()
```

- [ ] **Step 2 : Run → FAIL**

- [ ] **Step 3 : Implémenter** (ajouter à `anonymize_file.py`)

```python
class UnsupportedFormat(Exception):
    pass

def anonymize_file(path: Path, ner: NerDetector, ref: Referential,
                   output_dir: Path, when: datetime,
                   include: set[int] | None = None,
                   exclude: set[int] | None = None) -> FileResult:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return anonymize_txt(path, ner, ref, output_dir, when)
    if suffix == ".csv":
        return anonymize_csv(path, ner, ref, output_dir, when,
                             include=include, exclude=exclude)
    if suffix == ".xlsx":
        return anonymize_xlsx(path, ner, ref, output_dir, when)
    raise UnsupportedFormat(
        f"Format non supporté : {suffix} (formats acceptés : .txt, .csv, .xlsx)")
```

- [ ] **Step 4 : Run → PASS** (2 tests). Puis suite complète verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/anonymize_file.py tests/test_dispatch.py
git commit -m "feat: dispatcher fichier par extension + refus PDF/non supporté"
```

---

## Couverture du spec (auto-revue Plan 2)

- §6.1 types acceptés + refus PDF → Task 10. ✓
- §6.2 sniff séparateur + encodage cp1252 → Tasks 2,3,5. ✓
- §6.3 sélection colonnes (règle D + surcharges) → Tasks 4,7. ✓
- §6.4 préservation structure CSV / **xlsx en place tous onglets, formules/styles intacts** → Tasks 5,9. ✓
- §6.5 nouveau fichier suffixé, original intact → Task 1 + Tasks 7-9. ✓
- §7 rapport d'audit (type, valeur, occurrences, emplacement, CSV/JSON) → Task 6, alimenté par 7-9. ✓
- §9.1 nommage `<nom>_ano_AAAAMMJJHHMMSS.<ext>` → Task 1. ✓

**Limites volontaires :** dossier de sortie passé en paramètre (sa persistance = Paramètres, Plan 3) ; chunking texte long (Plan 3) ; aperçu/navigation onglets = UI (Plan 3) ; sélection de colonnes exposée en paramètres `include/exclude` mais l'UI de cases à cocher est en Plan 3. La détection réelle utilise `GlinerDetector` (injecté), non couverte par les tests unitaires (cf. test d'intégration Plan 1).
```
