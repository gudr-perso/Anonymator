from pathlib import Path
from anonymator.ui.preferences import Preferences


def test_defaults():
    p = Preferences()
    assert p.theme == "cuma"
    assert p.output_dir is None
    assert p.entity_overrides == {}


def test_roundtrip_save_load(tmp_path):
    path = tmp_path / "prefs.json"
    p = Preferences(theme="cap", output_dir="D:/out",
                    entity_overrides={"BIC": True})
    p.save(path)
    loaded = Preferences.load(path)
    assert loaded.theme == "cap"
    assert loaded.output_dir == "D:/out"
    assert loaded.entity_overrides == {"BIC": True}


def test_load_missing_file_returns_defaults(tmp_path):
    assert Preferences.load(tmp_path / "absent.json").theme == "cuma"
