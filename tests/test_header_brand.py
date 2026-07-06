from anonymator.brand import lock_brand, reset_brand
from anonymator.ui.components.header import HeaderBand


def teardown_function():
    reset_brand()


def _label_texts(widget):
    from PySide6.QtWidgets import QLabel
    return [c.text() for c in widget.findChildren(QLabel)]


def test_header_shows_dev_name_by_default(qtbot):
    reset_brand()
    h = HeaderBand(); qtbot.addWidget(h)
    assert "Anonymator" in _label_texts(h)


def test_header_shows_brand_name_when_locked(qtbot):
    lock_brand("cap")
    h = HeaderBand(); qtbot.addWidget(h)
    assert "CAP'nonyme" in _label_texts(h)
