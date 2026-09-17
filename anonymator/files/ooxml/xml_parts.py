"""Parcours et réécriture des parties XML d'une archive OOXML.

Règle de lecture de ce module : **tout ce qui n'est pas reconstruit ici sort du
fichier tel qu'il y est entré**, `_write_zip` recopiant les autres entrées octet
pour octet. Une partie oubliée n'est donc pas « non couverte », elle est
diffusée. C'est ce qui justifie de traiter explicitement trois choses que le
corps du document ne laisse pas voir :

- la **cible** des liens hypertexte, qui vit dans les fichiers de relations et
  non dans `document.xml` — Word y range l'adresse complète dès qu'un e-mail est
  saisi, alors que le texte affiché peut être quelconque ;
- les **attributs d'auteur** des révisions et des commentaires, que la purge des
  métadonnées ne touche pas : un document dépersonnalisé qui nomme encore chaque
  relecteur ne l'est pas ;
- les parties `customXml/`, magasin de données des contrôles de contenu liés.
"""
import zipfile
from pathlib import Path
from lxml import etree
from anonymator.report.audit import AuditReport
from anonymator.files.ooxml import scan, metadata, xmlsafe
from anonymator.files.ooxml.text_unit import TextUnit

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

_W_T = f"{{{_W}}}t"
_W_DEL_TEXT = f"{{{_W}}}delText"
_W_INSTR_TEXT = f"{{{_W}}}instrText"

# Balises de texte d'un <w:r> qui appartiennent au flux de la phrase.
# <w:delText> en fait partie : le texte supprimé en révision suivie reste dans
# le fichier et Word le réaffiche en mode « Afficher les marques ». Ne lire que
# <w:t> le laissait ressortir en clair — précisément la donnée que l'auteur
# croyait avoir retirée.
_WORD_TEXT_TAGS = (_W_T, _W_DEL_TEXT)

# Analyse durcie : cf. xmlsafe. Le XML vient d'un fichier reçu d'un tiers.
_parse, _serialize = xmlsafe.parse, xmlsafe.serialize


class XmlRun:
    """Adaptateur « run » sur un élément <w:r>/<a:r> : lit/écrit son texte
    (concaténation de ses nœuds de texte). L'écriture va dans le premier nœud,
    vide les suivants, et pose xml:space=preserve si le texte a des espaces
    en bordure."""

    def __init__(self, r_element, t_tags=_WORD_TEXT_TAGS):
        self._r = r_element
        self._t_tags = (t_tags,) if isinstance(t_tags, str) else tuple(t_tags)

    def _texts(self):
        # Parcours des enfants directs plutôt que `findall` par balise : un run
        # peut mêler <w:t> et <w:delText>, et deux `findall` concaténés les
        # rendraient groupés par balise, donc hors de l'ordre du document.
        return [c for c in self._r if c.tag in self._t_tags]

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


class AttrRun:
    """Adaptateur « run » sur un attribut d'élément (cible d'une relation).

    Permet de passer une adresse de lien dans le même pipeline que du texte :
    même détection, même masquage, même ligne de rapport d'audit."""

    def __init__(self, element, attribute: str):
        self._el, self._attr = element, attribute

    @property
    def text(self) -> str:
        return self._el.get(self._attr) or ""

    @text.setter
    def text(self, value: str) -> None:
        self._el.set(self._attr, value)


class NodeRun:
    """Adaptateur « run » sur le nœud texte d'un élément quelconque."""

    def __init__(self, element):
        self._el = element

    @property
    def text(self) -> str:
        return self._el.text or ""

    @text.setter
    def text(self, value: str) -> None:
        self._el.text = value


def paragraph_runs(p_element, t_tags=_WORD_TEXT_TAGS) -> list[XmlRun]:
    """Les <w:r> du paragraphe, dans l'ordre du document.

    Ne pas se contenter des enfants directs : le texte d'un lien hypertexte est
    enveloppé dans <w:hyperlink>, celui d'une insertion suivie dans <w:ins>,
    celui d'une suppression dans <w:del>. Word crée un <w:hyperlink> dès qu'une
    adresse e-mail est saisie — ce texte, invisible pour `findall`, ressortait
    donc en clair du document anonymisé.

    On s'arrête aux zones de texte (<w:txbxContent>) : elles ont leur propre
    passe, et les compter ici décalerait les offsets du paragraphe porteur."""
    runs: list[XmlRun] = []
    r_tag, txbx_tag = f"{{{_W}}}r", f"{{{_W}}}txbxContent"

    def walk(element) -> None:
        for child in element:
            if child.tag == txbx_tag:
                continue
            if child.tag == r_tag:
                runs.append(XmlRun(child, t_tags))
            else:
                walk(child)

    walk(p_element)
    return runs


def field_units(element, location: str = "Champ") -> list[TextUnit]:
    """Un TextUnit par run porteur d'une instruction de champ (<w:instrText>).

    Traité à part du flux visible, et non ajouté au paragraphe porteur : une
    instruction (` HYPERLINK "mailto:…" `, ` MERGEFIELD `, ` INCLUDETEXT
    \\\\serveur\\RH\\… `) n'est pas lue par le lecteur. L'injecter dans le
    paragraphe décalerait ses offsets et donnerait au modèle un contexte qui
    n'existe pas. Elle porte pourtant régulièrement une adresse ou un chemin
    réseau, invisibles à la relecture."""
    units: list[TextUnit] = []
    for r in element.iter(f"{{{_W}}}r"):
        if any(c.tag == _W_INSTR_TEXT for c in r):
            units.append(TextUnit([XmlRun(r, (_W_INSTR_TEXT,))], location))
    return units


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


# --- relations externes -------------------------------------------------

# Schémas dont la cible peut porter une donnée nominative. Une relation interne
# (image, style, en-tête) pointe vers une autre partie de l'archive : rien à y lire.
_TARGET_SCHEMES = ("mailto:", "http://", "https://", "ftp://", "file:", "\\\\")


def _relationship_units(root) -> list[TextUnit]:
    """Un TextUnit par cible de relation externe susceptible de porter une
    donnée : adresse e-mail d'un lien `mailto:`, chemin réseau d'un document lié."""
    units = []
    for rel in root:
        target = (rel.get("Target") or "").strip()
        if not target.lower().startswith(_TARGET_SCHEMES):
            continue
        units.append(TextUnit([AttrRun(rel, "Target")], "Cible de lien"))
    return units


def _xml_text_units(root, location: str) -> list[TextUnit]:
    """Un TextUnit par nœud texte non vide de la partie."""
    return [TextUnit([NodeRun(el)], location)
            for el in root.iter()
            if isinstance(el.tag, str) and (el.text or "").strip()]


# --- auteurs ------------------------------------------------------------

# Attributs d'identité, reconnus par nom local quel que soit l'espace de noms :
# w:author sur <w:ins>/<w:del>/<w:comment>, w15:author sur <w15:person>
# (word/people.xml), a:author sur un commentaire PowerPoint.
_AUTHOR_LOCALS = ("author", "initials")


def _purge_authors(root, report: AuditReport) -> bool:
    """Neutralise les attributs d'auteur. Renvoie True si quelque chose a changé.

    La purge des métadonnées ne voit pas ces attributs : elle traite
    `docProps/`, eux vivent dans le corps du document et dans people.xml. Sans
    cela, un document dont l'auteur a été retiré nomme encore chaque relecteur
    et chaque commentateur, ce qui révèle qui a écrit quoi."""
    changed = False
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        for name, value in list(el.attrib.items()):
            if name.split("}")[-1] not in _AUTHOR_LOCALS:
                continue
            if not (value or "").strip():
                continue
            report.add("META", value, "", "Métadonnées / Auteur de révision")
            el.set(name, "")
            changed = True
    return changed


# --- archive ------------------------------------------------------------

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


def _units_for_part(name: str, root) -> list[TextUnit]:
    """Unités de texte d'une partie donnée, [] si rien n'y est à lire."""
    if name.endswith(".rels"):
        return _relationship_units(root)
    if name.startswith("customXml/") and "/_rels/" not in name:
        return _xml_text_units(root, "Données XML liées")
    if name == "word/comments.xml":
        return _comment_units(root)
    if name == "word/footnotes.xml":
        return _footnote_units(root, "Note")
    if name == "word/endnotes.xml":
        return _footnote_units(root, "Note de fin")
    if name.startswith("word/") and name.endswith(".xml"):
        # document.xml, header*.xml, footer*.xml : le texte visible est déjà
        # traité en amont par docx_io, mais pas les instructions de champ.
        return field_units(root)
    return []


def _is_xml_part(name: str) -> bool:
    return name.endswith(".xml") or name.endswith(".rels")


def _postprocess(path: Path, ner, ref, report: AuditReport) -> AuditReport:
    """Reprend l'archive déjà écrite : masque ce que le parcours du corps ne
    voit pas, neutralise les auteurs, purge les métadonnées, réécrit le zip."""
    names, data = _read_zip(path)
    for name in names:
        if not _is_xml_part(name) or name.startswith("docProps/"):
            continue
        try:
            root = _parse(data[name])
        except etree.XMLSyntaxError:
            continue          # partie illisible : recopiée telle quelle
        changed = False
        units = _units_for_part(name, root)
        if units:
            retained = scan.confirmed_only(scan.scan_units(units, ner, ref))
            if retained:
                scan.apply_units(units, retained, ref, report)
                changed = True
        if _purge_authors(root, report):
            changed = True
        if changed:
            data[name] = _serialize(root)
    _purge_metadata(data, report)
    _write_zip(path, names, data)
    return report


def postprocess_docx(path: Path, ner, ref, report: AuditReport) -> AuditReport:
    """Masque commentaires/notes/champs, les cibles de lien et les données XML
    liées, neutralise les auteurs et purge les métadonnées du .docx déjà écrit."""
    return _postprocess(path, ner, ref, report)


def postprocess_pptx(path: Path, ner, ref, report: AuditReport) -> AuditReport:
    """Même passe pour une présentation : cibles de lien, données XML liées,
    auteurs de commentaires et métadonnées."""
    return _postprocess(path, ner, ref, report)


def postprocess_metadata(path: Path, report: AuditReport) -> AuditReport:
    """Purge des métadonnées seules. Conservé pour les appels qui n'ont ni
    détecteur ni référentiel sous la main."""
    names, data = _read_zip(path)
    _purge_metadata(data, report)
    _write_zip(path, names, data)
    return report
