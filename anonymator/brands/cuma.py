"""Point d'entrée verrouillé — marque CUMA (Cum'Anonyme)."""
from anonymator.brand import lock_brand
from anonymator.__main__ import main


def run() -> int:
    lock_brand("cuma")
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
