from datetime import datetime
from unittest.mock import patch
from PySide6.QtWidgets import QMessageBox
from anonymator.referential import Referential
from anonymator.ner import FakeNer
from anonymator.ui.model_loader import ModelLoader
from anonymator.ui.preferences import Preferences
from anonymator.ui.file_screen import FileScreen
from anonymator.ui.file_scan_worker import FileScanWorker
from anonymator.files import csv_io
from anonymator.files.columns import default_maskable_columns


def test_scan_worker_emits_result(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    doc = csv_io.read_csv(src)
    cols = default_maskable_columns(doc.rows, doc.has_header)
    worker = FileScanWorker(doc, ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                            Referential.load_default(), cols)
    with qtbot.waitSignal(worker.scan_finished, timeout=5000) as blocker:
        worker.start()
    worker.wait()           # ensure thread finishes before teardown
    scanned = blocker.args[0]
    assert (1, 0) in scanned


def test_scan_worker_emits_error_when_detector_load_fails(qtbot, tmp_path):
    """Le détecteur est construit DANS le thread : un échec de chargement
    remonte via `error` au lieu d'exploser en silence sur le thread principal."""
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    doc = csv_io.read_csv(src)
    cols = default_maskable_columns(doc.rows, doc.has_header)

    class BoomLoader:
        def get(self):
            raise RuntimeError("échec chargement modèle")

    worker = FileScanWorker(doc, BoomLoader(), Referential.load_default(), cols)
    with qtbot.waitSignal(worker.error, timeout=5000) as blocker:
        worker.start()
    worker.wait()
    assert "échec chargement modèle" in blocker.args[0]


def _screen(loader_map=None):
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer(loader_map or {}))
    return FileScreen(ref, loader, Preferences(), on_back=lambda: None)


def test_preview_splits_columns(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.table.columnCount() == 2
    assert s.table.horizontalHeaderItem(0).text() == "Nom"
    assert s.table.item(0, 0).text() == "Claire Martin"


def test_analyze_builds_session_and_side(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    s = _screen({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    qtbot.addWidget(s)
    s.load_path(str(src))
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.count_retained("PERSON") == 2
    assert s.side.topLevelItemCount() == 1            # un type : PERSON
    assert s.side.topLevelItem(0).childCount() == 2   # deux valeurs distinctes


def test_pagination_navigates(qtbot, tmp_path):
    lines = "Nom;Montant\n" + "".join(f"Nom{i};1,00\n" for i in range(45))
    src = tmp_path / "big.csv"; src.write_bytes(lines.encode("cp1252"))
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s._page_count() == 3            # 45 lignes / 20
    s._go(99)                              # clampé à la dernière
    assert s.page == 2
    assert s.table.rowCount() == 5         # 45 - 40
    s._go(0)
    assert s.table.rowCount() == 20


def test_apply_review_writes_user_choices(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    ref = Referential.load_default()
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON", "Paul Durand": "PERSON"}))
    s = FileScreen(ref, loader, Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src)); s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    s.session.set_value_enabled("PERSON", "Paul Durand", False)   # keep Paul in clear
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    assert "[PERSONNE]" in out and "Paul Durand" in out and "Claire Martin" not in out


def test_run_on_csv_writes_output(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    prefs = Preferences(output_dir=str(tmp_path))
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    screen = FileScreen(Referential.load_default(), loader, prefs, on_back=lambda: None)
    qtbot.addWidget(screen)
    screen.load_path(str(src))
    result = screen.run(when=datetime(2026, 1, 2, 3, 4, 5))
    assert result.output_path.exists()
    out = result.output_path.read_bytes().decode("cp1252")
    assert "[PERSONNE]" in out and "Claire Martin" not in out


def test_run_clicked_without_session_threads_and_confirms(qtbot, tmp_path):
    """Sans analyse préalable (pas de session), « Anonymiser » passe par un
    worker : overlay affiché, confirmation à la fin, fichier écrit."""
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    s = FileScreen(Referential.load_default(), loader,
                   Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.session is None
    with patch("anonymator.ui.file_screen.QMessageBox.information") as info:
        s._run_clicked()
        qtbot.waitUntil(lambda: info.called, timeout=5000)
    assert info.called
    outs = list(tmp_path.glob("*_ano_*.csv"))
    assert outs and outs[0].read_bytes().decode("cp1252").count("[PERSONNE]") == 1


def test_run_clicked_surfaces_detector_load_failure(qtbot, tmp_path):
    """Régression : un échec de chargement du modèle sur le chemin direct
    affiche un dialogue explicite au lieu d'un plantage silencieux."""
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))

    class BoomLoader:
        def has_detector(self):
            return True

        def get(self):
            raise RuntimeError("échec chargement modèle")

    s = FileScreen(Referential.load_default(), BoomLoader(),
                   Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src))
    with patch("anonymator.ui.file_screen.QMessageBox.warning") as warn:
        s._run_clicked()
        qtbot.waitUntil(lambda: warn.called, timeout=5000)
    assert warn.called


def test_review_enabled_for_xlsx(qtbot, tmp_path):
    """La revue est ouverte aux classeurs (chantier 3) : le bouton doit être
    actif dès le chargement, avant même toute lecture du fichier."""
    src = tmp_path / "f.xlsx"; src.write_bytes(b"PK\x03\x04stub")   # extension xlsx
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.btn_review.isEnabled() is True


def test_txt_routes_to_text_review(qtbot, tmp_path):
    called = {}
    ref = Referential.load_default()
    s = FileScreen(ref, ModelLoader(FakeNer({})), Preferences(),
                   on_back=lambda: None,
                   on_text_review=lambda text: called.setdefault("text", text))
    qtbot.addWidget(s)
    src = tmp_path / "n.txt"; src.write_text("Bonjour Claire", encoding="utf-8")
    s.load_path(str(src))
    s.analyze()
    assert called.get("text") == "Bonjour Claire"


def test_tabular_txt_opens_as_a_grid(qtbot, tmp_path):
    """Un FEC (.txt à tabulations) s'ouvre en grille, colonne par colonne, et
    l'analyse passe par le plan de colonnes, pas par la revue texte."""
    called = {}
    s = FileScreen(Referential.load_default(),
                   ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                   Preferences(), on_back=lambda: None,
                   on_text_review=lambda text: called.setdefault("text", text))
    qtbot.addWidget(s)
    src = tmp_path / "404833048FEC20251231.txt"
    src.write_bytes("JournalCode\tCompAuxLib\tDebit\r\n"
                    "VE\tClaire Martin\t10,00\r\n"
                    "VE\tClaire Martin\t0,00\r\n".encode("cp1252"))
    s.load_path(str(src))
    assert s.table.columnCount() == 3
    assert s.table.horizontalHeaderItem(1).text() == "CompAuxLib"
    s.analyze()
    assert "text" not in called
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.count_retained("PERSON") == 2


def test_busy_overlay_toggles(qtbot):
    s = _screen(); qtbot.addWidget(s); s.show()
    assert s._overlay.isVisible() is False
    s._set_busy(True)
    assert s._overlay.isVisible() is True
    assert s._overlay.text() == "⏳  Analyse en cours…"
    s._set_busy(False)
    assert s._overlay.isVisible() is False


def test_file_degraded_banner_when_model_absent(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;IBAN\nClaire Martin;FR7630006000011234567890189\n".encode("cp1252"))
    with patch("anonymator.ui.file_screen.is_model_available", return_value=False):
        s = FileScreen(Referential.load_default(), ModelLoader(), Preferences(),
                       on_back=lambda: None, on_request_model=lambda: None)
        qtbot.addWidget(s)
        s.load_path(str(src))
        s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is True
        assert s.banner.isVisibleTo(s) is True


def test_file_no_banner_with_injected_detector(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    with patch("anonymator.ui.file_screen.is_model_available", return_value=False):
        s = FileScreen(Referential.load_default(),
                       ModelLoader(FakeNer({"Claire Martin": "PERSON"})),
                       Preferences(), on_back=lambda: None)
        qtbot.addWidget(s)
        s.load_path(str(src)); s.analyze()
        qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
        assert s._degraded is False
        assert s.banner.isVisibleTo(s) is False


def test_analyze_docx_twice_does_not_crash(tmp_path, qtbot):
    """Régression : analyser un 2e document après un 1er ne doit pas planter avec
    « Internal C++ object (OoxmlScanWorker) already deleted ». Le worker précédent
    est supprimé côté C++ par deleteLater ; le garde-fou de `analyze()` ne doit pas
    déréférencer ce wrapper mort."""
    from tests.ooxml_fixtures import make_docx
    src1 = make_docx(tmp_path / "d1.docx")
    src2 = make_docx(tmp_path / "d2.docx")
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    s = FileScreen(Referential.load_default(), loader,
                   Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)

    s.load_path(str(src1))
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=10000)
    # À ce stade le 1er worker a fini : son objet C++ est supprimé (deleteLater)
    # mais `s._worker` en garde un wrapper mort.

    s.load_path(str(src2))
    s.analyze()                                            # ne doit pas lever
    qtbot.waitUntil(lambda: s.session is not None, timeout=10000)
    assert "PERSON" in s.session.types()


def test_file_screen_reviews_docx(tmp_path, qtbot):
    from anonymator.referential import Referential
    from anonymator.ner import FakeNer
    from anonymator.ui.model_loader import ModelLoader
    from anonymator.ui.preferences import Preferences
    from anonymator.ui.file_screen import FileScreen
    from anonymator.core.ooxml_review_session import OoxmlReviewSession
    from tests.ooxml_fixtures import make_docx

    src = make_docx(tmp_path / "d.docx")
    prefs = Preferences(output_dir=str(tmp_path))
    loader = ModelLoader(FakeNer({"Claire Martin": "PERSON"}))
    screen = FileScreen(Referential.load_default(), loader, prefs, on_back=lambda: None)
    qtbot.addWidget(screen)
    screen.load_path(str(src))
    assert screen.btn_review.isEnabled()

    screen.analyze()
    with qtbot.waitSignal(screen._worker.scan_finished, timeout=10000):
        pass
    qtbot.waitUntil(lambda: screen.session is not None, timeout=10000)
    assert isinstance(screen.session, OoxmlReviewSession)
    assert "PERSON" in screen.session.types()

    result = screen.run()
    assert result.output_path.exists()
    from docx import Document
    assert "[PERSONNE]" in Document(str(result.output_path)).paragraphs[0].text


# ---- interrupteur « première ligne = en-têtes » ----

def _no_sniff_csv(tmp_path):
    """Fichier 100 % texte : csv.Sniffer n'y détecte pas d'en-tête."""
    src = tmp_path / "h.csv"
    src.write_bytes(("contact_nom;secteur\n"
                     "Leclerc;Industrie\n"
                     "Berger;BTP\n").encode("cp1252"))
    return src


def test_header_switch_reflects_detection(qtbot, tmp_path):
    src = tmp_path / "f.csv"
    src.write_bytes("Nom;Montant\nClaire Martin;100,00\n".encode("cp1252"))
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.header_switch.isVisible() or not s.isVisible()   # affiché pour un CSV
    assert s.header_switch.isChecked() is True                # sniffer : en-tête


def test_header_switch_hidden_for_non_csv(qtbot, tmp_path):
    src = tmp_path / "n.txt"
    src.write_bytes("Claire Martin".encode("cp1252"))
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.header_switch.isHidden()


def test_header_switch_updates_document_and_preview(qtbot, tmp_path):
    src = _no_sniff_csv(tmp_path)
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    assert s.doc.has_header is False
    assert s.table.rowCount() == 3            # la ligne de titres compte comme donnée
    s.header_switch.setChecked(True)
    assert s.doc.has_header is True
    assert s.table.rowCount() == 2
    assert s.table.horizontalHeaderItem(0).text() == "contact_nom"


def _reviewed_screen(qtbot, tmp_path):
    """Écran avec une revue déjà faite, en-tête assumé (le sniffer, lui,
    hésite selon le nombre de lignes de données)."""
    src = tmp_path / "f.csv"
    src.write_bytes(
        "Nom;Montant\nClaire Martin;100,00\nPaul Durand;50,00\n".encode("cp1252"))
    s = _screen({"Claire Martin": "PERSON", "Paul Durand": "PERSON"})
    qtbot.addWidget(s)
    s.load_path(str(src))
    s.header_switch.setChecked(True)      # sans revue : aucun dialogue
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    return s


def test_header_switch_asks_before_discarding_review(qtbot, tmp_path):
    """Une revue représente du travail manuel : on ne la jette pas sur un
    clic de case à cocher sans demander."""
    s = _reviewed_screen(qtbot, tmp_path)
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.No) as ask:
        s.header_switch.setChecked(False)
    assert ask.called
    assert s.session is not None          # revue conservée
    assert s.doc.has_header is True       # hypothèse inchangée
    assert s.header_switch.isChecked() is True   # case revenue à son état


def test_header_switch_discards_review_once_confirmed(qtbot, tmp_path):
    s = _reviewed_screen(qtbot, tmp_path)
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    assert s.session is None
    assert s.doc.has_header is False
    assert s.side.isHidden()


def test_header_switch_restores_choices_after_reanalysis(qtbot, tmp_path):
    """Le plan de colonnes change, pas les arbitrages de l'utilisateur : ses
    décochages sont réappliqués à la nouvelle analyse."""
    s = _reviewed_screen(qtbot, tmp_path)
    s.session.set_value_enabled("PERSON", "Paul Durand", False)
    s.session.set_type_enabled("PERSON", True)
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.is_value_enabled("PERSON", "Paul Durand") is False
    assert s.session.is_value_enabled("PERSON", "Claire Martin") is True


def test_header_switch_without_review_needs_no_confirmation(qtbot, tmp_path):
    src = _no_sniff_csv(tmp_path)
    s = _screen(); qtbot.addWidget(s)
    s.load_path(str(src))
    with patch("anonymator.ui.file_screen.QMessageBox.question") as ask:
        s.header_switch.setChecked(True)
    assert not ask.called
    assert s.doc.has_header is True


def test_header_switch_drives_direct_anonymization(qtbot, tmp_path):
    """Sans revue, l'anonymisation directe doit suivre le choix de l'UI et non
    la détection automatique."""
    src = _no_sniff_csv(tmp_path)
    loader = ModelLoader(FakeNer({}))
    s = FileScreen(Referential.load_default(), loader,
                   Preferences(output_dir=str(tmp_path)), on_back=lambda: None)
    qtbot.addWidget(s)
    s.load_path(str(src))
    s.header_switch.setChecked(True)
    res = s.run(when=datetime(2026, 1, 2, 3, 4, 5))
    out = res.output_path.read_bytes().decode("cp1252")
    assert out.splitlines()[0] == "contact_nom;secteur"
    assert out.count("[PERSONNE]") == 2


def test_pending_choices_do_not_leak_to_another_file(qtbot, tmp_path):
    """Les arbitrages reportés valent pour le fichier en cours, pas pour le
    suivant, même si un nom s'y retrouve."""
    s = _reviewed_screen(qtbot, tmp_path)
    s.session.set_value_enabled("PERSON", "Paul Durand", False)
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    other = tmp_path / "autre.csv"
    other.write_bytes("Nom;Montant\nPaul Durand;10,00\n".encode("cp1252"))
    s.load_path(str(other))
    s.analyze()
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.session.is_value_enabled("PERSON", "Paul Durand") is True


def test_header_switch_relaunches_the_promised_analysis(qtbot, tmp_path):
    """Le dialogue annonce que l'analyse va être relancée, et l'utilisateur
    accepte : elle doit l'être. Sans cela la revue disparaissait sans être
    refaite, et « Anonymiser & enregistrer » repartait en détection
    automatique — une colonne forcée à la main n'était pas masquée du tout."""
    s = _reviewed_screen(qtbot, tmp_path)
    with patch("anonymator.ui.file_screen.QMessageBox.question",
               return_value=QMessageBox.Yes):
        s.header_switch.setChecked(False)
    qtbot.waitUntil(lambda: s.session is not None, timeout=5000)
    assert s.doc.has_header is False


def test_unreadable_csv_is_reported_not_raised(qtbot, tmp_path):
    """Un fichier illisible se dit sur l'écran Fichier, pas via le filet de
    sécurité « Erreur inattendue » de __main__."""
    src = tmp_path / "absent.csv"          # jamais créé → OSError à la lecture
    s = _screen(); qtbot.addWidget(s)
    with patch("anonymator.ui.file_screen.QMessageBox.warning") as warn:
        s.load_path(str(src))
    assert warn.called
    assert s.path is None and s.doc is None
    assert not s.btn_review.isEnabled()
