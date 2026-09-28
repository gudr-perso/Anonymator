# anonymator/files/image/layout.py
"""Reconstruit une couche de texte positionné depuis des boîtes OCR.

L'OCR rend des boîtes sans ordre garanti. GLiNER, lui, se nourrit du contexte :
la qualité de ce texte plat conditionne directement la détection des noms. On
regroupe donc les boîtes en lignes, puis on lit gauche→droite, haut→bas —
exactement ce que fait extract_page() côté PDF.

LIMITE CONNUE — mise en page en colonnes. `extract_page()` dispose des blocs
que PyMuPDF lit dans le PDF ; l'OCR, lui, ne rend que des boîtes isolées. Deux
colonnes côte à côte sont donc lues comme une seule ligne, en alternance. Les
rectangles restent justes — le caviardage ne rate rien — mais le texte plat est
entrelacé, ce qui affaiblit GLiNER, qui vit du contexte. Les détecteurs
déterministes (e-mail, IBAN, téléphone) ne sont pas touchés : ils reposent sur
des motifs internes au mot. Comportement épinglé par un test."""
from anonymator.files.image.ocr import OcrBox
from anonymator.files.textlayer import PageText, WordBox

# Deux boîtes appartiennent à la même ligne si leur chevauchement vertical
# dépasse cette fraction de la plus petite des deux hauteurs. Assez bas pour
# tolérer des tailles de police inégales, assez haut pour ne pas fusionner
# deux lignes voisines serrées.
_LINE_OVERLAP_RATIO = 0.5


def _same_line(a: OcrBox, b: OcrBox) -> bool:
    top = max(a.rect[1], b.rect[1])
    bottom = min(a.rect[3], b.rect[3])
    overlap = bottom - top
    if overlap <= 0:
        return False
    shortest = min(a.rect[3] - a.rect[1], b.rect[3] - b.rect[1])
    return shortest > 0 and overlap / shortest >= _LINE_OVERLAP_RATIO


def _group_lines(boxes: list[OcrBox]) -> list[list[OcrBox]]:
    """Regroupe en lignes, puis trie chaque ligne gauche→droite et les lignes
    haut→bas."""
    lines: list[list[OcrBox]] = []
    for box in sorted(boxes, key=lambda b: (b.rect[1], b.rect[0])):
        for line in lines:
            if _same_line(line[0], box):
                line.append(box)
                break
        else:
            lines.append([box])
    for line in lines:
        line.sort(key=lambda b: b.rect[0])
    lines.sort(key=lambda line: min(b.rect[1] for b in line))
    return lines


def page_from_boxes(boxes: list[OcrBox], page_index: int = 0) -> PageText:
    """Texte plat en ordre de lecture + une WordBox par boîte OCR."""
    parts: list[str] = []
    words: list[WordBox] = []
    cursor = 0
    for line_no, line in enumerate(_group_lines(boxes)):
        for word_no, box in enumerate(line):
            if line_no or word_no:
                parts.append("\n" if word_no == 0 else " ")
                cursor += 1
            start = cursor
            parts.append(box.text)
            cursor += len(box.text)
            words.append(WordBox(box.text, box.rect, start, cursor))
    return PageText(page_index, "".join(parts), words)
