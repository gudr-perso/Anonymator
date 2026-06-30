import re
from anonymator.model import Entity

# Jeton « secret » : suite sans espace ; on retire une ponctuation de fin (.!:).
_TOKEN = r"[^\s,;)\]]+(?<![.!:])"

# (?<!\w) empêche de matcher "passe"/"pass" À L'INTÉRIEUR d'un mot (impasse, bypass).
_PWD_KEYS = r"(?<!\w)(?:mots? de passe|mdp|password)"
_LOGIN_KEYS = (r"(?<!\w)(?:login|identifiant|utilisateur|username|"
               r"acc[eè]s au compte|connect[ée]\w*(?:\s+\w+){0,3}\s+avec)")
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
