# P-B — Moteur de détection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Améliorer le rappel/précision du moteur : IBAN/NIR « non confirmés », catégories `LOGIN`/`PASSWORD`, liste d'exclusion GLiNER, types optionnels via surcharges utilisateur.

**Architecture:** Détection déterministe étendue (émet `confirmed=False` au lieu de jeter les IBAN/NIR format-OK-clé-KO). Nouveau module `secrets_detect.py` (règles contextuelles + entropie). `pipeline.detect` agrège déterministe + secrets + NER, filtre la stoplist. `Referential` consulte les surcharges utilisateur (`entity_overrides`) et porte la stoplist. Le **chemin direct** de masquage ne masque pas les `confirmed=False` ; la revue les propose en opt-in.

**Tech Stack:** Python 3.14, pytest. Dépend de **P-A** (champ `Entity.confirmed`, `scan_csv` dans `anonymize_file.py`).

**Référence spec :** [2026-06-30-qualite-detection-design.md](../specs/2026-06-30-qualite-detection-design.md).

**Prérequis :** P-A mergé/présent sur la branche `feat/revue-fichier-coloree`. Tests : `.venv\Scripts\python.exe -m pytest -q`.

---

## Structure des fichiers (P-B)

```
anonymator/textnorm.py              CRÉER : normalisation (minuscule + sans accents)
anonymator/config/entities.json     MODIFIER : + LOGIN, PASSWORD (BIC/CP/URL restent off)
anonymator/config/ner_stoplist.json CRÉER : termes génériques à exclure
anonymator/ui/colors.py             MODIFIER : couleurs LOGIN, PASSWORD
anonymator/deterministic.py         MODIFIER : IBAN/NIR confirmed=False
anonymator/secrets_detect.py        CRÉER : détection logins/mots de passe
anonymator/referential.py           MODIFIER : overrides + stoplist + is_active prioritaire
anonymator/pipeline.py              MODIFIER : secrets + filtre stoplist + is_active
anonymator/files/anonymize_file.py  MODIFIER : chemin direct ignore confirmed=False
anonymator/core/review_session.py   MODIFIER : confirmed=False décoché par défaut
anonymator/report/audit.py          MODIFIER : indicateur "confirmé"
tests/...                           TDD par module
```

---

### Task 1 : Normalisation de texte

**Files:**
- Create: `anonymator/textnorm.py`
- Test: `tests/test_textnorm.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_textnorm.py
from anonymator.textnorm import normalize

def test_normalize_lowercases_and_strips_accents():
    assert normalize("Crédit Agricole") == "credit agricole"
    assert normalize("  SERVICE   Client ") == "service client"
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_textnorm.py -q` → FAIL (module absent).

- [ ] **Step 3 : Implémenter** `anonymator/textnorm.py`

```python
import unicodedata


def normalize(text: str) -> str:
    """Minuscule, accents retirés, espaces compactés — pour comparaisons robustes."""
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(no_accents.lower().split())
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_textnorm.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/textnorm.py tests/test_textnorm.py
git commit -m "feat: normalisation de texte (minuscule + sans accents)"
```

---

### Task 2 : Nouveaux types `LOGIN` / `PASSWORD` (référentiel + couleurs)

**Files:**
- Modify: `anonymator/config/entities.json`
- Modify: `anonymator/ui/colors.py:1-14`
- Test: `tests/test_referential.py`, `tests/test_colors.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_referential.py  (ajouter)
from anonymator.referential import Referential

def test_login_and_password_active_by_default():
    ref = Referential.load_default()
    assert ref.is_active("LOGIN") is True
    assert ref.is_active("PASSWORD") is True

def test_bic_cp_url_inactive_by_default():
    ref = Referential.load_default()
    assert ref.is_active("BIC") is False
    assert ref.is_active("POSTAL_CODE") is False
    assert ref.is_active("URL") is False
```

```python
# tests/test_colors.py  (ajouter)
from anonymator.ui.colors import color_for

def test_login_password_have_colors():
    assert color_for("LOGIN").startswith("#")
    assert color_for("PASSWORD").startswith("#")
    assert color_for("LOGIN") != color_for("PASSWORD")
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_referential.py tests/test_colors.py -q` → FAIL.

- [ ] **Step 3 : Implémenter**

Dans `anonymator/config/entities.json`, ajouter deux entrées avant l'accolade fermante du tableau `entities` (après `URL`), avec method `contextual` :

```json
    {"code": "URL",     "label": "URL",           "method": "deterministic","active": false, "tag": "[URL]",      "sensitivity": "Basse"},
    {"code": "LOGIN",    "label": "Identifiant",  "method": "contextual",   "active": true,  "tag": "[LOGIN]",   "sensitivity": "Haute"},
    {"code": "PASSWORD", "label": "Mot de passe", "method": "contextual",   "active": true,  "tag": "[SECRET]",  "sensitivity": "Haute"}
```

> (Retirer la virgule finale après l'objet `URL` n'est pas nécessaire — ici on AJOUTE après lui, donc la ligne `URL` reçoit une virgule de fin et les deux nouvelles entrées suivent ; la dernière `PASSWORD` n'a pas de virgule.)

Dans `anonymator/ui/colors.py`, ajouter au dictionnaire `ENTITY_COLORS` :

```python
    "URL":         "#577590",
    "LOGIN":       "#5f0f40",
    "PASSWORD":    "#9a031e",
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_referential.py tests/test_colors.py -q` → PASS.

> Note : `test_bic_cp_url_inactive_by_default` doit déjà passer avec le `is_active` actuel ; il garantit la non-régression du défaut. Si `is_active` n'est pas encore overrides-aware (Task 5), il fonctionne quand même ici.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/config/entities.json anonymator/ui/colors.py tests/test_referential.py tests/test_colors.py
git commit -m "feat: types LOGIN/PASSWORD (référentiel + couleurs)"
```

---

### Task 3 : IBAN / NIR « non confirmés »

**Files:**
- Modify: `anonymator/deterministic.py:24-33`
- Test: `tests/test_deterministic.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_deterministic.py  (ajouter)
from anonymator.deterministic import detect_deterministic

def _types(text):
    return {(e.type, e.confirmed) for e in detect_deterministic(text)}

def test_invalid_iban_emitted_unconfirmed():
    # FR76 ... checksum faux (valeur de test)
    ents = detect_deterministic("RIB FR76 3000 4000 1200 0000 1234 567")
    iban = [e for e in ents if e.type == "IBAN"]
    assert iban and iban[0].confirmed is False

def test_invalid_nir_emitted_unconfirmed():
    ents = detect_deterministic("ref 2 86 03 69 123 456 78")
    nir = [e for e in ents if e.type == "NIR"]
    assert nir and nir[0].confirmed is False

def test_invalid_bic_still_skipped():
    # un BIC au format faux ne doit PAS être émis (pas de mode non confirmé)
    ents = detect_deterministic("code ZZ99")
    assert not [e for e in ents if e.type == "BIC"]
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_deterministic.py -q` → FAIL (IBAN/NIR actuellement jetés).

- [ ] **Step 3 : Implémenter** — modifier la boucle de `detect_deterministic`

```python
_UNCONFIRMABLE = {"IBAN", "NIR"}   # format plausible conservé même si validation KO


def detect_deterministic(text: str) -> list[Entity]:
    found: list[Entity] = []
    for pattern, etype, validator in _PATTERNS:
        for m in pattern.finditer(text):
            value = m.group(0)
            confirmed = True
            if validator is not None and not validator(value):
                if etype in _UNCONFIRMABLE:
                    confirmed = False          # format OK, clé/checksum KO → non confirmé
                else:
                    continue                   # autres types : rejet pur
            found.append(Entity(etype, value, m.start(), m.end(),
                                 "deterministic", 1.0, confirmed))
    return found
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_deterministic.py -q` → PASS.
Suite complète → verte (un IBAN/NIR valide reste `confirmed=True`).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/deterministic.py tests/test_deterministic.py
git commit -m "feat(deterministic): IBAN/NIR format-plausible émis confirmed=False"
```

---

### Task 4 : Détection logins / mots de passe — règles contextuelles

**Files:**
- Create: `anonymator/secrets_detect.py`
- Test: `tests/test_secrets_detect.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_secrets_detect.py
from anonymator.secrets_detect import detect_secrets

def _by_type(text):
    out = {}
    for e in detect_secrets(text):
        out.setdefault(e.type, []).append(e.value)
    return out

def test_password_keyword():
    r = _by_type("son mot de passe provisoire — V3lo!2026#Claire — en se disant")
    assert "V3lo!2026#Claire" in r.get("PASSWORD", [])

def test_login_keyword_parenthesis():
    r = _by_type("un accès au compte (h.dupont90), mot de passe")
    assert "h.dupont90" in r.get("LOGIN", [])

def test_login_connecte_avec():
    r = _by_type("elle s'était connectée la veille avec claire.martin86.")
    assert "claire.martin86" in r.get("LOGIN", [])

def test_offsets_point_to_value():
    text = "mot de passe : T0ulouse*Hugo-90 ok"
    e = next(e for e in detect_secrets(text) if e.type == "PASSWORD")
    assert text[e.start:e.end] == "T0ulouse*Hugo-90"
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_secrets_detect.py -q` → FAIL (module absent).

- [ ] **Step 3 : Implémenter** `anonymator/secrets_detect.py` (règles contextuelles d'abord)

```python
import re
from anonymator.model import Entity

# Jeton « secret » : suite sans espace, on s'arrête à la ponctuation de fin usuelle.
_TOKEN = r"[^\s,;)\]]+(?<![.])"   # autorise . interne, pas en fin

_PWD_KEYS = r"(?:mot de passe|mots de passe|mdp|password|pass(?:e)?)"
_LOGIN_KEYS = (r"(?:login|identifiant|utilisateur|user(?:name)?|"
               r"acc[eè]s au compte|connect[ée]\w*\s+avec)")
# séparateurs entre le mot-clé et la valeur : : — - ( espace, "provisoire/temporaire"
_SEP = r"(?:\s+(?:provisoire|temporaire))?\s*(?:[:\-—(]\s*|\s+)"

_PWD_RE = re.compile(_PWD_KEYS + _SEP + r"(" + _TOKEN + r")", re.IGNORECASE)
_LOGIN_RE = re.compile(_LOGIN_KEYS + _SEP + r"(" + _TOKEN + r")", re.IGNORECASE)


def _matches(regex, text, etype):
    out = []
    for m in regex.finditer(text):
        value = m.group(1)
        out.append(Entity(etype, value, m.start(1), m.end(1), "secret", 1.0))
    return out


def detect_secrets(text: str) -> list[Entity]:
    return _matches(_PWD_RE, text, "PASSWORD") + _matches(_LOGIN_RE, text, "LOGIN")
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_secrets_detect.py -q` → PASS (4 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/secrets_detect.py tests/test_secrets_detect.py
git commit -m "feat(secrets): détection contextuelle logins/mots de passe"
```

---

### Task 5 : Heuristique d'entropie (mots de passe sans contexte)

**Files:**
- Modify: `anonymator/secrets_detect.py`
- Test: `tests/test_secrets_detect.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_secrets_detect.py  (ajouter)
def test_entropy_detects_strong_token():
    r = _by_type("clé V3lo!2026#Claire ailleurs")
    assert "V3lo!2026#Claire" in r.get("PASSWORD", [])

def test_entropy_ignores_account_number():
    # numéro de compte FEC : que des chiffres → pas un mot de passe
    assert detect_secrets("compte 41100000 montant") == [] or \
        all(e.type != "PASSWORD" or e.value != "41100000" for e in detect_secrets("41100000"))

def test_entropy_ignores_plain_words():
    assert all(e.type != "PASSWORD" for e in detect_secrets("Bonjour Madame Toulouse"))
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_secrets_detect.py -q` → FAIL (entropie absente).

- [ ] **Step 3 : Implémenter** — ajouter l'heuristique et la fusionner dans `detect_secrets`

```python
_WORD_RE = re.compile(r"\S+")


def _char_classes(token: str) -> int:
    classes = 0
    if any(c.islower() for c in token): classes += 1
    if any(c.isupper() for c in token): classes += 1
    if any(c.isdigit() for c in token): classes += 1
    if any(not c.isalnum() for c in token): classes += 1
    return classes


def _looks_like_secret(token: str) -> bool:
    t = token.strip(".,;:()[]")
    if len(t) < 8:
        return False
    if t.isdigit() or t.isalpha():          # pur numérique ou pur alpha → pas un secret
        return False
    return _char_classes(t) >= 3            # ≥3 classes parmi minuscule/majuscule/chiffre/symbole


def _entropy_secrets(text: str, already: list[Entity]) -> list[Entity]:
    taken = {(e.start, e.end) for e in already}
    out = []
    for m in _WORD_RE.finditer(text):
        raw = m.group(0)
        t = raw.strip(".,;:()[]")
        if not t or not _looks_like_secret(t):
            continue
        start = m.start() + raw.find(t)
        end = start + len(t)
        if (start, end) in taken:
            continue
        out.append(Entity("PASSWORD", t, start, end, "secret", 0.7))
    return out


def detect_secrets(text: str) -> list[Entity]:
    contextual = _matches(_PWD_RE, text, "PASSWORD") + _matches(_LOGIN_RE, text, "LOGIN")
    return contextual + _entropy_secrets(text, contextual)
```

> Cadrage anti-faux-positifs : longueur ≥ 8, ni pur numérique ni pur alpha, ≥ 3 classes de
> caractères. Les jetons déjà typés (IBAN/SIREN/NIR…) sont écartés lors de la fusion globale
> (`merge_entities`, priorité au déterministe) en Task 6. En mode Fichier, `scan_csv` n'appelle
> `detect` que sur les colonnes masquables (jamais les colonnes numériques), ce qui élimine les
> n° de compte/montants.

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_secrets_detect.py -q` → PASS (7 tests).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/secrets_detect.py tests/test_secrets_detect.py
git commit -m "feat(secrets): heuristique d'entropie cadrée pour mots de passe"
```

---

### Task 6 : `Referential` — surcharges utilisateur + stoplist

**Files:**
- Modify: `anonymator/referential.py`
- Create: `anonymator/config/ner_stoplist.json`
- Test: `tests/test_referential.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_referential.py  (ajouter)
def test_override_enables_inactive_type():
    ref = Referential.load_default(overrides={"BIC": True})
    assert ref.is_active("BIC") is True

def test_override_disables_active_type():
    ref = Referential.load_default(overrides={"PERSON": False})
    assert ref.is_active("PERSON") is False

def test_default_stoplist_loaded():
    ref = Referential.load_default()
    assert "service client" in ref.ner_stoplist()   # normalisé
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_referential.py -q` → FAIL.

- [ ] **Step 3 : Implémenter**

Créer `anonymator/config/ner_stoplist.json` :

```json
["service client", "client", "clients", "fournisseur", "fournisseurs",
 "divers", "la société", "société", "monsieur", "madame", "banque"]
```

Modifier `anonymator/referential.py` :

```python
import json
from pathlib import Path
from anonymator.textnorm import normalize

_TYPE_TO_NER_LABEL = {
    "PERSON": "personne",
    "ADDRESS": "adresse postale",
    "ORG": "organisation",
}
_DEFAULT_PATH = Path(__file__).parent / "config" / "entities.json"
_STOPLIST_PATH = Path(__file__).parent / "config" / "ner_stoplist.json"


class Referential:
    def __init__(self, entries: list[dict],
                 overrides: dict[str, bool] | None = None,
                 stoplist: list[str] | None = None):
        self._by_code = {e["code"]: e for e in entries}
        self._overrides = overrides or {}
        self._stoplist = stoplist or []

    @classmethod
    def load_default(cls, overrides: dict[str, bool] | None = None) -> "Referential":
        data = json.loads(_DEFAULT_PATH.read_text(encoding="utf-8"))
        stoplist: list[str] = []
        if _STOPLIST_PATH.exists():
            stoplist = json.loads(_STOPLIST_PATH.read_text(encoding="utf-8"))
        return cls(data["entities"], overrides=overrides, stoplist=stoplist)

    def tag_for(self, code: str) -> str:
        return self._by_code[code]["tag"]

    def is_active(self, code: str) -> bool:
        if code in self._overrides:
            return self._overrides[code]
        return self._by_code.get(code, {}).get("active", False)

    def active_ner_labels(self) -> list[str]:
        return [_TYPE_TO_NER_LABEL[c] for c in self._by_code
                if self._by_code[c]["method"] == "ner" and self.is_active(c)
                and c in _TYPE_TO_NER_LABEL]

    def active_deterministic_types(self) -> set[str]:
        return {c for c, e in self._by_code.items()
                if e["method"] == "deterministic" and self.is_active(c)}

    def ner_stoplist(self) -> set[str]:
        return {normalize(t) for t in self._stoplist}

    def with_stoplist(self, terms: list[str]) -> "Referential":
        """Copie avec une stoplist remplacée (édition utilisateur)."""
        return Referential(list(self._by_code.values()), self._overrides, terms)
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_referential.py -q` → PASS.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/referential.py anonymator/config/ner_stoplist.json tests/test_referential.py
git commit -m "feat(referential): surcharges utilisateur + stoplist NER"
```

---

### Task 7 : `pipeline.detect` — secrets + filtre stoplist

**Files:**
- Modify: `anonymator/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_pipeline.py  (ajouter)
from anonymator.pipeline import detect
from anonymator.referential import Referential
from anonymator.ner import FakeNer

def test_pipeline_detects_secrets():
    ref = Referential.load_default()
    ner = FakeNer({})
    ents = detect("mot de passe : V3lo!2026#Claire", ner, ref)
    assert any(e.type == "PASSWORD" for e in ents)

def test_pipeline_filters_stoplist():
    ref = Referential.load_default()
    ner = FakeNer({"service client": "ORG", "Claire Martin": "PERSON"})
    ents = detect("appel au service client par Claire Martin", ner, ref)
    types_values = {(e.type, e.value) for e in ents}
    assert ("ORG", "service client") not in types_values
    assert ("PERSON", "Claire Martin") in types_values
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_pipeline.py -q` → FAIL.

- [ ] **Step 3 : Implémenter** `anonymator/pipeline.py`

```python
from anonymator.model import Entity
from anonymator.deterministic import detect_deterministic
from anonymator.secrets_detect import detect_secrets
from anonymator.merge import merge_entities
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.textnorm import normalize


def detect(text: str, ner: NerDetector, ref: Referential) -> list[Entity]:
    deterministic = [e for e in detect_deterministic(text) if ref.is_active(e.type)]
    secrets = [e for e in detect_secrets(text) if ref.is_active(e.type)]
    labels = ref.active_ner_labels()
    ner_entities = ner.detect(text, labels) if labels else []
    stop = ref.ner_stoplist()
    ner_entities = [e for e in ner_entities
                    if ref.is_active(e.type) and normalize(e.value) not in stop]
    return merge_entities(deterministic + secrets + ner_entities)
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_pipeline.py -q` → PASS.
Suite complète → verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): intègre secrets + filtre stoplist NER"
```

---

### Task 8 : Chemin direct — ne pas masquer les `confirmed=False`

**Files:**
- Modify: `anonymator/files/anonymize_file.py` (`anonymize_txt`, `anonymize_csv`)
- Test: `tests/test_anonymize_file.py`

- [ ] **Step 1 : Tests qui échouent**

```python
# tests/test_anonymize_file.py  (ajouter)
from datetime import datetime
from anonymator.files.anonymize_file import anonymize_file
from anonymator.ner import FakeNer
from anonymator.referential import Referential

def test_direct_path_keeps_unconfirmed_iban_clear(tmp_path):
    src = tmp_path / "t.txt"
    src.write_text("RIB FR76 3000 4000 1200 0000 1234 567 fin", encoding="utf-8")
    res = anonymize_file(src, FakeNer({}), Referential.load_default(),
                         tmp_path, datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_text(encoding="utf-8")
    assert "FR76 3000 4000 1200 0000 1234 567" in out   # non confirmé → laissé en clair
    assert "[IBAN]" not in out
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_anonymize_file.py::test_direct_path_keeps_unconfirmed_iban_clear -q` → FAIL (masqué à tort).

- [ ] **Step 3 : Implémenter** — filtrer `confirmed` dans le chemin direct

Dans `anonymize_txt`, après la détection :

```python
def anonymize_txt(path: Path, ner: NerDetector, ref: Referential,
                  output_dir: Path, when: datetime) -> FileResult:
    text, encoding = txt_io.read_text(path)
    ents = [e for e in detect(text, ner, ref) if e.confirmed]   # direct : pas de non confirmé
    report = AuditReport()
    for e in ents:
        report.add(e.type, e.value, ref.tag_for(e.type), "texte")
    masked = apply_masking(text, ents, ref)
    out = anonymized_path(path, output_dir, when)
    txt_io.write_text(masked, encoding, out)
    return FileResult(out, report)
```

Dans `anonymize_csv`, filtrer le scan avant l'application :

```python
    scanned = scan_csv(doc, ner, ref, cols)
    scanned = {k: [e for e in v if e.confirmed]      # direct : ignore les non confirmés
               for k, v in scanned.items()}
    scanned = {k: v for k, v in scanned.items() if v}
    doc, report = apply_csv(doc, scanned, ref)
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_anonymize_file.py -q` → PASS. Suite complète → verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/files/anonymize_file.py tests/test_anonymize_file.py
git commit -m "feat(files): chemin direct ne masque pas les entités non confirmées"
```

---

### Task 9 : `ReviewSession` (texte) — non confirmé décoché par défaut

**Files:**
- Modify: `anonymator/core/review_session.py:14-19` (constructeur)
- Test: `tests/test_review_session.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_review_session.py  (ajouter)
from anonymator.model import Entity
from anonymator.core.review_session import ReviewSession
from anonymator.referential import Referential

REF = Referential.load_default()

def test_unconfirmed_not_retained_by_default():
    text = "IBAN FR00 0000 fin"
    ents = [Entity("IBAN", "FR00 0000", 5, 14, "deterministic", 1.0, confirmed=False)]
    s = ReviewSession(text, ents)
    assert s.retained() == []                       # non confirmé → non retenu
    # mais on peut l'activer
    s.set_entity_enabled(0, True)
    assert len(s.retained()) == 1
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_review_session.py::test_unconfirmed_not_retained_by_default -q` → FAIL (retenu par défaut).

- [ ] **Step 3 : Implémenter** — initialiser `_enabled` selon `confirmed`

Dans `anonymator/core/review_session.py`, remplacer la ligne `self._enabled = [True] * len(self._entities)` du constructeur par :

```python
        self._enabled = [e.confirmed for e in self._entities]
```

Et, dans `add_manual`, conserver le recalcul mais en respectant `confirmed` (une entité manuelle est `confirmed=True` par défaut, donc activée) :

```python
        self._enabled = [e.confirmed for e in self._entities]
```

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_review_session.py -q` → PASS (tests existants inclus : leurs entités sont `confirmed=True` par défaut → toujours retenues).

- [ ] **Step 5 : Commit**

```bash
git add anonymator/core/review_session.py tests/test_review_session.py
git commit -m "feat(review): entités non confirmées décochées par défaut"
```

---

### Task 10 : Rapport d'audit — indicateur « confirmé »

**Files:**
- Modify: `anonymator/report/audit.py`
- Test: `tests/test_audit.py`

- [ ] **Step 1 : Test qui échoue**

```python
# tests/test_audit.py  (ajouter ; créer si absent)
from anonymator.report.audit import AuditReport

def test_report_tracks_confirmed_flag():
    rep = AuditReport()
    rep.add("IBAN", "FR00 0000", "[IBAN]", "texte", confirmed=False)
    row = rep.to_rows()[0]
    assert row["confirme"] == "non"

def test_report_confirmed_defaults_yes():
    rep = AuditReport()
    rep.add("PERSON", "Claire", "[PERSONNE]", "texte")
    assert rep.to_rows()[0]["confirme"] == "oui"
```

- [ ] **Step 2 : Run → FAIL**

Run : `.venv\Scripts\python.exe -m pytest tests/test_audit.py -q` → FAIL.

- [ ] **Step 3 : Implémenter** — ajouter le paramètre `confirmed` à `AuditReport`

```python
class AuditReport:
    def __init__(self):
        self._entries: dict[tuple[str, str], dict] = {}

    def add(self, etype: str, original: str, tag: str, location: str,
            confirmed: bool = True) -> None:
        key = (etype, original)
        entry = self._entries.setdefault(
            key, {"tag": tag, "occurrences": 0, "locations": [], "confirmed": confirmed})
        entry["occurrences"] += 1
        entry["locations"].append(location)
        entry["confirmed"] = entry["confirmed"] and confirmed

    def to_rows(self) -> list[dict]:
        rows = []
        for (etype, original), e in self._entries.items():
            rows.append({
                "type": etype,
                "original": original,
                "tag": e["tag"],
                "occurrences": e["occurrences"],
                "locations": "; ".join(e["locations"]),
                "confirme": "oui" if e["confirmed"] else "non",
            })
        return rows

    def export_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_rows(), ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def export_csv(self, path: Path) -> None:
        rows = self.to_rows()
        fields = ["type", "original", "tag", "occurrences", "locations", "confirme"]
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
```

> Optionnel (cohérence) : faire passer `confirmed=e.confirmed` aux appels `report.add(...)` dans
> `apply_csv`, `anonymize_txt` et `FileReviewSession.report`/`ReviewSession.report`. Non bloquant
> pour les tests ci-dessus (défaut `True`).

- [ ] **Step 4 : Run → PASS**

Run : `.venv\Scripts\python.exe -m pytest tests/test_audit.py -q` → PASS. Suite complète → verte.

- [ ] **Step 5 : Commit**

```bash
git add anonymator/report/audit.py tests/test_audit.py
git commit -m "feat(audit): colonne confirmé (oui/non) dans le rapport"
```

---

## Auto-revue (P-B vs spec qualité détection)

- §3 `Entity.confirmed` (fait en P-A) + types LOGIN/PASSWORD → Task 2. ✓
- §4 logins/mdp contextuel + entropie → Tasks 4-5. ✓
- §5 IBAN/NIR non confirmés + non masqués en direct + indicateur rapport → Tasks 3, 8, 10. ✓
- §6 stoplist + filtre pipeline → Tasks 6-7. ✓
- §7 surcharges `is_active` → Task 6 (l'UI Paramètres est en **P-C**). ✓
- §8 intégration revue (texte) `confirmed` décoché → Task 9 ; revue fichier déjà gérée par P-A. ✓

**Hors P-B (→ P-C) :** écran Paramètres (toggles types + éditeur stoplist), persistance `preferences.ner_stoplist`, branchement `Referential` avec overrides/stoplist dans `MainWindow`.
