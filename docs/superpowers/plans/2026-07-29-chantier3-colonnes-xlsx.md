# Chantier 3 — Sélection par colonne + revue XLSX — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre à l'utilisateur de forcer le traitement d'une colonne depuis
l'en-tête du tableau d'aperçu (auto / tout anonymiser / tout libérer), et ouvrir
l'écran de revue aux fichiers `.xlsx` sous forme de grille.

**Architecture :** trois couches, du bas vers le haut. (1) Un socle commun
`ReviewSessionBase` absorbe la comptabilité types/valeurs aujourd'hui recopiée
mot pour mot dans `FileReviewSession` et `OoxmlReviewSession` ; par-dessus,
`TabularReviewSession` porte les entités par cellule et les arbitrages par
colonne, avec des clés opaques (`(ligne, colonne)` pour un CSV,
`(feuille, ligne, colonne)` pour un classeur). (2) `xlsx_io` se coupe en deux —
`scan_workbook` / `apply_workbook` — sur le modèle de `files/ooxml/scan.py`,
ce qui rend la revue possible : l'utilisateur tranche entre les deux.
(3) `file_screen` généralise sa grille (lignes, en-têtes, largeur) derrière
quelques accesseurs, ajoute un menu au clic sur l'en-tête et un sélecteur de
feuille, et remplace ses `isinstance(session, OoxmlReviewSession)` par un
attribut de vue `self._view`.

Le forçage « tout anonymiser » réutilise `pipeline.detect_column()` : une
entité couvrant la cellule entière, exactement ce que fait déjà la politique
`TYPED`. Aucun chemin de masquage neuf n'est inventé.

**Tech Stack :** Python 3, PySide6, openpyxl, pytest + pytest-qt.
Interpréteur : `.venv\Scripts\python.exe`. Tests : `.venv/Scripts/python.exe -m pytest -q`.

---

## Décisions de conception prises pour ce plan

Elles complètent celles du prompt (`docs/superpowers/specs/2026-07-29-chantier3-prompt.md`)
et n'y contreviennent pas.

1. **Le forçage d'une colonne est un état à deux valeurs : `(mode, type)`.**
   Le type est mémorisé avec le mode, et non recalculé, pour qu'un forçage
   survive à une hypothèse d'en-tête différente (où le type déduit
   disparaîtrait avec la ligne de titres).
2. **Un override de colonne survit au changement d'hypothèse d'en-tête.**
   Basculer « première ligne = en-têtes » déplace des lignes, jamais des
   colonnes : la position reste valide, l'override garde son sens. Il est
   capturé et restauré comme les décochages de valeurs. Testé en Task 8.
3. **Le type d'un forçage se choisit dans un sous-menu des types actifs.**
   Le type déduit du plan est proposé en tête, mais seulement s'il est actif :
   `POSTAL_CODE`, `BIC` et `URL` sont inactifs, et `detect_column` ne produit
   rien pour eux (cf. prompt). Une déduction inactive redonne la main à
   l'utilisateur au lieu de fabriquer un forçage muet.
4. **Les entités d'une colonne forcée entrent dans l'arbre des entités.**
   Un seul modèle mental : ce qui sera masqué est listé et décochable. La
   comptabilité est donc recalculée à chaque forçage (`_reindex`), en
   conservant les cases déjà décochées.
5. **La grille XLSX apparaît après « Analyser », pas au chargement.** Un
   classeur de 100 000 lignes ne se lit pas sur le thread UI ; c'est le
   `XlsxScanWorker` qui le charge, le classe et le scanne en une passe, et son
   `XlsxScanResult` alimente à la fois la grille et la session.
6. **`anonymize_workbook` garde son comportement au caractère près.** Le
   chemin direct masque aujourd'hui les entités non confirmées (contrairement
   au CSV, qui les filtre) ; c'est une divergence antérieure à ce chantier, le
   refactor ne la corrige pas — la corriger changerait des tests existants.
   Le chemin de revue, lui, applique la règle habituelle (non confirmé =
   décoché par défaut, opt-in).

---

## Structure des fichiers

| Fichier | Rôle | État |
|---|---|---|
| `anonymator/core/review_session_base.py` | comptabilité types/valeurs, filtres partagés | **à créer** |
| `anonymator/core/tabular_review_session.py` | entités par cellule + arbitrages par colonne, clés opaques | **à créer** |
| `anonymator/core/file_review_session.py` | revue CSV | hérite de `TabularReviewSession` |
| `anonymator/core/ooxml_review_session.py` | revue docx/pptx | hérite de `ReviewSessionBase` |
| `anonymator/core/xlsx_review_session.py` | revue classeur, clé `(feuille, ligne, colonne)` | **à créer** |
| `anonymator/files/xlsx_io.py` | lecture/classification/scan/application | **scindé** scan / apply |
| `anonymator/ui/xlsx_scan_worker.py` | scan du classeur hors thread UI | **à créer** |
| `anonymator/ui/file_screen.py` | l'écran | menu d'en-tête, sélecteur de feuille, grille généralisée |
| `anonymator/referential.py` | référentiel des types | + `active_codes()` |

Tests : `tests/test_review_session_base.py`, `tests/test_tabular_overrides.py`,
`tests/test_xlsx_scan.py`, `tests/test_xlsx_review_session.py`,
`tests/test_xlsx_scan_worker.py`, `tests/test_file_screen_columns.py`,
`tests/test_file_screen_xlsx.py`, plus retouches à `tests/test_file_screen.py`.

**Un test existant doit changer.** `tests/test_file_screen.py::test_review_disabled_for_xlsx`
(l. 161) affirme `btn_review.isEnabled() is False` pour un `.xlsx` : il encode
exactement la limitation que ce chantier lève. Il est remplacé, pas rafistolé
(Task 12). C'est la seule exception à « ne pas modifier les tests existants ».

---

## Task 1 : `ReviewSessionBase` — la comptabilité, une seule fois

**Files:**
- Create: `anonymator/core/review_session_base.py`
- Test: `tests/test_review_session_base.py`

- [ ] **Step 1 : écrire le test rouge**

Créer `tests/test_review_session_base.py` :

```python
from anonymator.model import Entity
from anonymator.core.review_session_base import ReviewSessionBase
from anonymator.referential import Referential


class _Session(ReviewSessionBase):
    """Sous-classe minimale : les entités sont rangées sous des clés entières."""

    def __init__(self, groups, ref):
        super().__init__(ref)
        self._groups = groups
        self._index(groups.values())

    def _keys(self):
        return self._groups.keys()

    def _retained(self, key):
        return self._kept(self._groups.get(key, []))


def _ent(etype, value, confirmed=True):
    return Entity(etype, value, 0, len(value), "deterministic", 1.0, confirmed)


def _session(**kwargs):
    return _Session(kwargs.pop("groups"), Referential.load_default())


def test_counts_distinct_values_and_occurrences():
    s = _session(groups={0: [_ent("PERSON", "Claire Martin")],
                         1: [_ent("PERSON", "Claire Martin")],
                         2: [_ent("PERSON", "Paul Durand")]})
    assert s.types() == ["PERSON"]
    assert dict(s.values_for("PERSON")) == {"Claire Martin": 2, "Paul Durand": 1}
    assert s.total_occurrences() == 3
    assert s.count_retained("PERSON") == 3


def test_unconfirmed_value_is_opt_in():
    s = _session(groups={0: [_ent("IBAN", "FR00", confirmed=False)]})
    assert s.is_value_enabled("IBAN", "FR00") is False
    assert s.is_value_confirmed("IBAN", "FR00") is False
    assert s.count_retained("IBAN") == 0
    assert [e.value for e in s._pending(s._groups[0])] == ["FR00"]


def test_reindex_keeps_user_choices_and_drops_vanished_types():
    """Réindexer est l'opération de base d'un forçage de colonne : elle doit
    recalculer les comptes sans effacer ce que l'utilisateur a décoché."""
    s = _session(groups={0: [_ent("PERSON", "Claire Martin")],
                         1: [_ent("ORG", "Bureau Sablons")]})
    s.set_value_enabled("PERSON", "Claire Martin", False)
    s.set_type_enabled("ORG", False)
    s._groups = {0: [_ent("PERSON", "Claire Martin")],
                 1: [_ent("PERSON", "Paul Durand")]}
    s._index(s._groups.values())
    assert s.types() == ["PERSON"]                      # ORG a disparu
    assert s.is_value_enabled("PERSON", "Claire Martin") is False   # choix gardé
    assert s.is_value_enabled("PERSON", "Paul Durand") is True
    assert dict(s.values_for("PERSON")) == {"Claire Martin": 1, "Paul Durand": 1}


def test_counts_retained_returns_every_type_in_one_pass():
    s = _session(groups={0: [_ent("PERSON", "Claire Martin")],
                         1: [_ent("ORG", "Bureau Sablons")]})
    assert s.counts_retained() == {"PERSON": 1, "ORG": 1}
    s.set_type_enabled("ORG", False)
    assert s.counts_retained() == {"PERSON": 1}
```

- [ ] **Step 2 : lancer le test, vérifier qu'il échoue**

```bash
.venv/Scripts/python.exe -m pytest tests/test_review_session_base.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.core.review_session_base'`.

- [ ] **Step 3 : écrire `anonymator/core/review_session_base.py`**

```python
"""Socle commun aux revues (CSV, classeur, docx/pptx).

La comptabilité type/valeur est la même partout : c'est elle qui alimente
l'arbre « Entités détectées » et ses cases à cocher. Ce qui change d'un format
à l'autre, c'est la clé sous laquelle les entités sont rangées — cellule pour
un tableau, index d'unité pour un document — et c'est tout ce qu'une
sous-classe a à fournir."""

from anonymator.model import Entity


class ReviewSessionBase:
    def __init__(self, ref):
        self.ref = ref
        self._types_enabled: dict[str, bool] = {}
        self._values_enabled: dict[tuple[str, str], bool] = {}
        self._values_count: dict[tuple[str, str], int] = {}
        self._values_confirmed: dict[tuple[str, str], bool] = {}

    def _index(self, groups) -> None:
        """(Re)construit la comptabilité à partir de groupes d'entités.

        Rejouable : les arbitrages déjà pris par l'utilisateur sont conservés,
        tout le reste est recalculé. C'est ce qui permet à un forçage de
        colonne d'ajouter ou de retirer des entités sans tenir de comptes
        différentiels — un compte différentiel finit toujours par dériver."""
        prev_types, prev_values = self._types_enabled, self._values_enabled
        self._types_enabled = {}
        self._values_enabled = {}
        self._values_count = {}
        self._values_confirmed = {}
        for ents in groups:
            for e in ents:
                self._types_enabled.setdefault(e.type, prev_types.get(e.type, True))
                key = (e.type, e.value)
                self._values_count[key] = self._values_count.get(key, 0) + 1
                # défaut : confirmé → activé ; non confirmé → désactivé (opt-in)
                self._values_enabled.setdefault(
                    key, prev_values.get(key, e.confirmed))
                # non confirmé si une occurrence échoue au contrôle de la clé
                self._values_confirmed[key] = (
                    self._values_confirmed.get(key, True) and e.confirmed)

    # --- lecture ---
    def types(self) -> list[str]:
        return sorted(self._types_enabled)

    def total_occurrences(self) -> int:
        """Nombre total d'occurrences détectées (toutes valeurs, tous types)."""
        return sum(self._values_count.values())

    def values_for(self, etype: str) -> list[tuple[str, int]]:
        items = [(v, n) for (t, v), n in self._values_count.items() if t == etype]
        return sorted(items)

    def is_type_enabled(self, etype: str) -> bool:
        return self._types_enabled.get(etype, True)

    def is_value_enabled(self, etype: str, value: str) -> bool:
        """État de la case d'une valeur distincte (pour cocher l'UI)."""
        return self._values_enabled.get((etype, value), True)

    def is_value_confirmed(self, etype: str, value: str) -> bool:
        """Faux = format reconnu mais contrôle de la clé (checksum) échoué."""
        return self._values_confirmed.get((etype, value), True)

    # --- écriture ---
    def set_type_enabled(self, etype: str, enabled: bool) -> None:
        self._types_enabled[etype] = enabled

    def set_value_enabled(self, etype: str, value: str, enabled: bool) -> None:
        self._values_enabled[(etype, value)] = enabled

    # --- filtres partagés ---
    def _kept(self, ents: list[Entity]) -> list[Entity]:
        return [e for e in ents
                if self._types_enabled.get(e.type, True)
                and self._values_enabled.get((e.type, e.value), True)]

    def _pending(self, ents: list[Entity]) -> list[Entity]:
        """Entités au format valide mais clé invalide, décochées par défaut :
        à surligner distinctement (non masquées, opt-in)."""
        return [e for e in ents
                if self._types_enabled.get(e.type, True)
                and not e.confirmed
                and not self._values_enabled.get((e.type, e.value), True)]

    # --- à fournir par les sous-classes ---
    def _keys(self):
        raise NotImplementedError

    def _retained(self, key) -> list[Entity]:
        raise NotImplementedError

    # --- comptes ---
    def counts_retained(self) -> dict[str, int]:
        """Occurrences retenues par type, en une seule passe.

        L'arbre en redemande un par type à chaque clic : les compter séparément
        relit tout le fichier une fois par type, ce qui se voit sur une colonne
        forcée de 100 000 lignes."""
        out: dict[str, int] = {}
        for key in self._keys():
            for e in self._retained(key):
                out[e.type] = out.get(e.type, 0) + 1
        return out

    def count_retained(self, etype: str) -> int:
        return self.counts_retained().get(etype, 0)
```

- [ ] **Step 4 : lancer le test, vérifier qu'il passe**

```bash
.venv/Scripts/python.exe -m pytest tests/test_review_session_base.py -q
```

Attendu : `4 passed`.

- [ ] **Step 5 : commit**

```bash
git add anonymator/core/review_session_base.py tests/test_review_session_base.py
git commit -m "refactor(revue): socle commun de comptabilite types/valeurs"
```

---

## Task 2 : brancher `OoxmlReviewSession` sur le socle

**Files:**
- Modify: `anonymator/core/ooxml_review_session.py`
- Test: `tests/test_ooxml_review_session.py` (existant, ne pas modifier)

- [ ] **Step 1 : lancer les tests existants pour établir la référence**

```bash
.venv/Scripts/python.exe -m pytest tests/test_ooxml_review_session.py -q
```

Attendu : tous verts. C'est le filet : le refactor ne doit rien changer.

- [ ] **Step 2 : réécrire `anonymator/core/ooxml_review_session.py`**

Remplacer **tout** le contenu du fichier par :

```python
from anonymator.model import Entity
from anonymator.files.ooxml import scan
from anonymator.core.review_session_base import ReviewSessionBase


class OoxmlReviewSession(ReviewSessionBase):
    """État de revue d'un document docx/pptx (non-Qt). Contrôle à deux
    niveaux combinés en ET : type activé, valeur distincte activée. Miroir de
    FileReviewSession sans la dimension colonnes/cellules (clé = index d'unité).

    En mode revue, l'arbre couvre les entités des parties principales ;
    commentaires/notes docx et métadonnées sont traités par `post_fn`
    (entités confirmées) au moment de l'application."""

    def __init__(self, units, scanned: dict[int, list[Entity]], ref,
                 save_fn, post_fn):
        super().__init__(ref)
        self._units = units
        self._scanned = scanned
        self._save_fn = save_fn
        self._post_fn = post_fn
        self._index(scanned.values())

    # --- lecture ---
    def _keys(self):
        return self._scanned.keys()

    def _retained(self, i: int) -> list[Entity]:
        return self._kept(self._scanned.get(i, []))

    def entities_for_unit(self, i: int) -> list[Entity]:
        return self._retained(i)

    def unconfirmed_for_unit(self, i: int) -> list[Entity]:
        """Entités de l'unité au format valide mais clé invalide, décochées par
        défaut : à surligner distinctement (non masquées, opt-in)."""
        return self._pending(self._scanned.get(i, []))

    # --- production ---
    def apply_and_save(self, out_path):
        retained = {i: self._retained(i) for i in self._scanned}
        retained = {i: v for i, v in retained.items() if v}
        report = scan.apply_units(self._units, retained, self.ref)
        self._save_fn(out_path)
        self._post_fn(out_path, report)
        return report
```

- [ ] **Step 3 : lancer les tests, vérifier qu'ils passent toujours**

```bash
.venv/Scripts/python.exe -m pytest tests/test_ooxml_review_session.py tests/test_file_screen.py -q
```

Attendu : tous verts, aucun test modifié.

- [ ] **Step 4 : commit**

```bash
git add anonymator/core/ooxml_review_session.py
git commit -m "refactor(revue): OoxmlReviewSession herite du socle commun"
```

---

## Task 3 : `TabularReviewSession` — entités par cellule, arbitrages par colonne

**Files:**
- Create: `anonymator/core/tabular_review_session.py`
- Test: `tests/test_tabular_overrides.py`

- [ ] **Step 1 : écrire le test rouge**

Créer `tests/test_tabular_overrides.py` :

```python
from anonymator.model import Entity
from anonymator.referential import Referential
from anonymator.files.columns import ColumnPlan, SKIP, TEXT, TYPED
from anonymator.core.tabular_review_session import (
    AUTO, CLEAR, MASK, TabularReviewSession)


class _Grid(TabularReviewSession):
    """Tableau minimal en mémoire : clé de cellule (ligne, colonne)."""

    def __init__(self, rows, scanned, ref, maskable, plans):
        self.rows = rows
        super().__init__(scanned, ref, maskable, plans)

    def column_of(self, cell_key):
        return cell_key[1]

    def has_column(self, col_key):
        return 0 <= col_key < max((len(r) for r in self.rows), default=0)

    def column_values(self, col_key):
        return {(r, col_key): row[col_key]
                for r, row in enumerate(self.rows) if col_key < len(row)}


def _ent(etype, value):
    return Entity(etype, value, 0, len(value), "ner", 1.0)


def _grid():
    rows = [["Claire Martin", "Industrie", "note libre"],
            ["Paul Durand", "BTP", "autre note"],
            ["", "Textile", "troisieme"]]
    plans = {0: ColumnPlan(TYPED, "PERSON", "en-tête « nom »"),
             1: ColumnPlan(SKIP, reason="nomenclature (peu de valeurs distinctes)"),
             2: ColumnPlan(TEXT, reason="texte libre")}
    scanned = {(0, 0): [_ent("PERSON", "Claire Martin")],
               (1, 0): [_ent("PERSON", "Paul Durand")]}
    return _Grid(rows, scanned, Referential.load_default(), {0, 2}, plans)


def test_default_state_is_auto():
    g = _grid()
    assert g.column_override(0) == (AUTO, None)
    assert g.count_retained("PERSON") == 2


def test_column_reason_is_exposed():
    g = _grid()
    assert g.column_reason(1) == "nomenclature (peu de valeurs distinctes)"


def test_clear_takes_a_column_out_of_scope():
    g = _grid()
    g.set_column_override(0, CLEAR)
    assert g.column_override(0) == (CLEAR, None)
    assert g.count_retained("PERSON") == 0
    assert g.retained_by_cell() == {}


def test_mask_covers_every_non_empty_cell_even_undetected():
    """L'état « tout anonymiser » n'existe sur aucun chemin de détection : il
    fabrique une entité couvrant la cellule, comme la politique TYPED."""
    g = _grid()
    g.set_column_override(2, MASK, "ORG")
    kept = g.retained_by_cell()
    assert [kept[(r, 2)][0].value for r in (0, 1, 2)] == [
        "note libre", "autre note", "troisieme"]
    assert g.count_retained("ORG") == 3
    assert dict(g.values_for("ORG")) == {
        "note libre": 1, "autre note": 1, "troisieme": 1}


def test_mask_skips_empty_cells():
    g = _grid()
    g.set_column_override(0, MASK, "PERSON")
    assert (2, 0) not in g.retained_by_cell()      # cellule vide
    assert g.count_retained("PERSON") == 2


def test_mask_on_a_skipped_column_works():
    """Une colonne écartée par le plan (nomenclature) reste forçable : c'est
    tout l'intérêt de l'override."""
    g = _grid()
    g.set_column_override(1, MASK, "ORG")
    assert g.count_retained("ORG") == 3


def test_auto_restores_the_computed_plan():
    g = _grid()
    g.set_column_override(0, MASK, "ORG")
    g.set_column_override(0, AUTO)
    assert g.column_override(0) == (AUTO, None)
    assert g.count_retained("PERSON") == 2
    assert g.count_retained("ORG") == 0


def test_forced_values_stay_decheckable():
    g = _grid()
    g.set_column_override(2, MASK, "ORG")
    g.set_value_enabled("ORG", "autre note", False)
    assert g.count_retained("ORG") == 2


def test_user_choices_survive_a_later_override():
    g = _grid()
    g.set_value_enabled("PERSON", "Paul Durand", False)
    g.set_column_override(2, MASK, "ORG")          # déclenche un réindexage
    assert g.is_value_enabled("PERSON", "Paul Durand") is False
    assert g.count_retained("PERSON") == 1


def test_mask_requires_a_type():
    import pytest
    g = _grid()
    with pytest.raises(ValueError):
        g.set_column_override(2, MASK)


def test_inactive_deduced_type_is_not_proposed():
    """POSTAL_CODE est inactif : le proposer fabriquerait un forçage muet."""
    rows = [["37000"], ["44000"]]
    plans = {0: ColumnPlan(TYPED, "POSTAL_CODE", "en-tête « code postal »")}
    g = _Grid(rows, {}, Referential.load_default(), {0}, plans)
    assert g.default_type_for(0) is None


def test_active_deduced_type_is_proposed():
    g = _grid()
    assert g.default_type_for(0) == "PERSON"
    assert g.default_type_for(2) is None            # colonne de texte libre


def test_overrides_are_exportable_and_replayable():
    g = _grid()
    g.set_column_override(2, MASK, "ORG")
    g.set_column_override(1, CLEAR)
    assert g.column_overrides() == {2: (MASK, "ORG"), 1: (CLEAR, None)}
    fresh = _grid()
    for key, (mode, etype) in g.column_overrides().items():
        fresh.set_column_override(key, mode, etype)
    assert fresh.count_retained("ORG") == 3
```

- [ ] **Step 2 : lancer le test, vérifier qu'il échoue**

```bash
.venv/Scripts/python.exe -m pytest tests/test_tabular_overrides.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.core.tabular_review_session'`.

- [ ] **Step 3 : écrire `anonymator/core/tabular_review_session.py`**

```python
"""Revue d'un tableau : entités rangées par cellule, arbitrages par colonne.

Les clés restent opaques — `(ligne, colonne)` pour un CSV, `(feuille, ligne,
colonne)` pour un classeur. Seule la sous-classe sait passer d'une cellule à sa
colonne et relire le contenu d'une colonne ; tout le reste est commun.

La classification automatique (cf. files/columns.py) reste le défaut. Un
forçage est un arbitrage explicite de l'utilisateur qui la recouvre pour une
colonne, sans la remplacer : revenir à AUTO rend la colonne à son plan."""

from anonymator.model import Entity
from anonymator.pipeline import detect_column
from anonymator.core.review_session_base import ReviewSessionBase

AUTO = "auto"      # le plan calculé par classify_columns fait foi
MASK = "mask"      # toutes les cellules non vides sont masquées
CLEAR = "clear"    # la colonne sort du périmètre


class TabularReviewSession(ReviewSessionBase):
    def __init__(self, scanned, ref, maskable_cols, plans=None):
        super().__init__(ref)
        self._cells = scanned
        self._columns_enabled = {c: True for c in maskable_cols}
        self.plans = dict(plans or {})
        self._overrides: dict[object, tuple[str, str | None]] = {}
        self._forced: dict[object, dict] = {}      # colonne -> {cellule: [Entity]}
        self._cells_excluded: set = set()
        self._all_keys: set = set()
        self._reindex()

    # --- à fournir par les sous-classes ---
    def column_of(self, cell_key):
        """Colonne à laquelle appartient une cellule."""
        raise NotImplementedError

    def column_values(self, col_key) -> dict:
        """{clé de cellule: texte} pour les lignes de données de la colonne."""
        raise NotImplementedError

    def has_column(self, col_key) -> bool:
        """La colonne existe-t-elle encore ? (report d'un override après
        réanalyse)"""
        raise NotImplementedError

    # --- plan et forçage ---
    def column_reason(self, col_key) -> str:
        """Pourquoi la colonne est traitée ainsi — texte prêt pour l'infobulle."""
        plan = self.plans.get(col_key)
        return plan.reason if plan else ""

    def default_type_for(self, col_key) -> str | None:
        """Type à proposer pour un forçage « tout anonymiser ».

        Un type déduit mais inactif (POSTAL_CODE, BIC, URL) ne produirait
        rien : mieux vaut ne rien proposer et laisser l'utilisateur choisir
        qu'offrir un forçage silencieusement sans effet."""
        plan = self.plans.get(col_key)
        etype = plan.etype if plan else None
        return etype if etype and self.ref.is_active(etype) else None

    def column_override(self, col_key) -> tuple[str, str | None]:
        return self._overrides.get(col_key, (AUTO, None))

    def column_overrides(self) -> dict:
        return dict(self._overrides)

    def set_column_override(self, col_key, mode: str,
                            etype: str | None = None) -> None:
        """AUTO rend la colonne à son plan ; MASK fabrique une entité couvrant
        chaque cellule non vide (même chemin que la politique TYPED, cf.
        pipeline.detect_column) ; CLEAR la sort du périmètre."""
        if mode == MASK and etype is None:
            raise ValueError("un forçage « tout anonymiser » exige un type")
        self._forced.pop(col_key, None)
        if mode == AUTO:
            self._overrides.pop(col_key, None)
        else:
            self._overrides[col_key] = (mode, etype)
        if mode == MASK:
            forced = {k: detect_column(v, etype, self.ref)
                      for k, v in self.column_values(col_key).items()}
            self._forced[col_key] = {k: v for k, v in forced.items() if v}
        self._reindex()

    def _reindex(self) -> None:
        groups = list(self._cells.values())
        keys = set(self._cells)
        for cells in self._forced.values():
            groups.extend(cells.values())
            keys |= set(cells)
        self._all_keys = keys
        self._index(groups)

    # --- lecture ---
    def _keys(self):
        return self._all_keys

    def _retained(self, cell_key) -> list[Entity]:
        col = self.column_of(cell_key)
        mode, _etype = self._overrides.get(col, (AUTO, None))
        if mode == CLEAR:
            return []
        if mode == MASK:
            return self._kept(self._forced.get(col, {}).get(cell_key, []))
        if not self._columns_enabled.get(col, False):
            return []
        if cell_key in self._cells_excluded:
            return []
        return self._kept(self._cells.get(cell_key, []))

    def _pending_at(self, cell_key) -> list[Entity]:
        col = self.column_of(cell_key)
        mode, _etype = self._overrides.get(col, (AUTO, None))
        if mode != AUTO:
            return []          # la colonne est tranchée : plus rien à signaler
        if not self._columns_enabled.get(col, False):
            return []
        if cell_key in self._cells_excluded:
            return []
        return self._pending(self._cells.get(cell_key, []))

    def retained_by_cell(self) -> dict:
        """{clé de cellule: entités retenues} — les cellules vides sont écartées."""
        out = {k: self._retained(k) for k in self._keys()}
        return {k: v for k, v in out.items() if v}

    # --- écriture ---
    def set_column_enabled(self, col_key, enabled: bool) -> None:
        self._columns_enabled[col_key] = enabled

    def set_cell_excluded(self, cell_key, excluded: bool) -> None:
        if excluded:
            self._cells_excluded.add(cell_key)
        else:
            self._cells_excluded.discard(cell_key)
```

- [ ] **Step 4 : lancer le test, vérifier qu'il passe**

```bash
.venv/Scripts/python.exe -m pytest tests/test_tabular_overrides.py -q
```

Attendu : `13 passed`.

- [ ] **Step 5 : commit**

```bash
git add anonymator/core/tabular_review_session.py tests/test_tabular_overrides.py
git commit -m "feat(revue): arbitrages par colonne (auto / tout anonymiser / tout liberer)"
```

---

## Task 4 : `FileReviewSession` sur `TabularReviewSession`

**Files:**
- Modify: `anonymator/core/file_review_session.py` (réécriture complète)
- Test: `tests/test_file_review_session.py` (existant, ne pas modifier) + ajouts

- [ ] **Step 1 : écrire le test rouge (ajout en fin de `tests/test_file_review_session.py`)**

```python
def test_column_override_masks_a_free_text_column(tmp_path):
    """Forcer une colonne masque même les cellules où rien n'a été détecté."""
    from anonymator.core.tabular_review_session import CLEAR, MASK
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Note\nClaire Martin;RAS\nPaul Durand;a rappeler\n"
                    .encode("cp1252"))
    doc = csv_io.read_csv(src)
    doc.has_header = True
    ref = Referential.load_default()
    s = FileReviewSession(doc, {}, ref, {0, 1})
    s.set_column_override(1, MASK, "ORG")
    md = s.masked_document()
    assert md.rows[0][1] == "Note"          # la ligne de titres reste intacte
    assert md.rows[1][1] == "[ORG]"
    assert md.rows[2][1] == "[ORG]"


def test_column_override_clear_wins_over_detection(tmp_path):
    from anonymator.core.tabular_review_session import CLEAR
    s = _session(tmp_path)
    s.set_column_override(0, CLEAR)
    assert s.count_retained("PERSON") == 0
    assert s.masked_document().rows[1][0] == "Claire Martin"


def test_column_plan_reason_is_available(tmp_path):
    from anonymator.files.columns import classify_columns
    src = tmp_path / "f.csv"
    src.write_bytes("telephone;montant\n03 73 41 92 92;100,00\n".encode("cp1252"))
    doc = csv_io.read_csv(src)
    doc.has_header = True
    plans = classify_columns(doc.rows, doc.has_header)
    s = FileReviewSession(doc, {}, Referential.load_default(), {0}, plans)
    assert "telephone" in s.column_reason(0)
    assert s.default_type_for(0) == "PHONE"


def test_apply_and_save_writes_the_csv(tmp_path):
    s = _session(tmp_path)
    out = tmp_path / "out.csv"
    report = s.apply_and_save(out)
    text = out.read_bytes().decode("cp1252")
    assert "[PERSONNE]" in text
    assert {r["original"] for r in report.to_rows()} == {"Claire Martin", "Paul Durand"}
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_review_session.py -q
```

Attendu : `AttributeError: 'FileReviewSession' object has no attribute 'set_column_override'`.

- [ ] **Step 3 : réécrire `anonymator/core/file_review_session.py`**

Remplacer **tout** le contenu du fichier par :

```python
from anonymator.model import Entity
from anonymator.anonymize import apply_masking
from anonymator.report.audit import AuditReport
from anonymator.core.tabular_review_session import TabularReviewSession


class FileReviewSession(TabularReviewSession):
    """État de revue d'un fichier CSV (non-Qt). Clé de cellule = (ligne, colonne).

    Cinq niveaux de contrôle : l'arbitrage de colonne (auto / tout anonymiser /
    tout libérer) l'emporte sur les quatre autres, combinés en ET — colonne
    incluse, type activé, valeur distincte activée, cellule non exclue
    individuellement. Une valeur démarre activée si ses entités sont
    `confirmed`, désactivée sinon (opt-in)."""

    def __init__(self, doc, scanned: dict[tuple[int, int], list[Entity]],
                 ref, maskable_cols: set[int], plans=None):
        self.doc = doc
        super().__init__(scanned, ref, maskable_cols, plans)

    # --- clés ---
    def column_of(self, cell_key):
        return cell_key[1]

    def has_column(self, col_key) -> bool:
        return 0 <= col_key < max((len(r) for r in self.doc.rows), default=0)

    def column_values(self, col_key) -> dict:
        start = 1 if self.doc.has_header else 0
        return {(r, col_key): self.doc.rows[r][col_key]
                for r in range(start, len(self.doc.rows))
                if col_key < len(self.doc.rows[r])}

    # --- adaptateurs de signature (r, c) ---
    def set_cell_excluded(self, r: int, c: int, excluded: bool) -> None:
        super().set_cell_excluded((r, c), excluded)

    def entities_for_cell(self, r: int, c: int) -> list[Entity]:
        """Entités actuellement retenues pour la cellule (pilote le surlignage)."""
        return self._retained((r, c))

    def unconfirmed_for_cell(self, r: int, c: int) -> list[Entity]:
        """Entités de la cellule au format valide mais clé invalide, décochées
        par défaut : à surligner distinctement (non masquées, opt-in)."""
        return self._pending_at((r, c))

    # --- producteurs ---
    def masked_document(self):
        import copy
        out = copy.deepcopy(self.doc)
        for (r, c), ents in self.retained_by_cell().items():
            out.rows[r][c] = apply_masking(out.rows[r][c], ents, self.ref)
        return out

    def report(self) -> AuditReport:
        from anonymator.files.anonymize_file import _column_label
        rep = AuditReport()
        for (r, c), ents in self.retained_by_cell().items():
            location = f"{_column_label(self.doc, c)} L{r + 1}"
            for e in ents:
                rep.add(e.type, e.value, self.ref.tag_for(e.type), location)
        return rep

    def apply_and_save(self, out_path) -> AuditReport:
        """Écrit le CSV masqué et rend le rapport. Même contrat que
        OoxmlReviewSession.apply_and_save : l'écran n'a plus à savoir de quel
        format relève la session qu'il tient."""
        from anonymator.files import csv_io
        report = self.report()
        csv_io.write_csv(self.masked_document(), out_path)
        return report
```

- [ ] **Step 4 : lancer les tests**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_review_session.py tests/test_file_screen.py -q
```

Attendu : tous verts (`test_review_disabled_for_xlsx` compris, il n'est pas encore touché).

- [ ] **Step 5 : commit**

```bash
git add anonymator/core/file_review_session.py tests/test_file_review_session.py
git commit -m "feat(revue csv): overrides de colonne et apply_and_save"
```

---

## Task 5 : `Referential.active_codes()`

**Files:**
- Modify: `anonymator/referential.py`
- Test: `tests/test_referential.py` (ajout)

- [ ] **Step 1 : écrire le test rouge (ajout en fin de `tests/test_referential.py`)**

```python
def test_active_codes_lists_only_active_types():
    """Le menu de forçage d'une colonne ne propose que des types qui masquent
    réellement quelque chose."""
    from anonymator.referential import Referential
    ref = Referential.load_default()
    codes = ref.active_codes()
    assert "PERSON" in codes and "PHONE" in codes
    assert "POSTAL_CODE" not in codes and "BIC" not in codes and "URL" not in codes


def test_active_codes_follows_overrides():
    from anonymator.referential import Referential
    ref = Referential.load_default(overrides={"PERSON": False, "URL": True})
    codes = ref.active_codes()
    assert "PERSON" not in codes and "URL" in codes
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_referential.py -q
```

Attendu : `AttributeError: 'Referential' object has no attribute 'active_codes'`.

- [ ] **Step 3 : ajouter la méthode dans `anonymator/referential.py`**

Insérer juste après `active_deterministic_types` :

```python
    def active_codes(self) -> list[str]:
        """Codes des types actifs, dans l'ordre du référentiel.

        Sert au forçage manuel d'une colonne : proposer un type inactif
        offrirait un masquage qui ne se produirait jamais."""
        return [c for c in self._by_code if self.is_active(c)]
```

- [ ] **Step 4 : lancer le test**

```bash
.venv/Scripts/python.exe -m pytest tests/test_referential.py -q
```

Attendu : tous verts.

- [ ] **Step 5 : commit**

```bash
git add anonymator/referential.py tests/test_referential.py
git commit -m "feat(referentiel): liste des types actifs"
```

---

## Task 6 : l'écran ne teste plus le type de sa session

**Files:**
- Modify: `anonymator/ui/file_screen.py:303-324` (`run`), `:437-468` (`_on_scanned`,
  `_on_ooxml_scanned`), `:531-545` (`_on_side_changed`), `:39-57` (`__init__`)
- Test: `tests/test_file_screen.py` (existant, ne pas modifier)

- [ ] **Step 1 : ajouter l'attribut de vue dans `__init__`**

Dans `FileScreen.__init__`, après la ligne `self._ooxml = None` (l. 50), ajouter :

```python
        # Forme de l'aperçu : "grid" (CSV, classeur) ou "units" (docx/pptx).
        # Remplace un test sur la classe de la session : à trois sessions, un
        # troisième `elif isinstance(...)` serait la faute.
        self._view = "grid"
```

- [ ] **Step 2 : remplacer `run()` (l. 303-324)**

```python
    def run(self, when: datetime | None = None):
        if not self.path:
            return None
        out_dir = Path(self.prefs.output_dir) if self.prefs.output_dir else self.path.parent
        when = when or datetime.now()
        if self.session is not None:
            # Toutes les sessions savent s'appliquer et se rendre : l'écran n'a
            # pas à savoir de quel format il s'agit.
            out = anonymized_path(self.path, out_dir, when)
            report = self.session.apply_and_save(out)
            return FileResult(out, report)
        try:
            ner = self.loader.get()
            result = anonymize_file(self.path, ner, self.ref, out_dir, when,
                                    has_header=self._header_override())
        except UnsupportedFormat as e:
            QMessageBox.warning(self, "Format non supporté", str(e))
            return None
        return result
```

- [ ] **Step 3 : ajouter `_render_current()` et l'utiliser dans `_on_side_changed`**

Remplacer `_on_side_changed` (l. 531-544) par :

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
        self._render_current()

    def _render_current(self):
        if self._view == "units":
            self._render_units_page()
        else:
            self._render_page()
```

- [ ] **Step 4 : positionner `_view` dans les deux gestionnaires de scan**

Dans `_on_scanned` (l. 437), première ligne du corps :

```python
        self._view = "grid"
```

Dans `_on_ooxml_scanned` (l. 450), après `self._ooxml = res` :

```python
        self._view = "units"
```

- [ ] **Step 5 : utiliser `counts_retained()` dans `_refresh_counts`**

Remplacer `_refresh_counts` (l. 546-550) par :

```python
    def _refresh_counts(self):
        counts = self.session.counts_retained()      # une passe pour tous les types
        for i in range(self.side.topLevelItemCount()):
            top = self.side.topLevelItem(i)
            _, t, _ = top.data(0, Qt.UserRole)
            top.setText(1, f"×{counts.get(t, 0)}")
```

Et dans `_build_side` (l. 494), remplacer la ligne
`top = QTreeWidgetItem([t, f"×{self.session.count_retained(t)}"])` par :

```python
        counts = self.session.counts_retained()
```
placée juste après `self.side.clear()`, puis dans la boucle :
```python
            top = QTreeWidgetItem([t, f"×{counts.get(t, 0)}"])
```

- [ ] **Step 6 : retirer l'import devenu inutile**

Dans `anonymator/ui/file_screen.py`, la ligne 27
`from anonymator.core.ooxml_review_session import OoxmlReviewSession` n'est
plus référencée : la supprimer.

- [ ] **Step 7 : lancer la suite complète**

```bash
.venv/Scripts/python.exe -m pytest -q
```

Attendu : tous verts, aucun test modifié.

- [ ] **Step 8 : commit**

```bash
git add anonymator/ui/file_screen.py
git commit -m "refactor(ui): rendu et application polymorphes, sans test de classe"
```

---

## Task 7 : clic sur l'en-tête d'une colonne CSV

**Files:**
- Modify: `anonymator/ui/file_screen.py`
- Test: `tests/test_file_screen_columns.py` (à créer)

- [ ] **Step 1 : écrire le test rouge**

Créer `tests/test_file_screen_columns.py` :

```python
from datetime import datetime
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.file_screen import FileScreen
from anonymator.core.tabular_review_session import AUTO, CLEAR, MASK


def _csv(tmp_path):
    src = tmp_path / "clients.csv"
    src.write_bytes(
        ("contact_nom;secteur;note\n"
         "Leclerc;Industrie;RAS\n"
         "Berger;BTP;a rappeler\n").encode("cp1252"))
    return src


def _screen(tmp_path):
    loader = ModelLoader(FakeNer({}))
    return FileScreen(Referential.load_default(), loader,
                      Preferences(output_dir=str(tmp_path)), on_back=lambda: None)


def _reviewed(qtbot, tmp_path):
    s = _screen(tmp_path)
    qtbot.addWidget(s)
    s.load_path(str(_csv(tmp_path)))
    s.header_switch.setChecked(True)
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    return s


def test_header_menu_offers_three_states(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    menu, actions = s._build_column_menu(2)
    labels = [a.text() for a in menu.actions()]
    assert any(l.startswith("Auto") for l in labels)
    assert "Tout anonymiser" in [a.text() for a in menu.actions() if a.menu()]
    assert "Tout libérer" in labels
    # le sous-menu ne propose que des types actifs
    types = {etype for (_mode, etype) in actions.values() if etype}
    assert "PERSON" in types and "POSTAL_CODE" not in types


def test_header_menu_puts_the_deduced_type_first(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    _menu, actions = s._build_column_menu(0)       # colonne « contact_nom »
    masks = [etype for (mode, etype) in actions.values() if mode == MASK]
    assert masks[0] == "PERSON"


def test_forcing_a_column_masks_every_cell(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")        # colonne « note »
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    lines = out.splitlines()
    assert lines[0].endswith(";note")              # titres intacts
    assert lines[1].endswith(";[ORG]")
    assert lines[2].endswith(";[ORG]")


def test_freeing_a_column_keeps_it_in_clear(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    assert s.session.count_retained("PERSON") > 0
    s.apply_column_override(0, CLEAR)
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    assert "Leclerc" in out and "[PERSONNE]" not in out


def test_forced_header_is_marked_and_explained(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")
    item = s.table.horizontalHeaderItem(2)
    assert item.text().endswith("note") and item.text() != "note"   # marqueur
    assert "Organisation" in item.toolTip()


def test_auto_header_tooltip_shows_the_reason(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    tip = s.table.horizontalHeaderItem(1).toolTip()   # « secteur » : nomenclature
    assert "nomenclature" in tip or "texte libre" in tip


def test_forced_column_appears_in_the_entity_tree(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")
    tops = [s.side.topLevelItem(i).data(0, __import__(
        "PySide6.QtCore", fromlist=["Qt"]).Qt.UserRole)[1]
        for i in range(s.side.topLevelItemCount())]
    assert "ORG" in tops
    assert s.occ_badge.text().startswith("2 occ") or "occ." in s.occ_badge.text()


def test_returning_to_auto_restores_the_plan(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(0, CLEAR)
    assert s.session.count_retained("PERSON") == 0
    s.apply_column_override(0, AUTO)
    assert s.session.count_retained("PERSON") == 2
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_screen_columns.py -q
```

Attendu : `AttributeError: 'FileScreen' object has no attribute '_build_column_menu'`.

- [ ] **Step 3 : implémenter dans `anonymator/ui/file_screen.py`**

**(a)** Compléter les imports en tête de fichier :

```python
from PySide6.QtWidgets import (QWidget, QFrame, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QFileDialog,
                               QMessageBox, QTreeWidget, QTreeWidgetItem, QLineEdit,
                               QCheckBox, QMenu, QComboBox)
from PySide6.QtGui import QColor, QCursor
```

et, à côté des autres imports `anonymator` :

```python
from anonymator.files.columns import classify_columns
from anonymator.core.tabular_review_session import AUTO, CLEAR, MASK
```

**(b)** Sous la constante `PAGE_SIZE` (l. 32), ajouter :

```python
# Marqueur d'un arbitrage manuel dans l'intitulé de colonne : l'en-tête doit
# dire d'un coup d'œil que le plan automatique a été recouvert.
_OVERRIDE_MARK = {MASK: "🔒 ", CLEAR: "🔓 "}
```

**(c)** Dans `__init__`, juste après la configuration de `self.table`
(après `self.table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)`) :

```python
        head = self.table.horizontalHeader()
        head.setSectionsClickable(True)
        head.sectionClicked.connect(self._on_header_clicked)
```

**(d)** Ajouter les méthodes, à la suite de `_render_page` :

```python
    # ---------- arbitrage par colonne ----------
    def _column_key(self, col: int):
        """Clé de colonne pour la session : un index pour un CSV, un couple
        (feuille, index) pour un classeur."""
        return col

    def _header_label(self, col: int) -> str:
        rows = self._grid_rows()
        if self._grid_has_header() and rows and col < len(rows[0]):
            return rows[0][col]
        return f"col{col}"

    def _column_tooltip(self, key, mode: str, etype: str | None) -> str:
        reason = self.session.column_reason(key) or "colonne non classée"
        if mode == MASK:
            return (f"Colonne forcée : toutes les cellules non vides sont "
                    f"masquées en {self.ref.label_for(etype)}.\n"
                    f"Plan automatique : {reason}.")
        if mode == CLEAR:
            return (f"Colonne libérée : hors du périmètre.\n"
                    f"Plan automatique : {reason}.")
        return (f"Plan automatique : {reason}.\n"
                f"Cliquez l'en-tête pour forcer cette colonne.")

    def _decorate_headers(self, width: int):
        """Rend lisibles, sur l'en-tête, l'état de la colonne et sa raison."""
        if self.session is None:
            return
        for c in range(width):
            item = self.table.horizontalHeaderItem(c)
            if item is None:
                continue
            key = self._column_key(c)
            mode, etype = self.session.column_override(key)
            item.setText(_OVERRIDE_MARK.get(mode, "") + self._header_label(c))
            item.setToolTip(self._column_tooltip(key, mode, etype))

    def _build_column_menu(self, col: int):
        """Menu des trois états d'une colonne. Rendu séparément de son
        exécution : c'est ce qui le rend vérifiable sans piloter la souris."""
        key = self._column_key(col)
        mode, etype = self.session.column_override(key)
        menu = QMenu(self)
        actions = {}

        reason = self.session.column_reason(key) or "colonne non classée"
        auto = menu.addAction(f"Auto — {reason}")
        auto.setCheckable(True)
        auto.setChecked(mode == AUTO)
        actions[auto] = (AUTO, None)

        sub = menu.addMenu("Tout anonymiser")
        deduced = self.session.default_type_for(key)
        codes = self.ref.active_codes()
        if deduced in codes:
            codes = [deduced] + [c for c in codes if c != deduced]
        for code in codes:
            label = self.ref.label_for(code)
            if code == deduced:
                label += "   (déduit)"
            act = sub.addAction(label)
            act.setCheckable(True)
            act.setChecked(mode == MASK and etype == code)
            actions[act] = (MASK, code)

        clear = menu.addAction("Tout libérer")
        clear.setCheckable(True)
        clear.setChecked(mode == CLEAR)
        actions[clear] = (CLEAR, None)
        return menu, actions

    def _on_header_clicked(self, col: int):
        if self.session is None or self._view != "grid":
            return
        menu, actions = self._build_column_menu(col)
        chosen = menu.exec(QCursor.pos())
        if chosen in actions:
            self.apply_column_override(col, *actions[chosen])

    def apply_column_override(self, col: int, mode: str,
                              etype: str | None = None):
        """Applique l'arbitrage et rafraîchit tout ce qu'il déplace : les
        entités d'une colonne forcée entrent dans l'arbre, donc le compteur
        d'occurrences et les cases à cocher bougent aussi."""
        self.session.set_column_override(self._column_key(col), mode, etype)
        self._build_side()
        self.occ_badge.setText(f"{_fmt_int(self.session.total_occurrences())} occ.")
        self._render_current()
```

**(e)** Dans `_render_page`, toujours nommer les colonnes (pour disposer d'un
`QTableWidgetItem` d'en-tête porteur de l'infobulle) et décorer. Remplacer le
bloc `if header: self.table.setHorizontalHeaderLabels(...)` (l. 580-582) par :

```python
        # Les intitulés sont toujours posés : sans QTableWidgetItem d'en-tête,
        # il n'y a nulle part où accrocher l'infobulle ni le marqueur d'état.
        self.table.setHorizontalHeaderLabels(
            [header[c] if (header and c < len(header)) else f"col{c}"
             for c in range(width)])
```

et, juste avant la ligne `last = self._page_count() - 1` :

```python
        self._decorate_headers(width)
```

**(f)** Dans `analyze()`, passer le plan **complet** à la session (les colonnes
`SKIP` comprises : leur `reason` alimente l'infobulle). Remplacer les l. 403-406 :

```python
        plans = csv_column_plans(self.doc)
        cols = set(plans)
        self._cols = cols
        # Plan complet, colonnes écartées comprises : c'est leur `reason` qui
        # explique à l'utilisateur pourquoi elles sont hors périmètre.
        self._full_plans = classify_columns(self.doc.rows, self.doc.has_header)
```

et dans `_on_scanned`, l. 438 :

```python
        self.session = FileReviewSession(self.doc, scanned, self.ref, self._cols,
                                         self._full_plans)
```

**(g)** Ajouter les accesseurs de grille utilisés par `_header_label` (ils
servent aussi à la Task 10 ; les poser dès maintenant). À la suite de
`_data_rows` :

```python
    # ---------- grille courante (CSV ou feuille de classeur) ----------
    def _grid_rows(self) -> list[list[str]]:
        return self.doc.rows if self.doc is not None else []

    def _grid_has_header(self) -> bool:
        return bool(self.doc is not None and self.doc.has_header)
```

- [ ] **Step 4 : lancer le test**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_screen_columns.py tests/test_file_screen.py -q
```

Attendu : tous verts.

- [ ] **Step 5 : commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen_columns.py
git commit -m "feat(ui): clic sur l'en-tete pour forcer une colonne (auto/masquer/liberer)"
```

---

## Task 8 : un override de colonne survit au changement d'hypothèse d'en-tête

**Files:**
- Modify: `anonymator/ui/file_screen.py:228-251` (`_capture_choices`, `_restore_choices`)
- Test: `tests/test_file_screen_columns.py` (ajout)

- [ ] **Step 1 : écrire le test rouge (ajout en fin de `tests/test_file_screen_columns.py`)**

```python
def test_column_override_survives_a_header_change(qtbot, tmp_path):
    """Basculer « première ligne = en-têtes » déplace des lignes, jamais des
    colonnes : l'arbitrage positionnel garde son sens et doit être reporté."""
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.column_override(2) == (MASK, "ORG")
    assert s.session.count_retained("ORG") == 3     # la ligne 1 est devenue donnée


def test_override_of_a_vanished_column_is_dropped(qtbot, tmp_path):
    """Reporter un arbitrage sur un fichier plus étroit ne doit pas lever."""
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(2, MASK, "ORG")
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    other = tmp_path / "etroit.csv"
    other.write_bytes("Nom;Ville\nLeclerc;Tours\n".encode("cp1252"))
    s.load_path(str(other))
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.column_overrides() == {}       # arbitrage d'un autre fichier
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_screen_columns.py::test_column_override_survives_a_header_change -q
```

Attendu : `assert (auto, None) == (mask, ORG)` — l'override n'est pas reporté.

- [ ] **Step 3 : étendre capture/restauration**

Remplacer `_capture_choices` et `_restore_choices` (l. 228-251) par :

```python
    def _capture_choices(self) -> dict | None:
        """Arbitrages manuels de la revue en cours. Types et valeurs sont
        indexés par (type, valeur) : ils survivent à un changement de plan de
        colonnes. Les forçages de colonne, eux, sont positionnels par nature —
        et la position reste valide, car changer l'hypothèse d'en-tête déplace
        des lignes, pas des colonnes."""
        if self.session is None:
            return None
        types = {t: self.session.is_type_enabled(t) for t in self.session.types()}
        values = {(t, v): self.session.is_value_enabled(t, v)
                  for t in self.session.types()
                  for v, _n in self.session.values_for(t)}
        columns = self.session.column_overrides()
        return {"types": types, "values": values, "columns": columns}

    def _restore_choices(self, choices: dict | None) -> None:
        """Réapplique les arbitrages qui gardent un sens dans la nouvelle
        analyse ; ignore en silence ce qui a disparu.

        Les colonnes d'abord : un forçage crée des entités, et les décochages
        de valeurs doivent pouvoir porter dessus."""
        if not choices or self.session is None:
            return
        for key, (mode, etype) in choices.get("columns", {}).items():
            if self.session.has_column(key):
                self.session.set_column_override(key, mode, etype)
        for etype, enabled in choices["types"].items():
            if etype in self.session.types():
                self.session.set_type_enabled(etype, enabled)
        known = {(t, v) for t in self.session.types()
                 for v, _n in self.session.values_for(t)}
        for (etype, value), enabled in choices["values"].items():
            if (etype, value) in known:
                self.session.set_value_enabled(etype, value, enabled)
```

- [ ] **Step 4 : lancer les tests**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_screen_columns.py tests/test_file_screen.py -q
```

Attendu : tous verts.

- [ ] **Step 5 : commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen_columns.py
git commit -m "feat(ui): les forcages de colonne survivent au changement d'en-tete"
```

---

## Task 9 : `xlsx_io` — séparer le scan de l'application

**Files:**
- Modify: `anonymator/files/xlsx_io.py`
- Test: `tests/test_xlsx_scan.py` (à créer), `tests/test_anonymize_xlsx.py` (existant, ne pas modifier)

- [ ] **Step 1 : écrire le test rouge**

Créer `tests/test_xlsx_scan.py` :

```python
from datetime import date
import openpyxl
from anonymator.referential import Referential
from anonymator.ner import FakeNer, NullNer
from anonymator.files import xlsx_io
from anonymator.files.columns import SKIP, TYPED


def _book(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients"
    for c, h in enumerate(["code_client", "contact_nom", "telephone",
                           "secteur", "ca_2025"], start=1):
        ws.cell(row=1, column=c, value=h)
    for i in range(24):
        r = i + 2
        ws.cell(row=r, column=1, value="C%07d" % (i + 1))
        ws.cell(row=r, column=2, value=["Leclerc", "Berger", "Poirier"][i % 3])
        ws.cell(row=r, column=3, value="03 73 41 92 %02d" % i)
        ws.cell(row=r, column=4, value=["Industrie", "BTP", "Textile"][i % 3])
        ws.cell(row=r, column=5, value=1000 + i)
    ws2 = wb.create_sheet("Notes")
    ws2["A1"] = "Fournisseur Claire Martin"
    ws2["A2"] = "=A1"
    wb.save(path)
    return path


def test_scan_reports_sheets_matrices_plans_and_headers(tmp_path):
    src = _book(tmp_path / "b.xlsx")
    res = xlsx_io.scan_workbook(src, NullNer(), Referential.load_default())
    assert res.sheets == ["Clients", "Notes"]
    assert res.has_header["Clients"] is True
    assert res.has_header["Notes"] is False
    assert res.plans["Clients"][1].policy == TYPED
    assert res.plans["Clients"][1].etype == "PERSON"
    assert res.plans["Clients"][4].policy == SKIP       # ca_2025 : mesures
    assert res.matrices["Clients"][0][1] == "contact_nom"


def test_scan_keys_entities_by_sheet_row_and_column(tmp_path):
    src = _book(tmp_path / "b.xlsx")
    res = xlsx_io.scan_workbook(src, NullNer(), Referential.load_default())
    assert ("Clients", 1, 1) in res.scanned            # 1re ligne de données
    assert res.scanned[("Clients", 1, 1)][0].type == "PERSON"
    assert ("Clients", 0, 1) not in res.scanned        # ligne de titres épargnée
    assert not any(k[2] == 4 for k in res.scanned)     # colonne de mesures


def test_scan_never_reads_a_formula(tmp_path):
    src = _book(tmp_path / "b.xlsx")
    res = xlsx_io.scan_workbook(src, FakeNer({"Claire Martin": "PERSON"}),
                                Referential.load_default())
    assert res.matrices["Notes"][1][0] == ""           # =A1 compte pour vide
    assert ("Notes", 1, 0) not in res.scanned


def test_header_override_wins_over_detection(tmp_path):
    src = _book(tmp_path / "b.xlsx")
    res = xlsx_io.scan_workbook(src, NullNer(), Referential.load_default(),
                                header_overrides={"Clients": False})
    assert res.has_header["Clients"] is False
    assert ("Clients", 0, 1) in res.scanned            # la ligne 1 est une donnée


def test_apply_writes_only_the_retained_cells(tmp_path):
    src = _book(tmp_path / "b.xlsx")
    ref = Referential.load_default()
    res = xlsx_io.scan_workbook(src, NullNer(), ref)
    retained = {k: v for k, v in res.scanned.items() if k[2] == 1}   # contact_nom
    report = xlsx_io.apply_workbook(res, retained, ref)
    ws = res.workbook["Clients"]
    assert ws.cell(row=2, column=2).value == "[PERSONNE]"
    assert ws.cell(row=2, column=3).value == "03 73 41 92 00"        # non retenue
    assert any(r["type"] == "PERSON" for r in report.to_rows())
    assert all("Clients!" in r["location"] for r in report.to_rows())


def test_apply_never_rewrites_a_formula(tmp_path):
    src = _book(tmp_path / "b.xlsx")
    ref = Referential.load_default()
    res = xlsx_io.scan_workbook(src, NullNer(), ref)
    from anonymator.model import Entity
    forged = {("Notes", 1, 0): [Entity("PERSON", "=A1", 0, 3, "column", 1.0)]}
    xlsx_io.apply_workbook(res, forged, ref)
    assert res.workbook["Notes"]["A2"].value == "=A1"
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_xlsx_scan.py -q
```

Attendu : `AttributeError: module 'anonymator.files.xlsx_io' has no attribute 'scan_workbook'`.

- [ ] **Step 3 : réécrire `anonymator/files/xlsx_io.py`**

Remplacer le fichier entier par :

```python
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial
from pathlib import Path

import openpyxl

from anonymator.model import Entity
from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.pipeline import detect, detect_column
from anonymator.anonymize import apply_masking
from anonymator.dedup import detect_unique
from anonymator.report.audit import AuditReport
from anonymator.output_naming import anonymized_path
from anonymator.files.columns import (
    SKIP, TYPED, ColumnPlan, classify_columns, looks_like_header_row)


def _is_formula(cell) -> bool:
    return cell.data_type == "f" or (isinstance(cell.value, str)
                                     and cell.value.startswith("="))


def _cell_text(cell) -> str:
    """Représentation texte d'une cellule pour la classification.

    Les formules comptent pour vides : leur source n'est pas une donnée, et
    elles ne doivent jamais peser sur le profil d'une colonne."""
    if cell.value is None or _is_formula(cell):
        return ""
    return str(cell.value)


def sheet_has_header(ws) -> bool:
    """Première ligne = en-têtes ?

    Contrairement au CSV, le classeur porte le type de chaque cellule : une
    ligne de titres est faite de texte, au-dessus d'au moins une colonne qui
    ne l'est pas. C'est un fait lu dans le fichier, pas une statistique — il
    reste donc le signal décisif, et un refus de sa part n'est jamais annulé.

    Il a un angle mort, et un seul : une feuille dont *toutes* les colonnes
    sont textuelles. Là, et là seulement, on regarde si la ligne 1 est faite
    de noms de colonnes connus (cf. columns.looks_like_header_row). Ce repli
    n'invente rien sur la forme des chaînes : il interroge le lexique qui
    pilote déjà le typage. Sans donnée en dessous, ou sans vocabulaire
    reconnu, la ligne est traitée comme une donnée — choix prudent : elle est
    analysée plutôt qu'ignorée."""
    rows = list(ws.iter_rows())
    if len(rows) < 2:
        return False
    first = [c for c in rows[0] if c.value is not None]
    if not first or not all(isinstance(c.value, str) and not _is_formula(c)
                            for c in first):
        return False
    if any(cell.value is not None and not isinstance(cell.value, str)
           for row in rows[1:] for cell in row):
        return True
    return looks_like_header_row([c.value for c in first])


def _sheet_matrix(ws) -> list[list[str]]:
    return [[_cell_text(c) for c in row] for row in ws.iter_rows()]


@dataclass
class XlsxScanResult:
    """Tout ce qu'une revue doit connaître d'un classeur, sans rien y écrire.

    Le classeur openpyxl reste ouvert : c'est lui qu'on masquera à la fin, ce
    qui préserve la mise en forme et les formules."""
    workbook: object
    sheets: list[str]
    matrices: dict[str, list[list[str]]]
    plans: dict[str, dict[int, ColumnPlan]]
    has_header: dict[str, bool]
    scanned: dict[tuple[str, int, int], list[Entity]] = field(default_factory=dict)


def scan_workbook(path: Path, ner: NerDetector, ref: Referential,
                  header_overrides: dict[str, bool] | None = None) -> XlsxScanResult:
    """Lit le classeur, classe ses colonnes et détecte les entités, sans rien
    écrire. Séparer le scan de l'application est ce qui rend la revue possible :
    l'utilisateur tranche entre les deux (cf. files/ooxml/scan.py).

    Le plan de traitement est décidé une fois par colonne et par feuille (cf.
    columns.py) : une colonne typée est masquée en entier sans passer par le
    NER, une nomenclature ou une mesure reste intacte.

    Indices de `scanned` : ceux de la matrice, donc décalés de 1 par rapport
    aux coordonnées openpyxl (ligne 1 du classeur = ligne 0 de la matrice)."""
    wb = openpyxl.load_workbook(path)
    overrides = header_overrides or {}
    sheets: list[str] = []
    matrices: dict[str, list[list[str]]] = {}
    plans: dict[str, dict[int, ColumnPlan]] = {}
    headers: dict[str, bool] = {}
    scanned: dict[tuple[str, int, int], list[Entity]] = {}
    for ws in wb.worksheets:
        title = ws.title
        sheets.append(title)
        matrix = _sheet_matrix(ws)
        matrices[title] = matrix
        if not matrix:
            plans[title] = {}
            headers[title] = False
            continue
        has_header = overrides.get(title, sheet_has_header(ws))
        headers[title] = has_header
        sheet_plans = classify_columns(matrix, has_header)
        plans[title] = sheet_plans
        start = 1 if has_header else 0
        for col, plan in sheet_plans.items():
            if plan.policy == SKIP:
                continue
            if plan.policy == TYPED and plan.etype:
                detector = partial(detect_column, etype=plan.etype, ref=ref)
            else:
                detector = lambda v: detect(v, ner, ref)  # noqa: E731
            rows = [r for r in range(start, len(matrix))
                    if col < len(matrix[r]) and matrix[r][col]]
            cache = detect_unique([matrix[r][col] for r in rows], detector)
            for r in rows:
                ents = cache.get(matrix[r][col], [])
                if ents:
                    scanned[(title, r, col)] = ents
    return XlsxScanResult(wb, sheets, matrices, plans, headers, scanned)


def apply_workbook(result: XlsxScanResult,
                   retained: dict[tuple[str, int, int], list[Entity]],
                   ref: Referential,
                   report: AuditReport | None = None) -> AuditReport:
    """Écrit les entités retenues dans les cellules du classeur.

    Une cellule de formule n'est jamais réécrite : sa source n'est pas une
    donnée, et l'écraser détruirait le calcul."""
    report = report if report is not None else AuditReport()
    for (title, r, c), ents in retained.items():
        if not ents:
            continue
        cell = result.workbook[title].cell(row=r + 1, column=c + 1)
        if _is_formula(cell):
            continue
        value = _cell_text(cell)
        location = f"{title}!{cell.coordinate}"
        for e in ents:
            report.add(e.type, e.value, ref.tag_for(e.type), location)
        cell.value = apply_masking(value, ents, ref)
    return report


def anonymize_workbook(path: Path, ner: NerDetector, ref: Referential,
                       output_dir: Path, when: datetime) -> tuple[Path, AuditReport]:
    """Chemin direct, sans revue : scan puis application immédiate."""
    result = scan_workbook(path, ner, ref)
    report = apply_workbook(result, result.scanned, ref)
    out = anonymized_path(path, output_dir, when)
    result.workbook.save(out)
    return out, report
```

- [ ] **Step 4 : lancer les tests, scan et chemin direct**

```bash
.venv/Scripts/python.exe -m pytest tests/test_xlsx_scan.py tests/test_anonymize_xlsx.py tests/test_anonymize_file.py -q
```

Attendu : tous verts, `tests/test_anonymize_xlsx.py` inchangé.

- [ ] **Step 5 : commit**

```bash
git add anonymator/files/xlsx_io.py tests/test_xlsx_scan.py
git commit -m "refactor(xlsx): separe le scan de l'application (XlsxScanResult)"
```

---

## Task 10 : `XlsxReviewSession`

**Files:**
- Create: `anonymator/core/xlsx_review_session.py`
- Test: `tests/test_xlsx_review_session.py`

- [ ] **Step 1 : écrire le test rouge**

Créer `tests/test_xlsx_review_session.py` :

```python
import openpyxl
from anonymator.referential import Referential
from anonymator.ner import FakeNer, NullNer
from anonymator.files import xlsx_io
from anonymator.core.xlsx_review_session import XlsxReviewSession
from anonymator.core.tabular_review_session import CLEAR, MASK


def _book(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients"
    for c, h in enumerate(["code_client", "contact_nom", "secteur", "note"],
                          start=1):
        ws.cell(row=1, column=c, value=h)
    for i in range(24):
        r = i + 2
        ws.cell(row=r, column=1, value="C%07d" % (i + 1))
        ws.cell(row=r, column=2, value=["Leclerc", "Berger", "Poirier"][i % 3])
        ws.cell(row=r, column=3, value=["Industrie", "BTP", "Textile"][i % 3])
        ws.cell(row=r, column=4, value="note %d" % i)
    ws2 = wb.create_sheet("Tiers")
    ws2["A1"] = "Fournisseur Claire Martin"
    wb.save(path)
    return path


def _session(tmp_path, ner=None):
    src = _book(tmp_path / "b.xlsx")
    ref = Referential.load_default()
    res = xlsx_io.scan_workbook(src, ner or NullNer(), ref)
    return XlsxReviewSession(res, ref), src


def test_types_and_counts(tmp_path):
    s, _src = _session(tmp_path)
    assert "PERSON" in s.types()
    assert s.count_retained("PERSON") == 24        # colonne typée par en-tête


def test_entities_are_keyed_by_sheet(tmp_path):
    s, _src = _session(tmp_path, FakeNer({"Claire Martin": "PERSON"}))
    assert [e.value for e in s.entities_for_cell("Clients", 1, 1)] == ["Leclerc"]
    assert s.entities_for_cell("Tiers", 0, 0)[0].value == "Claire Martin"


def test_column_override_is_per_sheet(tmp_path):
    """Une colonne s'entend « colonne de telle feuille » : forcer la colonne 0
    de Clients ne doit rien changer sur Tiers."""
    s, _src = _session(tmp_path, FakeNer({"Claire Martin": "PERSON"}))
    s.set_column_override(("Clients", 3), MASK, "ORG")
    assert s.count_retained("ORG") == 24
    assert s.entities_for_cell("Tiers", 0, 0)[0].type == "PERSON"


def test_clear_removes_a_typed_column(tmp_path):
    s, _src = _session(tmp_path)
    s.set_column_override(("Clients", 1), CLEAR)
    assert s.count_retained("PERSON") == 0


def test_apply_and_save_masks_and_preserves_the_rest(tmp_path):
    s, _src = _session(tmp_path, FakeNer({"Claire Martin": "PERSON"}))
    s.set_column_override(("Clients", 3), MASK, "ORG")
    out = tmp_path / "out.xlsx"
    report = s.apply_and_save(out)
    ws = openpyxl.load_workbook(out)["Clients"]
    assert ws.cell(row=1, column=2).value == "contact_nom"   # titres intacts
    assert ws.cell(row=2, column=2).value == "[PERSONNE]"
    assert ws.cell(row=2, column=3).value == "Industrie"     # nomenclature intacte
    assert ws.cell(row=2, column=4).value == "[ORG]"
    assert openpyxl.load_workbook(out)["Tiers"]["A1"].value == "Fournisseur [PERSONNE]"
    assert any(r["location"].startswith("Clients!") for r in report.to_rows())


def test_unchecked_value_stays_in_clear(tmp_path):
    s, _src = _session(tmp_path)
    s.set_value_enabled("PERSON", "Berger", False)
    out = tmp_path / "out.xlsx"
    s.apply_and_save(out)
    ws = openpyxl.load_workbook(out)["Clients"]
    assert ws.cell(row=3, column=2).value == "Berger"        # décochée
    assert ws.cell(row=2, column=2).value == "[PERSONNE]"


def test_has_column_guards_a_replayed_override(tmp_path):
    s, _src = _session(tmp_path)
    assert s.has_column(("Clients", 3)) is True
    assert s.has_column(("Clients", 99)) is False
    assert s.has_column(("Absente", 0)) is False
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_xlsx_review_session.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.core.xlsx_review_session'`.

- [ ] **Step 3 : écrire `anonymator/core/xlsx_review_session.py`**

```python
from anonymator.model import Entity
from anonymator.report.audit import AuditReport
from anonymator.files import xlsx_io
from anonymator.files.columns import SKIP
from anonymator.core.tabular_review_session import TabularReviewSession


class XlsxReviewSession(TabularReviewSession):
    """État de revue d'un classeur (non-Qt). Clé de cellule = (feuille, ligne,
    colonne), clé de colonne = (feuille, colonne).

    Même contrôle que le CSV, une dimension de plus : une colonne s'entend
    toujours « colonne de telle feuille », deux feuilles n'ayant aucune raison
    de partager un plan."""

    def __init__(self, result: xlsx_io.XlsxScanResult, ref):
        self.result = result
        plans = {(sheet, col): plan
                 for sheet, sheet_plans in result.plans.items()
                 for col, plan in sheet_plans.items()}
        maskable = {k for k, p in plans.items() if p.policy != SKIP}
        super().__init__(result.scanned, ref, maskable, plans)

    # --- clés ---
    def column_of(self, cell_key):
        sheet, _r, col = cell_key
        return (sheet, col)

    def has_column(self, col_key) -> bool:
        sheet, col = col_key
        matrix = self.result.matrices.get(sheet)
        if not matrix:
            return False
        return 0 <= col < max((len(r) for r in matrix), default=0)

    def column_values(self, col_key) -> dict:
        sheet, col = col_key
        matrix = self.result.matrices.get(sheet, [])
        start = 1 if self.result.has_header.get(sheet) else 0
        return {(sheet, r, col): matrix[r][col]
                for r in range(start, len(matrix)) if col < len(matrix[r])}

    # --- adaptateurs de signature ---
    def entities_for_cell(self, sheet: str, r: int, c: int) -> list[Entity]:
        return self._retained((sheet, r, c))

    def unconfirmed_for_cell(self, sheet: str, r: int, c: int) -> list[Entity]:
        return self._pending_at((sheet, r, c))

    def set_cell_excluded(self, sheet: str, r: int, c: int,
                          excluded: bool) -> None:
        super().set_cell_excluded((sheet, r, c), excluded)

    # --- production ---
    def apply_and_save(self, out_path) -> AuditReport:
        report = xlsx_io.apply_workbook(self.result, self.retained_by_cell(),
                                        self.ref)
        self.result.workbook.save(out_path)
        return report
```

- [ ] **Step 4 : lancer le test**

```bash
.venv/Scripts/python.exe -m pytest tests/test_xlsx_review_session.py -q
```

Attendu : `7 passed`.

- [ ] **Step 5 : commit**

```bash
git add anonymator/core/xlsx_review_session.py tests/test_xlsx_review_session.py
git commit -m "feat(revue xlsx): session de revue par feuille, ligne et colonne"
```

---

## Task 11 : `XlsxScanWorker`

**Files:**
- Create: `anonymator/ui/xlsx_scan_worker.py`
- Test: `tests/test_xlsx_scan_worker.py`

- [ ] **Step 1 : écrire le test rouge**

Créer `tests/test_xlsx_scan_worker.py` :

```python
import openpyxl
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.xlsx_scan_worker import XlsxScanWorker


def _book(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients"
    ws["A1"] = "contact_nom"; ws["B1"] = "ca_2025"
    for i in range(4):
        ws.cell(row=i + 2, column=1, value=["Leclerc", "Berger"][i % 2])
        ws.cell(row=i + 2, column=2, value=100 + i)
    wb.save(path)
    return path


def test_worker_emits_scan_result(qtbot, tmp_path):
    src = _book(tmp_path / "b.xlsx")
    worker = XlsxScanWorker(src, ModelLoader(FakeNer({})),
                            Referential.load_default())
    with qtbot.waitSignal(worker.scan_finished, timeout=10000) as blocker:
        worker.start()
    worker.wait()
    res = blocker.args[0]
    assert res.sheets == ["Clients"]
    assert ("Clients", 1, 0) in res.scanned


def test_worker_passes_header_overrides(qtbot, tmp_path):
    src = _book(tmp_path / "b.xlsx")
    worker = XlsxScanWorker(src, ModelLoader(FakeNer({})),
                            Referential.load_default(),
                            header_overrides={"Clients": False})
    with qtbot.waitSignal(worker.scan_finished, timeout=10000) as blocker:
        worker.start()
    worker.wait()
    assert blocker.args[0].has_header["Clients"] is False


def test_worker_reports_a_load_failure(qtbot, tmp_path):
    """Le détecteur est construit DANS le thread : un échec remonte via
    `error` au lieu d'exploser en silence sur le thread principal."""
    src = _book(tmp_path / "b.xlsx")

    class BoomLoader:
        def get(self):
            raise RuntimeError("échec chargement modèle")

    worker = XlsxScanWorker(src, BoomLoader(), Referential.load_default())
    with qtbot.waitSignal(worker.error, timeout=10000) as blocker:
        worker.start()
    worker.wait()
    assert "échec chargement modèle" in blocker.args[0]
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_xlsx_scan_worker.py -q
```

Attendu : `ModuleNotFoundError: No module named 'anonymator.ui.xlsx_scan_worker'`.

- [ ] **Step 3 : écrire `anonymator/ui/xlsx_scan_worker.py`**

```python
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from anonymator.files import xlsx_io


class XlsxScanWorker(QThread):
    """Lecture, classification et scan d'un classeur, hors thread UI.

    Un classeur de 100 000 lignes ne se lit pas sur le thread d'affichage :
    openpyxl à lui seul y prendrait plusieurs secondes, fenêtre gelée."""

    scan_finished = Signal(object)   # XlsxScanResult
    error = Signal(str)

    def __init__(self, path, loader, ref,
                 header_overrides: dict[str, bool] | None = None):
        super().__init__()
        self._path, self._loader, self._ref = Path(path), loader, ref
        self._headers = dict(header_overrides or {})

    def run(self):
        try:
            ner = self._loader.get()   # construction du détecteur DANS le thread
            self.scan_finished.emit(
                xlsx_io.scan_workbook(self._path, ner, self._ref, self._headers))
        except Exception as exc:  # noqa: BLE001 — remonté à l'UI via error
            self.error.emit(str(exc))
```

- [ ] **Step 4 : lancer le test**

```bash
.venv/Scripts/python.exe -m pytest tests/test_xlsx_scan_worker.py -q
```

Attendu : `3 passed`.

- [ ] **Step 5 : commit**

```bash
git add anonymator/ui/xlsx_scan_worker.py tests/test_xlsx_scan_worker.py
git commit -m "feat(ui): scan d'un classeur hors thread UI"
```

---

## Task 12 : la revue XLSX dans l'écran — grille, feuilles, pagination

**Files:**
- Modify: `anonymator/ui/file_screen.py`
- Modify: `tests/test_file_screen.py:161-165` (remplacement de `test_review_disabled_for_xlsx`)
- Test: `tests/test_file_screen_xlsx.py` (à créer)

- [ ] **Step 1 : écrire le test rouge**

Créer `tests/test_file_screen_xlsx.py` :

```python
from datetime import datetime
import openpyxl
from anonymator.referential import Referential
from anonymator.ner import FakeNer, NullNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.file_screen import FileScreen
from anonymator.core.xlsx_review_session import XlsxReviewSession
from anonymator.core.tabular_review_session import CLEAR, MASK


def _book(path, rows=24):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Clients"
    for c, h in enumerate(["code_client", "contact_nom", "secteur", "note"],
                          start=1):
        ws.cell(row=1, column=c, value=h)
    for i in range(rows):
        r = i + 2
        ws.cell(row=r, column=1, value="C%07d" % (i + 1))
        ws.cell(row=r, column=2, value=["Leclerc", "Berger", "Poirier"][i % 3])
        ws.cell(row=r, column=3, value=["Industrie", "BTP", "Textile"][i % 3])
        ws.cell(row=r, column=4, value="note %d" % i)
    ws2 = wb.create_sheet("Tiers")
    ws2["A1"] = "Fournisseur Claire Martin"
    wb.save(path)
    return path


def _screen(tmp_path, mapping=None):
    loader = ModelLoader(FakeNer(mapping or {}))
    return FileScreen(Referential.load_default(), loader,
                      Preferences(output_dir=str(tmp_path)), on_back=lambda: None)


def _reviewed(qtbot, tmp_path, rows=24, mapping=None):
    s = _screen(tmp_path, mapping)
    qtbot.addWidget(s)
    s.load_path(str(_book(tmp_path / "b.xlsx", rows)))
    assert s.btn_review.isEnabled()
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=15000)
    return s


def test_review_is_open_to_xlsx(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    assert isinstance(s.session, XlsxReviewSession)
    assert "PERSON" in s.session.types()


def test_grid_shows_the_first_sheet_with_its_headers(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    assert s.table.columnCount() == 4
    assert s.table.horizontalHeaderItem(1).text() == "contact_nom"
    assert s.table.item(0, 1).text() == "Leclerc"


def test_sheet_selector_switches_the_grid(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    assert [s.sheet_box.itemText(i) for i in range(s.sheet_box.count())] == [
        "Clients", "Tiers"]
    s.sheet_box.setCurrentText("Tiers")
    assert s.table.item(0, 0).text() == "Fournisseur Claire Martin"
    assert s.page == 0


def test_grid_paginates_a_long_sheet(qtbot, tmp_path):
    """_render_units_page ne pagine pas : une feuille de 100 000 lignes gèlerait
    l'interface. La grille, elle, pagine comme le CSV."""
    s = _reviewed(qtbot, tmp_path, rows=45)
    assert s._page_count() == 3
    s._go(99)
    assert s.page == 2
    assert s.table.rowCount() == 5
    s._go(0)
    assert s.table.rowCount() == 20


def test_highlighting_follows_the_session(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    assert s.table.item(0, 1).background().color().alpha() > 0    # PERSON
    assert s.table.item(0, 2).background().color().alpha() == 0   # nomenclature


def test_column_override_works_on_a_sheet(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.apply_column_override(3, MASK, "ORG")            # colonne « note »
    assert s.session.column_override(("Clients", 3)) == (MASK, "ORG")
    assert s.session.count_retained("ORG") == 24


def test_apply_writes_the_workbook(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path, mapping={"Claire Martin": "PERSON"})
    s.apply_column_override(0, CLEAR)                  # code_client hors périmètre
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    ws = openpyxl.load_workbook(res.output_path)["Clients"]
    assert ws.cell(row=1, column=2).value == "contact_nom"
    assert ws.cell(row=2, column=1).value == "C0000001"
    assert ws.cell(row=2, column=2).value == "[PERSONNE]"


def test_unchecking_a_value_updates_the_grid(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    s.session.set_value_enabled("PERSON", "Leclerc", False)
    s._render_current()
    assert s.table.item(0, 1).background().color().alpha() == 0


def test_perimeter_card_stays_hidden_for_xlsx(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    assert s.perimetre_card.isHidden()
```

Remplacer dans `tests/test_file_screen.py` le test `test_review_disabled_for_xlsx`
(l. 161-165) par :

```python
def test_review_enabled_for_xlsx(qtbot, tmp_path):
    """La revue est ouverte aux classeurs (chantier 3) : le bouton doit être
    actif dès le chargement, avant même toute lecture du fichier."""
    src = tmp_path / "f.xlsx"; src.write_bytes(b"PK\x03\x04stub")   # extension xlsx
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.btn_review.isEnabled() is True
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_screen_xlsx.py -q
```

Attendu : `AssertionError` sur `assert s.btn_review.isEnabled()`.

- [ ] **Step 3 : implémenter dans `anonymator/ui/file_screen.py`**

**(a)** Imports (à ajouter aux imports `anonymator`) :

```python
from anonymator.core.xlsx_review_session import XlsxReviewSession
from anonymator.ui.xlsx_scan_worker import XlsxScanWorker
```

**(b)** Dans `__init__`, à côté de `self._ooxml = None` :

```python
        self._xlsx = None            # XlsxScanResult de la revue en cours
        self._sheet: str | None = None
        self._sheet_headers: dict[str, bool] = {}   # choix explicites par feuille
```

**(c)** Sélecteur de feuille, dans `__init__`, juste avant
`table_card.head.addWidget(self.header_switch)` :

```python
        # Une feuille à la fois : la lecture tabulaire est l'objet même de la
        # revue, et concaténer les feuilles la perdrait.
        self.sheet_box = QComboBox()
        self.sheet_box.setObjectName("sheetBox")
        self.sheet_box.currentTextChanged.connect(self._on_sheet_changed)
        self.sheet_box.hide()
        table_card.head.addWidget(self.sheet_box)
```

**(d)** `load_path` : activer le bouton et remettre l'état classeur à zéro.
Remplacer les l. 203-226 par :

```python
    def load_path(self, path: str):
        self.path = Path(path)
        self.doc = None
        self.session = None
        self._ooxml = None
        self._xlsx = None
        self._sheet = None
        self._sheet_headers = {}
        self._view = "grid"
        self._pending_choices = None   # arbitrages d'un autre fichier : sans objet
        self.side.hide(); self.pager_widget.hide()
        self.occ_badge.hide(); self._hint.hide()
        self.sheet_box.hide()
        suffix = self.path.suffix.lower()
        self.btn_review.setEnabled(
            suffix in (".csv", ".txt", ".xlsx", ".docx", ".pptx"))
        if suffix == ".csv":
            self.doc = csv_io.read_csv(self.path)
            self.header_switch.blockSignals(True)     # reflet, pas une action
            self.header_switch.setChecked(self.doc.has_header)
            self.header_switch.blockSignals(False)
            self.header_switch.show()
            self._fill_preview(self.doc.rows[:50])
        else:
            # Un classeur n'est pas lu ici : sa grille apparaît avec l'analyse,
            # qui le charge hors thread UI (cf. XlsxScanWorker).
            self.header_switch.hide()
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
        self.perimetre_card.setVisible(False)
        self._set_meta()
```

**(e)** `analyze()` : brancher le classeur. Insérer, juste après le bloc
`.docx/.pptx` (avant `if self.doc is None:`) :

```python
        if self.path and self.path.suffix.lower() == ".xlsx":
            self._degraded = not (self.loader.has_detector() or is_model_available())
            loader = ModelLoader(NullNer()) if self._degraded else self.loader
            self._set_busy(True)
            self._worker = XlsxScanWorker(self.path, loader, self.ref,
                                          self._sheet_headers)
            self._worker.scan_finished.connect(self._on_xlsx_scanned)
            self._worker.error.connect(self._on_scan_error)
            self._worker.finished.connect(self._worker.deleteLater)
            self._worker.finished.connect(self._forget_worker)
            self._worker.start()
            return
```

**(f)** Gestionnaire de scan, à ajouter après `_on_scanned` :

```python
    def _on_xlsx_scanned(self, res):
        self._xlsx = res
        self._view = "grid"
        self.session = XlsxReviewSession(res, self.ref)
        self._restore_choices(self._pending_choices)
        self._pending_choices = None
        self._set_busy(False)
        self.banner.setVisible(self._degraded)
        self.occ_badge.setText(f"{_fmt_int(self.session.total_occurrences())} occ.")
        self.occ_badge.show(); self._hint.show()
        self.sheet_box.blockSignals(True)
        self.sheet_box.clear()
        self.sheet_box.addItems(res.sheets)
        self._sheet = res.sheets[0] if res.sheets else None
        self.sheet_box.blockSignals(False)
        self.sheet_box.show()
        self.header_switch.blockSignals(True)        # reflet, pas une action
        self.header_switch.setChecked(self._grid_has_header())
        self.header_switch.blockSignals(False)
        self.header_switch.show()
        self.page = 0
        self._build_side()
        self.side.show(); self.pager_widget.show()
        self.perimetre_card.hide()
        self._render_page()

    def _on_sheet_changed(self, title: str):
        if not title or self._xlsx is None:
            return
        self._sheet = title
        self.page = 0
        self.header_switch.blockSignals(True)
        self.header_switch.setChecked(self._grid_has_header())
        self.header_switch.blockSignals(False)
        self._render_page()
```

**(g)** Généraliser les accesseurs de grille (remplacer ceux posés en Task 7) :

```python
    # ---------- grille courante (CSV ou feuille de classeur) ----------
    def _grid_rows(self) -> list[list[str]]:
        if self._xlsx is not None:
            return self._xlsx.matrices.get(self._sheet, [])
        return self.doc.rows if self.doc is not None else []

    def _grid_has_header(self) -> bool:
        if self._xlsx is not None:
            return bool(self._xlsx.has_header.get(self._sheet, False))
        return bool(self.doc is not None and self.doc.has_header)

    def _cell_entities(self, r: int, c: int):
        if self._xlsx is not None:
            return self.session.entities_for_cell(self._sheet, r, c)
        return self.session.entities_for_cell(r, c)

    def _cell_unconfirmed(self, r: int, c: int):
        if self._xlsx is not None:
            return self.session.unconfirmed_for_cell(self._sheet, r, c)
        return self.session.unconfirmed_for_cell(r, c)
```

et remplacer `_column_key` (posé en Task 7) par :

```python
    def _column_key(self, col: int):
        """Clé de colonne pour la session : un index pour un CSV, un couple
        (feuille, index) pour un classeur — deux feuilles n'ont aucune raison
        de partager un plan."""
        return (self._sheet, col) if self._xlsx is not None else col
```

**(h)** `_data_rows` et `_render_page` sur la grille générique. Remplacer
`_data_rows` (l. 552-554) par :

```python
    def _data_rows(self):
        start = 1 if self._grid_has_header() else 0
        return list(range(start, len(self._grid_rows())))
```

et `_render_page` par :

```python
    def _render_page(self):
        if self.session is None:
            return
        grid = self._grid_rows()
        rows = self._data_rows()
        width = max((len(r) for r in grid), default=0)
        page_rows = rows[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        header = grid[0] if (grid and self._grid_has_header()) else None
        self.table.clear()
        self.table.setColumnCount(width)
        self.table.setRowCount(len(page_rows))
        # Les intitulés sont toujours posés : sans QTableWidgetItem d'en-tête,
        # il n'y a nulle part où accrocher l'infobulle ni le marqueur d'état.
        self.table.setHorizontalHeaderLabels(
            [header[c] if (header and c < len(header)) else f"col{c}"
             for c in range(width)])
        for vr, r in enumerate(page_rows):
            for c in range(width):
                val = grid[r][c] if c < len(grid[r]) else ""
                item = QTableWidgetItem(val)
                ents = self._cell_entities(r, c)
                if ents:
                    col = QColor(color_for(ents[0].type)); col.setAlpha(70)
                    item.setBackground(col)
                else:
                    # cellule sans entité retenue : signale les « non confirmées »
                    # (clé invalide) avec un fond atténué.
                    pend = self._cell_unconfirmed(r, c)
                    if pend:
                        col = QColor(color_for(pend[0].type)); col.setAlpha(28)
                        item.setBackground(col)
                self.table.setItem(vr, c, item)
        self._decorate_headers(width)
        last = self._page_count() - 1
        self.lbl_page.setText(f"Page {self.page + 1} / {self._page_count()}")
        self.btn_first.setEnabled(self.page > 0)
        self.btn_prev.setEnabled(self.page > 0)
        self.btn_next.setEnabled(self.page < last)
        self.btn_last.setEnabled(self.page < last)
```

**(i)** `_set_meta` ne suppose plus un CSV. Remplacer les l. 187-188 par :

```python
        if self.doc is not None:
            parts.append(f"{_fmt_int(len(self.doc.rows))} lignes")
        elif self._xlsx is not None:
            parts.append(f"{len(self._xlsx.sheets)} feuille(s)")
```

- [ ] **Step 4 : lancer les tests**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_screen_xlsx.py tests/test_file_screen.py tests/test_file_screen_columns.py -q
```

Attendu : tous verts.

- [ ] **Step 5 : commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen_xlsx.py tests/test_file_screen.py
git commit -m "feat(ui): revue des classeurs xlsx en grille, feuille par feuille"
```

---

## Task 13 : interrupteur « première ligne = en-têtes » par feuille

**Files:**
- Modify: `anonymator/ui/file_screen.py:253-281` (`_on_header_toggled`)
- Test: `tests/test_file_screen_xlsx.py` (ajout)

- [ ] **Step 1 : écrire le test rouge (ajout en fin de `tests/test_file_screen_xlsx.py`)**

```python
def test_header_switch_reflects_the_current_sheet(qtbot, tmp_path):
    s = _reviewed(qtbot, tmp_path)
    assert s.header_switch.isChecked() is True        # Clients a des titres
    s.sheet_box.setCurrentText("Tiers")
    assert s.header_switch.isChecked() is False       # une seule ligne


def test_header_switch_reanalyses_the_sheet(qtbot, tmp_path):
    """Un classeur ne peut pas se re-rendre sans rescan : le choix de
    l'utilisateur ne veut rien dire tant que les colonnes n'ont pas été
    reclassées."""
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    s = _reviewed(qtbot, tmp_path)
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    qtbot.waitUntil(lambda: s.session is not None and not s._busy, timeout=15000)
    assert s._xlsx.has_header["Clients"] is False
    assert s.table.item(0, 1).text() == "contact_nom"   # ligne 1 = donnée


def test_header_switch_can_be_declined(qtbot, tmp_path):
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    s = _reviewed(qtbot, tmp_path)
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.No):
        s.header_switch.setChecked(False)
    assert s.header_switch.isChecked() is True
    assert s._xlsx.has_header["Clients"] is True


def test_header_change_reports_manual_choices(qtbot, tmp_path):
    from unittest.mock import patch
    from PySide6.QtWidgets import QMessageBox
    s = _reviewed(qtbot, tmp_path)
    s.session.set_value_enabled("PERSON", "Berger", False)
    s.apply_column_override(3, MASK, "ORG")
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    qtbot.waitUntil(lambda: s.session is not None and not s._busy, timeout=15000)
    assert s.session.is_value_enabled("PERSON", "Berger") is False
    assert s.session.column_override(("Clients", 3)) == (MASK, "ORG")
```

- [ ] **Step 2 : lancer, vérifier l'échec**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_screen_xlsx.py -q
```

Attendu : échec sur `test_header_switch_reflects_the_current_sheet` ou
`test_header_switch_reanalyses_the_sheet` (le bouton ne pilote que `self.doc`).

- [ ] **Step 3 : implémenter**

Remplacer `_on_header_toggled` (l. 253-281) par :

```python
    def _on_header_toggled(self, checked: bool):
        """L'hypothèse d'en-tête décide du typage des colonnes, donc du
        périmètre : une revue faite sous l'ancienne hypothèse ne peut pas être
        rejouée telle quelle. Elle représente du travail manuel, on demande
        avant de la relancer, et on reporte les arbitrages sur la suivante."""
        if self._xlsx is not None:
            self._on_sheet_header_toggled(checked)
            return
        if self.doc is None:
            return
        if self.session is not None and not self._confirm_reanalysis():
            self.header_switch.blockSignals(True)
            self.header_switch.setChecked(not checked)   # retour à l'état
            self.header_switch.blockSignals(False)
            return
        if self.session is not None:
            self._pending_choices = self._capture_choices()
        self.doc.has_header = checked
        self.session = None
        self.side.hide(); self._hint.hide(); self.occ_badge.hide()
        self.pager_widget.hide()
        self.page = 0
        self._fill_preview(self.doc.rows[:50])
        self._set_meta()

    def _confirm_reanalysis(self) -> bool:
        answer = QMessageBox.question(
            self, "Relancer l'analyse ?",
            "Changer l'hypothèse d'en-tête modifie le périmètre des "
            "colonnes : l'analyse doit être relancée.\n\n"
            "Vos choix (valeurs, catégories et colonnes forcées) seront "
            "reportés sur la nouvelle analyse.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        return answer == QMessageBox.Yes

    def _on_sheet_header_toggled(self, checked: bool):
        """Côté classeur, l'analyse repart tout de suite. Un CSV sait
        re-afficher son aperçu sans rescan — ses lignes sont déjà en mémoire ;
        une feuille, elle, n'existe à l'écran que par le résultat du scan."""
        if self._sheet is None:
            return
        if self.session is not None and not self._confirm_reanalysis():
            self.header_switch.blockSignals(True)
            self.header_switch.setChecked(not checked)
            self.header_switch.blockSignals(False)
            return
        self._pending_choices = self._capture_choices()
        self._sheet_headers[self._sheet] = checked
        self.session = None
        self.analyze()
```

Note : après réanalyse, `_on_xlsx_scanned` remet `self._sheet` sur la première
feuille. Pour rester sur la feuille en cours, mémoriser le titre avant l'appel
et le restaurer. Ajouter dans `_on_sheet_header_toggled`, juste avant
`self.analyze()` :

```python
        self._sheet_to_restore = self._sheet
```

et à la fin de `_on_xlsx_scanned`, avant `self._render_page()`, remplacer
l'affectation de `self._sheet` en tête par ce bloc placé juste après
`self.sheet_box.addItems(res.sheets)` :

```python
        wanted = getattr(self, "_sheet_to_restore", None)
        self._sheet = (wanted if wanted in res.sheets
                       else (res.sheets[0] if res.sheets else None))
        self._sheet_to_restore = None
        if self._sheet is not None:
            self.sheet_box.setCurrentText(self._sheet)
```

Initialiser `self._sheet_to_restore = None` dans `__init__` à côté de
`self._sheet`, et le remettre à `None` dans `load_path`.

- [ ] **Step 4 : lancer les tests**

```bash
.venv/Scripts/python.exe -m pytest tests/test_file_screen_xlsx.py tests/test_file_screen.py -q
```

Attendu : tous verts.

- [ ] **Step 5 : commit**

```bash
git add anonymator/ui/file_screen.py tests/test_file_screen_xlsx.py
git commit -m "feat(ui): hypothese d'en-tete par feuille, avec relance de l'analyse"
```

---

## Task 14 : vérification sur le jeu de données de démonstration

**Files:**
- Create: `exemples/clients_demo.xlsx`
- Create: `tests/test_demo_dataset.py`

- [ ] **Step 1 : produire la conversion `.xlsx` du jeu de démonstration**

Le fichier `exemples/clients_demo.csv` (120 lignes, 19 colonnes mêlant
identités, nomenclatures et mesures) est le cas de référence du chantier
précédent. Sa conversion sert de cas de référence XLSX.

```bash
.venv/Scripts/python.exe -c "import csv, io, openpyxl; from pathlib import Path; p = Path('exemples/clients_demo.csv'); text = p.read_bytes().decode('utf-8-sig'); rows = list(csv.reader(io.StringIO(text, newline=''), delimiter=';')); wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Clients'; [ws.append(r) for r in rows]; wb.save('exemples/clients_demo.xlsx'); print('ok', ws.max_row, ws.max_column)"
```

Attendu : `ok 121 19`.

Les colonnes numériques restent des chaînes après cette conversion. Retyper
les mesures pour que le signal des types de cellules joue son rôle :

```bash
.venv/Scripts/python.exe -c "import openpyxl; wb = openpyxl.load_workbook('exemples/clients_demo.xlsx'); ws = wb.active; cols = {i for i, h in enumerate([c.value for c in ws[1]], start=1) if h in ('effectif', 'ca_2023', 'ca_2024', 'ca_2025')}; [setattr(ws.cell(row=r, column=c), 'value', int(ws.cell(row=r, column=c).value)) for r in range(2, ws.max_row + 1) for c in cols]; wb.save('exemples/clients_demo.xlsx'); print('retype', sorted(cols))"
```

Attendu : `retype [11, 15, 16, 17]`.

- [ ] **Step 2 : écrire le test de non-régression sur le jeu de démonstration**

Créer `tests/test_demo_dataset.py` :

```python
"""Le jeu de démonstration est le cas de référence du chantier : colonnes
d'identités, nomenclatures et mesures dans un même fichier, en CSV et en XLSX."""
from datetime import datetime
from pathlib import Path

import openpyxl
import pytest

from anonymator.referential import Referential
from anonymator.ner import NullNer
from anonymator.files import csv_io, xlsx_io
from anonymator.files.anonymize_file import csv_column_plans, scan_csv
from anonymator.files.columns import SKIP, TYPED, classify_columns
from anonymator.core.file_review_session import FileReviewSession
from anonymator.core.xlsx_review_session import XlsxReviewSession
from anonymator.core.tabular_review_session import CLEAR, MASK

CSV = Path("exemples/clients_demo.csv")
XLSX = Path("exemples/clients_demo.xlsx")

pytestmark = pytest.mark.skipif(not CSV.exists(),
                                reason="jeu de démonstration absent")


def _csv_session():
    doc = csv_io.read_csv(CSV)
    doc.has_header = True
    ref = Referential.load_default()
    plans = classify_columns(doc.rows, doc.has_header)
    scan_plans = csv_column_plans(doc)
    scanned = scan_csv(doc, NullNer(), ref, scan_plans)
    return FileReviewSession(doc, scanned, ref, set(scan_plans), plans)


def test_demo_csv_plan_separates_identities_measures_and_nomenclatures():
    s = _csv_session()
    header = s.doc.rows[0]
    by_name = {h: c for c, h in enumerate(header)}
    assert s.plans[by_name["contact_nom"]].policy == TYPED
    assert s.plans[by_name["telephone"]].policy == TYPED
    assert s.plans[by_name["ca_2025"]].policy == SKIP
    assert s.plans[by_name["statut"]].policy == SKIP


def test_demo_csv_column_override_masks_a_skipped_column(tmp_path):
    """Forcer une nomenclature écartée par le plan : 120 cellules masquées."""
    s = _csv_session()
    by_name = {h: c for c, h in enumerate(s.doc.rows[0])}
    col = by_name["secteur"]
    assert s.count_retained("ORG") == 0
    s.set_column_override(col, MASK, "ORG")
    assert s.count_retained("ORG") == 120
    out = tmp_path / "demo.csv"
    s.apply_and_save(out)
    lines = out.read_bytes().decode(s.doc.encoding).splitlines()
    assert lines[0].split(";")[col] == "secteur"          # titres intacts
    assert lines[1].split(";")[col] == "[ORG]"


def test_demo_csv_column_override_frees_a_typed_column(tmp_path):
    s = _csv_session()
    by_name = {h: c for c, h in enumerate(s.doc.rows[0])}
    s.set_column_override(by_name["email"], CLEAR)
    out = tmp_path / "demo.csv"
    s.apply_and_save(out)
    text = out.read_bytes().decode(s.doc.encoding)
    assert "sandra.leclerc@bureau-sablons.net" in text
    assert "[PERSONNE]" in text                            # le reste est traité


@pytest.mark.skipif(not XLSX.exists(), reason="conversion xlsx absente")
def test_demo_xlsx_reviews_like_the_csv(tmp_path):
    ref = Referential.load_default()
    res = xlsx_io.scan_workbook(XLSX, NullNer(), ref)
    s = XlsxReviewSession(res, ref)
    assert res.has_header["Clients"] is True
    assert "PERSON" in s.types() and "EMAIL" in s.types()
    header = res.matrices["Clients"][0]
    by_name = {h: c for c, h in enumerate(header)}
    assert s.plans[("Clients", by_name["ca_2025"])].policy == SKIP
    s.set_column_override(("Clients", by_name["secteur"]), MASK, "ORG")
    out = tmp_path / "demo.xlsx"
    s.apply_and_save(out)
    ws = openpyxl.load_workbook(out)["Clients"]
    col = by_name["secteur"] + 1
    assert ws.cell(row=1, column=col).value == "secteur"
    assert ws.cell(row=2, column=col).value == "[ORG]"
    assert ws.cell(row=2, column=by_name["contact_nom"] + 1).value == "[PERSONNE]"
    assert ws.cell(row=2, column=by_name["ca_2025"] + 1).value == 5230650
```

- [ ] **Step 3 : lancer le test**

```bash
.venv/Scripts/python.exe -m pytest tests/test_demo_dataset.py -q
```

Attendu : `4 passed`. En cas d'échec sur les noms de colonnes, relire
l'en-tête réel avec :

```bash
.venv/Scripts/python.exe -c "from pathlib import Path; print(Path('exemples/clients_demo.csv').read_bytes().decode('utf-8-sig').splitlines()[0])"
```

- [ ] **Step 4 : lancer la suite complète**

```bash
.venv/Scripts/python.exe -m pytest -q
```

Attendu : tout vert. Le compte doit avoir augmenté d'une cinquantaine de tests
par rapport aux ~529 de départ, sans aucun échec.

- [ ] **Step 5 : commit**

```bash
git add exemples/clients_demo.xlsx tests/test_demo_dataset.py
git commit -m "test(exemples): verification du chantier sur le jeu de demonstration"
```

---

## Task 15 : vérification manuelle dans l'application

**Files:** aucun (vérification)

- [ ] **Step 1 : lancer l'application**

```bash
.venv/Scripts/python.exe -m anonymator
```

Si ce point d'entrée n'existe pas, le retrouver avec :

```bash
.venv/Scripts/python.exe -c "import tomllib, pathlib; print(tomllib.loads(pathlib.Path('pyproject.toml').read_text(encoding='utf-8')).get('project', {}).get('scripts'))"
```

- [ ] **Step 2 : parcours CSV**

1. Ouvrir `exemples/clients_demo.csv`, cliquer « Analyser ».
2. Survoler l'en-tête `ca_2025` : l'infobulle doit dire « valeurs numériques ».
3. Survoler `statut` : « nomenclature (peu de valeurs distinctes) ».
4. Cliquer l'en-tête `secteur` → « Tout anonymiser » → « Organisation ».
   L'intitulé prend le marqueur 🔒, la colonne se surligne entièrement,
   `ORG` apparaît dans l'arbre et le compteur d'occurrences augmente.
5. Cliquer l'en-tête `contact_nom` → « Tout libérer » : le surlignage disparaît,
   le compteur baisse.
6. « Anonymiser & enregistrer », rouvrir le fichier produit et vérifier que
   `secteur` est masqué et `contact_nom` en clair.

- [ ] **Step 3 : parcours XLSX**

1. Ouvrir `exemples/clients_demo.xlsx`, cliquer « Analyser ».
2. La grille apparaît, sélecteur de feuille visible, pagination active
   (121 lignes → 6 pages).
3. Même essai de forçage de colonne que sur le CSV.
4. Décocher une valeur dans l'arbre : le surlignage de la grille suit.
5. Basculer « Première ligne = en-têtes » : le dialogue de confirmation
   apparaît, l'analyse repart, la feuille affichée reste la même.
6. « Anonymiser & enregistrer », rouvrir le classeur produit : mise en forme
   conservée, colonnes de mesures intactes, formules intactes.

- [ ] **Step 4 : consigner le résultat**

Si un écart est constaté, ne pas le corriger à la volée : écrire le test qui
le reproduit d'abord (convention TDD du dépôt), puis corriger.

- [ ] **Step 5 : commit final**

```bash
.venv/Scripts/python.exe -m pytest -q
git add -A
git commit -m "chore(chantier3): selection par colonne et revue xlsx"
```

---

## Auto-revue du plan face au prompt

| Exigence du prompt | Tâche |
|---|---|
| A. Trois états par colonne pilotés depuis l'en-tête | 3, 7 |
| État courant et `reason` lisibles (infobulle) | 7 (`_column_tooltip`, `_decorate_headers`) |
| « Tout anonymiser » via `pipeline.detect_column` | 3 (`set_column_override`) |
| Type « à choisir ou à déduire » | 3 (`default_type_for`), 5, 7 (sous-menu) |
| Override positionnel : décider s'il survit à l'en-tête, et le tester | 8 |
| B. Revue ouverte aux `.xlsx`, en grille | 9-13 |
| `xlsx_io` scindé scan/apply, `XlsxScanResult` complet | 9 |
| `XlsxReviewSession` clé (feuille, ligne, colonne) | 10 |
| `XlsxScanWorker` obligatoire | 11 |
| Sélecteur de feuille, pagination, surlignage | 12 |
| Interrupteur en-tête par feuille | 13 |
| Piège 1 — paginer la grille XLSX | 12 (`test_grid_paginates_a_long_sheet`) |
| Piège 2 — plus d'`isinstance` de session | 6 (`self._view`, `apply_and_save`) |
| Piège 3 — factoriser la comptabilité avant d'en ajouter une 3ᵉ | 1, 2 |
| Piège 4 — en-tête instable, interrupteur manuel | 13 |
| Piège 5 — `_data_rows`/`_page_count`/`_render_page` généralisés | 12 |
| Piège 6 — jamais réécrire une formule, ni la profiler | 9 (`test_apply_never_rewrites_a_formula`) |
| TDD, tests `pytest-qt`, français, ne pas toucher aux tests existants | toutes (une exception documentée : Task 12) |
| Vérifier sur `exemples/clients_demo.csv` et sa conversion `.xlsx` | 14, 15 |
| Hors périmètre : classification, docx/pptx, txt | non touchés |
