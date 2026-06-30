import unicodedata


def normalize(text: str) -> str:
    """Minuscule, accents retirés, espaces compactés — pour comparaisons robustes."""
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(no_accents.lower().split())
