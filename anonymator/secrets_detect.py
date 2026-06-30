import re
from anonymator.model import Entity

# Jeton « secret » : suite sans espace, on s'arrête à la ponctuation de fin usuelle.
_TOKEN = r"[^\s,;)\]]+(?<![.])"   # autorise . interne, pas en fin

_PWD_KEYS = r"(?:mot de passe|mots de passe|mdp|password|pass(?:e)?)"
_LOGIN_KEYS = (r"(?:login|identifiant|utilisateur|user(?:name)?|"
               r"acc[eè]s au compte|connect[ée]\w*(?:\s+\w+)*\s+avec)")
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
