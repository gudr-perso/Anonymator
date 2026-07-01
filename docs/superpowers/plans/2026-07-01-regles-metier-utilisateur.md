# Règles métier utilisateur — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Donner à l'utilisateur des règles métier à base de motifs (« ne jamais masquer » / « toujours masquer ») éditables sans toucher au code, et assainir l'heuristique PASSWORD trop agressive.

**Architecture:** Un module `user_rules.py` porte la compilation des motifs (mode simple → regex, ou regex expert), la classe `UserRules` (chargement/sauvegarde JSON), et deux fonctions pures : `detect_forced` (détecteur d'entités `REGLE_INTERNE`, ajouté avant fusion) et `apply_allow` (filtre appliqué après fusion, dernier mot). `Referential` transporte l'objet `UserRules` (comme il transporte déjà la stoplist). `pipeline.detect` lit `ref.user_rules`. L'ancienne `ner_stoplist` est migrée en règles `keep`.

**Tech Stack:** Python 3, `re`, `dataclasses`, `json`, PySide6 (UI), pytest.

**Spec de référence:** `docs/superpowers/specs/2026-07-01-regles-metier-utilisateur-design.md`

**Choix d'implémentation actés (divergences/précisions vs spec):**
- Correspondance **insensible à la casse** (`re.IGNORECASE`) sur le **texte brut** ; insensibilité aux accents **reportée** (offset-safety du forçage). Spec point ouvert #1.
- `detect_forced` / `apply_allow` vivent dans `user_rules.py` (cohésion avec les règles), `pipeline.detect` les appelle. Spec les situait dans `pipeline.py` — refinement.
- `Referential` **porte** l'objet `UserRules` ; `detect` le lit via `ref.user_rules` (aucun changement de signature chez les nombreux appelants de `detect`).
- Le forçage n'est **pas** conditionné par `is_active("REGLE_INTERNE")` : une règle utilisateur est un ordre explicite.

## File Structure

- **Create** `anonymator/user_rules.py` — `compile_pattern`, `Rule`, `UserRules`, `detect_forced`, `apply_allow`.
- **Create** `tests/test_user_rules.py` — compilation, matching, load/save, migration, forced, allow, précédence.
- **Modify** `anonymator/merge.py` — `_rank` reconnaît `source == "rule"` comme prioritaire.
- **Modify** `anonymator/config/entities.json` — entrée `REGLE_INTERNE`.
- **Modify** `anonymator/referential.py` — attribut `user_rules`, seeding depuis la stoplist, `with_user_rules`.
- **Modify** `anonymator/pipeline.py` — intègre `detect_forced` + `apply_allow`, retire le filtre stoplist inline.
- **Modify** `anonymator/secrets_detect.py` — assainit `_looks_like_secret`.
- **Modify** `anonymator/ui/main_window.py` — `RULES_PATH`, chargement/migration, `with_user_rules`.
- **Modify** `anonymator/ui/settings_screen.py` — remplace l'éditeur de stoplist par l'éditeur de règles + chemin + « Ouvrir le dossier ».
- **Modify** `tests/test_pipeline.py`, `tests/test_secrets_detect.py`, `tests/test_referential.py` — adaptations/ajouts.

---

### Task 1: Compilation des motifs (`compile_pattern`)

**Files:**
- Create: `anonymator/user_rules.py`
- Test: `tests/test_user_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_user_rules.py
import re
from anonymator.user_rules import compile_pattern


def test_simple_hash_is_digit():
    pat = compile_pattern("simple", "A#######")
    assert pat.fullmatch("A0000015")
    assert not pat.fullmatch("A000001")     # 6 chiffres
    assert not pat.fullmatch("XA0000015")   # ancré (fullmatch)


def test_simple_star_is_anything():
    pat = compile_pattern("simple", "FACT.*")
    assert pat.fullmatch("FACT.01/01/2023")
    assert pat.fullmatch("FACT.")
    assert not pat.fullmatch("XFACT.2023")


def test_simple_question_is_one_char():
    pat = compile_pattern("simple", "REF-?")
    assert pat.fullmatch("REF-9")
    assert not pat.fullmatch("REF-99")


def test_simple_escapes_special_chars():
    # le '.' d'un motif simple est littéral, pas un joker regex
    pat = compile_pattern("simple", "A.N. au")
    assert pat.fullmatch("A.N. au")
    assert not pat.fullmatch("AXNX au")


def test_simple_is_case_insensitive():
    pat = compile_pattern("simple", "fact.*")
    assert pat.fullmatch("FACT.2023")


def test_regex_mode_passthrough():
    pat = compile_pattern("regex", r"A\d{7}")
    assert pat.fullmatch("A0000015")
    assert not pat.fullmatch("A00000")


def test_invalid_regex_returns_none():
    assert compile_pattern("regex", "A(\\d{7}") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_user_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'anonymator.user_rules'`

- [ ] **Step 3: Write minimal implementation**

```python
# anonymator/user_rules.py
import re


def compile_pattern(mode: str, pattern: str) -> "re.Pattern | None":
    """Traduit un motif utilisateur en regex ancrée (fullmatch), casse ignorée.

    mode="simple" : # → un chiffre, ? → un caractère, * → n'importe quelle
    suite ; tout autre caractère est échappé littéralement.
    mode="regex"  : le motif est une regex brute.
    Retourne None si la regex (mode expert) est invalide.
    """
    if mode == "simple":
        parts = []
        for ch in pattern:
            if ch == "#":
                parts.append(r"\d")
            elif ch == "?":
                parts.append(".")
            elif ch == "*":
                parts.append(".*")
            else:
                parts.append(re.escape(ch))
        regex = "".join(parts)
    else:
        regex = pattern
    try:
        return re.compile(regex, re.IGNORECASE)
    except re.error:
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_user_rules.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add anonymator/user_rules.py tests/test_user_rules.py
git commit -m "feat(rules): compile_pattern (motif simple/regex → regex ancrée)"
```

---

### Task 2: `Rule` + `UserRules` (matching, chargement, migration)

**Files:**
- Modify: `anonymator/user_rules.py`
- Test: `tests/test_user_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_user_rules.py  (ajouter en bas)
from pathlib import Path
from anonymator.user_rules import Rule, UserRules


def test_keep_matches_uses_enabled_rules():
    rules = UserRules([Rule("simple", "A#######", "keep", True, "codes internes")])
    assert rules.keep_matches("A0000015")
    assert not rules.keep_matches("bonjour")


def test_disabled_rule_is_inert():
    rules = UserRules([Rule("simple", "A#######", "keep", False, "")])
    assert not rules.keep_matches("A0000015")


def test_mask_rules_exposes_enabled_mask_only():
    rules = UserRules([
        Rule("simple", "PRJ-*", "mask", True, "projets"),
        Rule("simple", "A#######", "keep", True, ""),
        Rule("simple", "OLD-*", "mask", False, ""),
    ])
    got = [r.pattern for r, _ in rules.mask_rules()]
    assert got == ["PRJ-*"]


def test_invalid_regex_rule_is_collected_not_crashing():
    rules = UserRules([Rule("regex", "A(\\d{7}", "keep", True, "")])
    assert rules.keep_matches("A0000015") is False
    assert len(rules.invalid) == 1


def test_load_absent_file_migrates_fallback_terms(tmp_path):
    path = tmp_path / "user_rules.json"
    rules = UserRules.load(path, fallback_terms=["service client", "banque"])
    assert path.exists()                       # migration écrite
    assert rules.keep_matches("service client")
    assert rules.keep_matches("banque")
    # chaque terme est devenu une règle keep/simple
    assert all(r.action == "keep" and r.mode == "simple" for r in rules.rules)


def test_load_existing_file_ignores_fallback(tmp_path):
    path = tmp_path / "user_rules.json"
    UserRules([Rule("simple", "PRJ-*", "mask", True, "")]).save(path)
    rules = UserRules.load(path, fallback_terms=["service client"])
    assert not rules.keep_matches("service client")
    assert [r.pattern for r, _ in rules.mask_rules()] == ["PRJ-*"]


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "user_rules.json"
    original = UserRules([Rule("regex", r"A\d{7}", "keep", True, "note")])
    original.save(path)
    reloaded = UserRules.load(path)
    assert reloaded.keep_matches("A0000015")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_user_rules.py -v`
Expected: FAIL — `ImportError: cannot import name 'Rule'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `anonymator/user_rules.py` (sous `compile_pattern`) :

```python
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Rule:
    mode: str          # "simple" | "regex"
    pattern: str
    action: str        # "keep" | "mask"
    enabled: bool = True
    note: str = ""


class UserRules:
    def __init__(self, rules: list[Rule]):
        self.rules = rules
        self._compiled: list[tuple[Rule, "re.Pattern"]] = []
        self.invalid: list[Rule] = []
        for r in rules:
            pat = compile_pattern(r.mode, r.pattern)
            if pat is None:
                self.invalid.append(r)
            else:
                self._compiled.append((r, pat))

    def keep_matches(self, value: str) -> bool:
        return any(r.enabled and r.action == "keep" and pat.fullmatch(value)
                   for r, pat in self._compiled)

    def mask_rules(self) -> list[tuple[Rule, "re.Pattern"]]:
        return [(r, pat) for r, pat in self._compiled
                if r.enabled and r.action == "mask"]

    # --- persistance -------------------------------------------------
    @classmethod
    def from_dicts(cls, dicts: list[dict]) -> "UserRules":
        rules = [Rule(mode=d.get("mode", "simple"),
                      pattern=d.get("pattern", ""),
                      action=d.get("action", "keep"),
                      enabled=d.get("enabled", True),
                      note=d.get("note", ""))
                 for d in dicts]
        return cls(rules)

    def to_dicts(self) -> list[dict]:
        return [{"mode": r.mode, "pattern": r.pattern, "action": r.action,
                 "enabled": r.enabled, "note": r.note} for r in self.rules]

    @classmethod
    def load(cls, path: Path,
             fallback_terms: list[str] | None = None) -> "UserRules":
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_dicts(data.get("rules", []))
        rules = [Rule("simple", t, "keep", True, "importé de la liste d'exclusion")
                 for t in (fallback_terms or [])]
        obj = cls(rules)
        obj.save(path)
        return obj

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"rules": self.to_dicts()},
                                   ensure_ascii=False, indent=2),
                        encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_user_rules.py -v`
Expected: PASS (14 tests au total)

- [ ] **Step 5: Commit**

```bash
git add anonymator/user_rules.py tests/test_user_rules.py
git commit -m "feat(rules): UserRules (matching keep/mask, load/save, migration stoplist)"
```

---

### Task 3: Détecteur `detect_forced` et filtre `apply_allow`

**Files:**
- Modify: `anonymator/user_rules.py`
- Test: `tests/test_user_rules.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_user_rules.py  (ajouter en bas)
from anonymator.model import Entity
from anonymator.user_rules import detect_forced, apply_allow


def test_detect_forced_emits_regle_interne_with_offsets():
    rules = UserRules([Rule("simple", "PRJ-####", "mask", True, "projet")])
    text = "dossier PRJ-2024 clos"
    ents = detect_forced(text, rules)
    assert len(ents) == 1
    e = ents[0]
    assert e.type == "REGLE_INTERNE"
    assert e.source == "rule"
    assert text[e.start:e.end] == "PRJ-2024"


def test_detect_forced_multiple_occurrences():
    rules = UserRules([Rule("simple", "PRJ-####", "mask", True, "")])
    ents = detect_forced("PRJ-2024 et PRJ-2025", rules)
    assert [text_slice for text_slice in (e.value for e in ents)] == ["PRJ-2024", "PRJ-2025"]


def test_detect_forced_ignores_keep_rules():
    rules = UserRules([Rule("simple", "A#######", "keep", True, "")])
    assert detect_forced("A0000015", rules) == []


def test_apply_allow_drops_matching_entities():
    rules = UserRules([Rule("simple", "A#######", "keep", True, "")])
    ents = [Entity("ADDRESS", "A0000015", 0, 8, "ner", 0.9),
            Entity("PERSON", "Claire Martin", 20, 33, "ner", 0.9)]
    kept = apply_allow(ents, rules)
    assert [e.type for e in kept] == ["PERSON"]


def test_keep_wins_over_mask_precedence():
    # une valeur qui matche à la fois mask et keep est conservée en clair
    rules = UserRules([
        Rule("simple", "PRJ-*", "mask", True, ""),
        Rule("simple", "PRJ-2024", "keep", True, ""),
    ])
    forced = detect_forced("PRJ-2024", rules)
    assert len(forced) == 1                       # le forçage a bien matché
    kept = apply_allow(forced, rules)
    assert kept == []                             # mais keep a le dernier mot
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_user_rules.py -k "forced or allow or precedence" -v`
Expected: FAIL — `ImportError: cannot import name 'detect_forced'`

- [ ] **Step 3: Write minimal implementation**

Ajouter à `anonymator/user_rules.py` (imports en tête : `from anonymator.model import Entity`) :

```python
def detect_forced(text: str, rules: UserRules) -> list[Entity]:
    """Émet une entité REGLE_INTERNE par occurrence d'un motif action=mask."""
    out: list[Entity] = []
    for _rule, pat in rules.mask_rules():
        for m in pat.finditer(text):
            if m.start() == m.end():          # match vide (ex. '*') → ignoré
                continue
            out.append(Entity("REGLE_INTERNE", m.group(0),
                              m.start(), m.end(), "rule", 1.0))
    return out


def apply_allow(entities: list[Entity], rules: UserRules) -> list[Entity]:
    """Retire les entités dont la valeur correspond à une règle action=keep."""
    return [e for e in entities if not rules.keep_matches(e.value)]
```

**Note d'implémentation :** placer `from anonymator.model import Entity` en haut du fichier, à côté de `import re`, `import json`. `finditer` scanne le texte brut (offsets corrects). Un motif comme `PRJ-*` peut produire des chevauchements entre règles ; la fusion (`merge_entities`) s'en charge en aval.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_user_rules.py -v`
Expected: PASS (19 tests au total)

- [ ] **Step 5: Commit**

```bash
git add anonymator/user_rules.py tests/test_user_rules.py
git commit -m "feat(rules): detect_forced (mask) + apply_allow (keep, dernier mot)"
```

---

### Task 4: Priorité de fusion des entités forcées

**Files:**
- Modify: `anonymator/merge.py:8-10`
- Test: `tests/test_merge.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_merge.py  (ajouter en bas)
from anonymator.model import Entity
from anonymator.merge import merge_entities


def test_forced_rule_wins_over_ner_overlap():
    # une entité forcée (source="rule") doit survivre face à un NER chevauchant
    forced = Entity("REGLE_INTERNE", "PRJ-2024", 0, 8, "rule", 1.0)
    ner = Entity("ORG", "PRJ-2024", 0, 8, "ner", 0.95)
    kept = merge_entities([ner, forced])
    assert len(kept) == 1
    assert kept[0].source == "rule"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_merge.py::test_forced_rule_wins_over_ner_overlap -v`
Expected: FAIL — le NER (0.95) l'emporte car `source=="deterministic"` est False pour les deux, et la confiance NER... en réalité `rule` a 1.0 > 0.95 donc pourrait déjà passer ; **vérifier**. Si le test passe déjà, garder quand même le test et ajuster `_rank` pour rendre la priorité explicite (robustesse si un NER a confiance 1.0).

- [ ] **Step 3: Write minimal implementation**

Modifier `_rank` dans `anonymator/merge.py` :

```python
def _rank(e: Entity) -> tuple:
    # 1) déterministe ou règle utilisateur prioritaire  2) confiance  3) span long
    return (e.source in ("deterministic", "rule"), e.confidence, e.length)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_merge.py -v`
Expected: PASS (tous les tests de merge, dont l'existant)

- [ ] **Step 5: Commit**

```bash
git add anonymator/merge.py tests/test_merge.py
git commit -m "feat(merge): les entités forcées (source=rule) gagnent les chevauchements"
```

---

### Task 5: Étiquette `REGLE_INTERNE` + `Referential` porte les règles

**Files:**
- Modify: `anonymator/config/entities.json`
- Modify: `anonymator/referential.py`
- Test: `tests/test_referential.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_referential.py  (ajouter en bas)
from anonymator.user_rules import UserRules, Rule


def test_regle_interne_tag_resolves():
    ref = Referential.load_default()
    assert ref.tag_for("REGLE_INTERNE") == "[REGLE-INTERNE]"


def test_regle_interne_not_in_ner_or_deterministic():
    ref = Referential.load_default()
    assert "REGLE_INTERNE" not in ref.active_deterministic_types()
    assert set(ref.active_ner_labels()) == {"personne", "adresse postale", "organisation"}


def test_default_seeds_user_rules_from_stoplist():
    ref = Referential.load_default()
    assert ref.user_rules.keep_matches("service client")


def test_with_user_rules_replaces_ruleset():
    ref = Referential.load_default().with_user_rules(
        UserRules([Rule("simple", "PRJ-*", "mask", True, "")]))
    assert not ref.user_rules.keep_matches("service client")
    assert [r.pattern for r, _ in ref.user_rules.mask_rules()] == ["PRJ-*"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_referential.py -k "regle or user_rules or seeds" -v`
Expected: FAIL — `KeyError: 'REGLE_INTERNE'` puis `AttributeError: 'Referential' object has no attribute 'user_rules'`

- [ ] **Step 3: Write minimal implementation**

Dans `anonymator/config/entities.json`, ajouter l'entrée avant la `]` finale de `"entities"` (après `PASSWORD`, penser à la virgule sur la ligne PASSWORD) :

```json
    {"code": "REGLE_INTERNE", "label": "Règle interne", "method": "rule", "active": true, "tag": "[REGLE-INTERNE]", "sensitivity": "Moyenne"}
```

Dans `anonymator/referential.py`, importer `UserRules`/`Rule` et porter les règles :

```python
from anonymator.user_rules import UserRules, Rule
```

Modifier `__init__` et `load_default`, ajouter `with_user_rules` :

```python
    def __init__(self, entries, overrides=None, stoplist=None, user_rules=None):
        self._by_code = {e["code"]: e for e in entries}
        self._overrides = overrides or {}
        self._stoplist = stoplist or []
        self.user_rules = user_rules or self._seed_rules_from_stoplist()

    def _seed_rules_from_stoplist(self) -> UserRules:
        return UserRules([Rule("simple", t, "keep", True,
                               "importé de la liste d'exclusion")
                          for t in self._stoplist])

    def with_user_rules(self, user_rules: UserRules) -> "Referential":
        ref = Referential(list(self._by_code.values()),
                          self._overrides, self._stoplist, user_rules)
        return ref
```

**Note :** `_TYPE_TO_NER_LABEL` ne contient pas `REGLE_INTERNE`, et `active_ner_labels`/`active_deterministic_types` filtrent par `method` (`"ner"` / `"deterministic"`), donc `method="rule"` est naturellement exclu des deux — aucun autre changement requis.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_referential.py -v`
Expected: PASS (tous, dont les existants `test_default_stoplist_loaded`, `test_active_ner_labels_...`)

- [ ] **Step 5: Commit**

```bash
git add anonymator/config/entities.json anonymator/referential.py tests/test_referential.py
git commit -m "feat(rules): étiquette REGLE_INTERNE + Referential porte les UserRules"
```

---

### Task 6: Intégration pipeline (`detect`)

**Files:**
- Modify: `anonymator/pipeline.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline.py  (ajouter en bas)
from anonymator.user_rules import UserRules, Rule


def test_pipeline_forces_mask_rule():
    ref = Referential.load_default().with_user_rules(
        UserRules([Rule("simple", "PRJ-####", "mask", True, "projet")]))
    ner = FakeNer({})
    ents = detect("dossier PRJ-2024", ner, ref)
    assert any(e.type == "REGLE_INTERNE" and e.value == "PRJ-2024" for e in ents)


def test_pipeline_keep_rule_shields_detection():
    # une valeur qu'un détecteur aurait masquée est conservée grâce à keep
    ref = Referential.load_default().with_user_rules(
        UserRules([Rule("simple", "A#######", "keep", True, "codes")]))
    ner = FakeNer({"A0000015": "ADDRESS"})
    ents = detect("code A0000015", ner, ref)
    assert all(e.value != "A0000015" for e in ents)
```

Le test existant `test_pipeline_filters_stoplist` doit rester vert (la stoplist par défaut est désormais appliquée via `apply_allow` grâce au seeding de `Referential`).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: FAIL sur les 2 nouveaux (REGLE_INTERNE absent / A0000015 non filtré).

- [ ] **Step 3: Write minimal implementation**

Réécrire `anonymator/pipeline.py` :

```python
from anonymator.model import Entity
from anonymator.deterministic import detect_deterministic
from anonymator.secrets_detect import detect_secrets
from anonymator.merge import merge_entities
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.user_rules import detect_forced, apply_allow


def detect(text: str, ner: NerDetector, ref: Referential) -> list[Entity]:
    rules = ref.user_rules
    deterministic = [e for e in detect_deterministic(text) if ref.is_active(e.type)]
    secrets = [e for e in detect_secrets(text) if ref.is_active(e.type)]
    labels = ref.active_ner_labels()
    ner_entities = ner.detect(text, labels) if labels else []
    ner_entities = [e for e in ner_entities if ref.is_active(e.type)]
    forced = detect_forced(text, rules)
    merged = merge_entities(deterministic + secrets + ner_entities + forced)
    return apply_allow(merged, rules)
```

**Note :** le filtre stoplist inline (`normalize(e.value) not in stop`) est **supprimé** ; `apply_allow` le remplace en s'appuyant sur les règles `keep` seedées depuis la stoplist. L'import de `normalize` n'est plus utilisé dans ce fichier — le retirer.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py -v`
Expected: PASS (existants + 2 nouveaux)

- [ ] **Step 5: Run the full suite (non-régression fichiers/PDF)**

Run: `python -m pytest -q`
Expected: PASS (les appels `detect(text, ner, ref)` de `chunking.py`, `anonymize_file.py`, `xlsx_io.py`, `pdf_io.py` sont inchangés ; `ref.user_rules` est seedé par défaut).

- [ ] **Step 6: Commit**

```bash
git add anonymator/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): applique forçage (mask) et allow-list (keep) dans detect"
```

---

### Task 7: Assainissement de l'heuristique PASSWORD

**Files:**
- Modify: `anonymator/secrets_detect.py:31-46`
- Test: `tests/test_secrets_detect.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_secrets_detect.py  (ajouter en bas)
def test_entropy_ignores_naming_convention_no_lowercase():
    # FACT.01/01/2023 : majuscules + chiffres + ponctuation, PAS de minuscule
    assert all(e.type != "PASSWORD" for e in detect_secrets("piece FACT.01/01/2023 reglee"))


def test_entropy_ignores_internal_code_no_lowercase():
    assert all(e.type != "PASSWORD" for e in detect_secrets("code A0000015 interne"))


def test_entropy_still_detects_mixed_case_secret():
    # min + MAJ + chiffre → vraie signature de secret
    r = _by_type("cle Xk9mPq2aZ ailleurs")
    assert "Xk9mPq2aZ" in r.get("PASSWORD", [])
```

Les tests existants restent valides : `V3lo!2026#Claire` (min+MAJ+chiffre) est toujours détecté ; les nombres purs / mots purs restent exclus.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_secrets_detect.py -k "naming_convention or internal_code or mixed_case" -v`
Expected: FAIL sur les deux premiers (`FACT.01/01/2023` et `A0000015` encore vus comme PASSWORD).

- [ ] **Step 3: Write minimal implementation**

Remplacer `_looks_like_secret` dans `anonymator/secrets_detect.py` :

```python
def _looks_like_secret(token: str) -> bool:
    t = token.strip(".,;:()[]")
    if len(t) < 8:
        return False
    if t.isdigit() or t.isalpha():          # pur numérique ou pur alpha → pas un secret
        return False
    has_lower = any(c.islower() for c in t)
    has_upper = any(c.isupper() for c in t)
    has_digit = any(c.isdigit() for c in t)
    # vraie signature de secret : minuscule ET majuscule ET chiffre présents
    # simultanément. Les conventions de nommage (FACT.01/01/2023, A0000015…),
    # en majuscules + chiffres sans minuscule, ne déclenchent plus l'entropie.
    return has_lower and has_upper and has_digit
```

`_char_classes` n'est plus utilisé par cette fonction ; le laisser en place s'il sert ailleurs, sinon le supprimer (vérifier via recherche `_char_classes`).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_secrets_detect.py -v`
Expected: PASS (existants + 3 nouveaux)

- [ ] **Step 5: Commit**

```bash
git add anonymator/secrets_detect.py tests/test_secrets_detect.py
git commit -m "fix(secrets): entropie PASSWORD sur vraie signature (min+MAJ+chiffre)"
```

---

### Task 8: Câblage `main_window` (chemin, chargement, migration)

**Files:**
- Modify: `anonymator/ui/main_window.py:18,59-63`
- Test: `tests/test_ui_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_smoke.py  (ajouter ; réutilise le pattern MainWindow(prefs_path=...))
from anonymator.user_rules import UserRules, Rule


def test_main_window_migrates_stoplist_to_rules_file(tmp_path, qtbot=None):
    from anonymator.ui.main_window import MainWindow
    from anonymator.ui.model_loader import ModelLoader
    from anonymator.ner import FakeNer
    prefs_path = tmp_path / "prefs.json"
    prefs_path.write_text('{"theme":"cuma","entity_overrides":{},'
                          '"ner_stoplist":["service client","monsieur"]}',
                          encoding="utf-8")
    win = MainWindow(loader=ModelLoader(FakeNer({})), prefs_path=prefs_path)
    rules_path = prefs_path.parent / "user_rules.json"
    assert rules_path.exists()
    assert win.ref.user_rules.keep_matches("service client")
    assert win.ref.user_rules.keep_matches("monsieur")
```

**Note :** ce test suppose que `RULES_PATH` est dérivé de `prefs_path.parent` (voir implémentation). Adapter le nom du paramètre/fixture Qt à la convention du fichier `test_ui_smoke.py` existant.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py -k migrates_stoplist -v`
Expected: FAIL — `user_rules.json` non créé / `keep_matches` faux.

- [ ] **Step 3: Write minimal implementation**

Dans `anonymator/ui/main_window.py`, ajouter l'import et la constante, et rendre le chemin des règles dérivable du dossier de prefs :

```python
from anonymator.user_rules import UserRules

PREFS_PATH = Path.home() / ".anonymator" / "preferences.json"
```

Dans `__init__`, après `self.prefs = Preferences.load(prefs_path)` :

```python
        self.rules_path = prefs_path.parent / "user_rules.json"
```

Remplacer `_build_ref` :

```python
    def _build_ref(self):
        ref = Referential.load_default(overrides=self.prefs.entity_overrides)
        # migration one-shot : la stoplist (éditée ou par défaut) alimente user_rules.json
        fallback = self.prefs.ner_stoplist
        if fallback is None:
            fallback = list(Referential.load_default()._stoplist)
        rules = UserRules.load(self.rules_path, fallback_terms=fallback)
        return ref.with_user_rules(rules)
```

Passer `rules_path` au `SettingsScreen` (utilisé en Task 9). Modifier la construction :

```python
        self.settings_screen = SettingsScreen(self.ref, self.prefs,
                                              self._apply_prefs, self.show_home,
                                              rules_path=self.rules_path)
```

Et dans `_apply_prefs`, après reconstruire `ref`, rien de plus n'est requis : `_build_ref` relit `user_rules.json`.

**Note :** `Referential.load_default()._stoplist` expose la liste brute de `ner_stoplist.json` (attribut existant). Accès à un attribut « privé » toléré ici (même paquet) ; sinon ajouter un accesseur `stoplist_terms()` sur `Referential`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_smoke.py -k migrates_stoplist -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add anonymator/ui/main_window.py tests/test_ui_smoke.py
git commit -m "feat(ui): main_window charge/migre user_rules.json et l'attache au référentiel"
```

---

### Task 9: Éditeur de règles dans `settings_screen`

**Files:**
- Modify: `anonymator/ui/settings_screen.py`
- Test: `tests/test_ui_smoke.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_smoke.py  (ajouter)
def test_settings_screen_adds_and_persists_rule(tmp_path):
    from anonymator.ui.settings_screen import SettingsScreen
    from anonymator.ui.preferences import Preferences
    from anonymator.referential import Referential
    from anonymator.user_rules import UserRules
    rules_path = tmp_path / "user_rules.json"
    UserRules([]).save(rules_path)
    prefs = Preferences()
    ref = Referential.load_default()
    screen = SettingsScreen(ref, prefs, lambda: None, lambda: None,
                            rules_path=rules_path)
    screen.add_rule(mode="simple", pattern="A#######",
                    action="keep", note="codes internes")
    reloaded = UserRules.load(rules_path)
    assert reloaded.keep_matches("A0000015")
    assert screen.rules_path_label.text().find("user_rules.json") != -1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py -k adds_and_persists_rule -v`
Expected: FAIL — `SettingsScreen.__init__() got an unexpected keyword argument 'rules_path'`

- [ ] **Step 3: Write minimal implementation**

Dans `anonymator/ui/settings_screen.py` :

1. Ajouter les imports nécessaires en tête :

```python
import os
import subprocess
import sys
from pathlib import Path
from anonymator.user_rules import UserRules, Rule
```

2. Modifier la signature `__init__` pour accepter `rules_path` :

```python
    def __init__(self, ref, prefs, on_apply, on_back, rules_path: Path | None = None):
        super().__init__()
        self.ref, self.prefs, self.on_apply = ref, prefs, on_apply
        self.rules_path = rules_path
        self.user_rules = UserRules.load(rules_path) if rules_path else UserRules([])
```

3. **Remplacer** le bloc « Liste d'exclusion (NER) » (de `root.addWidget(QLabel("Liste d'exclusion (NER)"))` jusqu'à `self._reload_stoplist()`) par la section « Règles métier » :

```python
        root.addWidget(QLabel("Règles métier"))
        help_rules = QLabel(
            "Définissez vos propres règles. « Ne jamais masquer » protège une "
            "codification interne (ex. A####### = A + 7 chiffres, FACT.* = "
            "convention de nommage). « Toujours masquer » remplace par "
            "[REGLE-INTERNE]. Mode simple : # = un chiffre, ? = un caractère, "
            "* = n'importe quoi. Mode expert : expression régulière.")
        help_rules.setWordWrap(True); help_rules.setObjectName("muted")
        root.addWidget(help_rules)

        add_rule_row = QHBoxLayout()
        self.rule_pattern = QLineEdit(); self.rule_pattern.setPlaceholderText("Motif, ex. A#######")
        self.rule_mode = QComboBox(); self.rule_mode.addItems(["simple", "expert"])
        self.rule_action = QComboBox(); self.rule_action.addItems(["Ne jamais masquer", "Toujours masquer"])
        self.rule_note = QLineEdit(); self.rule_note.setPlaceholderText("Note (optionnel)")
        btn_add_rule = QPushButton("Ajouter"); btn_add_rule.setObjectName("secondary")
        btn_add_rule.clicked.connect(self._on_add_rule_clicked)
        for w in (self.rule_pattern, self.rule_mode, self.rule_action, self.rule_note, btn_add_rule):
            add_rule_row.addWidget(w)
        root.addLayout(add_rule_row)
        self.rule_error = QLabel(""); self.rule_error.setObjectName("muted")
        root.addWidget(self.rule_error)
        self.rules_list = QListWidget(); root.addWidget(self.rules_list)

        path_row = QHBoxLayout()
        self.rules_path_label = QLabel(
            f"Fichier des règles : {self.rules_path}" if self.rules_path
            else "Fichier des règles : (non défini)")
        self.rules_path_label.setObjectName("muted"); self.rules_path_label.setWordWrap(True)
        btn_open = QPushButton("Ouvrir le dossier"); btn_open.setObjectName("ghost")
        btn_open.clicked.connect(self._open_rules_folder)
        path_row.addWidget(self.rules_path_label); path_row.addStretch(); path_row.addWidget(btn_open)
        root.addLayout(path_row)
        self._reload_rules()
```

4. **Supprimer** les méthodes devenues inutiles (`_reload_stoplist`, `add_stop_term`, `remove_stop_term`) et le bloc `base = self.prefs.ner_stoplist ...` qui précédait. Ajouter les nouvelles méthodes :

```python
    def _reload_rules(self):
        self.rules_list.clear()
        for r in self.user_rules.rules:
            sens = "garder" if r.action == "keep" else "masquer"
            label = f"[{sens}] {r.pattern}  ({r.mode})" + (f" — {r.note}" if r.note else "")
            host = QWidget(); h = QHBoxLayout(host); h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QLabel(label)); h.addStretch()
            x = QPushButton("✕"); x.setObjectName("ghost"); x.setFixedWidth(30)
            x.clicked.connect(lambda _=False, rule=r: self.remove_rule(rule))
            h.addWidget(x)
            it = QListWidgetItem(); it.setSizeHint(host.sizeHint())
            self.rules_list.addItem(it); self.rules_list.setItemWidget(it, host)

    def _on_add_rule_clicked(self):
        mode = "simple" if self.rule_mode.currentText() == "simple" else "regex"
        action = "keep" if self.rule_action.currentIndex() == 0 else "mask"
        self.add_rule(mode=mode, pattern=self.rule_pattern.text().strip(),
                      action=action, note=self.rule_note.text().strip())

    def add_rule(self, mode: str, pattern: str, action: str, note: str = ""):
        if not pattern:
            self.rule_error.setText("Le motif est vide.")
            return
        from anonymator.user_rules import compile_pattern
        if compile_pattern(mode, pattern) is None:
            self.rule_error.setText("Expression régulière invalide.")
            return
        self.rule_error.setText("")
        self.user_rules.rules.append(Rule(mode, pattern, action, True, note))
        self.user_rules = UserRules(self.user_rules.rules)   # recompile
        if self.rules_path:
            self.user_rules.save(self.rules_path)
        self.rule_pattern.clear(); self.rule_note.clear()
        self._reload_rules(); self.on_apply()

    def remove_rule(self, rule: Rule):
        if rule in self.user_rules.rules:
            self.user_rules.rules.remove(rule)
            self.user_rules = UserRules(self.user_rules.rules)
            if self.rules_path:
                self.user_rules.save(self.rules_path)
            self._reload_rules(); self.on_apply()

    def _open_rules_folder(self):
        if not self.rules_path:
            return
        folder = str(Path(self.rules_path).parent)
        if sys.platform.startswith("win"):
            os.startfile(folder)                      # noqa: S606 (Windows)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])
```

**Note :** `on_apply` (=`main_window._apply_prefs`) relit `user_rules.json` et reconstruit `ref`, donc l'ajout/suppression d'une règle prend effet immédiatement sur les écrans. Le champ `Preferences.ner_stoplist` n'est plus édité ici (il ne sert qu'à la migration one-shot).

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_smoke.py -k adds_and_persists_rule -v`
Expected: PASS

- [ ] **Step 5: Run full suite**

Run: `python -m pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add anonymator/ui/settings_screen.py tests/test_ui_smoke.py
git commit -m "feat(ui): éditeur de règles métier (remplace la stoplist) + chemin + ouvrir dossier"
```

---

### Task 10: Vérification manuelle & non-régression finale

**Files:** aucun (validation)

- [ ] **Step 1: Suite complète**

Run: `python -m pytest -q`
Expected: PASS (259 tests existants + nouveaux).

- [ ] **Step 2: Essai fonctionnel du cas d'usage réel**

Écrire un petit script jetable (dans le scratchpad, pas committé) :

```python
from anonymator.referential import Referential
from anonymator.user_rules import UserRules, Rule
from anonymator.ner import FakeNer
from anonymator.pipeline import detect
from anonymator.anonymize import apply_masking

ref = Referential.load_default().with_user_rules(UserRules([
    Rule("simple", "A#######", "keep", True, "codes internes"),
    Rule("simple", "A.N. au", "keep", True, "littéral"),
    Rule("simple", "FACT.*", "keep", True, "convention"),
]))
ner = FakeNer({"A0000015": "ADDRESS", "A.N. au": "ADDRESS"})
text = "ref A0000015, A.N. au, piece FACT.01/01/2023, mot de passe : Xk9mPq2aZ"
ents = detect(text, ner, ref)
print(apply_masking(text, ents, ref))
```

Expected : `A0000015`, `A.N. au`, `FACT.01/01/2023` **conservés en clair** ; `Xk9mPq2aZ` remplacé par `[SECRET]`.

- [ ] **Step 3: Commit final (si ajustements)**

```bash
git add -A
git commit -m "test(rules): validation bout-en-bout des règles métier"
```

---

## Self-Review (rempli par l'auteur du plan)

- **Couverture spec :** moteur keep/mask (T2-3-6), modes simple/expert (T1), assainissement PASSWORD (T7), fusion stoplist→keep (T2/T5/T8), étiquette unique `[REGLE-INTERNE]` (T5), chemin affiché + ouvrir dossier (T9), précédence keep>mask (T3), priorité fusion forcée (T4), tests (chaque tâche). ✔
- **Divergences signalées :** accents (raw + IGNORECASE, reporté) ; `detect_forced`/`apply_allow` dans `user_rules.py` ; règles portées par `Referential`. Toutes documentées en tête.
- **Cohérence des types :** `Rule(mode, pattern, action, enabled, note)`, `UserRules.keep_matches/mask_rules/load/save`, `detect_forced`/`apply_allow`, `Entity(type="REGLE_INTERNE", source="rule")`, tag `[REGLE-INTERNE]` — noms constants d'une tâche à l'autre. ✔
- **Points ouverts spec :** #1 accents (tranché : reporté) ; #2 visibilité `REGLE_INTERNE` (tranché : exclu des listes NER/déterministe, résout seulement le tag) ; #3 ouvrir dossier (tranché : `os.startfile`/`open`/`xdg-open`). ✔
