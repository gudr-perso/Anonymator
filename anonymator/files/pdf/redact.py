# anonymator/files/pdf/redact.py
"""Caviardage d'un PDF et nettoyage de ce qui n'est pas dans le flux de page.

`apply_redactions` détruit réellement le texte du flux de contenu, ce qui est
l'essentiel. Mais trois porteurs de données vivent ailleurs dans le fichier et
y survivent intacts :

- **la valeur d'un champ de formulaire**, rangée dans l'objet du widget et non
  dans le flux. Elle est pourtant extraite par `get_text`, donc détectée,
  affichée à la revue et cochée par l'utilisateur : sans la vider ici, la donnée
  ressort d'un document que l'application vient de présenter comme caviardé ;
- **le contenu et l'auteur des annotations**, invisibles à l'aperçu de revue
  puisque l'extraction ne lit que les mots de la page ;
- **les pièces jointes embarquées et les titres de signets**, que `garbage=4`
  ne supprime pas : ils sont référencés depuis le catalogue, donc pas orphelins.
"""
from pathlib import Path
import fitz

from anonymator.anonymize import apply_masking
from anonymator.pipeline import detect
from anonymator.report.audit import AuditReport

Rect = tuple[float, float, float, float]

# Types d'annotation qui portent la saisie de l'utilisateur. Le widget (champ de
# formulaire) est traité à part : il se vide, il ne se supprime pas.
_WIDGET = getattr(fitz, "PDF_ANNOT_WIDGET", 19)


def _clear_widgets(page: "fitz.Page", boxes: list["fitz.Rect"]) -> int:
    """Vide les champs de formulaire recoupant une zone caviardée.

    On se limite aux champs effectivement visés : l'utilisateur a coché des
    entités, pas décidé de vider tout le formulaire. Un champ intact hors zone
    reste donc rempli, comme le reste du texte non coché."""
    cleared = 0
    for widget in list(page.widgets() or []):
        if not any(widget.rect.intersects(b) for b in boxes):
            continue
        if not (widget.field_value or ""):
            continue
        # Affecter la chaîne vide ne prend pas : PyMuPDF ignore une valeur
        # fausse et laisse `/V` intact, donc la donnée reste dans le fichier
        # (vérifié en 1.28). Une espace, elle, est bien écrite et régénère le
        # flux d'apparence sans le texte.
        widget.field_value = " "
        widget.update()
        try:
            # Affinage : `/V` réellement vide plutôt qu'une espace. Passe par
            # l'objet brut, faute d'API publique pour le faire. Sans effet sur
            # la fuite, déjà traitée ci-dessus — d'où le garde silencieux.
            page.parent.xref_set_key(widget.xref, "V", "()")
        except Exception:   # noqa: BLE001 — API bas niveau, absente ailleurs
            pass
        cleared += 1
    return cleared


def redact_page(page: "fitz.Page", rects: list[Rect]) -> None:
    """Marque chaque rectangle pour rédaction puis applique — destruction réelle
    du texte dans le flux du PDF (pas un simple masque visuel).

    Les champs de formulaire visés sont vidés avant : `apply_redactions` ne
    touche pas à leur valeur, qui vit hors du flux de page."""
    boxes = [fitz.Rect(*r) for r in rects]
    _clear_widgets(page, boxes)
    for box in boxes:
        page.add_redact_annot(box, fill=(0, 0, 0))
    images = getattr(fitz, "PDF_REDACT_IMAGE_REMOVE", None)
    if images is None:
        page.apply_redactions()
    else:
        # Une image incluse dans une zone caviardée est retirée, pas seulement
        # recouverte : sinon le bitmap d'origine reste extractible du fichier.
        page.apply_redactions(images=images)


def scrub_annotations(doc: "fitz.Document", ner, ref,
                      report: AuditReport) -> None:
    """Masque le contenu des annotations et efface le nom de leur auteur.

    Une annotation n'est jamais proposée à la revue : son texte n'appartient pas
    au flux de page, donc l'extraction ne le voit pas. On applique donc ici les
    seules entités confirmées, comme pour les commentaires d'un .docx — une
    donnée invisible à l'écran ne peut pas être arbitrée à l'écran."""
    for index, page in enumerate(doc, 1):
        for annot in list(page.annots() or []):
            if annot.type[0] == _WIDGET:
                continue                  # champ de formulaire : cf. _clear_widgets
            info = annot.info
            content = info.get("content") or ""
            author = info.get("title") or ""
            changes = {}
            if content.strip():
                ents = [e for e in detect(content, ner, ref) if e.confirmed]
                if ents:
                    for e in ents:
                        report.add(e.type, e.value, ref.tag_for(e.type),
                                   f"page {index} / Annotation")
                    changes["content"] = apply_masking(content, ents, ref)
            if author.strip():
                report.add("META", author, "", "Métadonnées / Auteur d'annotation")
                # Une espace, pas la chaîne vide : PyMuPDF ignore une valeur
                # fausse et laisse le champ intact (même piège que pour la
                # valeur d'un champ de formulaire, cf. `_clear_widgets`).
                changes["title"] = " "
            if changes:
                annot.set_info(**changes)
                annot.update()


def scrub_toc(doc: "fitz.Document", ner, ref, report: AuditReport) -> None:
    """Masque les titres de signets. « Dossier de Claire Petit » nomme la
    personne dans le volet de navigation, sans jamais paraître sur une page."""
    toc = doc.get_toc()
    if not toc:
        return
    changed = False
    for entry in toc:
        title = entry[1] or ""
        if not title.strip():
            continue
        ents = [e for e in detect(title, ner, ref) if e.confirmed]
        if not ents:
            continue
        for e in ents:
            report.add(e.type, e.value, ref.tag_for(e.type), "Signet")
        entry[1] = apply_masking(title, ents, ref)
        changed = True
    if changed:
        doc.set_toc(toc)


def drop_embedded_files(doc: "fitz.Document", report: AuditReport) -> None:
    """Retire les pièces jointes embarquées.

    Leur contenu est opaque — c'est souvent le tableur source du rapport — donc
    ni analysable ni masquable. Elles voyagent avec le PDF et s'extraient en
    deux clics dans un lecteur : les laisser reviendrait à diffuser le fichier
    source à côté du document caviardé."""
    for name in list(doc.embfile_names() or []):
        doc.embfile_del(name)
        report.add("META", name, "", "Pièce jointe retirée")


def purge_metadata(doc: "fitz.Document") -> None:
    """Vide les métadonnées document et le bloc XML (XMP)."""
    doc.set_metadata({})
    try:
        doc.del_xml_metadata()
    except Exception:   # noqa: BLE001 — absent sur certains PDF, sans gravité
        pass


def save_redacted(doc: "fitz.Document", out_path: Path) -> None:
    """Sauvegarde avec nettoyage (garbage collection des objets orphelins)."""
    doc.save(str(out_path), garbage=4, deflate=True, clean=True)
