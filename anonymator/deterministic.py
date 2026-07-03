import re
from anonymator.model import Entity
from anonymator.validators import luhn_is_valid, iban_is_valid, nir_is_valid, bic_is_plausible, postal_code_fr_is_plausible

# (pattern, type, validateur optionnel sur la valeur normalisée)
_UNCONFIRMABLE = {"IBAN", "NIR"}   # format plausible conservé même si validation KO

_PATTERNS = [
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "EMAIL", None),
    (re.compile(r"(?:(?:\+33|0033)\s?|0)[1-9](?:[\s.\-]?\d{2}){4}"),
     "PHONE", None),
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
    (re.compile(r"https?://[^\s]+"), "URL", None),
]


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
