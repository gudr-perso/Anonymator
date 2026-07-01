# tests/test_model_download.py
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
