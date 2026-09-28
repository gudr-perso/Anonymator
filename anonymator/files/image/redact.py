# anonymator/files/image/redact.py
"""Caviardage destructif d'une image.

Les pixels sont ÉCRASÉS dans le tampon, jamais recouverts par un calque : une
forme dessinée par-dessus se retire, un pixel noirci ne se retrouve pas."""
from PIL import Image, ImageDraw

Rect = tuple[float, float, float, float]

FILL = (0, 0, 0)


def redact_image(img: Image.Image, rects: list[Rect]) -> Image.Image:
    """Rend une copie dont chaque rectangle est écrasé en noir opaque.
    L'image reçue n'est pas modifiée."""
    out = img.convert("RGB").copy()
    if not rects:
        return out
    draw = ImageDraw.Draw(out)
    width, height = out.size
    for x0, y0, x1, y1 in rects:
        left = max(0, int(min(x0, x1)))
        top = max(0, int(min(y0, y1)))
        right = min(width, int(round(max(x0, x1))))
        bottom = min(height, int(round(max(y0, y1))))
        if right > left and bottom > top:
            draw.rectangle([left, top, right - 1, bottom - 1], fill=FILL)
    return out
