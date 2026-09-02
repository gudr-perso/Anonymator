# tests/test_model_download.py
import sys
from anonymator.core import model_download


def test_progress_tracker_accumulates():
    seen = []
    t = model_download.ProgressTracker(total=300, emit=lambda r, tot: seen.append((r, tot)))
    t.add(100)
    t.add(50)
    assert seen == [(100, 300), (150, 300)]


def test_download_model_aggregates_progress_across_files(monkeypatch):
    # snapshot_download factice : instancie le tqdm_class et simule deux fichiers
    def fake_snapshot(model_name, tqdm_class=None, **kwargs):
        bar1 = tqdm_class(total=100, unit="B"); bar1.update(100); bar1.close()
        bar2 = tqdm_class(total=200, unit="B"); bar2.update(200); bar2.close()

    monkeypatch.setattr(model_download, "snapshot_download", fake_snapshot)
    monkeypatch.setattr(model_download, "repo_total_size", lambda model_name=None: 300)

    received = []
    statuses = []
    model_download.download_model(on_progress=lambda r, t: received.append((r, t)),
                                  on_status=statuses.append)

    assert received[-1] == (300, 300)         # cumul final sur tous les fichiers
    assert "Téléchargement…" in statuses


def test_download_model_survives_none_stderr(monkeypatch):
    # Reproduit l'exe windowed : sys.stderr est None → tqdm ne doit PAS planter.
    monkeypatch.setattr(sys, "stderr", None)

    def fake_snapshot(model_name, tqdm_class=None, **kwargs):
        bar = tqdm_class(total=10, unit="B"); bar.update(10); bar.close()

    monkeypatch.setattr(model_download, "snapshot_download", fake_snapshot)
    monkeypatch.setattr(model_download, "repo_total_size", lambda model_name=None: 10)

    received = []
    model_download.download_model(on_progress=lambda r, t: received.append((r, t)))
    assert received[-1] == (10, 10)


def test_tqdm_class_raises_when_cancelled():
    """Point d'annulation : `snapshot_download` ne sait pas s'interrompre, mais
    il passe par tqdm à chaque incrément d'octets."""
    import pytest
    tqdm_class = model_download.make_tqdm_class(None, should_cancel=lambda: True)
    bar = tqdm_class(total=100, unit="B")
    with pytest.raises(model_download.DownloadCancelled):
        bar.update(10)
    bar.close()


def test_download_model_passes_cancel_hook_to_tqdm(monkeypatch):
    cancelled = {"value": False}

    def fake_snapshot(model_name, tqdm_class=None, **kwargs):
        bar = tqdm_class(total=100, unit="B")
        bar.update(10)              # avant annulation : passe
        cancelled["value"] = True
        try:
            bar.update(10)          # après : doit lever
        finally:
            bar.close()

    monkeypatch.setattr(model_download, "snapshot_download", fake_snapshot)
    monkeypatch.setattr(model_download, "repo_total_size", lambda model_name=None: 100)

    import pytest
    with pytest.raises(model_download.DownloadCancelled):
        model_download.download_model(should_cancel=lambda: cancelled["value"])
