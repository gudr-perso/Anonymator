from datetime import datetime
from functools import partial
from pathlib import Path

import openpyxl

from anonymator.ner import NerDetector
from anonymator.referential import Referential
from anonymator.pipeline import detect, detect_column
from anonymator.anonymize import apply_masking
from anonymator.dedup import detect_unique
from anonymator.report.audit import AuditReport
from anonymator.output_naming import anonymized_path
from anonymator.files.columns import (
    SKIP, TYPED, classify_columns, looks_like_header_row)


def _is_formula(cell) -> bool:
    return cell.data_type == "f" or (isinstance(cell.value, str)
                                     and cell.value.startswith("="))


def _cell_text(cell) -> str:
    """Représentation texte d'une cellule pour la classification.

    Les formules comptent pour vides : leur source n'est pas une donnée, et
    elles ne doivent jamais peser sur le profil d'une colonne."""
    if cell.value is None or _is_formula(cell):
        return ""
    return str(cell.value)


def sheet_has_header(ws) -> bool:
    """Première ligne = en-têtes ?

    Contrairement au CSV, le classeur porte le type de chaque cellule : une
    ligne de titres est faite de texte, au-dessus d'au moins une colonne qui
    ne l'est pas. C'est un fait lu dans le fichier, pas une statistique — il
    reste donc le signal décisif, et un refus de sa part n'est jamais annulé.

    Il a un angle mort, et un seul : une feuille dont *toutes* les colonnes
    sont textuelles. Là, et là seulement, on regarde si la ligne 1 est faite
    de noms de colonnes connus (cf. columns.looks_like_header_row). Ce repli
    n'invente rien sur la forme des chaînes : il interroge le lexique qui
    pilote déjà le typage. Sans donnée en dessous, ou sans vocabulaire
    reconnu, la ligne est traitée comme une donnée — choix prudent : elle est
    analysée plutôt qu'ignorée."""
    rows = list(ws.iter_rows())
    if len(rows) < 2:
        return False
    first = [c for c in rows[0] if c.value is not None]
    if not first or not all(isinstance(c.value, str) and not _is_formula(c)
                            for c in first):
        return False
    if any(cell.value is not None and not isinstance(cell.value, str)
           for row in rows[1:] for cell in row):
        return True
    return looks_like_header_row([c.value for c in first])


def _sheet_matrix(ws) -> list[list[str]]:
    return [[_cell_text(c) for c in row] for row in ws.iter_rows()]


def anonymize_workbook(path: Path, ner: NerDetector, ref: Referential,
                       output_dir: Path, when: datetime) -> tuple[Path, AuditReport]:
    """Anonymise chaque feuille colonne par colonne.

    Le plan de traitement est décidé une fois par colonne (cf. columns.py) :
    une colonne typée est masquée en entier sans passer par le NER, une
    nomenclature ou une mesure reste intacte."""
    wb = openpyxl.load_workbook(path)
    report = AuditReport()
    for ws in wb.worksheets:
        rows = list(ws.iter_rows())
        if not rows:
            continue
        has_header = sheet_has_header(ws)
        plans = classify_columns(_sheet_matrix(ws), has_header)
        data_rows = rows[1:] if has_header else rows
        for col, plan in plans.items():
            if plan.policy == SKIP:
                continue
            if plan.policy == TYPED and plan.etype:
                detector = partial(detect_column, etype=plan.etype, ref=ref)
            else:
                detector = lambda v: detect(v, ner, ref)  # noqa: E731
            cells = [row[col] for row in data_rows
                     if col < len(row) and not _is_formula(row[col])
                     and row[col].value is not None]
            cache = detect_unique([_cell_text(c) for c in cells], detector)
            for cell in cells:
                value = _cell_text(cell)
                ents = cache.get(value, [])
                if not ents:
                    continue
                location = f"{ws.title}!{cell.coordinate}"
                for e in ents:
                    report.add(e.type, e.value, ref.tag_for(e.type), location)
                cell.value = apply_masking(value, ents, ref)
    out = anonymized_path(path, output_dir, when)
    wb.save(out)
    return out, report
