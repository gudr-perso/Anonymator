"""Marque de distribution — surcouche du thème.

Une « marque » fige, pour un exécutable diffusé, le thème imposé, le nom de
produit affiché et le nom du fichier exe. Le mode dev (défaut) n'est pas
verrouillé : le thème vient des préférences et le sélecteur de thème reste
visible dans les réglages.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Brand:
    key: str
    theme: str | None       # None en dev : le thème vient des préférences
    product_name: str       # nom affiché (titre, en-tête, à propos)
    exe_name: str           # nom du fichier exe / dossier dist
    icon: str               # fichier .ico dans anonymator/ui/assets
    locked: bool


BRANDS = {
    "cuma": Brand("cuma", "cuma", "Cum'Anonyme", "cumanonyme", "anonymator.ico", True),
    "cap":  Brand("cap",  "cap",  "CAP'nonyme",  "capnonyme",  "anonymator.ico", True),
}

DEV_BRAND = Brand("dev", None, "Anonymator", "anonymator", "anonymator.ico", False)

_active = DEV_BRAND


def lock_brand(key: str) -> None:
    """Fige la marque active. À appeler AVANT de construire la fenêtre."""
    global _active
    _active = BRANDS[key]


def reset_brand() -> None:
    """Rétablit le mode dev non verrouillé (isolation des tests)."""
    global _active
    _active = DEV_BRAND


def active_brand() -> Brand:
    return _active


def is_locked() -> bool:
    return _active.locked


def build_target(build_brand: str) -> tuple[str, str, str]:
    """(script d'entrée, nom d'exe, icône) pour un build PyInstaller.

    `build_brand` ∈ {"cap", "cuma", "dev"} ; toute valeur inconnue → dev.
    Lu par `anonymator.spec` depuis la variable d'env ANONYMATOR_BUILD_BRAND.
    """
    b = BRANDS.get(build_brand)
    if b is not None:
        return (f"anonymator/brands/{b.key}.py", b.exe_name, b.icon)
    return ("anonymator/__main__.py", DEV_BRAND.exe_name, DEV_BRAND.icon)
