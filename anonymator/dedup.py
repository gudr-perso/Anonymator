from typing import Callable
from anonymator.model import Entity

def detect_unique(
    values: list[str],
    detect: Callable[[str], list[Entity]],
) -> dict[str, list[Entity]]:
    """Lance `detect` une fois par valeur unique. Retourne {valeur: entités}.

    Les offsets (start/end) des entités retournées sont relatifs à la chaîne
    `value` elle-même, pas à un document englobant : un appelant qui réutilise
    ces entités (ex. mode fichier) doit appliquer le masquage sur la valeur de
    cellule, ou re-baser les offsets sur la position de la cellule.
    """
    cache: dict[str, list[Entity]] = {}
    for value in values:
        if value not in cache:
            cache[value] = detect(value)
    return cache
