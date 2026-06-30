from typing import Callable
from anonymator.model import Entity

def detect_unique(
    values: list[str],
    detect: Callable[[str], list[Entity]],
) -> dict[str, list[Entity]]:
    """Lance `detect` une fois par valeur unique. Retourne {valeur: entités}."""
    cache: dict[str, list[Entity]] = {}
    for value in values:
        if value not in cache:
            cache[value] = detect(value)
    return cache
