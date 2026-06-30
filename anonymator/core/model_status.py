from pathlib import Path

MODEL_NAME = "urchade/gliner_multi-v2.1"
_CACHE_SUBDIR = "models--urchade--gliner_multi-v2.1"

def model_cache_dir() -> Path:
    return Path.home() / ".cache" / "huggingface" / "hub" / _CACHE_SUBDIR

def is_model_available() -> bool:
    snapshots = model_cache_dir() / "snapshots"
    return snapshots.exists() and any(snapshots.iterdir())
