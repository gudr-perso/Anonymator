from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "third-party-licenses"


def test_notice_mentions_qt_lgpl():
    txt = (TPL / "README.md").read_text(encoding="utf-8")
    assert "PySide6" in txt and "Qt" in txt
    assert "LGPL-3.0" in txt
    # La liberté clé de la LGPL (re-linking) doit être expliquée.
    assert "re-link" in txt.lower() or "remplacer" in txt.lower()


def test_lgpl_and_gpl_texts_present():
    lgpl = (TPL / "LGPL-3.0.txt").read_text(encoding="utf-8")
    gpl = (TPL / "GPL-3.0.txt").read_text(encoding="utf-8")
    assert "GNU LESSER GENERAL PUBLIC LICENSE" in lgpl
    assert "GNU GENERAL PUBLIC LICENSE" in gpl
    assert len(gpl) > 30_000  # texte intégral, pas un stub


def test_spec_bundles_third_party_licenses():
    spec = (ROOT / "anonymator.spec").read_text(encoding="utf-8")
    assert "third-party-licenses" in spec
