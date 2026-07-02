from anonymator.ui.components.nav_band import NavBand

def test_home_callback(qtbot):
    called = []
    band = NavBand("Détection & masquage", "settings", on_home=lambda: called.append(True))
    qtbot.addWidget(band)
    band.home_btn.click()
    assert called == [True]

def test_active_title(qtbot):
    band = NavBand("Règles métier", "layers", on_home=lambda: None)
    qtbot.addWidget(band)
    assert band.active_btn.text().strip() == "Règles métier"
