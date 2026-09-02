"""Lecture et anonymisation d'un .docx.

Le parcours se fait sur l'arbre XML, pas sur l'API `paragraphs`/`tables` de
python-docx. Trois raisons, toutes constatées sur des documents réels :

- `Paragraph.runs` n'expose que les <w:r> enfants directs : le texte d'un lien
  hypertexte lui échappe (cf. `xml_parts.paragraph_runs`) ;
- `container.paragraphs` ne voit que les <w:p> enfants directs du corps : les
  paragraphes d'un contrôle de contenu (<w:sdt>), omniprésents dans les
  modèles et formulaires, n'étaient jamais analysés ;
- `row.cells` répète le même objet cellule pour chaque colonne d'une fusion
  horizontale : la même cellule était masquée deux fois, et le second passage
  réappliquait les offsets d'origine sur un texte déjà masqué
  (« Mail [EMAIL] fin » → « Mail [EMAIL]s [EMA[EMAIL] »).

Un <w:tc> ou un <w:p> n'apparaissant qu'une fois dans l'arbre, parcourir le XML
règle les trois cas ensemble.
"""
from datetime import datetime
from pathlib import Path
from docx import Document
from anonymator.output_naming import anonymized_path
from anonymator.report.audit import AuditReport
from anonymator.files.ooxml import scan, xml_parts
from anonymator.files.ooxml.text_unit import TextUnit
from anonymator.files.ooxml.xml_parts import paragraph_runs

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_P = f"{{{_W}}}p"
_TBL = f"{{{_W}}}tbl"
_TR = f"{{{_W}}}tr"
_TC = f"{{{_W}}}tc"
_SDT = f"{{{_W}}}sdt"
_SDT_CONTENT = f"{{{_W}}}sdtContent"
_TXBX = f"{{{_W}}}txbxContent"


def _iter_container(element, location: str):
    """TextUnits des paragraphes et tableaux enfants de `element`.

    Descend dans les contrôles de contenu (<w:sdt>), laisse les zones de texte
    à `_iter_textboxes` — sans quoi elles seraient traitées deux fois."""
    for child in element:
        if child.tag == _P:
            runs = paragraph_runs(child)
            if runs:
                yield TextUnit(runs, location)
        elif child.tag == _TBL:
            yield from _iter_table(child, location)
        elif child.tag == _SDT:
            content = child.find(_SDT_CONTENT)
            if content is not None:
                yield from _iter_container(content, location)


def _iter_table(tbl, prefix: str):
    """Un parcours par <w:tc> réellement présent : une cellule fusionnée n'est
    visitée qu'une fois. Les tableaux imbriqués sont pris par la récursion de
    `_iter_container`."""
    base = "" if prefix == "Corps" else f"{prefix} / "
    for ri, tr in enumerate(tbl.findall(_TR), 1):
        for ci, tc in enumerate(tr.findall(_TC), 1):
            yield from _iter_container(tc, f"{base}Tableau L{ri}C{ci}")


def _iter_textboxes(element):
    for txbx in element.iter(_TXBX):
        yield from _iter_container(txbx, "Zone de texte")


def _headers_and_footers(section):
    """(objet, libellé) des en-têtes et pieds propres à la section.

    Word en distingue trois jeux — normal, première page, pages paires — et une
    donnée nominative peut ne figurer que sur la première page. Ceux hérités de
    la section précédente sont ignorés : leur contenu appartient à celle-ci et
    y est déjà traité."""
    parts = [(section.header, "En-tête"), (section.footer, "Pied")]
    for attr, label in (("first_page_header", "En-tête (1re page)"),
                        ("first_page_footer", "Pied (1re page)"),
                        ("even_page_header", "En-tête (pages paires)"),
                        ("even_page_footer", "Pied (pages paires)")):
        part = getattr(section, attr, None)
        if part is not None:
            parts.append((part, label))
    return [(p, label) for p, label in parts if not p.is_linked_to_previous]


def iter_main_units(doc):
    """Unités des conteneurs de la partie principale (sauvegardées nativement
    par doc.save) : corps, tableaux, en-têtes/pieds, zones de texte."""
    body = doc.element.body
    yield from _iter_container(body, "Corps")
    yield from _iter_textboxes(body)
    for section in doc.sections:
        for part, label in _headers_and_footers(section):
            element = part._element
            yield from _iter_container(element, label)
            yield from _iter_textboxes(element)


def anonymize_document(path: Path, ner, ref, output_dir: Path,
                       when: datetime) -> tuple[Path, AuditReport]:
    doc = Document(str(path))
    units = list(iter_main_units(doc))
    retained = scan.confirmed_only(scan.scan_units(units, ner, ref))
    report = scan.apply_units(units, retained, ref)
    out = anonymized_path(path, output_dir, when)
    doc.save(str(out))
    xml_parts.postprocess_docx(out, ner, ref, report)
    return out, report
