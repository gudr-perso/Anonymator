# anonymator/files/pdf/extract.py
from dataclasses import dataclass
from pathlib import Path
import fitz

MIN_CHARS_PER_PAGE = 10   # < ce seuil de caractères extractibles / page → scanné


class ScannedPdfNotSupported(Exception):
    pass


class EncryptedPdfError(Exception):
    pass


class CorruptPdfError(Exception):
    pass


@dataclass
class WordBox:
    text: str
    rect: tuple[float, float, float, float]   # (x0, y0, x1, y1) en points PDF
    char_start: int                            # offset inclusif dans le texte plat
    char_end: int                              # offset exclusif


@dataclass
class PageText:
    page_index: int
    text: str                # texte plat reconstruit en ordre de lecture
    words: list[WordBox]


def open_document(path: Path) -> "fitz.Document":
    try:
        doc = fitz.open(str(path))
    except Exception as exc:   # noqa: BLE001 — traduit en erreur métier claire
        raise CorruptPdfError("Fichier PDF illisible ou endommagé") from exc
    if doc.needs_pass:
        doc.close()
        raise EncryptedPdfError("PDF protégé par mot de passe : non supporté")
    return doc


def ensure_native(doc: "fitz.Document") -> None:
    """Lève ScannedPdfNotSupported si aucune page n'a de couche texte."""
    for page in doc:
        if len(page.get_text().strip()) >= MIN_CHARS_PER_PAGE:
            return
    raise ScannedPdfNotSupported(
        "PDF scanné : reconnaissance de texte (OCR) non supportée pour l'instant")


def _block_is_vertical(block_words) -> bool:
    """Vrai si les mots (≥2 car.) du bloc sont majoritairement plus hauts
    que larges — signe d'un texte de marge pivoté."""
    votes = total = 0
    for x0, y0, x1, y1, text, *_ in block_words:
        if len(text) < 2:
            continue
        total += 1
        if (y1 - y0) > (x1 - x0):
            votes += 1
    return total > 0 and votes * 2 > total


def _ordered_words(words):
    """Regroupe par bloc, ordonne les blocs horizontaux haut→bas/gauche→droite,
    relègue les blocs verticaux en fin, conserve (ligne, mot) dans chaque bloc."""
    blocks: dict[int, list] = {}
    for w in words:
        blocks.setdefault(w[5], []).append(w)
    horizontal, vertical = [], []
    for bw in blocks.values():
        y0 = min(w[1] for w in bw)
        x0 = min(w[0] for w in bw)
        (vertical if _block_is_vertical(bw) else horizontal).append((y0, x0, bw))
    horizontal.sort(key=lambda e: (round(e[0] / 10) * 10, e[1]))
    vertical.sort(key=lambda e: (e[1], e[0]))
    ordered: list = []
    for _y, _x, bw in horizontal + vertical:
        ordered.extend(sorted(bw, key=lambda w: (w[6], w[7])))
    return ordered


def extract_page(page: "fitz.Page", page_index: int) -> PageText:
    """Reconstruit le texte plat en ordre de lecture + une WordBox par mot."""
    ordered = _ordered_words(page.get_text("words"))  # (x0,y0,x1,y1,mot,bloc,ligne,n°)
    parts: list[str] = []
    boxes: list[WordBox] = []
    cursor = 0
    prev_line: tuple[int, int] | None = None
    for x0, y0, x1, y1, text, block, line, _wno in ordered:
        line_key = (block, line)
        if prev_line is not None and line_key != prev_line:
            parts.append("\n"); cursor += 1
        elif parts:
            parts.append(" "); cursor += 1
        start = cursor
        parts.append(text); cursor += len(text)
        boxes.append(WordBox(text, (x0, y0, x1, y1), start, cursor))
        prev_line = line_key
    return PageText(page_index, "".join(parts), boxes)


def extract_pages(doc: "fitz.Document") -> list[PageText]:
    return [extract_page(page, i) for i, page in enumerate(doc)]
