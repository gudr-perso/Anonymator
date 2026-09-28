import re
from anonymator.model import Entity
from anonymator.validators import (luhn_is_valid, iban_is_valid, nir_is_valid,
                                   bic_is_plausible, postal_code_fr_is_plausible,
                                   vat_fr_is_plausible)

# (pattern, type, validateur optionnel sur la valeur normalisée)
_UNCONFIRMABLE = {"IBAN", "NIR", "VAT"}   # format plausible conservé même si validation KO

_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "EMAIL", None),
    # Séparateurs internes : espace et espaces insécables seulement. Avec
    # \s, un numéro enjambe une tabulation ou un retour à la ligne et le
    # motif fabrique de faux téléphones dans un tableau dense en chiffres —
    # un FEC lu en .txt recolle ainsi la fin d'une colonne au début de la
    # suivante (« 01<TAB>20250106 »).
    (re.compile(r"(?:(?:\+33|0033)[ \u00a0\u202f]?|0)"
                r"[1-9](?:[ \u00a0\u202f.\-]?\d{2}){4}"),
     "PHONE", None),
    # TVA intracommunautaire FR : clé + SIREN, espaces tolérés. La regex IBAN
    # lit aussi « FR47404833048 », comme un IBAN invalide : la fusion garde la
    # TVA, validée, plutôt que l'IBAN seulement plausible.
    (re.compile(r"\bFR\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{3}\b"),
     "VAT", lambda v: vat_fr_is_plausible(v)),
    (re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{2,4}){2,8}\b"),
     "IBAN", lambda v: iban_is_valid(v)),
    (re.compile(r"\b[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"),
     "BIC", lambda v: bic_is_plausible(v)),
    (re.compile(r"\b\d{14}\b"), "SIRET", lambda v: luhn_is_valid(v)),
    (re.compile(r"\b\d{9}\b"), "SIREN", lambda v: luhn_is_valid(v)),
    (re.compile(r"\b[12]\s?\d{2}\s?\d{2}\s?(?:\d{2}|2[AB])\s?\d{3}\s?\d{3}\s?\d{2}\b"),
     "NIR", lambda v: nir_is_valid(v)),
    (re.compile(
        r"\b\d{1,4}(?:\s?(?:bis|ter|quater))?[,\s]+"
        r"(?:rue|avenue|av|ave|bd|bld|boulevard|impasse|all[ée]e|allee|"
        r"chemin|place|route|rte|quai|cours|passage|square|villa|voie|"
        r"faubourg|fbg|sentier|r[ée]sidence|residence)\b"
        # nom de voie : quelques mots après le type de voie, bornés. On
        # s'arrête à toute ponctuation (virgule, point, parenthèse…) et au
        # retour à la ligne, pour ne pas engloutir la phrase en prose.
        r"(?:[ \t]+[\w'’&-]+){0,5}",
        re.IGNORECASE),
     "ADDRESS", None),
    (re.compile(r"\b\d{5}\b"), "POSTAL_CODE",
     lambda v: postal_code_fr_is_plausible(v)),
    # Avec ou sans schéma : « www.exemple.fr » est la forme usuelle d'un pied
    # de page, et le domaine nomme souvent l'organisation. La ponctuation qui
    # clôt la phrase (point final, parenthèse, virgule) n'en fait pas partie.
    (re.compile(r"(?:https?://|\bwww\.)[^\s<>\"]*[^\s<>\".,;:!?)\]'’]"),
     "URL", None),
]


# Motifs à contexte obligatoire : la valeur seule est trop banale pour être
# masquée, c'est son voisinage qui en fait une donnée personnelle.
#
# Une date en est l'exemple : masquer toutes les dates rendrait illisible
# n'importe quelle facture ou compte rendu, alors qu'une date de naissance est
# un quasi-identifiant de premier ordre — avec le code postal et le sexe, elle
# suffit à ré-identifier une part importante de la population dans un fichier
# dont les noms ont pourtant été remplacés. On ne la retient donc que là où le
# texte dit ce qu'elle est. Le second chemin est l'en-tête de colonne
# (« date de naissance »), traité par files/columns.py.
_CONTEXTUAL_PATTERNS = [
    (re.compile(r"(?<!\w)(?:n[ée]e?\s+le|date\s+de\s+naissance|naissance)"
                r"\s*:?\s*"
                r"(\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}|\d{4}-\d{2}-\d{2})",
                re.IGNORECASE),
     "BIRTHDATE", None),
    # SIREN écrit par groupes de trois (« RCS Nantes 404 833 048 ») : sous cette
    # forme, seul le voisinage le distingue d'un montant.
    (re.compile(r"(?<!\w)(?:SIREN|R\.?C\.?S\.?(?:\s+[A-ZÀ-Ý][\w'’-]*){1,3})"
                r"\s*(?:n°|:)?\s*"
                r"(\d{3}[ \u00a0]\d{3}[ \u00a0]\d{3})(?!\d)"),
     "SIREN", luhn_is_valid),
    # SIRET écrit par groupes (« SIRET : 404 833 048 00022 ») : même raison que
    # ci-dessus, hors contexte la suite de chiffres ne se distingue pas d'un
    # montant et la masquer rendrait un FEC illisible. L'OCR et les documents
    # bureautiques écrivent pourtant presque toujours les numéros espacés. La
    # forme collée, elle, reste captée sans contexte par \b\d{14}\b.
    (re.compile(r"(?<!\w)SIRET\s*(?:n°|:)?\s*"
                r"(\d{3}[  ]\d{3}[  ]\d{3}[  ]\d{5})(?!\d)"),
     "SIRET", luhn_is_valid),
]


_WHITESPACE = re.compile(r"\s+")


def _longest_valid_prefix(value: str, validator) -> str | None:
    """Le plus long préfixe de `value` qui passe la validation, coupé à une
    frontière de blanc — ou None si aucun ne passe.

    Les motifs à clé de contrôle sont gloutons. Celui de l'IBAN est une suite
    de groupes `[A-Z0-9]{2,4}` séparés par un blanc **optionnel** : deux
    groupes consécutifs peuvent donc absorber un mot voisin, et « FR76 … 189
    SIRET » est lu d'un bloc. La clé échoue alors, l'entité passe en « non
    confirmée » et n'est pas masquée par défaut — alors qu'un IBAN parfaitement
    valide se trouve là. Le saut de ligne n'y est pour rien : le même mot
    accolé sur la même ligne produit le même effet.

    Rendre None laisse l'appelant sur le comportement d'origine (valeur
    entière, non confirmée) : cette passe ne masque jamais moins qu'avant."""
    for m in reversed(list(_WHITESPACE.finditer(value))):
        candidate = value[:m.start()]
        if validator(candidate):
            return candidate
    return None


def detect_deterministic(text: str) -> list[Entity]:
    found: list[Entity] = []
    for pattern, etype, validator in _CONTEXTUAL_PATTERNS:
        for m in pattern.finditer(text):
            if validator is not None and not validator(m.group(1)):
                continue
            found.append(Entity(etype, m.group(1), m.start(1), m.end(1),
                                "deterministic", 1.0))
    for pattern, etype, validator in _PATTERNS:
        for m in pattern.finditer(text):
            value, start, end = m.group(0), m.start(), m.end()
            confirmed = True
            if validator is not None and not validator(value):
                if etype in _UNCONFIRMABLE:
                    # Avant de renoncer : le motif a-t-il absorbé un mot voisin ?
                    shorter = _longest_valid_prefix(value, validator)
                    if shorter is not None:
                        value, end = shorter, start + len(shorter)
                    else:
                        confirmed = False      # format OK, clé/checksum KO
                else:
                    continue                   # autres types : rejet pur
            found.append(Entity(etype, value, start, end,
                                 "deterministic", 1.0, confirmed))
    return found
