# tests/test_pdf_io.py
from datetime import datetime
import fitz
import pytest
from tests.pdf_fixtures import (make_native_pdf, make_scanned_pdf,
                                make_repeat_pdf)
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.model import Entity
from anonymator.files.pdf import pdf_io
from anonymator.files.pdf.extract import ScannedPdfNotSupported


def _ref():
    return Referential.load_default()


def test_scan_pdf_returns_pagescan_with_entities(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    pages = pdf_io.scan_pdf(src, FakeNer({"Claire Martin": "PERSON"}), _ref())
    assert len(pages) == 1
    ps = pages[0]
    assert ps.page_index == 0
    assert any(e.type == "PERSON" and e.value == "Claire Martin" for e in ps.entities)
    assert ps.words   # les boîtes sont conservées pour le mapping


def test_scan_pdf_rejects_scanned(tmp_path):
    src = make_scanned_pdf(tmp_path / "s.pdf")
    with pytest.raises(ScannedPdfNotSupported):
        pdf_io.scan_pdf(src, FakeNer({}), _ref())


def test_anonymize_pdf_text_writes_masked_txt(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    res = pdf_io.anonymize_pdf_text(src, FakeNer({"Claire Martin": "PERSON"}),
                                    _ref(), tmp_path, datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".txt"
    out = res.output_path.read_text(encoding="utf-8")
    assert "[PERSONNE]" in out and "Claire Martin" not in out


def test_anonymize_pdf_redact_destroys_and_saves(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    pages = pdf_io.scan_pdf(src, FakeNer({"Claire Martin": "PERSON"}), _ref())
    ps = pages[0]
    from anonymator.files.pdf import mapping
    ent = next(e for e in ps.entities if e.value == "Claire Martin")
    rects = mapping.rects_for_entity(_page_text(ps), ent)
    out = pdf_io.anonymize_pdf_redact(src, {0: rects}, tmp_path,
                                      datetime(2026, 1, 2, 3, 4, 5))
    assert out.suffix == ".pdf"
    check = fitz.open(str(out))
    assert "Claire Martin" not in check[0].get_text()
    check.close()


def test_anonymize_pdf_text_from_session_honors_decochage(tmp_path):
    """Mode texte via la session : une valeur décochée reste en clair dans le .txt."""
    from anonymator.core.pdf_review_session import PdfReviewSession
    src = make_native_pdf(tmp_path / "n.pdf",
                          "Contact Claire Martin et Jean Dupont ici")
    pages = pdf_io.scan_pdf(
        src, FakeNer({"Claire Martin": "PERSON", "Jean Dupont": "PERSON"}), _ref())
    session = PdfReviewSession(pages, _ref())
    session.set_value_enabled("PERSON", "Jean Dupont", False)
    res = pdf_io.anonymize_pdf_text_from_session(
        src, session, tmp_path, datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".txt"
    out = res.output_path.read_text(encoding="utf-8")
    assert "Jean Dupont" in out            # décoché → conservé en clair
    assert "Claire Martin" not in out      # coché → masqué
    assert "[PERSONNE]" in out
    # le rapport ne liste que l'entité réellement masquée
    originals = [r["original"] for r in res.report.to_rows()]
    assert "Claire Martin" in originals and "Jean Dupont" not in originals


def _page_text(ps):
    """Reconstruit un PageText à partir d'un PageScan pour appeler mapping."""
    from anonymator.files.pdf.extract import PageText
    return PageText(ps.page_index, ps.text, ps.words)


class _OnceNer:
    """Ne détecte que la 1re occurrence de la surface (simule un miss GLiNER)."""
    def __init__(self, surface, etype):
        self._s, self._t = surface, etype

    def detect(self, text, labels):
        i = text.find(self._s)
        if i < 0:
            return []
        return [Entity(self._t, self._s, i, i + len(self._s), "ner", 0.9, True)]


def test_scan_pdf_propagates_missed_occurrence(tmp_path):
    src = make_repeat_pdf(tmp_path / "r.pdf")
    pages = pdf_io.scan_pdf(src, _OnceNer("GUILLAUME DROGLAND", "PERSON"), _ref())
    persons = [e for e in pages[0].entities
               if e.type == "PERSON" and e.value == "GUILLAUME DROGLAND"]
    assert len(persons) == 2


class _WindowNer:
    """Simule la limite d'entrée de GLiNER : ne détecte les surfaces que dans
    les `window` premiers caractères du texte reçu (au-delà, GLiNER tronque)."""
    def __init__(self, mapping, window):
        self._mapping, self._window = mapping, window

    def detect(self, text, labels):
        head = text[:self._window]
        out = []
        for surface, etype in self._mapping.items():
            i = head.find(surface)
            if i >= 0:
                out.append(Entity(etype, surface, i, i + len(surface),
                                  "ner", 1.0, True))
        return out


def _make_long_pdf(path, tail_name):
    """Page dont le texte dépasse la fenêtre du NER, avec un nom tout en bas."""
    doc = fitz.open()
    page = doc.new_page()
    filler = " ".join(f"remplissage{n:03d}" for n in range(180))  # ~2500 chars
    page.insert_textbox(fitz.Rect(40, 40, 550, 780),
                        filler + " " + tail_name, fontsize=9)
    doc.save(str(path))
    doc.close()
    return path


def test_scan_pdf_chunks_pages_so_ner_sees_whole_page(tmp_path):
    """Une entité au-delà de la fenêtre d'entrée du NER n'est retrouvée que si
    scan_pdf découpe la page avant de la passer au NER (régression gltest2)."""
    src = _make_long_pdf(tmp_path / "long.pdf", "Jean Dupont")
    # fenêtre > taille de chunk (1000) mais < page entière (~2500) : modélise
    # GLiNER, qui voit un chunk entier mais tronque la page complète.
    ner = _WindowNer({"Jean Dupont": "PERSON"}, window=1200)
    pages = pdf_io.scan_pdf(src, ner, _ref())
    assert any(e.type == "PERSON" and e.value == "Jean Dupont"
               for e in pages[0].entities)


def test_render_page_at_returns_png(tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "un texte")
    png = pdf_io.render_page_at(src, 0)
    assert png[:4] == b"\x89PNG"
