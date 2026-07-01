from huggingface_hub import HfApi, snapshot_download
from tqdm import tqdm as _base_tqdm
from anonymator.core.model_status import MODEL_NAME


class ProgressTracker:
    """Cumule les octets reçus à travers plusieurs fichiers et émet (reçu, total)."""
    def __init__(self, total, emit):
        self._total = total
        self._received = 0
        self._emit = emit

    def add(self, n: int) -> None:
        self._received += int(n)
        self._emit(self._received, self._total)


def repo_total_size(model_name: str = MODEL_NAME) -> int | None:
    """Somme des tailles des fichiers du dépôt, ou None si indéterminable."""
    try:
        info = HfApi().model_info(model_name, files_metadata=True)
        sizes = [s.size for s in info.siblings if getattr(s, "size", None)]
        return sum(sizes) if sizes else None
    except Exception:        # noqa: BLE001 — total inconnu → barre indéterminée
        return None


def make_tqdm_class(tracker: ProgressTracker):
    """Sous-classe tqdm qui pousse chaque incrément d'octets dans le tracker."""
    class _Tqdm(_base_tqdm):
        def update(self, n=1):
            tracker.add(n or 0)
            return super().update(n)
    return _Tqdm


def download_model(on_progress=None, on_status=None) -> None:
    """Télécharge le modèle GLiNER dans le cache HuggingFace, en signalant
    la progression. `on_progress(reçu, total)` (total peut être None),
    `on_status(texte)`."""
    if on_status:
        on_status("Connexion…")
    total = repo_total_size()
    tqdm_class = None
    if on_progress is not None:
        tracker = ProgressTracker(total, on_progress)
        tqdm_class = make_tqdm_class(tracker)
    if on_status:
        on_status("Téléchargement…")
    snapshot_download(MODEL_NAME, tqdm_class=tqdm_class)
    if on_status:
        on_status("Finalisation…")
