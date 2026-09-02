_CANDIDATES = ("utf-8", "cp1252")
_LAST_RESORT = "latin-1"


def detect_encoding(data: bytes) -> str:
    """Encodage sous lequel `data` se décode *réellement*.

    cp1252 laisse cinq octets non définis (0x81, 0x8D, 0x8F, 0x90, 0x9D) : le
    renvoyer sans vérifier ne repoussait le problème que d'une ligne, et
    l'UnicodeDecodeError remontait jusqu'au dialogue « Erreur inattendue »
    quand l'appelant décodait. latin-1 accepte tout octet : il ferme la porte,
    au prix de quelques caractères fantaisistes sur un fichier vraiment exotique
    — un fichier lisible reste toujours préférable à un plantage.
    """
    for enc in _CANDIDATES:
        try:
            data.decode(enc)
        except UnicodeDecodeError:
            continue
        return enc
    return _LAST_RESORT
