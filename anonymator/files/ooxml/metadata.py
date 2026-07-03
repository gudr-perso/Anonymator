from lxml import etree

_DC = "http://purl.org/dc/elements/1.1/"
_CP = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
_EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"

# (namespace, balise, libellé audit)
_CORE_FIELDS = [
    (_DC, "creator", "Auteur"),
    (_CP, "lastModifiedBy", "Dernier modifié par"),
    (_DC, "title", "Titre"),
    (_DC, "subject", "Sujet"),
    (_CP, "keywords", "Mots-clés"),
    (_DC, "description", "Commentaires"),
    (_CP, "category", "Catégorie"),
]
_APP_FIELDS = [
    (_EP, "Company", "Société"),
    (_EP, "Manager", "Manager"),
]


def _purge(xml_bytes: bytes, fields) -> tuple[bytes, list[tuple[str, str]]]:
    root = etree.fromstring(xml_bytes)
    purged: list[tuple[str, str]] = []
    for ns, tag, label in fields:
        el = root.find(f"{{{ns}}}{tag}")
        if el is not None and (el.text or "").strip():
            purged.append((label, el.text))
            el.text = ""
    out = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                         standalone=True)
    return out, purged


def purge_core_xml(xml_bytes: bytes) -> tuple[bytes, list[tuple[str, str]]]:
    return _purge(xml_bytes, _CORE_FIELDS)


def purge_app_xml(xml_bytes: bytes) -> tuple[bytes, list[tuple[str, str]]]:
    return _purge(xml_bytes, _APP_FIELDS)
