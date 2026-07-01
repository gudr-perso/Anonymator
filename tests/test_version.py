import re
import tomllib
from pathlib import Path

import anonymator

_SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def test_version_is_semver():
    assert isinstance(anonymator.__version__, str)
    assert _SEMVER.match(anonymator.__version__), anonymator.__version__


def test_pyproject_version_matches_package():
    root = Path(__file__).resolve().parents[1]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["version"] == anonymator.__version__
