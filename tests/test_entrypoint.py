# tests/test_entrypoint.py
import sys
from unittest.mock import patch

def test_build_app_returns_window(qtbot):
    from anonymator.__main__ import build_window
    with patch("anonymator.ui.main_window.is_model_available", return_value=True):
        win = build_window()
    qtbot.addWidget(win)
    assert win.windowTitle() == "Anonymator"


def test_ensure_std_streams_replaces_none(monkeypatch):
    from anonymator.__main__ import ensure_std_streams
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    ensure_std_streams()
    assert sys.stdout is not None and hasattr(sys.stdout, "write")
    assert sys.stderr is not None and hasattr(sys.stderr, "write")


def test_install_os_trust_store_delegates_to_system(monkeypatch):
    """Les antivirus qui inspectent le HTTPS (Norton…) presentent un certificat
    signe par une autorite locale : presente dans le magasin Windows, absente de
    `certifi`. Sans delegation au systeme, le telechargement du modele echoue
    sur CERTIFICATE_VERIFY_FAILED."""
    import ssl
    import truststore
    from anonymator.__main__ import install_os_trust_store
    monkeypatch.setattr(ssl, "SSLContext", ssl.SSLContext)   # restaure a la sortie
    assert install_os_trust_store() is True
    assert ssl.SSLContext is truststore.SSLContext


def test_install_os_trust_store_tolerates_missing_module(monkeypatch):
    """Absence de truststore : degradation silencieuse, pas de plantage au
    demarrage (le telechargement marche hors interception TLS)."""
    from anonymator.__main__ import install_os_trust_store
    monkeypatch.setitem(sys.modules, "truststore", None)     # -> ImportError
    assert install_os_trust_store() is False


def test_main_installs_trust_store_before_the_window(monkeypatch):
    """La validation TLS doit etre en place avant tout acces reseau."""
    import anonymator.__main__ as entry
    ordre = []
    monkeypatch.setattr(entry, "install_os_trust_store", lambda: ordre.append("tls"))
    monkeypatch.setattr(entry, "ensure_std_streams", lambda: ordre.append("flux"))
    monkeypatch.setattr(entry, "install_excepthook", lambda: ordre.append("hook"))
    monkeypatch.setattr(entry, "build_window", lambda: ordre.append("fenetre") or _FakeWin())
    monkeypatch.setattr(entry, "QApplication", lambda argv: _FakeApp())
    entry.main()
    assert ordre.index("tls") < ordre.index("fenetre")


class _FakeWin:
    def resize(self, *a): pass
    def show(self): pass


class _FakeApp:
    def exec(self): return 0
