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

def test_available_when_snapshots_exist(tmp_path):
    fake_dir = tmp_path / "models--urchade--gliner_multi-v2.1" / "snapshots" / "abc123"
    fake_dir.mkdir(parents=True)
    with patch("anonymator.core.model_status.model_cache_dir",
               return_value=tmp_path / "models--urchade--gliner_multi-v2.1"):
        assert is_model_available() is True

def test_unavailable_when_dir_absent(tmp_path):
    with patch("anonymator.core.model_status.model_cache_dir",
               return_value=tmp_path / "absent"):
        assert is_model_available() is False
