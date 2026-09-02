import io
import sys
from huggingface_hub import HfApi, snapshot_download
from tqdm import tqdm as _base_tqdm
from anonymator.core.model_status import MODEL_NAME


class DownloadCancelled(Exception):
    """Annulation demandée par l'appelant (fermeture de la fenêtre).

    `snapshot_download` ne connaît pas la notion d'annulation et un QThread
    bloqué dedans ne voit jamais passer un `quit()`. On lève donc depuis le
    seul point de contrôle qui soit appelé en continu : l'incrément de tqdm."""


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


def make_tqdm_class(tracker: ProgressTracker | None, should_cancel=None):
    """Sous-classe tqdm qui pousse chaque incrément d'octets dans le tracker
    et sert de point d'annulation.

    Défense pour l'exe *windowed* : si `sys.stderr` est None (pas de console),
    tqdm écrirait sur None → « 'NoneType' object has no attribute 'write' ».
    On lui fournit alors un flux poubelle."""
    class _Tqdm(_base_tqdm):
        def __init__(self, *args, **kwargs):
            if kwargs.get("file") is None and sys.stderr is None:
                kwargs["file"] = io.StringIO()
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            if should_cancel is not None and should_cancel():
                raise DownloadCancelled("téléchargement annulé")
            if tracker is not None:
                tracker.add(n or 0)
            return super().update(n)
    return _Tqdm


def download_model(on_progress=None, on_status=None, should_cancel=None) -> None:
    """Télécharge le modèle GLiNER dans le cache HuggingFace, en signalant
    la progression. `on_progress(reçu, total)` (total peut être None),
    `on_status(texte)`.

    `should_cancel()` est consulté à chaque incrément d'octets : s'il devient
    vrai, `DownloadCancelled` est levée et remonte à travers
    `snapshot_download`. C'est ce qui permet de fermer la fenêtre sans attendre
    la fin des ~2,2 Go."""
    if on_status:
        on_status("Connexion…")
    total = repo_total_size()
    tracker = ProgressTracker(total, on_progress) if on_progress is not None else None
    tqdm_class = (make_tqdm_class(tracker, should_cancel)
                  if tracker is not None or should_cancel is not None else None)
    if on_status:
        on_status("Téléchargement…")
    snapshot_download(MODEL_NAME, tqdm_class=tqdm_class)
    if on_status:
        on_status("Finalisation…")
