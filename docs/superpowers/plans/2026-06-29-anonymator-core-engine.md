# Anonymator — Plan 1 : Moteur de détection & anonymisation texte (core headless)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construire le moteur de détection PII et d'anonymisation de texte, entièrement testable sans interface graphique.

**Architecture:** Couche déterministe (regex + checksums validés) et couche NER (GLiNER) tournent en parallèle sur des valeurs **dédupliquées**, puis une étape de **fusion** résout les chevauchements (priorité au déterministe validé). Le résultat est une liste d'entités `{type, value, start, end, source, confidence}` qu'un applicateur transforme en texte masqué `[CATÉGORIE]`.

**Tech Stack:** Python 3.11+, pytest, gliner (PyTorch). Les tests unitaires utilisent un **faux GLiNER** (l'inférence réelle est testée en intégration, marquée `@pytest.mark.integration`).

**Référence spec :** [2026-06-29-anonymator-design.md](../specs/2026-06-29-anonymator-design.md) — §3.2, §4, §5.

---

## Structure des fichiers (Plan 1)

```
pyproject.toml                  config projet + pytest
requirements.txt                dépendances
anonymator/__init__.py
anonymator/model.py             dataclass Entity
anonymator/validators.py        luhn_is_valid, iban_is_valid, nir_is_valid
anonymator/deterministic.py     détecteurs regex+checksum → list[Entity]
anonymator/merge.py             fusion / résolution de chevauchements
anonymator/dedup.py             détection sur valeurs uniques + remap des offsets
anonymator/ner.py               NerDetector (protocole) + GlinerDetector + FakeNer (tests)
anonymator/pipeline.py          orchestrateur détection (déterministe ∥ NER → merge)
anonymator/referential.py       chargement du référentiel d'entités (JSON) + actif/labels
anonymator/anonymize.py         application du masquage [LABEL] sur du texte
anonymator/config/entities.json référentiel par défaut
tests/                          un fichier de test par module
```

---

### Task 0 : Échafaudage du projet

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `anonymator/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1 : Créer `requirements.txt`**

```
gliner>=0.2.13
pytest>=8.0
```

- [ ] **Step 2 : Créer `pyproject.toml`** (config pytest, marqueur `integration`)

```toml
[project]
name = "anonymator"
version = "0.1.0"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: tests nécessitant le vrai modèle GLiNER (lents)",
]
addopts = "-m 'not integration'"
```

- [ ] **Step 3 : Créer les packages vides**

`anonymator/__init__.py` et `tests/__init__.py` : fichiers vides.

- [ ] **Step 4 : Créer et activer un venv, installer pytest**

Run :
```bash
python -m venv .venv
.venv/Scripts/python -m pip install pytest
```
Expected : installation OK (gliner/torch s'installeront avant les tests d'intégration, Task 8).

- [ ] **Step 5 : Vérifier que pytest démarre**

Run : `.venv/Scripts/python -m pytest -q`
Expected : `no tests ran` (aucun test encore).

- [ ] **Step 6 : Commit**

```bash
git add pyproject.toml requirements.txt anonymator/__init__.py tests/__init__.py
git commit -m "chore: échafaudage projet anonymator + pytest"
```

---

### Task 1 : Modèle d'entité

**Files:**
- Create: `anonymator/model.py`
- Test: `tests/test_model.py`

- [ ] **Step 1 : Écrire le test qui échoue**

```python
# tests/test_model.py
from anonymator.model import Entity

def test_entity_holds_span_and_metadata():
    e = Entity(type="EMAIL", value="a@b.fr", start=3, end=9,
               source="deterministic", confidence=1.0)
    assert e.type == "EMAIL"
    assert (e.start, e.end) == (3, 9)
    assert e.length == 6  # end - start

def test_entity_is_orderable_by_start_then_length():
    a = Entity("PERSON", "X", 0, 5, "ner", 0.9)
    b = Entity("PERSON", "Y", 0, 8, "ner", 0.9)
    assert sorted([b, a])[0] is a  # même start → plus court d'abord
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_model.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.model`).

- [ ] **Step 3 : Implémenter le modèle**

```python
# anonymator/model.py
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Entity:
    type: str          # code du référentiel, ex. "EMAIL", "PERSON"
    value: str         # texte exact détecté
    start: int         # offset caractère inclusif
    end: int           # offset caractère exclusif
    source: str        # "deterministic" | "ner"
    confidence: float = 1.0

    @property
    def length(self) -> int:
        return self.end - self.start

    def __lt__(self, other: "Entity") -> bool:
        return (self.start, self.length) < (other.start, other.length)
```

- [ ] **Step 4 : Lancer le test pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_model.py -q`
Expected : PASS (2 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/model.py tests/test_model.py
git commit -m "feat: modèle Entity avec span et tri"
```

---

### Task 2 : Validateur Luhn (SIREN/SIRET)

**Files:**
- Create: `anonymator/validators.py`
- Test: `tests/test_validators.py`

- [ ] **Step 1 : Écrire le test qui échoue**

```python
# tests/test_validators.py
from anonymator.validators import luhn_is_valid

def test_luhn_valid_siren():
    assert luhn_is_valid("552081317") is True      # SIREN Danone (valide)

def test_luhn_invalid_siren():
    assert luhn_is_valid("552081318") is False

def test_luhn_rejects_too_short():
    assert luhn_is_valid("7") is False

def test_luhn_valid_real_sirens():
    # vrais SIREN valides qui distinguent l'algo correct d'une parité inversée
    assert luhn_is_valid("542107651") is True   # BNP Paribas
    assert luhn_is_valid("775672272") is True   # EDF

def test_luhn_detects_single_digit_error():
    assert luhn_is_valid("542107652") is False
```

> ⚠️ Ne PAS utiliser uniquement `552081317` comme exemple valide : ce numéro passe aussi bien
> avec l'algorithme correct qu'avec une parité inversée, donc il ne détecte pas le bug.

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_validators.py -q`
Expected : FAIL (`ImportError: luhn_is_valid`).

- [ ] **Step 3 : Implémenter**

```python
# anonymator/validators.py
def luhn_is_valid(number: str) -> bool:
    digits = [int(c) for c in number if c.isdigit()]
    if len(digits) < 2:
        return False
    checksum = 0
    parity = (len(digits) - 1) % 2
    for i, d in enumerate(digits):
        if i % 2 != parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0
```

- [ ] **Step 4 : Lancer le test pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_validators.py -q`
Expected : PASS (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/validators.py tests/test_validators.py
git commit -m "feat: validateur Luhn (SIREN/SIRET)"
```

---

### Task 3 : Validateur IBAN (mod 97)

**Files:**
- Modify: `anonymator/validators.py`
- Test: `tests/test_validators.py` (ajout)

- [ ] **Step 1 : Ajouter le test qui échoue**

```python
# tests/test_validators.py  (ajouter)
from anonymator.validators import iban_is_valid

def test_iban_valid_fr():
    assert iban_is_valid("FR7630006000011234567890189") is True

def test_iban_valid_with_spaces():
    assert iban_is_valid("FR76 3000 6000 0112 3456 7890 189") is True

def test_iban_invalid_checksum():
    assert iban_is_valid("FR7630006000011234567890188") is False
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_validators.py -q`
Expected : FAIL (`ImportError: iban_is_valid`).

- [ ] **Step 3 : Implémenter (ajouter à `validators.py`)**

```python
import re

def iban_is_valid(iban: str) -> bool:
    s = iban.replace(" ", "").upper()
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s):
        return False
    rearranged = s[4:] + s[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1
```

- [ ] **Step 4 : Lancer le test pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_validators.py -q`
Expected : PASS (6 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/validators.py tests/test_validators.py
git commit -m "feat: validateur IBAN mod 97"
```

---

### Task 4 : Validateur NIR (n° sécurité sociale)

**Files:**
- Modify: `anonymator/validators.py`
- Test: `tests/test_validators.py` (ajout)

- [ ] **Step 1 : Ajouter le test qui échoue**

```python
# tests/test_validators.py  (ajouter)
from anonymator.validators import nir_is_valid

def test_nir_valid():
    # 1 55 08 13 084 024 + clé 16  → NIR valide
    assert nir_is_valid("1 55 08 13 084 024 16") is True

def test_nir_invalid_key():
    assert nir_is_valid("1 55 08 13 084 024 17") is False

def test_nir_corsica_2a():
    # département 2A → remplacé par 19 dans le calcul de clé
    assert nir_is_valid("1 55 08 2A 084 024 08") is True
```

- [ ] **Step 2 : Lancer le test pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_validators.py -q`
Expected : FAIL (`ImportError: nir_is_valid`).

- [ ] **Step 3 : Implémenter (ajouter à `validators.py`)**

```python
def nir_is_valid(nir: str) -> bool:
    s = nir.replace(" ", "").upper()
    m = re.fullmatch(r"([12]\d{2}(?:0[1-9]|1[0-2]|[02-9]\d)"
                     r"(?:\d{2}|2[AB])\d{3}\d{3})(\d{2})", s)
    if not m:
        return False
    body, key = m.group(1), int(m.group(2))
    num = body.replace("2A", "19").replace("2B", "18")
    if not num.isdigit():
        return False
    return (97 - (int(num) % 97)) == key
```

- [ ] **Step 4 : Lancer le test pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_validators.py -q`
Expected : PASS (9 tests). Si un cas Corsica échoue, ajuster la clé de la fixture au calcul réel (le calcul fait foi, pas l'inverse) — ne jamais affaiblir la validation pour faire passer un test.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/validators.py tests/test_validators.py
git commit -m "feat: validateur NIR (format + clé, Corse 2A/2B)"
```

---

### Task 5 : Détecteurs déterministes (regex + checksum) → Entities

**Files:**
- Create: `anonymator/deterministic.py`
- Test: `tests/test_deterministic.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

```python
# tests/test_deterministic.py
from anonymator.deterministic import detect_deterministic

def types_at(text):
    return {(e.type, e.value) for e in detect_deterministic(text)}

def test_detects_email():
    assert ("EMAIL", "jp.lefevre@gmail.com") in types_at(
        "Contact : jp.lefevre@gmail.com.")

def test_detects_phone_fr():
    assert ("PHONE", "06 12 34 56 78") in types_at("Tel 06 12 34 56 78")

def test_detects_iban_only_if_valid_checksum():
    good = "FR7630006000011234567890189"
    bad = "FR7630006000011234567890188"
    assert ("IBAN", good) in types_at(f"vir {good}")
    assert all(e.type != "IBAN" for e in detect_deterministic(f"vir {bad}"))

def test_detects_siret_via_luhn():
    # 73282932000074 = SIRET valide (Luhn)
    assert ("SIRET", "73282932000074") in types_at("SIRET 73282932000074")

def test_spans_are_correct():
    text = "mail jp.lefevre@gmail.com fin"
    e = next(e for e in detect_deterministic(text) if e.type == "EMAIL")
    assert text[e.start:e.end] == "jp.lefevre@gmail.com"
    assert e.source == "deterministic"
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_deterministic.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.deterministic`).

- [ ] **Step 3 : Implémenter**

```python
# anonymator/deterministic.py
import re
from anonymator.model import Entity
from anonymator.validators import luhn_is_valid, iban_is_valid, nir_is_valid

# (pattern, type, validateur optionnel sur la valeur normalisée)
_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "EMAIL", None),
    (re.compile(r"(?:(?:\+33|0033)\s?|0)[1-9](?:[\s.\-]?\d{2}){4}"),
     "PHONE", None),
    (re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{2,4}){2,8}\b"),
     "IBAN", lambda v: iban_is_valid(v)),
    (re.compile(r"\b\d{14}\b"), "SIRET", lambda v: luhn_is_valid(v)),
    (re.compile(r"\b\d{9}\b"), "SIREN", lambda v: luhn_is_valid(v)),
    (re.compile(r"\b[12]\s?\d{2}\s?\d{2}\s?(?:\d{2}|2[AB])\s?\d{3}\s?\d{3}\s?\d{2}\b"),
     "NIR", lambda v: nir_is_valid(v)),
    (re.compile(r"https?://[^\s]+"), "URL", None),
]

def detect_deterministic(text: str) -> list[Entity]:
    found: list[Entity] = []
    for pattern, etype, validator in _PATTERNS:
        for m in pattern.finditer(text):
            value = m.group(0)
            if validator is not None and not validator(value):
                continue
            found.append(Entity(etype, value, m.start(), m.end(),
                                 "deterministic", 1.0))
    return found
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_deterministic.py -q`
Expected : PASS (5 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/deterministic.py tests/test_deterministic.py
git commit -m "feat: détecteurs déterministes regex+checksum"
```

---

### Task 6 : Fusion / résolution des chevauchements

**Files:**
- Create: `anonymator/merge.py`
- Test: `tests/test_merge.py`

**Règles (spec §3.2) :** priorité au déterministe validé ; à défaut plus haute confiance ; en cas de chevauchement on garde le span gagnant et on **supprime les spans qui le chevauchent**.

- [ ] **Step 1 : Écrire les tests qui échouent**

```python
# tests/test_merge.py
from anonymator.model import Entity
from anonymator.merge import merge_entities

def test_no_overlap_keeps_all():
    a = Entity("EMAIL", "a@b.fr", 0, 6, "deterministic", 1.0)
    b = Entity("PERSON", "Zoé", 10, 13, "ner", 0.9)
    assert sorted(merge_entities([a, b])) == sorted([a, b])

def test_deterministic_wins_over_ner_on_overlap():
    det = Entity("IBAN", "FR76...", 5, 30, "deterministic", 1.0)
    ner = Entity("ORG", "FR76 3000", 5, 14, "ner", 0.95)
    assert merge_entities([ner, det]) == [det]

def test_longer_ner_span_wins_over_shorter_when_same_source():
    short = Entity("PERSON", "Martin", 0, 6, "ner", 0.8)
    long = Entity("PERSON", "Martin Dupont", 0, 13, "ner", 0.8)
    assert merge_entities([short, long]) == [long]
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_merge.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.merge`).

- [ ] **Step 3 : Implémenter**

```python
# anonymator/merge.py
from anonymator.model import Entity

def _overlaps(a: Entity, b: Entity) -> bool:
    return a.start < b.end and b.start < a.end

def _rank(e: Entity) -> tuple:
    # 1) déterministe prioritaire  2) plus grande confiance  3) span plus long
    return (e.source == "deterministic", e.confidence, e.length)

def merge_entities(entities: list[Entity]) -> list[Entity]:
    ordered = sorted(entities, key=_rank, reverse=True)
    kept: list[Entity] = []
    for e in ordered:
        if any(_overlaps(e, k) for k in kept):
            continue
        kept.append(e)
    return sorted(kept)
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_merge.py -q`
Expected : PASS (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/merge.py tests/test_merge.py
git commit -m "feat: fusion des entités avec résolution de chevauchements"
```

---

### Task 7 : Détecteur NER — protocole, faux pour tests, vrai GLiNER

**Files:**
- Create: `anonymator/ner.py`
- Test: `tests/test_ner.py`

- [ ] **Step 1 : Écrire les tests qui échouent (avec un faux NER)**

```python
# tests/test_ner.py
from anonymator.model import Entity
from anonymator.ner import FakeNer

def test_fake_ner_returns_configured_entities():
    ner = FakeNer({"Claire Martin": "PERSON"})
    text = "Bonjour Claire Martin."
    out = ner.detect(text, labels=["PERSON"])
    assert out == [Entity("PERSON", "Claire Martin", 8, 21, "ner", 1.0)]

def test_fake_ner_finds_all_occurrences():
    ner = FakeNer({"Zoé": "PERSON"})
    out = ner.detect("Zoé et Zoé", labels=["PERSON"])
    assert [(e.start, e.end) for e in out] == [(0, 3), (7, 10)]
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_ner.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.ner`).

- [ ] **Step 3 : Implémenter le protocole + le faux + le vrai (le vrai n'est pas importé au chargement)**

```python
# anonymator/ner.py
from typing import Protocol
import re
from anonymator.model import Entity

class NerDetector(Protocol):
    def detect(self, text: str, labels: list[str]) -> list[Entity]: ...

class FakeNer:
    """NER déterministe pour les tests : mappe des chaînes exactes → type."""
    def __init__(self, mapping: dict[str, str]):
        self._mapping = mapping

    def detect(self, text: str, labels: list[str]) -> list[Entity]:
        out: list[Entity] = []
        for surface, etype in self._mapping.items():
            for m in re.finditer(re.escape(surface), text):
                out.append(Entity(etype, surface, m.start(), m.end(), "ner", 1.0))
        return sorted(out)

# Carte label GLiNER (français) → code d'entité interne
_LABEL_TO_TYPE = {
    "personne": "PERSON",
    "adresse postale": "ADDRESS",
    "organisation": "ORG",
}

class GlinerDetector:
    """Adaptateur autour du modèle GLiNER. Importé paresseusement."""
    def __init__(self, model_name: str = "urchade/gliner_multi-v2.1",
                 threshold: float = 0.5):
        from gliner import GLiNER  # import paresseux : torch lourd
        self._model = GLiNER.from_pretrained(model_name)
        self._threshold = threshold

    def detect(self, text: str, labels: list[str]) -> list[Entity]:
        raw = self._model.predict_entities(text, labels,
                                            threshold=self._threshold)
        out: list[Entity] = []
        for r in raw:
            etype = _LABEL_TO_TYPE.get(r["label"], r["label"].upper())
            out.append(Entity(etype, r["text"], r["start"], r["end"],
                              "ner", float(r["score"])))
        return sorted(out)
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_ner.py -q`
Expected : PASS (2 tests). `GlinerDetector` n'est pas instancié ici (pas d'import torch).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/ner.py tests/test_ner.py
git commit -m "feat: NerDetector (protocole), FakeNer, GlinerDetector paresseux"
```

---

### Task 8 : Test d'intégration GLiNER réel (marqué lent)

**Files:**
- Test: `tests/test_ner_integration.py`

- [ ] **Step 1 : Écrire le test d'intégration**

```python
# tests/test_ner_integration.py
import pytest
from anonymator.ner import GlinerDetector

@pytest.mark.integration
def test_gliner_detects_person_and_address():
    ner = GlinerDetector()
    text = "Jean-Pierre Lefèvre habite 14 rue des Acacias à Toulouse."
    out = ner.detect(text, ["personne", "adresse postale", "organisation"])
    types = {e.type for e in out}
    assert "PERSON" in types
    # le span personne doit recouvrir le nom
    person = next(e for e in out if e.type == "PERSON")
    assert "Lefèvre" in text[person.start:person.end]
```

- [ ] **Step 2 : Installer GLiNER et lancer le test d'intégration**

Run :
```bash
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pytest tests/test_ner_integration.py -m integration -q
```
Expected : PASS (téléchargement du modèle au 1er run, plusieurs minutes). Si le rappel d'adresse est faible, noter l'observation — l'ajustement du `threshold`/des labels se fera au calibrage (hors de ce test qui ne vérifie que PERSON).

- [ ] **Step 3 : Commit**

```bash
git add tests/test_ner_integration.py
git commit -m "test: intégration GLiNER réel (marqué integration)"
```

---

### Task 9 : Déduplication batch (détecter une fois, remapper partout)

**Files:**
- Create: `anonymator/dedup.py`
- Test: `tests/test_dedup.py`

**But (spec §3.2) :** pour une liste de valeurs cellulaires très répétitives, ne lancer la détection que sur les **valeurs uniques**, puis reporter les entités trouvées sur **toutes** les occurrences. Fonction pure, réutilisée par le mode fichier (Plan 2).

- [ ] **Step 1 : Écrire les tests qui échouent**

```python
# tests/test_dedup.py
from anonymator.model import Entity
from anonymator.dedup import detect_unique

def fake_detect(value):
    # détecte "Zoé" comme PERSON où qu'elle soit
    return [Entity("PERSON", "Zoé", i, i + 3, "ner", 1.0)
            for i in range(len(value)) if value[i:i + 3] == "Zoé"]

def test_detects_each_unique_value_once(monkeypatch):
    calls = []
    def counting(value):
        calls.append(value)
        return fake_detect(value)
    values = ["Zoé Martin", "Zoé Martin", "Banque X"]
    result = detect_unique(values, counting)
    # 2 valeurs uniques → 2 appels seulement
    assert sorted(calls) == ["Banque X", "Zoé Martin"]
    # résultat indexé par valeur
    assert result["Zoé Martin"][0].type == "PERSON"
    assert result["Banque X"] == []
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_dedup.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.dedup`).

- [ ] **Step 3 : Implémenter**

```python
# anonymator/dedup.py
from typing import Callable
from anonymator.model import Entity

def detect_unique(
    values: list[str],
    detect: Callable[[str], list[Entity]],
) -> dict[str, list[Entity]]:
    """Lance `detect` une fois par valeur unique. Retourne {valeur: entités}."""
    cache: dict[str, list[Entity]] = {}
    for value in values:
        if value not in cache:
            cache[value] = detect(value)
    return cache
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_dedup.py -q`
Expected : PASS (1 test).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/dedup.py tests/test_dedup.py
git commit -m "feat: déduplication batch de la détection"
```

---

### Task 10 : Référentiel d'entités (JSON)

**Files:**
- Create: `anonymator/config/entities.json`
- Create: `anonymator/referential.py`
- Test: `tests/test_referential.py`

- [ ] **Step 1 : Créer le référentiel par défaut**

```json
// anonymator/config/entities.json
{
  "entities": [
    {"code": "PERSON",  "label": "Personne",      "method": "ner",          "active": true,  "tag": "[PERSONNE]", "sensitivity": "Haute"},
    {"code": "ADDRESS", "label": "Adresse",       "method": "ner",          "active": true,  "tag": "[ADRESSE]",  "sensitivity": "Haute"},
    {"code": "ORG",     "label": "Organisation",  "method": "ner",          "active": true,  "tag": "[ORG]",      "sensitivity": "Moyenne"},
    {"code": "EMAIL",   "label": "E-mail",        "method": "deterministic","active": true,  "tag": "[EMAIL]",    "sensitivity": "Haute"},
    {"code": "PHONE",   "label": "Téléphone",     "method": "deterministic","active": true,  "tag": "[TEL]",      "sensitivity": "Haute"},
    {"code": "IBAN",    "label": "IBAN",          "method": "deterministic","active": true,  "tag": "[IBAN]",     "sensitivity": "Haute"},
    {"code": "SIREN",   "label": "SIREN",         "method": "deterministic","active": true,  "tag": "[SIREN]",    "sensitivity": "Moyenne"},
    {"code": "SIRET",   "label": "SIRET",         "method": "deterministic","active": true,  "tag": "[SIRET]",    "sensitivity": "Moyenne"},
    {"code": "NIR",     "label": "N° sécu",       "method": "deterministic","active": true,  "tag": "[NIR]",      "sensitivity": "Haute"},
    {"code": "URL",     "label": "URL",           "method": "deterministic","active": false, "tag": "[URL]",      "sensitivity": "Basse"}
  ]
}
```

- [ ] **Step 2 : Écrire les tests qui échouent**

```python
# tests/test_referential.py
from anonymator.referential import Referential

def test_loads_default_referential():
    ref = Referential.load_default()
    assert ref.tag_for("EMAIL") == "[EMAIL]"
    assert ref.is_active("EMAIL") is True
    assert ref.is_active("URL") is False

def test_active_ner_labels_maps_codes_to_french_labels():
    ref = Referential.load_default()
    assert set(ref.active_ner_labels()) == {"personne", "adresse postale", "organisation"}

def test_active_deterministic_types_excludes_inactive():
    ref = Referential.load_default()
    types = ref.active_deterministic_types()
    assert "EMAIL" in types and "URL" not in types
```

- [ ] **Step 3 : Lancer les tests pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_referential.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.referential`).

- [ ] **Step 4 : Implémenter**

```python
# anonymator/referential.py
import json
from pathlib import Path

_TYPE_TO_NER_LABEL = {
    "PERSON": "personne",
    "ADDRESS": "adresse postale",
    "ORG": "organisation",
}
_DEFAULT_PATH = Path(__file__).parent / "config" / "entities.json"

class Referential:
    def __init__(self, entries: list[dict]):
        self._by_code = {e["code"]: e for e in entries}

    @classmethod
    def load_default(cls) -> "Referential":
        data = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
        return cls(data["entities"])

    def tag_for(self, code: str) -> str:
        return self._by_code[code]["tag"]

    def is_active(self, code: str) -> bool:
        return self._by_code.get(code, {}).get("active", False)

    def active_ner_labels(self) -> list[str]:
        return [_TYPE_TO_NER_LABEL[c] for c, e in self._by_code.items()
                if e["method"] == "ner" and e["active"] and c in _TYPE_TO_NER_LABEL]

    def active_deterministic_types(self) -> set[str]:
        return {c for c, e in self._by_code.items()
                if e["method"] == "deterministic" and e["active"]}
```

- [ ] **Step 5 : Lancer les tests pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_referential.py -q`
Expected : PASS (3 tests).

- [ ] **Step 6 : Commit**

```bash
git add anonymator/config/entities.json anonymator/referential.py tests/test_referential.py
git commit -m "feat: référentiel d'entités piloté par JSON"
```

---

### Task 11 : Pipeline de détection (déterministe ∥ NER → filtre actifs → merge)

**Files:**
- Create: `anonymator/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

```python
# tests/test_pipeline.py
from anonymator.ner import FakeNer
from anonymator.referential import Referential
from anonymator.pipeline import detect

def test_pipeline_combines_deterministic_and_ner():
    ref = Referential.load_default()
    ner = FakeNer({"Claire Martin": "PERSON"})
    text = "Claire Martin — mail c@x.fr"
    types = {e.type for e in detect(text, ner, ref)}
    assert {"PERSON", "EMAIL"} <= types

def test_pipeline_drops_inactive_types():
    ref = Referential.load_default()           # URL inactif par défaut
    ner = FakeNer({})
    out = detect("voir https://x.fr", ner, ref)
    assert all(e.type != "URL" for e in out)

def test_pipeline_deterministic_wins_overlap():
    ref = Referential.load_default()
    # le NER tente de tagger l'IBAN comme ORG : doit perdre
    iban = "FR7630006000011234567890189"
    ner = FakeNer({iban: "ORG"})
    out = detect(f"vir {iban}", ner, ref)
    assert any(e.type == "IBAN" for e in out)
    assert all(e.type != "ORG" for e in out)
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_pipeline.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.pipeline`).

- [ ] **Step 3 : Implémenter**

```python
# anonymator/pipeline.py
from anonymator.model import Entity
from anonymator.deterministic import detect_deterministic
from anonymator.merge import merge_entities
from anonymator.ner import NerDetector
from anonymator.referential import Referential

def detect(text: str, ner: NerDetector, ref: Referential) -> list[Entity]:
    det_types = ref.active_deterministic_types()
    deterministic = [e for e in detect_deterministic(text)
                     if e.type in det_types]
    labels = ref.active_ner_labels()
    ner_entities = ner.detect(text, labels) if labels else []
    ner_entities = [e for e in ner_entities if ref.is_active(e.type)]
    return merge_entities(deterministic + ner_entities)
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_pipeline.py -q`
Expected : PASS (3 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline de détection (déterministe ∥ NER → merge)"
```

---

### Task 12 : Application du masquage sur du texte

**Files:**
- Create: `anonymator/anonymize.py`
- Test: `tests/test_anonymize.py`

**But (spec §5) :** à partir d'un texte et d'une liste d'entités **retenues** (après revue), produire le texte masqué en remplaçant chaque span par l'étiquette de son type. On remplace de la **fin vers le début** pour ne pas décaler les offsets.

- [ ] **Step 1 : Écrire les tests qui échouent**

```python
# tests/test_anonymize.py
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.anonymize import apply_masking

def test_replaces_spans_with_tags():
    ref = Referential.load_default()
    text = "Claire Martin a écrit à c@x.fr"
    ents = [Entity("PERSON", "Claire Martin", 0, 13, "ner", 1.0),
            Entity("EMAIL", "c@x.fr", 24, 30, "deterministic", 1.0)]
    assert apply_masking(text, ents, ref) == "[PERSONNE] a écrit à [EMAIL]"

def test_ignores_overlapping_or_unsorted_entities_safely():
    ref = Referential.load_default()
    text = "c@x.fr"
    ents = [Entity("EMAIL", "c@x.fr", 0, 6, "deterministic", 1.0)]
    assert apply_masking(text, ents, ref) == "[EMAIL]"

def test_only_masks_provided_entities():
    ref = Referential.load_default()
    text = "Zoé reste"
    assert apply_masking(text, [], ref) == "Zoé reste"
```

- [ ] **Step 2 : Lancer les tests pour vérifier l'échec**

Run : `.venv/Scripts/python -m pytest tests/test_anonymize.py -q`
Expected : FAIL (`ModuleNotFoundError: anonymator.anonymize`).

- [ ] **Step 3 : Implémenter**

```python
# anonymator/anonymize.py
from anonymator.model import Entity
from anonymator.referential import Referential

def apply_masking(text: str, entities: list[Entity],
                  ref: Referential) -> str:
    # remplacer de la fin vers le début pour préserver les offsets
    for e in sorted(entities, key=lambda e: e.start, reverse=True):
        text = text[:e.start] + ref.tag_for(e.type) + text[e.end:]
    return text
```

- [ ] **Step 4 : Lancer les tests pour vérifier le succès**

Run : `.venv/Scripts/python -m pytest tests/test_anonymize.py -q`
Expected : PASS (3 tests).

- [ ] **Step 5 : Lancer toute la suite (hors intégration)**

Run : `.venv/Scripts/python -m pytest -q`
Expected : PASS (tous les tests unitaires).

- [ ] **Step 6 : Commit**

```bash
git add anonymator/anonymize.py tests/test_anonymize.py
git commit -m "feat: application du masquage [LABEL] sur texte"
```

---

## Couverture du spec (auto-revue Plan 1)

- §3.2 dédup batch → Task 9 ; fusion chevauchements → Task 6 ; pipeline → Task 11. ✓
- §4.1 déterministe (IBAN/NIR/SIREN/SIRET/email/tél/URL) → Tasks 2-5. ✓
- §4.2 GLiNER spans → Tasks 7-8. ✓
- §4.3 référentiel JSON + actif/labels → Task 10. ✓
- §5 masquage texte [CATÉGORIE] → Task 12. ✓ (la **revue interactive** et l'export relèvent du Plan 3 UI / Plan 2 rapport.)
- §10 chunking texte très long → **non couvert ici**, prévu en amont du pipeline lors du branchement UI (Plan 3) ; le pipeline étant sans état, le chunking se fait par découpe + recalage d'offsets.

**Limites volontaires de ce plan :** pas d'E/S fichiers (Plan 2), pas d'UI/thèmes/packaging (Plan 3), pas de rapport d'audit (Plan 2). Code postal (`POSTAL_CODE`) et BIC non implémentés en Task 5 : à ajouter au même endroit que les autres patterns si retenus au calibrage (entrées à ajouter au référentiel + une ligne dans `_PATTERNS`).
