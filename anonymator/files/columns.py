"""Classification des colonnes d'un tableau (CSV/XLSX) avant détection.

Une colonne est homogène par construction : c'est une information bien plus
fiable que le score d'un modèle NER sur une cellule isolée, qui n'a ni phrase
ni en-tête pour se situer. On décide donc une fois par colonne :

- TYPED : le type est connu (en-tête explicite, ou contenu homogène) ; toute
  la cellule est l'entité, sans passer par le NER ;
- TEXT  : colonne libre, détection normale (règles + NER) ;
- SKIP  : hors périmètre (mesures numériques, nomenclatures).
"""
import re
import unicodedata
from dataclasses import dataclass

from anonymator.deterministic import detect_deterministic

SKIP = "skip"
TEXT = "text"
TYPED = "typed"

# Une colonne n'est considérée comme nomenclature qu'au-delà de ce nombre de
# lignes : sous ce seuil, peu de valeurs distinctes ne prouve rien.
_CARDINALITY_MIN_ROWS = 20
_CARDINALITY_RATIO = 0.15
# Plafond en valeur absolue : une nomenclature a une poignée de modalités.
# Sans lui, un même client répété sur des milliers d'écritures passerait pour
# un axe d'analyse et sortirait du périmètre.
_CARDINALITY_MAX_DISTINCT = 15
# Part des cellules non vides devant correspondre au même type pour typer une
# colonne sur son contenu.
_HOMOGENEITY_RATIO = 0.6
# Profilage du contenu : échantillon suffisant pour trancher, borne le coût
# sur les gros fichiers.
_PROFILE_SAMPLE = 500


@dataclass(frozen=True)
class ColumnPlan:
    policy: str
    etype: str | None = None
    reason: str = ""


def looks_structured(value: str) -> bool:
    """Vrai si la valeur ne contient aucune lettre (nombre, date, code, vide)."""
    return not any(ch.isalpha() for ch in value)


def normalize_header(header: str) -> str:
    """Minuscules, sans accents, camelCase séparé, ponctuation → espace."""
    header = unicodedata.normalize("NFKD", header)
    header = "".join(c for c in header if not unicodedata.combining(c))
    header = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", header)
    header = re.sub(r"[^0-9A-Za-z]+", " ", header)
    return " ".join(header.lower().split())


# Types techniques : reconnus avant le garde-fou « identifiant », car
# « code postal » ou « num tel » contiennent code/num sans être des clés.
_TECHNICAL = [
    (r"\b(code\s+postal|cp)\b", "POSTAL_CODE"),
    (r"\b(e\s*mail|email|mail|courriel)\b", "EMAIL"),
    (r"\b(tel|telephone|portable|mobile|gsm|fax)\b", "PHONE"),
    (r"\b(iban|rib)\b", "IBAN"),
    (r"\b(bic|swift)\b", "BIC"),
    (r"\b(nir|secu|securite\s+sociale)\b", "NIR"),
    (r"\bsiret\b", "SIRET"),
    (r"\bsiren\b", "SIREN"),
    (r"\b(url|site\s+web)\b", "URL"),
]

# Clés de jointure et références internes : masquer une telle colonne casse le
# fichier sans rien protéger. On laisse la détection normale s'en charger.
_IDENTIFIER = r"\b(code|id|ident|num|numero|ref|reference|matricule|cle|clef)\b"

_SEMANTIC = [
    (r"\b(adresse|rue|voie|domicile|ville|commune|localite)\b", "ADDRESS"),
    (r"\b(raison\s+sociale|societe|entreprise|client|fournisseur|organisme|"
     r"etablissement|enseigne|denomination|partenaire)\b", "ORG"),
    (r"\b(nom|prenom|contact|interlocuteur|responsable|commercial|gerant|"
     r"beneficiaire|patient|eleve|salarie|employe|collaborateur)\b", "PERSON"),
]


# Vocabulaire qui nomme une colonne sans porter de type : ni identité, ni
# identifiant. Sert uniquement à reconnaître une ligne de titres.
_NEUTRAL = (
    r"\b(date|montant|quantite|qte|total|libelle|designation|statut|etat|"
    r"categorie|type|nature|commentaire|note|observation|compte|journal|"
    r"exercice|periode|annee|mois|jour|taux|prix|tarif|unite|remise|solde|"
    r"debit|credit|echeance|produit|article|famille|marque|gamme|pays|region|"
    r"departement|secteur|activite|effectif|taille|source|canal|origine|"
    r"quantité|ht|ttc|tva)\b"
)


def header_type(header: str) -> str | None:
    """Type d'entité déduit du nom de colonne, None si non reconnu."""
    norm = normalize_header(header)
    if not norm:
        return None
    for pattern, etype in _TECHNICAL:
        if re.search(pattern, norm):
            return etype
    if re.search(_IDENTIFIER, norm):
        return None
    for pattern, etype in _SEMANTIC:
        if re.search(pattern, norm):
            return etype
    return None


def is_column_name(header: str) -> bool:
    """Vrai si la chaîne appartient au vocabulaire des noms de colonnes.

    S'appuie sur les dictionnaires qui pilotent déjà le typage, pas sur la
    forme de la chaîne : c'est un fait sur notre propre lexique, vérifiable et
    modifiable, et non une seconde couche de devinette."""
    norm = normalize_header(header)
    if not norm:
        return False
    if header_type(header) is not None:
        return True
    return bool(re.search(_IDENTIFIER, norm) or re.search(_NEUTRAL, norm))


def looks_like_header_row(cells: list[str]) -> bool:
    """Vrai si la ligne est faite de noms de colonnes.

    Dernier recours, à n'employer que là où aucun signal fiable n'existe (une
    feuille dont toutes les colonnes sont textuelles). Trois conditions
    cumulatives, calibrées pour se taire plutôt que se tromper : au moins deux
    intitulés reconnus — un seul peut être une coïncidence —, la moitié de la
    ligne au minimum, et des noms tous distincts."""
    filled = [c for c in cells if c.strip()]
    if len(filled) < 2:
        return False
    if len({normalize_header(c) for c in filled}) != len(filled):
        return False
    recognised = sum(1 for c in filled if is_column_name(c))
    return recognised >= 2 and recognised * 2 >= len(filled)


def full_match_type(value: str) -> str | None:
    """Type dont une entité couvre la cellule entière, None sinon.

    Le plein-cadre écarte les faux positifs de sous-chaîne : « 15866,00 »
    contient bien cinq chiffres, mais n'est pas un code postal."""
    stripped = value.strip()
    if not stripped:
        return None
    start = len(value) - len(value.lstrip())
    end = start + len(stripped)
    for e in detect_deterministic(value):
        if e.start == start and e.end == end:
            return e.type
    return None


def dominant_full_match_type(values: list[str]) -> str | None:
    """Type couvrant au moins `_HOMOGENEITY_RATIO` des cellules non vides."""
    filled = [v for v in values if v.strip()][:_PROFILE_SAMPLE]
    if not filled:
        return None
    counts: dict[str, int] = {}
    for v in filled:
        etype = full_match_type(v)
        if etype:
            counts[etype] = counts.get(etype, 0) + 1
    if not counts:
        return None
    etype, n = max(counts.items(), key=lambda kv: kv[1])
    return etype if n >= _HOMOGENEITY_RATIO * len(filled) else None


def _is_nomenclature(values: list[str]) -> bool:
    """Une poignée de modalités sur beaucoup de lignes : c'est un axe d'analyse
    (secteur, statut, catégorie), pas une identité.

    Les deux critères sont nécessaires. Le ratio seul écarterait à tort une
    colonne de noms de clients dans un grand livre, où chaque client revient
    sur des centaines d'écritures ; le plafond absolu seul écarterait à tort
    une petite table dont chaque ligne est distincte."""
    filled = [v for v in values if v.strip()]
    if len(filled) < _CARDINALITY_MIN_ROWS:
        return False
    distinct = len(set(filled))
    return (distinct <= _CARDINALITY_MAX_DISTINCT
            and distinct <= max(2, _CARDINALITY_RATIO * len(filled)))


def classify_columns(rows: list[list[str]],
                     has_header: bool) -> dict[int, ColumnPlan]:
    """Plan de traitement pour chaque colonne du tableau."""
    data = rows[1:] if has_header else rows
    width = max((len(r) for r in rows), default=0)
    plans: dict[int, ColumnPlan] = {}
    for col in range(width):
        values = [r[col] for r in data if col < len(r)]
        if not any(v.strip() for v in values):
            plans[col] = ColumnPlan(SKIP, reason="colonne vide")
            continue

        if has_header and col < len(rows[0]):
            etype = header_type(rows[0][col])
            if etype:
                plans[col] = ColumnPlan(TYPED, etype, "en-tête « %s »"
                                        % rows[0][col].strip())
                continue

        if all(looks_structured(v) for v in values):
            etype = dominant_full_match_type(values)
            plans[col] = (ColumnPlan(TYPED, etype, "contenu homogène")
                          if etype else
                          ColumnPlan(SKIP, reason="valeurs numériques"))
            continue

        if _is_nomenclature(values):
            plans[col] = ColumnPlan(SKIP, reason="nomenclature (peu de valeurs "
                                                 "distinctes)")
            continue

        plans[col] = ColumnPlan(TEXT, reason="texte libre")
    return plans


def default_maskable_columns(rows: list[list[str]], has_header: bool) -> set[int]:
    """Colonnes retenues dans le périmètre d'analyse par défaut."""
    return {col for col, plan in classify_columns(rows, has_header).items()
            if plan.policy != SKIP}
