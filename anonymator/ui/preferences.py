import json
from dataclasses import dataclass, field, asdict
from pathlib import Path


@dataclass
class Preferences:
    theme: str = "cuma"
    output_dir: str | None = None
    entity_overrides: dict[str, bool] = field(default_factory=dict)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2),
                        encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "Preferences":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(theme=data.get("theme", "cuma"),
                   output_dir=data.get("output_dir"),
                   entity_overrides=data.get("entity_overrides", {}))
