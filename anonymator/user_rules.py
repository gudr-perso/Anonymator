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
