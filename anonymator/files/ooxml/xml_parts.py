import zipfile
from pathlib import Path
from lxml import etree
from anonymator.report.audit import AuditReport
from anonymator.files.ooxml import scan, metadata
from anonymator.files.ooxml.text_unit import TextUnit

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


class XmlRun:
    """Adaptateur « run » sur un élément <w:r>/<a:r> : lit/écrit son texte
    (concaténation des <w:t>/<a:t>). L'écriture va dans le premier nœud texte,
    vide les suivants, et pose xml:space=preserve si le texte a des espaces
    en bordure."""

    def __init__(self, r_element, t_tag: str = f"{{{_W}}}t"):
        self._r = r_element
        self._t_tag = t_tag

    def _texts(self):
        return self._r.findall(self._t_tag)

    @property
    def text(self) -> str:
        return "".join((t.text or "") for t in self._texts())

    @text.setter
    def text(self, value: str) -> None:
        ts = self._texts()
        if not ts:
            return
        ts[0].text = value
        if value != value.strip():
            ts[0].set(_XML_SPACE, "preserve")
        for extra in ts[1:]:
            extra.text = ""


def paragraph_runs(p_element, t_tag: str = f"{{{_W}}}t") -> list[XmlRun]:
    """Les <w:r> du paragraphe, dans l'ordre du document.

    Ne pas se contenter des enfants directs : le texte d'un lien hypertexte est
    enveloppé dans <w:hyperlink>, celui d'une insertion suivie dans <w:ins>.
    Word crée un <w:hyperlink> dès qu'une adresse e-mail est saisie — ce texte,
    invisible pour `findall`, ressortait donc en clair du document anonymisé.

    On s'arrête aux zones de texte (<w:txbxContent>) : elles ont leur propre
    passe, et les compter ici décalerait les offsets du paragraphe porteur."""
    runs: list[XmlRun] = []
    r_tag, txbx_tag = f"{{{_W}}}r", f"{{{_W}}}txbxContent"

    def walk(element) -> None:
        for child in element:
            if child.tag == txbx_tag:
                continue
            if child.tag == r_tag:
                runs.append(XmlRun(child, t_tag))
            else:
                walk(child)

    walk(p_element)
    return runs


def _word_units_from_container(container, location: str) -> list[TextUnit]:
    """Un TextUnit par <w:p> descendant."""
    units = []
    for p in container.iter(f"{{{_W}}}p"):
        runs = paragraph_runs(p)
        if runs:
            units.append(TextUnit(runs, location))
    return units


def _comment_units(root) -> list[TextUnit]:
    units = []
    for n, comment in enumerate(root.findall(f"{{{_W}}}comment"), 1):
        units += _word_units_from_container(comment, f"Commentaire {n}")
    return units


def _footnote_units(root, label: str) -> list[TextUnit]:
    tag = "footnote" if label == "Note" else "endnote"
    units = []
    n = 0
    for note in root.findall(f"{{{_W}}}{tag}"):
        # Ignore les notes de séparateur (type "separator"/"continuationSeparator").
        ntype = note.get(f"{{{_W}}}type")
        if ntype in ("separator", "continuationSeparator"):
            continue
        n += 1
        units += _word_units_from_container(note, f"{label} {n}")
    return units


def _read_zip(path: Path) -> tuple[list[str], dict[str, bytes]]:
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        return names, {n: z.read(n) for n in names}


def _write_zip(path: Path, names: list[str], data: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            z.writestr(n, data[n])


def _purge_metadata(data: dict[str, bytes], report: AuditReport) -> None:
    for name, purge in (("docProps/core.xml", metadata.purge_core_xml),
                        ("docProps/app.xml", metadata.purge_app_xml)):
        if name in data:
            new_bytes, purged = purge(data[name])
            if purged:
                data[name] = new_bytes
                for label, old in purged:
                    report.add("META", old, "", f"Métadonnées / {label}")


def postprocess_docx(path: Path, ner, ref, report: AuditReport) -> AuditReport:
    """Masque commentaires/notes (entités confirmées) + purge métadonnées,
    dans le .docx déjà écrit. Réécrit le zip. Complète `report`."""
    names, data = _read_zip(path)
    part_extractors = {
        "word/comments.xml": _comment_units,
        "word/footnotes.xml": lambda root: _footnote_units(root, "Note"),
        "word/endnotes.xml": lambda root: _footnote_units(root, "Note de fin"),
    }
    for name, extract in part_extractors.items():
        if name not in data:
            continue
        root = etree.fromstring(data[name])
        units = extract(root)
        retained = scan.confirmed_only(scan.scan_units(units, ner, ref))
        if retained:
            scan.apply_units(units, retained, ref, report)
            data[name] = etree.tostring(root, xml_declaration=True,
                                        encoding="UTF-8", standalone=True)
    _purge_metadata(data, report)
    _write_zip(path, names, data)
    return report


def postprocess_metadata(path: Path, report: AuditReport) -> AuditReport:
    """Purge des métadonnées seules (pptx). Réécrit le zip. Complète `report`."""
    names, data = _read_zip(path)
    _purge_metadata(data, report)
    _write_zip(path, names, data)
    return report
