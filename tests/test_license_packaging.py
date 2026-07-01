import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_license_file_present_and_is_agpl():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text
    assert "Version 3" in text
    assert len(text) > 30_000


def test_pyproject_declares_agpl_spdx():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["license"] == "AGPL-3.0-or-later"


def test_spec_bundles_license_in_zip():
    spec = (ROOT / "anonymator.spec").read_text(encoding="utf-8")
    assert "'LICENSE'" in spec
