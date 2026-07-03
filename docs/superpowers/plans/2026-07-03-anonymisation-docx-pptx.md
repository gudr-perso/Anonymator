# Anonymisation docx/pptx — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Étendre Anonymator à l'anonymisation des fichiers Word (`.docx`) et PowerPoint (`.pptx`), avec revue par liste d'entités, purge des métadonnées et affichage du périmètre.

**Architecture :** Un seul moteur de masquage (`run_remap`) opérant sur tout objet exposant `.text`. Les parties principales (corps, tableaux, en-têtes/pieds, zones de texte, slides, notes) sont masquées via les objets `Run` de python-docx/pptx (sauvegarde native). Les parties séparées docx (commentaires, notes de bas de page/fin) et les métadonnées (`core.xml`, `app.xml`) sont traitées par une post-passe zip+lxml qui réutilise `run_remap` via un adaptateur `XmlRun`. Détection/dédup/masquage/rapport = pipeline existant, inchangé.

**Tech Stack :** Python, python-docx, python-pptx, lxml (déjà tiré par les deux), PySide6 (UI), pytest.

**Spec de référence :** `docs/superpowers/specs/2026-07-03-anonymisation-docx-pptx-design.md`

---

## Structure des fichiers

**Créés :**
```
anonymator/files/ooxml/
├── __init__.py              # COVERAGE (constante périmètre, source de vérité)
├── text_unit.py             # TextUnit (paragraphe = liste de runs + location)
├── run_remap.py             # build_offsets + apply (cœur masquage, testé isolément)
├── scan.py                  # scan_units, confirmed_only, apply_units (génériques)
├── metadata.py              # purge core.xml / app.xml (sur bytes)
├── xml_parts.py             # XmlRun + extracteurs word-part + post-passe zip
├── docx_io.py               # iter_main_units + anonymize_document (Word)
└── pptx_io.py               # iter_main_units + anonymize_document (PowerPoint)

anonymator/core/ooxml_review_session.py   # session de revue (type/valeur)
anonymator/ui/ooxml_scan_worker.py        # worker QThread d'analyse
anonymator/ui/components/perimetre_card.py# encart « traité / non traité »

tests/ooxml_fixtures.py
tests/test_ooxml_run_remap.py
tests/test_ooxml_scan.py
tests/test_ooxml_metadata.py
tests/test_ooxml_xml_parts.py
tests/test_anonymize_docx.py
tests/test_anonymize_pptx.py
tests/test_ooxml_review_session.py
tests/test_ooxml_scan_worker.py
```

**Modifiés :**
- `requirements.txt` — ajout des deux libs
- `anonymator/files/anonymize_file.py` — dispatch `.docx`/`.pptx`
- `anonymator/ui/file_screen.py` — ouverture, analyse, revue, préview, encart périmètre
- `anonymator.spec` — datas des gabarits

**Comportement v1 (à garder en tête) :** en mode revue UI, l'arbre couvre les entités des **parties principales** ; les commentaires/notes docx et les métadonnées sont anonymisés **automatiquement** (entités confirmées) lors de l'application, sans passer par l'arbre. La `PerimetreCard` l'annonce.

---

## Task 1 : Dépendances

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1 : Ajouter les deux libs à `requirements.txt`**

Ajouter à la fin du fichier :

```
python-docx>=1.1
python-pptx>=0.6.23
```

- [ ] **Step 2 : Installer dans le venv du projet**

Run : `.venv/Scripts/python.exe -m pip install "python-docx>=1.1" "python-pptx>=0.6.23"`
Expected : installation réussie de python-docx, python-pptx et de leurs dépendances (lxml, XlsxWriter, typing_extensions).

- [ ] **Step 3 : Vérifier l'import**

Run : `.venv/Scripts/python.exe -c "import docx, pptx; print('ok')"`
Expected : affiche `ok`.

- [ ] **Step 4 : Commit**

```bash
git add requirements.txt
git commit -m "build(deps): ajoute python-docx et python-pptx"
```

---

## Task 2 : `TextUnit`

**Files:**
- Create: `anonymator/files/ooxml/__init__.py` (vide pour l'instant, complété Task 6)
- Create: `anonymator/files/ooxml/text_unit.py`
- Test: `tests/test_ooxml_run_remap.py` (partagé avec Task 3)

- [ ] **Step 1 : Créer le package et `text_unit.py`**

Créer `anonymator/files/ooxml/__init__.py` vide.

Créer `anonymator/files/ooxml/text_unit.py` :

```python
from dataclasses import dataclass


@dataclass
class TextUnit:
    """Un paragraphe : une liste de « runs » (objets exposant un attribut
    `.text` mutable — Run python-docx/pptx ou XmlRun) et une localisation
    d'audit lisible (« Corps », « Tableau L2C3 », « Slide 3 / Notes »)."""
    runs: list
    location: str

    def text(self) -> str:
        return "".join((r.text or "") for r in self.runs)
```

- [ ] **Step 2 : Commit**

```bash
git add anonymator/files/ooxml/__init__.py anonymator/files/ooxml/text_unit.py
git commit -m "feat(ooxml): TextUnit (paragraphe = runs + location)"
```

---

## Task 3 : `run_remap` (cœur du masquage)

**Files:**
- Create: `anonymator/files/ooxml/run_remap.py`
- Test: `tests/test_ooxml_run_remap.py`

- [ ] **Step 1 : Écrire les tests d'abord**

Créer `tests/test_ooxml_run_remap.py` :

```python
from dataclasses import dataclass
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.files.ooxml import run_remap


@dataclass
class FakeRun:
    text: str


def _ref():
    return Referential.load_default()


def _runs(*texts):
    return [FakeRun(t) for t in texts]


def _ent(value, start, end, etype="PERSON"):
    return Entity(etype, value, start, end, "ner", 1.0)


def test_build_offsets_concatenates_and_maps():
    runs = _runs("Contact : ", "Jean ", "Dup", "ont")
    text, spans = run_remap.build_offsets(runs)
    assert text == "Contact : Jean Dupont"
    assert spans == [(0, 0, 10), (1, 10, 15), (2, 15, 18), (3, 18, 21)]


def test_span_within_single_run():
    runs = _runs("Bonjour Jean Dupont !")
    run_remap.apply(runs, [_ent("Jean Dupont", 8, 19)], _ref())
    assert runs[0].text == "Bonjour [PERSONNE] !"


def test_span_across_three_runs_preserves_untouched_runs():
    runs = _runs("Contact : ", "Jean ", "Dup", "ont", " (svc)")
    run_remap.apply(runs, [_ent("Jean Dupont", 10, 21)], _ref())
    assert runs[0].text == "Contact : "
    assert runs[1].text == "[PERSONNE]"
    assert runs[2].text == ""
    assert runs[3].text == ""
    assert runs[4].text == " (svc)"
    assert "".join(r.text for r in runs) == "Contact : [PERSONNE] (svc)"


def test_empty_runs_interspersed():
    runs = _runs("Jean", "", " ", "Dupont")
    run_remap.apply(runs, [_ent("Jean Dupont", 0, 11)], _ref())
    assert "".join(r.text for r in runs) == "[PERSONNE]"


def test_two_entities_same_paragraph():
    runs = _runs("De Jean Dupont a Marie Curie")
    ents = [_ent("Jean Dupont", 3, 14), _ent("Marie Curie", 17, 28)]
    run_remap.apply(runs, ents, _ref())
    assert runs[0].text == "De [PERSONNE] a [PERSONNE]"


def test_entity_at_start_and_end():
    runs = _runs("Jean Dupont")
    run_remap.apply(runs, [_ent("Jean Dupont", 0, 11)], _ref())
    assert runs[0].text == "[PERSONNE]"
```

- [ ] **Step 2 : Lancer les tests pour les voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_run_remap.py -v`
Expected : FAIL — `module anonymator.files.ooxml.run_remap has no attribute 'build_offsets'`.

- [ ] **Step 3 : Implémenter `run_remap.py`**

Créer `anonymator/files/ooxml/run_remap.py` :

```python
from anonymator.model import Entity
from anonymator.merge import merge_entities
from anonymator.referential import Referential


def build_offsets(runs) -> tuple[str, list[tuple[int, int, int]]]:
    """Texte concaténé + table [(index_run, char_start, char_end)].
    Un run vide occupe 0 caractère. Symétrique de pdf/mapping.py."""
    parts, spans, pos = [], [], 0
    for i, run in enumerate(runs):
        t = run.text or ""
        spans.append((i, pos, pos + len(t)))
        parts.append(t)
        pos += len(t)
    return "".join(parts), spans


def apply(runs, entities: list[Entity], ref: Referential) -> None:
    """Masque chaque span en préservant la mise en forme des runs non touchés.
    Mute `runs` en place.

    On traite de la fin vers le début : un remplacement n'affecte que le
    suffixe du texte, donc les offsets (absolus) des entités plus à gauche
    restent valides. On recalcule les offsets à chaque entité car la longueur
    des runs change après masquage (peu d'entités par paragraphe → négligeable).
    """
    for e in sorted(merge_entities(entities), key=lambda e: e.start, reverse=True):
        _, spans = build_offsets(runs)
        _mask_span(runs, spans, e.start, e.end, ref.tag_for(e.type))


def _mask_span(runs, spans, s: int, e: int, tag: str) -> None:
    touched = [(i, a, b) for (i, a, b) in spans if a < e and s < b]
    if not touched:
        return
    first = True
    for (i, a, b) in touched:
        lo = max(s, a) - a          # offset relatif au début du run
        hi = min(e, b) - a
        t = runs[i].text or ""
        if first:
            runs[i].text = t[:lo] + tag + t[hi:]
            first = False
        else:
            runs[i].text = t[:lo] + t[hi:]
```

- [ ] **Step 4 : Lancer les tests pour les voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_run_remap.py -v`
Expected : PASS (6 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/ooxml/run_remap.py tests/test_ooxml_run_remap.py
git commit -m "feat(ooxml): run_remap — masquage multi-runs preservant la mise en forme"
```

---

## Task 4 : `scan` (détection + application génériques sur `TextUnit`)

**Files:**
- Create: `anonymator/files/ooxml/scan.py`
- Test: `tests/test_ooxml_scan.py`

- [ ] **Step 1 : Écrire les tests d'abord**

Créer `tests/test_ooxml_scan.py` :

```python
from dataclasses import dataclass
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.ooxml import scan
from anonymator.files.ooxml.text_unit import TextUnit


@dataclass
class FakeRun:
    text: str


def _ref():
    return Referential.load_default()


def _unit(location, *texts):
    return TextUnit([FakeRun(t) for t in texts], location)


def test_scan_units_detects_per_unit():
    units = [_unit("Corps", "Bonjour Claire Martin"),
             _unit("Corps", "Rien ici")]
    ner = FakeNer({"Claire Martin": "PERSON"})
    scanned = scan.scan_units(units, ner, _ref())
    assert 0 in scanned and 1 not in scanned
    assert scanned[0][0].value == "Claire Martin"


def test_apply_units_masks_and_reports():
    units = [_unit("Tableau L1C1", "Client Claire Martin")]
    ner = FakeNer({"Claire Martin": "PERSON"})
    ref = _ref()
    scanned = scan.scan_units(units, ner, ref)
    report = scan.apply_units(units, scan.confirmed_only(scanned), ref)
    assert units[0].text() == "Client [PERSONNE]"
    rows = report.to_rows()
    assert rows[0]["original"] == "Claire Martin"
    assert rows[0]["locations"] == "Tableau L1C1"


def test_confirmed_only_drops_unconfirmed_and_empties():
    from anonymator.model import Entity
    scanned = {
        0: [Entity("PERSON", "X", 0, 1, "ner", 1.0, confirmed=True)],
        1: [Entity("IBAN", "Y", 0, 1, "deterministic", 1.0, confirmed=False)],
    }
    kept = scan.confirmed_only(scanned)
    assert 0 in kept and 1 not in kept
```

- [ ] **Step 2 : Lancer les tests pour les voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_scan.py -v`
Expected : FAIL — `module anonymator.files.ooxml.scan has no attribute 'scan_units'`.

- [ ] **Step 3 : Implémenter `scan.py`**

Créer `anonymator/files/ooxml/scan.py` :

```python
from anonymator.model import Entity
from anonymator.pipeline import detect
from anonymator.dedup import detect_unique
from anonymator.report.audit import AuditReport
from anonymator.files.ooxml import run_remap
from anonymator.files.ooxml.text_unit import TextUnit


def scan_units(units: list[TextUnit], ner, ref) -> dict[int, list[Entity]]:
    """Détecte les entités par unité (dédupliqué). Clé = index d'unité.
    Offsets relatifs au texte de l'unité (cf. dedup.detect_unique)."""
    texts = [u.text() for u in units]
    cache = detect_unique(texts, lambda v: detect(v, ner, ref))
    result: dict[int, list[Entity]] = {}
    for i, u in enumerate(units):
        ents = cache.get(u.text(), [])
        if ents:
            result[i] = ents
    return result


def confirmed_only(scanned: dict[int, list[Entity]]) -> dict[int, list[Entity]]:
    kept = {i: [e for e in ents if e.confirmed] for i, ents in scanned.items()}
    return {i: v for i, v in kept.items() if v}


def apply_units(units: list[TextUnit], retained: dict[int, list[Entity]],
                ref, report: AuditReport | None = None) -> AuditReport:
    """Masque les entités retenues par unité et alimente le rapport.
    Mute les runs des unités en place. Réutilise un `report` existant si fourni."""
    report = report if report is not None else AuditReport()
    for i, ents in retained.items():
        if not ents:
            continue
        u = units[i]
        for e in ents:
            report.add(e.type, e.value, ref.tag_for(e.type), u.location)
        run_remap.apply(u.runs, ents, ref)
    return report
```

- [ ] **Step 4 : Lancer les tests pour les voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_scan.py -v`
Expected : PASS (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/ooxml/scan.py tests/test_ooxml_scan.py
git commit -m "feat(ooxml): scan/apply generiques sur TextUnit"
```

---

## Task 5 : `metadata` (purge core.xml / app.xml)

**Files:**
- Create: `anonymator/files/ooxml/metadata.py`
- Test: `tests/test_ooxml_metadata.py`

- [ ] **Step 1 : Écrire les tests d'abord**

Créer `tests/test_ooxml_metadata.py` :

```python
from anonymator.files.ooxml import metadata

CORE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<cp:coreProperties '
    'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/">'
    '<dc:creator>Alice Durand</dc:creator>'
    '<cp:lastModifiedBy>Bob Martin</cp:lastModifiedBy>'
    '<dc:title>Rapport confidentiel</dc:title>'
    '</cp:coreProperties>'
).encode("utf-8")

APP = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Properties '
    'xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
    '<Company>ACME SARL</Company><Manager>Alice Durand</Manager>'
    '</Properties>'
).encode("utf-8")


def test_purge_core_xml_blanks_identity_fields():
    out, purged = metadata.purge_core_xml(CORE)
    labels = {label for label, _ in purged}
    assert labels == {"Auteur", "Dernier modifié par", "Titre"}
    assert b"Alice Durand" not in out
    assert b"Bob Martin" not in out
    assert b"Rapport confidentiel" not in out


def test_purge_app_xml_blanks_company_manager():
    out, purged = metadata.purge_app_xml(APP)
    labels = {label for label, _ in purged}
    assert labels == {"Société", "Manager"}
    assert b"ACME" not in out


def test_purge_core_xml_ignores_missing_fields():
    minimal = (
        '<?xml version="1.0"?><cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties">'
        '</cp:coreProperties>'
    ).encode("utf-8")
    out, purged = metadata.purge_core_xml(minimal)
    assert purged == []
```

- [ ] **Step 2 : Lancer les tests pour les voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_metadata.py -v`
Expected : FAIL — `module anonymator.files.ooxml.metadata has no attribute 'purge_core_xml'`.

- [ ] **Step 3 : Implémenter `metadata.py`**

Créer `anonymator/files/ooxml/metadata.py` :

```python
from lxml import etree

_DC = "http://purl.org/dc/elements/1.1/"
_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"

# (namespace, balise, libellé audit)
_CORE_FIELDS = [
    (_DC, "creator", "Auteur"),
    (_CP, "lastModifiedBy", "Dernier modifié par"),
    (_DC, "title", "Titre"),
    (_DC, "subject", "Sujet"),
    (_CP, "keywords", "Mots-clés"),
    (_DC, "description", "Commentaires"),
    (_CP, "category", "Catégorie"),
]
_APP_FIELDS = [
    (_EP, "Company", "Société"),
    (_EP, "Manager", "Manager"),
]


def _purge(xml_bytes: bytes, fields) -> tuple[bytes, list[tuple[str, str]]]:
    root = etree.fromstring(xml_bytes)
    purged: list[tuple[str, str]] = []
    for ns, tag, label in fields:
        el = root.find(f"{{{ns}}}{tag}")
        if el is not None and (el.text or "").strip():
            purged.append((label, el.text))
            el.text = ""
    out = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                         standalone=True)
    return out, purged


def purge_core_xml(xml_bytes: bytes) -> tuple[bytes, list[tuple[str, str]]]:
    return _purge(xml_bytes, _CORE_FIELDS)


def purge_app_xml(xml_bytes: bytes) -> tuple[bytes, list[tuple[str, str]]]:
    return _purge(xml_bytes, _APP_FIELDS)
```

- [ ] **Step 4 : Lancer les tests pour les voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_metadata.py -v`
Expected : PASS (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/ooxml/metadata.py tests/test_ooxml_metadata.py
git commit -m "feat(ooxml): purge des metadonnees core.xml/app.xml"
```

---

## Task 6 : `COVERAGE` (constante périmètre)

**Files:**
- Modify: `anonymator/files/ooxml/__init__.py`
- Test: `tests/test_ooxml_xml_parts.py` (créé Task 7 ; ici un test minimal inline)

- [ ] **Step 1 : Écrire le test d'abord**

Créer `tests/test_ooxml_coverage.py` :

```python
from anonymator.files import ooxml


def test_coverage_has_both_lists_nonempty():
    assert set(ooxml.COVERAGE) == {"traite", "non_traite"}
    assert ooxml.COVERAGE["traite"]
    assert ooxml.COVERAGE["non_traite"]
    assert any("OCR" in x or "image" in x for x in ooxml.COVERAGE["non_traite"])
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_coverage.py -v`
Expected : FAIL — `module 'anonymator.files.ooxml' has no attribute 'COVERAGE'`.

- [ ] **Step 3 : Implémenter la constante**

Remplacer le contenu de `anonymator/files/ooxml/__init__.py` par :

```python
# Périmètre de l'anonymisation OOXML — source de vérité unique partagée
# entre l'UI (PerimetreCard) et la documentation.
COVERAGE = {
    "traite": [
        "Corps du document et paragraphes",
        "Tableaux (y compris imbriqués)",
        "En-têtes et pieds de page",
        "Zones de texte",
        "Commentaires et notes de bas de page / de fin (Word)",
        "Slides, groupes de formes et notes du présentateur (PowerPoint)",
        "Purge des métadonnées (auteur, société, dernier éditeur…)",
    ],
    "non_traite": [
        "Champs calculés et insertions automatiques",
        "Équations",
        "Texte à l'intérieur des images (pas d'OCR)",
        "Données de graphiques liées à un fichier externe",
        "Diagrammes SmartArt",
    ],
}
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_coverage.py -v`
Expected : PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/ooxml/__init__.py tests/test_ooxml_coverage.py
git commit -m "feat(ooxml): constante COVERAGE (perimetre traite/non traite)"
```

---

## Task 7 : `xml_parts` (XmlRun + post-passe zip)

**Files:**
- Create: `anonymator/files/ooxml/xml_parts.py`
- Test: `tests/test_ooxml_xml_parts.py`

**Contexte :** `XmlRun` adapte un élément `<w:r>` (ou `<a:r>`) à l'interface « run » (`.text`). `postprocess_docx` ouvre le fichier .docx produit comme un zip, masque les commentaires/notes (entités confirmées) en réutilisant `scan`, purge core.xml/app.xml, et réécrit le zip. `postprocess_metadata` fait la même chose mais métadonnées seules (pour pptx).

- [ ] **Step 1 : Écrire les tests d'abord**

Créer `tests/test_ooxml_xml_parts.py` :

```python
from lxml import etree
from anonymator.files.ooxml.xml_parts import XmlRun

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _run(text):
    r = etree.SubElement(etree.Element(f"{{{W}}}p"), f"{{{W}}}r")
    t = etree.SubElement(r, f"{{{W}}}t")
    t.text = text
    return r


def test_xmlrun_reads_text():
    assert XmlRun(_run("Bonjour")).text == "Bonjour"


def test_xmlrun_writes_text_into_first_t():
    r = _run("Bonjour")
    run = XmlRun(r)
    run.text = "Salut"
    assert run.text == "Salut"
    assert r.find(f"{{{W}}}t").text == "Salut"


def test_xmlrun_sets_space_preserve_on_leading_space():
    r = _run("x")
    XmlRun(r).text = " abc "
    t = r.find(f"{{{W}}}t")
    assert t.get("{http://www.w3.org/XML/1998/namespace}space") == "preserve"
```

Et un test d'intégration de la post-passe sur un zip fabriqué à la main (sans
python-docx), qui valide le masquage des commentaires/notes + la purge des
métadonnées. Ajouter à `tests/test_ooxml_xml_parts.py` :

```python
import zipfile
from anonymator.report.audit import AuditReport
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.ooxml import xml_parts


def _para(text):
    return f'<w:p xmlns:w="{W}"><w:r><w:t>{text}</w:t></w:r></w:p>'


def _make_docx_zip(path):
    parts = {
        "[Content_Types].xml": '<?xml version="1.0"?><Types/>',
        "word/document.xml":
            f'<?xml version="1.0"?><w:document xmlns:w="{W}"><w:body/></w:document>',
        "word/comments.xml":
            f'<?xml version="1.0"?><w:comments xmlns:w="{W}">'
            f'<w:comment w:id="1">{_para("Vu par Claire Martin")}</w:comment>'
            f'</w:comments>',
        "word/footnotes.xml":
            f'<?xml version="1.0"?><w:footnotes xmlns:w="{W}">'
            f'<w:footnote w:type="separator" w:id="1">{_para("")}</w:footnote>'
            f'<w:footnote w:id="2">{_para("Note de Claire Martin")}</w:footnote>'
            f'</w:footnotes>',
        "docProps/core.xml":
            '<?xml version="1.0"?><cp:coreProperties '
            'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            '<dc:creator>Alice Durand</dc:creator></cp:coreProperties>',
    }
    with zipfile.ZipFile(path, "w") as z:
        for name, blob in parts.items():
            z.writestr(name, blob)


def test_postprocess_docx_masks_parts_and_purges_metadata(tmp_path):
    path = tmp_path / "d.docx"
    _make_docx_zip(path)
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    report = xml_parts.postprocess_docx(path, ner, ref, AuditReport())
    with zipfile.ZipFile(path) as z:
        comments = z.read("word/comments.xml").decode("utf-8")
        footnotes = z.read("word/footnotes.xml").decode("utf-8")
        core = z.read("docProps/core.xml").decode("utf-8")
    assert "Claire Martin" not in comments and "[PERSONNE]" in comments
    assert "Claire Martin" not in footnotes and "[PERSONNE]" in footnotes
    assert "Alice Durand" not in core
    assert any(r["original"] == "Claire Martin" for r in report.to_rows())
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_xml_parts.py -v`
Expected : FAIL — `cannot import name 'XmlRun'`.

- [ ] **Step 3 : Implémenter `xml_parts.py`**

Créer `anonymator/files/ooxml/xml_parts.py` :

```python
import zipfile
from pathlib import Path
from lxml import etree
from anonymator.report.audit import AuditReport
from anonymator.files.ooxml import scan, metadata
from anonymator.files.ooxml.text_unit import TextUnit

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


class XmlRun:
    """Adaptateur « run » sur un élément <w:r>/<a:r> : lit/écrit son texte
    (concaténation des <w:t>/<a:t>). L'écriture va dans le premier nœud texte,
    vide les suivants, et pose xml:space=preserve si le texte a des espaces
    en bordure."""

    def __init__(self, r_element, t_tag: str = f"{{{_W}}}t"):
        self._r = r_element
        self._t_tag = t_tag

    def _texts(self):
        return self._r.findall(self._t_tag)

    @property
    def text(self) -> str:
        return "".join((t.text or "") for t in self._texts())

    @text.setter
    def text(self, value: str) -> None:
        ts = self._texts()
        if not ts:
            return
        ts[0].text = value
        if value != value.strip():
            ts[0].set(_XML_SPACE, "preserve")
        for extra in ts[1:]:
            extra.text = ""


def _word_units_from_container(container, location: str) -> list[TextUnit]:
    """Un TextUnit par <w:p> descendant, runs = <w:r> enfants directs du <w:p>."""
    t_tag = f"{{{_W}}}t"
    units = []
    for p in container.iter(f"{{{_W}}}p"):
        runs = [XmlRun(r, t_tag) for r in p.findall(f"{{{_W}}}r")]
        if runs:
            units.append(TextUnit(runs, location))
    return units


def _comment_units(root) -> list[TextUnit]:
    units = []
    for n, comment in enumerate(root.findall(f"{{{_W}}}comment"), 1):
        units += _word_units_from_container(comment, f"Commentaire {n}")
    return units


def _footnote_units(root, label: str) -> list[TextUnit]:
    tag = "footnote" if label == "Note" else "endnote"
    units = []
    n = 0
    for note in root.findall(f"{{{_W}}}{tag}"):
        # Ignore les notes de séparateur (type "separator"/"continuationSeparator").
        ntype = note.get(f"{{{_W}}}type")
        if ntype in ("separator", "continuationSeparator"):
            continue
        n += 1
        units += _word_units_from_container(note, f"{label} {n}")
    return units


def _read_zip(path: Path) -> tuple[list[str], dict[str, bytes]]:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        return names, {n: z.read(n) for n in names}


def _write_zip(path: Path, names: list[str], data: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, data[n])


def _purge_metadata(data: dict[str, bytes], report: AuditReport) -> None:
    for name, purge in (("docProps/core.xml", metadata.purge_core_xml),
                        ("docProps/app.xml", metadata.purge_app_xml)):
        if name in data:
            new_bytes, purged = purge(data[name])
            if purged:
                data[name] = new_bytes
                for label, old in purged:
                    report.add("META", old, "", f"Métadonnées / {label}")


def postprocess_docx(path: Path, ner, ref, report: AuditReport) -> AuditReport:
    """Masque commentaires/notes (entités confirmées) + purge métadonnées,
    dans le .docx déjà écrit. Réécrit le zip. Complète `report`."""
    names, data = _read_zip(path)
    part_extractors = {
        "word/comments.xml": _comment_units,
        "word/footnotes.xml": lambda root: _footnote_units(root, "Note"),
        "word/endnotes.xml": lambda root: _footnote_units(root, "Note de fin"),
    }
    for name, extract in part_extractors.items():
        if name not in data:
            continue
        root = etree.fromstring(data[name])
        units = extract(root)
        retained = scan.confirmed_only(scan.scan_units(units, ner, ref))
        if retained:
            scan.apply_units(units, retained, ref, report)
            data[name] = etree.tostring(root, xml_declaration=True,
                                        encoding="UTF-8", standalone=True)
    _purge_metadata(data, report)
    _write_zip(path, names, data)
    return report


def postprocess_metadata(path: Path, report: AuditReport) -> AuditReport:
    """Purge des métadonnées seules (pptx). Réécrit le zip. Complète `report`."""
    names, data = _read_zip(path)
    _purge_metadata(data, report)
    _write_zip(path, names, data)
    return report
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_xml_parts.py -v`
Expected : PASS (4 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/ooxml/xml_parts.py tests/test_ooxml_xml_parts.py
git commit -m "feat(ooxml): XmlRun + post-passe zip (commentaires/notes/metadonnees)"
```

---

## Task 8 : Fixtures de test docx/pptx

**Files:**
- Create: `tests/ooxml_fixtures.py`
- Test: `tests/test_ooxml_fixtures.py`

- [ ] **Step 1 : Écrire le test d'abord**

Créer `tests/test_ooxml_fixtures.py` :

```python
from docx import Document
from pptx import Presentation
from tests.ooxml_fixtures import make_docx, make_pptx


def test_make_docx_roundtrips(tmp_path):
    path = make_docx(tmp_path / "s.docx")
    doc = Document(str(path))
    assert any("Claire Martin" in p.text for p in doc.paragraphs)


def test_make_pptx_roundtrips(tmp_path):
    path = make_pptx(tmp_path / "s.pptx")
    prs = Presentation(str(path))
    texts = [sh.text_frame.text for sl in prs.slides for sh in sl.shapes
             if sh.has_text_frame]
    assert any("Claire Martin" in t for t in texts)
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_fixtures.py -v`
Expected : FAIL — `No module named 'tests.ooxml_fixtures'`.

- [ ] **Step 3 : Implémenter les fixtures**

Créer `tests/ooxml_fixtures.py` :

```python
from pathlib import Path
from docx import Document
from pptx import Presentation
from pptx.util import Inches


def make_docx(path: Path) -> Path:
    """Document Word couvrant corps, tableau, en-tête, pied, zone de texte et
    métadonnées — tous conservés par le round-trip python-docx.

    Note : les commentaires / notes de bas de page vivent dans des parties
    séparées (comments.xml, footnotes.xml) qui, dans un vrai .docx, sont
    référencées par des relations et donc conservées à la sauvegarde. On ne
    les injecte pas ici (python-docx les abandonnerait faute de relation) : le
    mécanisme de post-passe est validé isolément dans test_ooxml_xml_parts.py.
    """
    doc = Document()
    doc.core_properties.author = "Alice Durand"
    doc.core_properties.last_modified_by = "Bob Martin"

    # Corps, avec un run scindé manuellement pour tester le remap.
    p = doc.add_paragraph("Contact : ")
    p.add_run("Claire ")
    p.add_run("Mar")
    p.add_run("tin")

    # Tableau
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Fournisseur"
    table.rows[0].cells[1].text = "Claire Martin"

    # En-tête / pied
    section = doc.sections[0]
    section.header.paragraphs[0].text = "Dossier de Claire Martin"
    section.footer.paragraphs[0].text = "Rédigé par Claire Martin"

    doc.save(str(path))
    _inject_textbox(path)
    return path


def _inject_textbox(path: Path) -> None:
    """Ajoute au document.xml une zone de texte (txbxContent) contenant
    « Claire Martin » — que python-docx ne crée pas directement, mais qu'il
    conserve car elle réside dans la partie principale."""
    import zipfile
    from lxml import etree
    W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}

    doc_root = etree.fromstring(data["word/document.xml"])
    body = doc_root.find(f"{{{W}}}body")
    txbx = etree.SubElement(body, f"{{{W}}}txbxContent")
    txbx.append(etree.fromstring(
        f'<w:p xmlns:w="{W}"><w:r><w:t>Zone de Claire Martin</w:t></w:r></w:p>'))
    data["word/document.xml"] = etree.tostring(doc_root, xml_declaration=True,
                                               encoding="UTF-8", standalone=True)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, data[n])


def make_pptx(path: Path) -> Path:
    """Présentation couvrant une zone de texte, un tableau, un groupe et
    les notes du présentateur."""
    prs = Presentation()
    prs.core_properties.author = "Alice Durand"
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

    box = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
    box.text_frame.text = "Client Claire Martin"

    table = slide.shapes.add_table(1, 2, Inches(1), Inches(3),
                                   Inches(4), Inches(1)).table
    table.cell(0, 0).text = "Nom"
    table.cell(0, 1).text = "Claire Martin"

    notes = slide.notes_slide.notes_text_frame
    notes.text = "Présenté par Claire Martin"

    prs.save(str(path))
    return path
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_fixtures.py -v`
Expected : PASS (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add tests/ooxml_fixtures.py tests/test_ooxml_fixtures.py
git commit -m "test(ooxml): fixtures docx/pptx programmatiques"
```

---

## Task 9 : `docx_io` + intégration bout-en-bout Word

**Files:**
- Create: `anonymator/files/ooxml/docx_io.py`
- Test: `tests/test_anonymize_docx.py`

- [ ] **Step 1 : Écrire le test d'abord**

Créer `tests/test_anonymize_docx.py` :

```python
from datetime import datetime
import zipfile
from docx import Document
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.ooxml import docx_io
from tests.ooxml_fixtures import make_docx


def _anonymize(tmp_path):
    src = make_docx(tmp_path / "src.docx")
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    out, report = docx_io.anonymize_document(
        src, ner, ref, tmp_path, when=datetime(2026, 7, 3, 9, 0, 0))
    return src, out, report


def test_output_name_and_body_masked(tmp_path):
    _, out, _ = _anonymize(tmp_path)
    assert out.name == "src_ano_20260703090000.docx"
    doc = Document(str(out))
    assert doc.paragraphs[0].text == "Contact : [PERSONNE]"


def test_table_header_footer_masked(tmp_path):
    _, out, _ = _anonymize(tmp_path)
    doc = Document(str(out))
    assert doc.tables[0].rows[0].cells[1].text == "[PERSONNE]"
    assert "[PERSONNE]" in doc.sections[0].header.paragraphs[0].text
    assert "[PERSONNE]" in doc.sections[0].footer.paragraphs[0].text


def test_textbox_masked(tmp_path):
    # La zone de texte vit dans document.xml : elle survit au round-trip
    # python-docx. (Commentaires/notes = testés dans test_ooxml_xml_parts.py.)
    _, out, _ = _anonymize(tmp_path)
    with zipfile.ZipFile(out) as z:
        document = z.read("word/document.xml").decode("utf-8")
    assert "Claire Martin" not in document and "[PERSONNE]" in document


def test_metadata_purged(tmp_path):
    _, out, _ = _anonymize(tmp_path)
    doc = Document(str(out))
    assert (doc.core_properties.author or "") == ""
    assert (doc.core_properties.last_modified_by or "") == ""


def test_report_and_original_untouched(tmp_path):
    src, _, report = _anonymize(tmp_path)
    assert any(r["original"] == "Claire Martin" for r in report.to_rows())
    assert "Claire Martin" in Document(str(src)).paragraphs[0].text
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_anonymize_docx.py -v`
Expected : FAIL — `cannot import name 'docx_io'` ou `anonymize_document` absent.

- [ ] **Step 3 : Implémenter `docx_io.py`**

Créer `anonymator/files/ooxml/docx_io.py` :

```python
from datetime import datetime
from pathlib import Path
from docx import Document
from anonymator.output_naming import anonymized_path
from anonymator.report.audit import AuditReport
from anonymator.files.ooxml import scan, xml_parts
from anonymator.files.ooxml.text_unit import TextUnit
from anonymator.files.ooxml.xml_parts import XmlRun

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _iter_block(container, prefix: str):
    for p in container.paragraphs:
        if p.runs:
            yield TextUnit(list(p.runs), prefix)
    for table in container.tables:
        yield from _iter_table(table, prefix)


def _iter_table(table, prefix: str):
    base = "" if prefix == "Corps" else f"{prefix} / "
    for ri, row in enumerate(table.rows, 1):
        for ci, cell in enumerate(row.cells, 1):
            loc = f"{base}Tableau L{ri}C{ci}"
            for p in cell.paragraphs:
                if p.runs:
                    yield TextUnit(list(p.runs), loc)
            for nested in cell.tables:
                yield from _iter_table(nested, loc)


def _iter_textboxes(doc):
    t_tag = f"{{{_W}}}t"
    body = doc.element.body
    for txbx in body.iter(f"{{{_W}}}txbxContent"):
        for p in txbx.iter(f"{{{_W}}}p"):
            runs = [XmlRun(r, t_tag) for r in p.findall(f"{{{_W}}}r")]
            if runs:
                yield TextUnit(runs, "Zone de texte")


def iter_main_units(doc):
    """Unités des conteneurs de la partie principale (sauvegardées nativement
    par doc.save) : corps, tableaux, en-têtes/pieds, zones de texte."""
    yield from _iter_block(doc, "Corps")
    for section in doc.sections:
        if not section.header.is_linked_to_previous:
            yield from _iter_block(section.header, "En-tête")
        if not section.footer.is_linked_to_previous:
            yield from _iter_block(section.footer, "Pied")
    yield from _iter_textboxes(doc)


def anonymize_document(path: Path, ner, ref, output_dir: Path,
                       when: datetime) -> tuple[Path, AuditReport]:
    doc = Document(str(path))
    units = list(iter_main_units(doc))
    retained = scan.confirmed_only(scan.scan_units(units, ner, ref))
    report = scan.apply_units(units, retained, ref)
    out = anonymized_path(path, output_dir, when)
    doc.save(str(out))
    xml_parts.postprocess_docx(out, ner, ref, report)
    return out, report
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_anonymize_docx.py -v`
Expected : PASS (5 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/ooxml/docx_io.py tests/test_anonymize_docx.py
git commit -m "feat(ooxml): docx_io — anonymisation Word bout-en-bout"
```

---

## Task 10 : `pptx_io` + intégration bout-en-bout PowerPoint

**Files:**
- Create: `anonymator/files/ooxml/pptx_io.py`
- Test: `tests/test_anonymize_pptx.py`

- [ ] **Step 1 : Écrire le test d'abord**

Créer `tests/test_anonymize_pptx.py` :

```python
from datetime import datetime
from pptx import Presentation
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.files.ooxml import pptx_io
from tests.ooxml_fixtures import make_pptx


def _anonymize(tmp_path):
    src = make_pptx(tmp_path / "src.pptx")
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    out, report = pptx_io.anonymize_document(
        src, ner, ref, tmp_path, when=datetime(2026, 7, 3, 9, 0, 0))
    return src, out, report


def test_output_name_and_textbox_masked(tmp_path):
    _, out, _ = _anonymize(tmp_path)
    assert out.name == "src_ano_20260703090000.pptx"
    prs = Presentation(str(out))
    texts = [sh.text_frame.text for sl in prs.slides for sh in sl.shapes
             if sh.has_text_frame]
    assert "Client [PERSONNE]" in texts


def test_table_and_notes_masked(tmp_path):
    _, out, _ = _anonymize(tmp_path)
    prs = Presentation(str(out))
    slide = prs.slides[0]
    table = next(sh.table for sh in slide.shapes if sh.has_table)
    assert table.cell(0, 1).text == "[PERSONNE]"
    assert "[PERSONNE]" in slide.notes_slide.notes_text_frame.text


def test_metadata_purged(tmp_path):
    _, out, _ = _anonymize(tmp_path)
    prs = Presentation(str(out))
    assert (prs.core_properties.author or "") == ""


def test_report_present(tmp_path):
    _, _, report = _anonymize(tmp_path)
    assert any(r["original"] == "Claire Martin" for r in report.to_rows())
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_anonymize_pptx.py -v`
Expected : FAIL — `cannot import name 'pptx_io'`.

- [ ] **Step 3 : Implémenter `pptx_io.py`**

Créer `anonymator/files/ooxml/pptx_io.py` :

```python
from datetime import datetime
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from anonymator.output_naming import anonymized_path
from anonymator.report.audit import AuditReport
from anonymator.files.ooxml import scan, xml_parts
from anonymator.files.ooxml.text_unit import TextUnit


def _iter_frame(text_frame, location: str):
    for p in text_frame.paragraphs:
        if p.runs:
            yield TextUnit(list(p.runs), location)


def _iter_shapes(shapes, prefix: str):
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _iter_shapes(shape.shapes, prefix)
            continue
        # has_table n'existe que sur GraphicFrame ; has_text_frame varie selon
        # le type de forme → accès défensif via getattr.
        if getattr(shape, "has_text_frame", False):
            yield from _iter_frame(shape.text_frame, prefix)
        if getattr(shape, "has_table", False):
            for ri, row in enumerate(shape.table.rows, 1):
                for ci, cell in enumerate(row.cells, 1):
                    yield from _iter_frame(
                        cell.text_frame, f"{prefix} / Tableau L{ri}C{ci}")


def iter_main_units(prs):
    for si, slide in enumerate(prs.slides, 1):
        yield from _iter_shapes(slide.shapes, f"Slide {si}")
        if slide.has_notes_slide:
            tf = slide.notes_slide.notes_text_frame
            if tf is not None:
                yield from _iter_frame(tf, f"Slide {si} / Notes")


def anonymize_document(path: Path, ner, ref, output_dir: Path,
                       when: datetime) -> tuple[Path, AuditReport]:
    prs = Presentation(str(path))
    units = list(iter_main_units(prs))
    retained = scan.confirmed_only(scan.scan_units(units, ner, ref))
    report = scan.apply_units(units, retained, ref)
    out = anonymized_path(path, output_dir, when)
    prs.save(str(out))
    xml_parts.postprocess_metadata(out, report)
    return out, report
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_anonymize_pptx.py -v`
Expected : PASS (4 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/ooxml/pptx_io.py tests/test_anonymize_pptx.py
git commit -m "feat(ooxml): pptx_io — anonymisation PowerPoint bout-en-bout"
```

---

## Task 11 : Dispatch dans `anonymize_file`

**Files:**
- Modify: `anonymator/files/anonymize_file.py:105-125`
- Test: `tests/test_anonymize_file.py`

- [ ] **Step 1 : Ajouter les tests de dispatch**

Ajouter à la fin de `tests/test_anonymize_file.py` :

```python
def test_dispatch_docx(tmp_path):
    from datetime import datetime
    from anonymator.referential import Referential
    from anonymator.ner import FakeNer
    from anonymator.files.anonymize_file import anonymize_file
    from tests.ooxml_fixtures import make_docx
    src = make_docx(tmp_path / "d.docx")
    res = anonymize_file(src, FakeNer({"Claire Martin": "PERSON"}),
                         Referential.load_default(), tmp_path, datetime.now())
    assert res.output_path.suffix == ".docx"
    assert any(r["original"] == "Claire Martin" for r in res.report.to_rows())


def test_dispatch_pptx(tmp_path):
    from datetime import datetime
    from anonymator.referential import Referential
    from anonymator.ner import FakeNer
    from anonymator.files.anonymize_file import anonymize_file
    from tests.ooxml_fixtures import make_pptx
    src = make_pptx(tmp_path / "p.pptx")
    res = anonymize_file(src, FakeNer({"Claire Martin": "PERSON"}),
                         Referential.load_default(), tmp_path, datetime.now())
    assert res.output_path.suffix == ".pptx"
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_anonymize_file.py -k "docx or pptx" -v`
Expected : FAIL — `UnsupportedFormat: Format non supporté : .docx`.

- [ ] **Step 3 : Ajouter le dispatch**

Dans `anonymator/files/anonymize_file.py`, ajouter les fonctions et les branches.

Après `anonymize_xlsx` (vers la ligne 46), ajouter :

```python
def anonymize_docx(path: Path, ner: NerDetector, ref: Referential,
                   output_dir: Path, when: datetime) -> FileResult:
    from anonymator.files.ooxml import docx_io
    out, report = docx_io.anonymize_document(path, ner, ref, output_dir, when)
    return FileResult(out, report)


def anonymize_pptx(path: Path, ner: NerDetector, ref: Referential,
                   output_dir: Path, when: datetime) -> FileResult:
    from anonymator.files.ooxml import pptx_io
    out, report = pptx_io.anonymize_document(path, ner, ref, output_dir, when)
    return FileResult(out, report)
```

Dans `anonymize_file`, avant le `raise UnsupportedFormat`, ajouter :

```python
    if suffix == ".docx":
        return anonymize_docx(path, ner, ref, output_dir, when)
    if suffix == ".pptx":
        return anonymize_pptx(path, ner, ref, output_dir, when)
```

Et mettre à jour le message d'erreur final :

```python
    raise UnsupportedFormat(
        f"Format non supporté : {suffix} "
        f"(formats acceptés : .txt, .csv, .xlsx, .docx, .pptx)")
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_anonymize_file.py -v`
Expected : PASS (dont les 2 nouveaux + non-régression).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/anonymize_file.py tests/test_anonymize_file.py
git commit -m "feat(files): dispatch .docx/.pptx dans anonymize_file"
```

---

## Task 12 : `OoxmlReviewSession`

**Files:**
- Create: `anonymator/core/ooxml_review_session.py`
- Test: `tests/test_ooxml_review_session.py`

**Interface (miroir de `FileReviewSession`, sans colonnes) :** l'arbre UI existant consomme `types()`, `values_for(type)`, `count_retained(type)`, `total_occurrences()`, `is_type_enabled`/`set_type_enabled`, `is_value_enabled`/`set_value_enabled`. On ajoute `entities_for_unit(i)` (préview) et `apply_and_save(out_path)`.

- [ ] **Step 1 : Écrire les tests d'abord**

Créer `tests/test_ooxml_review_session.py` :

```python
from dataclasses import dataclass
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.files.ooxml.text_unit import TextUnit
from anonymator.core.ooxml_review_session import OoxmlReviewSession


@dataclass
class FakeRun:
    text: str


def _unit(loc, text):
    return TextUnit([FakeRun(text)], loc)


def _session(saved):
    units = [_unit("Corps", "Claire Martin et Marie Curie")]
    scanned = {0: [
        Entity("PERSON", "Claire Martin", 0, 13, "ner", 1.0, confirmed=True),
        Entity("PERSON", "Marie Curie", 17, 28, "ner", 1.0, confirmed=True),
    ]}

    def save_fn(out_path):
        saved["text"] = units[0].text()

    def post_fn(out_path, report):
        saved["report"] = report

    ref = Referential.load_default()
    return OoxmlReviewSession(units, scanned, ref, save_fn, post_fn), saved


def test_types_and_values():
    session, _ = _session({})
    assert session.types() == ["PERSON"]
    assert ("Claire Martin", 1) in session.values_for("PERSON")
    assert session.total_occurrences() == 2


def test_apply_masks_enabled_only():
    saved = {}
    session, saved = _session(saved)
    session.set_value_enabled("PERSON", "Marie Curie", False)
    session.apply_and_save("out.docx")
    assert saved["text"] == "[PERSONNE] et Marie Curie"


def test_disabling_type_keeps_all_clear():
    saved = {}
    session, saved = _session(saved)
    session.set_type_enabled("PERSON", False)
    session.apply_and_save("out.docx")
    assert saved["text"] == "Claire Martin et Marie Curie"
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_review_session.py -v`
Expected : FAIL — `No module named 'anonymator.core.ooxml_review_session'`.

- [ ] **Step 3 : Implémenter la session**

Créer `anonymator/core/ooxml_review_session.py` :

```python
from anonymator.model import Entity
from anonymator.files.ooxml import scan


class OoxmlReviewSession:
    """État de revue d'un document docx/pptx (non-Qt). Contrôle à deux
    niveaux combinés en ET : type activé, valeur distincte activée. Miroir de
    FileReviewSession sans la dimension colonnes/cellules (clé = index d'unité).

    En mode revue, l'arbre couvre les entités des parties principales ;
    commentaires/notes docx et métadonnées sont traités par `post_fn`
    (entités confirmées) au moment de l'application."""

    def __init__(self, units, scanned: dict[int, list[Entity]], ref,
                 save_fn, post_fn):
        self._units = units
        self._scanned = scanned
        self._ref = ref
        self._save_fn = save_fn
        self._post_fn = post_fn
        self._types_enabled: dict[str, bool] = {}
        self._values_enabled: dict[tuple[str, str], bool] = {}
        self._values_count: dict[tuple[str, str], int] = {}
        for ents in scanned.values():
            for e in ents:
                self._types_enabled.setdefault(e.type, True)
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                self._values_enabled.setdefault(key, e.confirmed)

    # --- lecture ---
    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def total_occurrences(self) -> int:
        return sum(self._values_count.values())

    def values_for(self, etype: str) -> list[tuple[str, int]]:
        items = [(v, n) for (t, v), n in self._values_count.items() if t == etype]
        return sorted(items)

    def _unit_retained(self, i: int) -> list[Entity]:
        out = []
        for e in self._scanned.get(i, []):
            if not self._types_enabled.get(e.type, True):
                continue
            if not self._values_enabled.get((e.type, e.value), True):
                continue
            out.append(e)
        return out

    def count_retained(self, etype: str) -> int:
        return sum(1 for i in self._scanned
                   for e in self._unit_retained(i) if e.type == etype)

    def entities_for_unit(self, i: int) -> list[Entity]:
        return self._unit_retained(i)

    def is_type_enabled(self, etype: str) -> bool:
        return self._types_enabled.get(etype, True)

    def is_value_enabled(self, etype: str, value: str) -> bool:
        return self._values_enabled.get((etype, value), True)

    # --- écriture ---
    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        self._types_enabled[etype] = enabled

    def set_value_enabled(self, etype: str, value: str, enabled: bool) -> None:
        self._values_enabled[(etype, value)] = enabled

    # --- production ---
    def apply_and_save(self, out_path):
        retained = {i: self._unit_retained(i) for i in self._scanned}
        retained = {i: v for i, v in retained.items() if v}
        report = scan.apply_units(self._units, retained, self._ref)
        self._save_fn(out_path)
        self._post_fn(out_path, report)
        return report
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_review_session.py -v`
Expected : PASS (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/ooxml_review_session.py tests/test_ooxml_review_session.py
git commit -m "feat(core): OoxmlReviewSession (revue par type/valeur)"
```

---

## Task 13 : Worker d'analyse UI

**Files:**
- Create: `anonymator/ui/ooxml_scan_worker.py`
- Test: `tests/test_ooxml_scan_worker.py`

Le worker ouvre le document dans le thread, produit les unités principales + le scan brut, et émet un objet `OoxmlScanResult` (dataclass) portant tout ce dont l'écran a besoin pour construire la session (doc, units, scanned, fmt).

- [ ] **Step 1 : Écrire le test d'abord**

Créer `tests/test_ooxml_scan_worker.py` :

```python
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.ooxml_scan_worker import OoxmlScanWorker, OoxmlScanResult
from tests.ooxml_fixtures import make_docx, make_pptx


def _run_worker(path, qtbot):
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    worker = OoxmlScanWorker(path, loader, Referential.load_default())
    results = []
    worker.scan_finished.connect(results.append)
    with qtbot.waitSignal(worker.scan_finished, timeout=10000):
        worker.start()
    return results[0]


def test_worker_docx(tmp_path, qtbot):
    res = _run_worker(make_docx(tmp_path / "d.docx"), qtbot)
    assert isinstance(res, OoxmlScanResult)
    assert res.fmt == "docx"
    assert res.scanned  # au moins une unité avec entités
    assert res.units


def test_worker_pptx(tmp_path, qtbot):
    res = _run_worker(make_pptx(tmp_path / "p.pptx"), qtbot)
    assert res.fmt == "pptx"
    assert res.scanned
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_scan_worker.py -v`
Expected : FAIL — `No module named 'anonymator.ui.ooxml_scan_worker'`.

- [ ] **Step 3 : Implémenter le worker**

Créer `anonymator/ui/ooxml_scan_worker.py` :

```python
from dataclasses import dataclass
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from anonymator.files.ooxml import scan, docx_io, pptx_io


@dataclass
class OoxmlScanResult:
    fmt: str                 # "docx" | "pptx"
    doc: object              # Document python-docx ou Presentation python-pptx
    units: list              # list[TextUnit] des parties principales
    scanned: dict            # dict[int, list[Entity]] (brut, incl. non confirmés)


class OoxmlScanWorker(QThread):
    scan_finished = Signal(object)   # OoxmlScanResult
    error = Signal(str)

    def __init__(self, path: Path, loader, ref):
        super().__init__()
        self._path, self._loader, self._ref = Path(path), loader, ref

    def run(self):
        try:
            ner = self._loader.get()
            suffix = self._path.suffix.lower()
            if suffix == ".docx":
                from docx import Document
                doc = Document(str(self._path))
                units = list(docx_io.iter_main_units(doc))
                fmt = "docx"
            else:
                from pptx import Presentation
                doc = Presentation(str(self._path))
                units = list(pptx_io.iter_main_units(doc))
                fmt = "pptx"
            scanned = scan.scan_units(units, ner, self._ref)
            self.scan_finished.emit(OoxmlScanResult(fmt, doc, units, scanned))
        except Exception as exc:  # noqa: BLE001 — remonté à l'UI via error
            self.error.emit(str(exc))
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_ooxml_scan_worker.py -v`
Expected : PASS (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/ooxml_scan_worker.py tests/test_ooxml_scan_worker.py
git commit -m "feat(ui): OoxmlScanWorker (analyse docx/pptx hors thread UI)"
```

---

## Task 14 : `PerimetreCard`

**Files:**
- Create: `anonymator/ui/components/perimetre_card.py`
- Test: `tests/test_perimetre_card.py`

- [ ] **Step 1 : Écrire le test d'abord**

Créer `tests/test_perimetre_card.py` :

```python
from anonymator.ui.components.perimetre_card import PerimetreCard
from anonymator.files import ooxml


def test_card_lists_all_coverage_items(qtbot):
    card = PerimetreCard()
    qtbot.addWidget(card)
    text = card.rendered_text()
    for item in ooxml.COVERAGE["traite"]:
        assert item in text
    for item in ooxml.COVERAGE["non_traite"]:
        assert item in text
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_perimetre_card.py -v`
Expected : FAIL — `No module named 'anonymator.ui.components.perimetre_card'`.

- [ ] **Step 3 : Implémenter la carte**

Créer `anonymator/ui/components/perimetre_card.py` :

```python
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from anonymator.files import ooxml
from anonymator.ui.theme import color


class PerimetreCard(QFrame):
    """Encart persistant listant ce qui est traité et ce qui ne l'est pas,
    à partir de la constante ooxml.COVERAGE (source de vérité unique)."""

    def __init__(self):
        super().__init__()
        self.setObjectName("PerimetreCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(4)
        traite = "".join(f"• {x}<br>" for x in ooxml.COVERAGE["traite"])
        non = "".join(f"• {x}<br>" for x in ooxml.COVERAGE["non_traite"])
        self._html = (
            f"<b style='color:{color('action')}'>✅ Traité</b><br>{traite}"
            f"<br><b>⚠️ Non traité — à vérifier manuellement</b><br>{non}"
        )
        label = QLabel(self._html)
        label.setTextFormat(Qt.RichText)
        label.setWordWrap(True)
        lay.addWidget(label)

    def rendered_text(self) -> str:
        """Texte brut (pour tests) : items sans balises."""
        return self._html
```

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_perimetre_card.py -v`
Expected : PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/components/perimetre_card.py tests/test_perimetre_card.py
git commit -m "feat(ui): PerimetreCard (affichage traite/non traite)"
```

---

## Task 15 : Intégration dans `FileScreen`

**Files:**
- Modify: `anonymator/ui/file_screen.py`
- Test: `tests/test_file_screen.py`

**But :** ouvrir/analyser/réviser/appliquer les docx/pptx en réutilisant l'arbre « Entités détectées » (compatible via l'API de `OoxmlReviewSession`), afficher la préview 2 colonnes (Emplacement / Texte) et la `PerimetreCard`. Les méthodes CSV existantes (`_render_page`, `_data_rows`) restent pour le CSV ; on ajoute un rendu dédié pour les unités.

- [ ] **Step 1 : Écrire le test d'abord**

Ajouter à `tests/test_file_screen.py` :

```python
def test_file_screen_reviews_docx(tmp_path, qtbot):
    from anonymator.referential import Referential
    from anonymator.ner import FakeNer
    from anonymator.ui.model_loader import ModelLoader
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.file_screen import FileScreen
    from anonymator.core.ooxml_review_session import OoxmlReviewSession
    from tests.ooxml_fixtures import make_docx

    src = make_docx(tmp_path / "d.docx")
    prefs = Preferences(output_dir=str(tmp_path))
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    screen = FileScreen(Referential.load_default(), loader, prefs, on_back=lambda: None)
    qtbot.addWidget(screen)
    screen.load_path(str(src))
    assert screen.btn_review.isEnabled()

    with qtbot.waitSignal(screen._worker.scan_finished, timeout=10000):
        screen.analyze()
    assert isinstance(screen.session, OoxmlReviewSession)
    assert "PERSON" in screen.session.types()

    result = screen.run()
    assert result.output_path.exists()
    from docx import Document
    assert "[PERSONNE]" in Document(str(result.output_path)).paragraphs[0].text
```

- [ ] **Step 2 : Lancer pour voir échouer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_file_screen.py -k docx -v`
Expected : FAIL (l'analyse docx n'est pas branchée ; `screen._worker` est un `FileScanWorker` CSV ou None).

- [ ] **Step 3 : Modifier `file_screen.py`**

**3a.** En tête de fichier, ajouter les imports :

```python
from anonymator.core.ooxml_review_session import OoxmlReviewSession
from anonymator.ui.ooxml_scan_worker import OoxmlScanWorker
from anonymator.ui.components.perimetre_card import PerimetreCard
from anonymator.files.ooxml import xml_parts, metadata  # noqa: F401
```

**3b.** Filtre d'ouverture et libellés. Remplacer le filtre ligne ~173 :

```python
        path, _ = QFileDialog.getOpenFileName(
            self, "Ouvrir", "",
            "Fichiers (*.txt *.csv *.xlsx *.docx *.pptx)")
```

Et les deux libellés « Importez un fichier .txt, .csv ou .xlsx » (l. ~65 et ~157) :

```python
        self.meta_label = QLabel("Importez un fichier .txt, .csv, .xlsx, .docx ou .pptx")
```

**3c.** Ajouter la `PerimetreCard` au corps, masquée par défaut. Après la création de `ent_card` (vers l. 109), avant l'ajout au layout :

```python
        self.perimetre = PerimetreCard()
        self.perimetre.hide()
        ent_card.body.addWidget(self.perimetre)
```

**3d.** `load_path` : activer « Analyser » pour docx/pptx et cacher la grille CSV. Remplacer la ligne 184 :

```python
        self.btn_review.setEnabled(suffix in (".csv", ".txt", ".docx", ".pptx"))
```

Et après le bloc `if suffix == ".csv": ...`, ajouter :

```python
        else:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
        self.perimetre.setVisible(False)
```

**3e.** `analyze()` : brancher docx/pptx. Après le bloc `.txt` (l. 269-274) et avant `if self.doc is None:` (l. 275), insérer :

```python
        if self.path and self.path.suffix.lower() in (".docx", ".pptx"):
            self._degraded = not (self.loader.has_detector() or is_model_available())
            loader = ModelLoader(NullNer()) if self._degraded else self.loader
            self._set_busy(True)
            self._worker = OoxmlScanWorker(self.path, loader, self.ref)
            self._worker.scan_finished.connect(self._on_ooxml_scanned)
            self._worker.error.connect(self._on_scan_error)
            self._worker.finished.connect(self._worker.deleteLater)
            self._worker.start()
            return
```

**3f.** Ajouter les handlers de résultat et de rendu. Après `_on_scanned` (vers l. 317), ajouter :

```python
    def _on_ooxml_scanned(self, res):
        self._ooxml = res
        if res.fmt == "docx":
            save_fn = lambda out: res.doc.save(str(out))
            post_fn = lambda out, rep: xml_parts.postprocess_docx(
                out, self._detector_for_apply(), self.ref, rep)
        else:
            save_fn = lambda out: res.doc.save(str(out))
            post_fn = lambda out, rep: xml_parts.postprocess_metadata(out, rep)
        self.session = OoxmlReviewSession(
            res.units, res.scanned, self.ref, save_fn, post_fn)
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        self.occ_badge.setText(f"{_fmt_int(self.session.total_occurrences())} occ.")
        self.occ_badge.show(); self._hint.show()
        self._build_side()
        self.side.show(); self.perimetre.show()
        self.pager_widget.hide()
        self._render_units_page()

    def _detector_for_apply(self):
        # Post-passe (commentaires/notes) : même détecteur que l'analyse.
        return NullNer() if self._degraded else self.loader.get()

    def _render_units_page(self):
        units = self._ooxml.units
        self.table.clear()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Emplacement", "Texte extrait"])
        self.table.setRowCount(len(units))
        for r, u in enumerate(units):
            self.table.setItem(r, 0, QTableWidgetItem(u.location))
            item = QTableWidgetItem(u.text())
            if self.session.entities_for_unit(r):
                ents = self.session.entities_for_unit(r)
                col = QColor(color_for(ents[0].type)); col.setAlpha(70)
                item.setBackground(col)
            self.table.setItem(r, 1, item)
```

**3g.** Guarder `_on_side_changed` et `run()` pour la session OOXML.

Dans `_on_side_changed` (l. 346-356), remplacer la fin après avoir mis à jour la session :

```python
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
        if isinstance(self.session, OoxmlReviewSession):
            self._render_units_page()
        else:
            self._render_page()
```

Dans `run()` (l. 206-223), après `if self.session is not None:` remplacer le corps par une branche selon le type :

```python
        if self.session is not None:
            out = anonymized_path(self.path, out_dir, when)
            if isinstance(self.session, OoxmlReviewSession):
                report = self.session.apply_and_save(out)
                return FileResult(out, report)
            masked = self.session.masked_document()
            report = self.session.report()
            csv_io.write_csv(masked, out)
            return FileResult(out, report)
```

**3h.** Ajouter l'attribut `self._ooxml = None` dans `__init__` (près de `self.session = None`, l. 44) et le remettre à `None` dans `load_path` (près de `self.session = None`, l. 180), et masquer `self.perimetre` dans `load_path`.

- [ ] **Step 4 : Lancer pour voir passer**

Run : `.venv/Scripts/python.exe -m pytest tests/test_file_screen.py -v`
Expected : PASS (dont le nouveau test docx + non-régression CSV/txt).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen.py
git commit -m "feat(ui): FileScreen — revue et anonymisation docx/pptx"
```

---

## Task 16 : Packaging PyInstaller

**Files:**
- Modify: `anonymator.spec`
- Test: manuel (build de fumée)

- [ ] **Step 1 : Ajouter les data files des deux libs**

Dans `anonymator.spec`, en tête (après les imports PyInstaller existants) :

```python
from PyInstaller.utils.hooks import collect_data_files

ooxml_datas = collect_data_files('docx') + collect_data_files('pptx')
```

Puis, dans l'appel `Analysis(...)`, fusionner avec les `datas` existants :

```python
    datas=[...existants...] + ooxml_datas,
```

(Repérer la liste `datas=` actuelle et concaténer `ooxml_datas`.)

- [ ] **Step 2 : Build de fumée**

Run : `.venv/Scripts/python.exe -m PyInstaller anonymator.spec --noconfirm`
Expected : build sans erreur ; l'exe est produit dans `dist/`.

- [ ] **Step 3 : Vérifier l'exe sur un docx et un pptx**

Lancer l'exe produit, ouvrir un `.docx` puis un `.pptx`, analyser et anonymiser. Vérifier qu'un fichier `*_ano_*.docx` / `*.pptx` est écrit et lisible, sans erreur « gabarit manquant » (default.docx/default.pptx).
Expected : anonymisation fonctionnelle depuis l'exe.

- [ ] **Step 4 : Commit**

```bash
git add anonymator.spec
git commit -m "build(pyinstaller): embarque les gabarits python-docx/pptx"
```

---

## Task 17 : Vérification finale

- [ ] **Step 1 : Suite complète**

Run : `.venv/Scripts/python.exe -m pytest -q`
Expected : toute la suite passe (aucune régression sur txt/csv/xlsx/pdf).

- [ ] **Step 2 : Revue du périmètre affiché**

Ouvrir un docx dans l'app, vérifier que la `PerimetreCard` liste bien les items de `ooxml.COVERAGE` (traité / non traité) et correspond au comportement réel.

- [ ] **Step 3 : Commit de clôture (si ajustements)**

```bash
git add -A
git commit -m "test(ooxml): verification finale anonymisation docx/pptx"
```
