import os
from pathlib import Path

MODEL_NAME = "urchade/gliner_multi-v2.1"
_CACHE_SUBDIR = "models--urchade--gliner_multi-v2.1"

def model_cache_dir() -> Path:
    if hub_cache := os.environ.get("HUGGINGFACE_HUB_CACHE"):
        return Path(hub_cache) / _CACHE_SUBDIR
    if hf_home := os.environ.get("HF_HOME"):
        return Path(hf_home) / "hub" / _CACHE_SUBDIR
    return Path.home() / ".cache" / "huggingface" / "hub" / _CACHE_SUBDIR

def is_model_available() -> bool:
    snapshots = model_cache_dir() / "snapshots"
    return snapshots.exists() and any(snapshots.iterdir())

def installed_size() -> int | None:
    """Taille en octets du modèle en cache, ou None s'il n'est pas installé."""
    if not is_model_available():
        return None
    d = model_cache_dir()
    blobs = d / "blobs"
    base = blobs if blobs.exists() else d
    return sum(p.stat().st_size for p in base.rglob("*") if p.is_file())
