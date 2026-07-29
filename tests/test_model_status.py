import os
from pathlib import Path
from unittest.mock import patch
from anonymator.core.model_status import is_model_available, MODEL_NAME, model_cache_dir

def test_model_name_is_gliner_multi():
    assert MODEL_NAME == "urchade/gliner_multi-v2.1"

def test_cache_dir_is_in_home(monkeypatch):
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    monkeypatch.delenv("HF_HOME", raising=False)
    d = model_cache_dir()
    assert d.parts[-1] == "models--urchade--gliner_multi-v2.1"
    assert str(Path.home()) in str(d)

def test_cache_dir_uses_huggingface_hub_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("HUGGINGFACE_HUB_CACHE", str(tmp_path))
    monkeypatch.delenv("HF_HOME", raising=False)
    d = model_cache_dir()
    assert str(d).startswith(str(tmp_path))

def test_cache_dir_uses_hf_home(monkeypatch, tmp_path):
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    monkeypatch.setenv("HF_HOME", str(tmp_path))
    d = model_cache_dir()
    assert str(d).startswith(str(tmp_path / "hub"))

def _cache(tmp_path, *files: str):
    """Fabrique un cache HuggingFace factice contenant `files` dans l'instantané."""
    cache = tmp_path / "models--urchade--gliner_multi-v2.1"
    snap = cache / "snapshots" / "abc123"; snap.mkdir(parents=True)
    for name in files:
        (snap / name).write_bytes(b"x" * 10)
    return cache


def test_available_when_snapshots_exist(tmp_path):
    cache = _cache(tmp_path, "pytorch_model.bin", "gliner_config.json")
    with patch("anonymator.core.model_status.model_cache_dir", return_value=cache):
        assert is_model_available() is True

def test_unavailable_when_dir_absent(tmp_path):
    with patch("anonymator.core.model_status.model_cache_dir",
               return_value=tmp_path / "absent"):
        assert is_model_available() is False


def test_unavailable_when_snapshot_revision_is_empty(tmp_path):
    """Téléchargement interrompu : `snapshots/<rev>/` est créé mais reste vide,
    les octets sont dans des blobs `.incomplete`. L'écran affichait alors
    « ✅ Installé (0 Mo) » et l'app se croyait en mode complet."""
    cache = _cache(tmp_path)                       # instantané vide
    blobs = cache / "blobs"; blobs.mkdir()
    (blobs / "14208dbc.f9a062f6.incomplete").write_bytes(b"x" * 1024)
    with patch("anonymator.core.model_status.model_cache_dir", return_value=cache):
        assert is_model_available() is False


def test_unavailable_when_weights_missing(tmp_path):
    """Instantané partiel : la config est là, pas les poids → inchargeable."""
    cache = _cache(tmp_path, "gliner_config.json", "tokenizer.json")
    with patch("anonymator.core.model_status.model_cache_dir", return_value=cache):
        assert is_model_available() is False


def test_available_with_safetensors_weights(tmp_path):
    cache = _cache(tmp_path, "model.safetensors")
    with patch("anonymator.core.model_status.model_cache_dir", return_value=cache):
        assert is_model_available() is True


def test_installed_size_none_when_absent(tmp_path):
    from anonymator.core.model_status import installed_size
    with patch("anonymator.core.model_status.model_cache_dir",
               return_value=tmp_path / "absent"):
        assert installed_size() is None


def test_installed_size_sums_blobs(tmp_path):
    from anonymator.core.model_status import installed_size
    cache = _cache(tmp_path, "pytorch_model.bin")
    blobs = cache / "blobs"; blobs.mkdir()
    (blobs / "a").write_bytes(b"x" * 100)
    (blobs / "b").write_bytes(b"y" * 50)
    with patch("anonymator.core.model_status.model_cache_dir", return_value=cache):
        assert installed_size() == 150


def test_installed_size_falls_back_to_snapshots_when_blobs_empty(tmp_path):
    # Windows sans lien symbolique : blobs/ vide, vrais fichiers dans snapshots/
    from anonymator.core.model_status import installed_size
    cache = tmp_path / "models--urchade--gliner_multi-v2.1"
    snap = cache / "snapshots" / "abc"; snap.mkdir(parents=True)
    (cache / "blobs").mkdir()  # existe mais vide
    (snap / "model.safetensors").write_bytes(b"x" * 200)
    (snap / "config.json").write_bytes(b"y" * 25)
    with patch("anonymator.core.model_status.model_cache_dir", return_value=cache):
        assert installed_size() == 225


def test_announced_download_size_is_derived_from_repo_size():
    """Le libellé annoncé était figé à « ~300 Mo » alors que le dépôt embarque
    les poids en double (pytorch_model.bin + model.safetensors)."""
    from anonymator.core.model_status import (MODEL_DOWNLOAD_SIZE,
                                              MODEL_DOWNLOAD_SIZE_BYTES)
    assert MODEL_DOWNLOAD_SIZE_BYTES == 2_311_737_240
    # C'est précisément ce dépassement qui provoquait l'OverflowError.
    assert MODEL_DOWNLOAD_SIZE_BYTES > 2 ** 31 - 1
    assert MODEL_DOWNLOAD_SIZE == "~2,2 Go"
