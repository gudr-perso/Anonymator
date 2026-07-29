# tests/test_download_worker.py
from anonymator.ui import download_worker
from anonymator.ui.download_worker import DownloadWorker

_INT32_MAX = 2 ** 31 - 1
_BIG = 3 * 1024 ** 3          # 3 Gio : au-delà de la limite d'un int C++ 32 bits


def test_worker_emits_progress_and_finished(qtbot, monkeypatch):
    def fake_download(on_progress=None, on_status=None):
        if on_status:
            on_status("Téléchargement…")
        if on_progress:
            on_progress(150, 300)

    monkeypatch.setattr(download_worker, "download_model", fake_download)
    w = DownloadWorker()
    progresses, statuses = [], []
    w.progress.connect(lambda r, t: progresses.append((r, t)))
    w.status.connect(statuses.append)
    with qtbot.waitSignal(w.download_finished, timeout=3000):
        w.start()
    assert (150, 300) in progresses
    assert "Téléchargement…" in statuses


def test_worker_progress_carries_sizes_above_int32(qtbot, monkeypatch):
    """Le dépôt du modèle pèse plus de 2 Gio : les octets doivent traverser le
    signal intacts. Avec un `Signal(int, int)` (int C++ 32 bits) shiboken
    déborde, lève un OverflowError hors du try/except du worker et transmet une
    valeur négative tronquée."""
    def fake_download(on_progress=None, on_status=None):
        on_progress(_BIG // 2, _BIG)

    monkeypatch.setattr(download_worker, "download_model", fake_download)
    w = DownloadWorker()
    progresses = []
    w.progress.connect(lambda r, t: progresses.append((r, t)))
    with qtbot.waitSignal(w.download_finished, timeout=3000):
        w.start()
    assert _BIG > _INT32_MAX
    assert (_BIG // 2, _BIG) in progresses


def test_worker_emits_error(qtbot, monkeypatch):
    def boom(on_progress=None, on_status=None):
        raise RuntimeError("pas de réseau")

    monkeypatch.setattr(download_worker, "download_model", boom)
    w = DownloadWorker()
    errors = []
    w.error.connect(errors.append)
    with qtbot.waitSignal(w.error, timeout=3000):
        w.start()
    assert "pas de réseau" in errors[0]
