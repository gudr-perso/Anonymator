"""Génère anonymator/ui/assets/anonymator.ico depuis picto.png."""
from pathlib import Path
from PIL import Image

src = Path(__file__).parent.parent / "anonymator" / "ui" / "assets" / "picto.png"
dst = src.with_name("anonymator.ico")

img = Image.open(src).convert("RGBA")
img.save(dst, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
print(f"Généré : {dst}")
