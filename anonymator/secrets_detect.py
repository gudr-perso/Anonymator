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
