# tests/test_download_worker.py
from anonymator.ui import download_worker
from anonymator.ui.download_worker import DownloadWorker


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
