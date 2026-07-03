# tests/test_pdf_screen.py
from datetime import datetime
from unittest.mock import patch
import fitz
from PySide6.QtWidgets import QMessageBox
from tests.pdf_fixtures import (make_native_pdf, make_scanned_pdf,
                                make_encrypted_pdf, make_repeat_pdf)
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.pdf_screen import PdfScreen


def _screen(mapping=None, out=None):
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer(mapping or {}))
    prefs = Preferences(output_dir=str(out)) if out else Preferences()
    return PdfScreen(ref, loader, prefs, on_back=lambda: None)


def test_load_enables_analyze(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.btn_review.isEnabled() is True


def test_load_renders_preview_without_analysis(qtbot, tmp_path):
    """Dès l'ouverture, l'aperçu (non caviardé) s'affiche — sans analyse ni
    modèle. Le canevas a une page et aucun overlay."""
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.canvas.has_page() is True
    assert s.canvas.overlay_count() == 0
    assert s._page_count == 1


def test_single_page_shows_bar_but_hides_pagination(qtbot, tmp_path):
    # Page unique : la barre du bas est visible (elle héberge le zoom), mais
    # les contrôles de pagination restent masqués.
    src = make_repeat_pdf(tmp_path / "r.pdf")   # 1 page
    s = _screen(); qtbot.addWidget(s); s.show()
    s.load_path(str(src))
    assert s.canvas.has_page() is True
    assert s._page_count == 1
    assert s.pager_widget.isVisible() is True
    assert s.btn_prev.isVisibleTo(s.pager_widget) is False
    assert s.btn_next.isVisibleTo(s.pager_widget) is False
    assert s.btn_zoom_in.isVisibleTo(s.pager_widget) is True


def test_multipage_shows_pagination(qtbot, tmp_path):
    doc = fitz.open()
    for i in range(2):
        doc.new_page().insert_text((72, 100), f"page {i}", fontsize=11)
    path = tmp_path / "multi.pdf"; doc.save(str(path)); doc.close()
    s = _screen(); qtbot.addWidget(s); s.show()
    s.load_path(str(path))
    assert s._page_count == 2
    assert s.pager_widget.isVisible() is True
    assert s.btn_next.isVisibleTo(s.pager_widget) is True


def test_zoom_button_updates_label(qtbot, tmp_path):
    src = make_repeat_pdf(tmp_path / "r.pdf")
    s = _screen(); qtbot.addWidget(s); s.show()
    s.load_path(str(src))
    assert s.lbl_zoom.text() == "100 %"
    s._zoom(s.canvas.zoom_in)
    assert s.canvas.display_zoom > 1.0
    assert s.lbl_zoom.text() == f"{round(s.canvas.display_zoom * 100)} %"


def test_fit_button_enables_fit_mode(qtbot, tmp_path):
    src = make_repeat_pdf(tmp_path / "r.pdf")
    s = _screen(); qtbot.addWidget(s); s.resize(500, 600); s.show()
    qtbot.waitExposed(s)
    s.load_path(str(src))
    s.btn_fit.click()
    assert s.canvas._fit_width is True


def test_shortcuts_are_documented_in_screen(qtbot):
    s = _screen(); qtbot.addWidget(s)
    txt = s.lbl_shortcuts.text()
    # la légende à l'écran mentionne les raccourcis de zoom
    assert "Ctrl" in txt
    assert "molette" in txt.lower()


def test_load_corrupt_pdf_shows_error_immediately(qtbot, tmp_path):
    """Un PDF illisible affiche le message d'erreur dès l'ouverture, sans
    attendre « Analyser »."""
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 ceci n'est pas un vrai PDF")
    s = _screen(); qtbot.addWidget(s)
    with patch("anonymator.ui.pdf_screen.QMessageBox.warning") as warn:
        s.load_path(str(bad))
    assert warn.called
    assert s.canvas.has_page() is False


def test_load_encrypted_pdf_shows_error_immediately(qtbot, tmp_path):
    src = make_encrypted_pdf(tmp_path / "e.pdf")
    s = _screen(); qtbot.addWidget(s)
    with patch("anonymator.ui.pdf_screen.QMessageBox.warning") as warn:
        s.load_path(str(src))
    assert warn.called


def test_busy_overlay_toggles(qtbot):
    s = _screen(); qtbot.addWidget(s); s.show()
    assert s._overlay.isVisible() is False
    s._set_busy(True)
    assert s._overlay.isVisible() is True
    assert s._overlay.text() == "⏳  Analyse en cours…"
    s._set_busy(False)
    assert s._overlay.isVisible() is False


def test_analyze_builds_session_and_side(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.count_retained("PERSON") == 1
    assert s.side.topLevelItemCount() == 1


def test_redact_run_writes_destroyed_pdf(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    res = s.run_redact(when=datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".pdf"
    check = fitz.open(str(res.output_path))
    assert "Claire Martin" not in check[0].get_text()
    check.close()


def test_text_run_writes_masked_txt(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src))
    res = s.run_text(when=datetime(2026, 1, 2, 3, 4, 5))
    assert res.output_path.suffix == ".txt"
    out = res.output_path.read_text(encoding="utf-8")
    assert "[PERSONNE]" in out and "Claire Martin" not in out


def test_text_run_honors_review_decochage(qtbot, tmp_path):
    """Après analyse, décocher une valeur la conserve en clair dans le .txt —
    le mode texte est cohérent avec la revue visuelle."""
    src = make_native_pdf(tmp_path / "n.pdf",
                          "Contact Claire Martin et Jean Dupont ici")
    s = _screen({"Claire Martin": "PERSON", "Jean Dupont": "PERSON"}, out=tmp_path)
    qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s.session.set_value_enabled("PERSON", "Jean Dupont", False)
    res = s.run_text(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_text(encoding="utf-8")
    assert "Jean Dupont" in out            # décoché → conservé en clair
    assert "Claire Martin" not in out      # coché → masqué


def test_text_export_warns_when_manual_zones_present(qtbot, tmp_path):
    """Cliquer « Extraire en .txt » avec des zones manuelles tracées prévient
    qu'elles ne figureront pas dans le texte (concept propre au caviardage)."""
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s._on_manual_rect((300.0, 300.0, 360.0, 330.0))
    with patch("anonymator.ui.pdf_screen.QMessageBox.question",
               return_value=QMessageBox.Yes) as q, \
         patch("anonymator.ui.pdf_screen.QMessageBox.information"):
        s._text_clicked()
    assert q.called


def test_text_export_no_warning_without_manual_zones(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    with patch("anonymator.ui.pdf_screen.QMessageBox.question") as q, \
         patch("anonymator.ui.pdf_screen.QMessageBox.information"):
        s._text_clicked()
    assert not q.called


def test_text_export_aborts_when_user_declines_manual_warning(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}, out=tmp_path); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s._on_manual_rect((300.0, 300.0, 360.0, 330.0))
    with patch("anonymator.ui.pdf_screen.QMessageBox.question",
               return_value=QMessageBox.No), \
         patch("anonymator.ui.pdf_screen.QMessageBox.information"), \
         patch.object(s, "run_text") as run:
        s._text_clicked()
    assert not run.called


def test_manual_rect_added_to_session(qtbot, tmp_path):
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")
    s = _screen({"Claire Martin": "PERSON"}); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s._on_manual_rect((300.0, 300.0, 360.0, 330.0))
    assert (300.0, 300.0, 360.0, 330.0) in s.session.manual_rects(0)


def test_analyze_surfaces_detector_load_failure(qtbot, tmp_path):
    """Régression du bug « rien ne se passe » : si le chargement du modèle
    échoue, un dialogue explicite s'affiche au lieu d'un plantage silencieux."""
    src = make_native_pdf(tmp_path / "n.pdf", "Contact Claire Martin ici")

    class BoomLoader:
        def has_detector(self):
            return True

        def get(self):
            raise RuntimeError("échec chargement modèle")

    from anonymator.ui.preferences import Preferences
    s = PdfScreen(Referential.load_default(), BoomLoader(), Preferences(),
                  on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src))
    with patch("anonymator.ui.pdf_screen.QMessageBox.warning") as warn:
        s.analyze()
        qtbot.waitUntil(lambda: warn.called, timeout=5000)
    assert warn.called


def test_scanned_pdf_shows_error(qtbot, tmp_path):
    src = make_scanned_pdf(tmp_path / "s.pdf")
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    with patch("anonymator.ui.pdf_screen.QMessageBox.warning") as warn:
        s.analyze()
        qtbot.waitUntil(lambda: warn.called, timeout=5000)
    assert warn.called
