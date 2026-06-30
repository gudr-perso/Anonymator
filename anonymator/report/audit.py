import csv
import json
from pathlib import Path


class AuditReport:
    def __init__(self):
        self._entries: dict[tuple[str, str], dict] = {}

    def add(self, etype: str, original: str, tag: str, location: str,
            confirmed: bool = True) -> None:
        key = (etype, original)
        entry = self._entries.setdefault(
            key, {"tag": tag, "occurrences": 0, "locations": [], "confirmed": confirmed})
        entry["occurrences"] += 1
        entry["locations"].append(location)
        entry["confirmed"] = entry["confirmed"] and confirmed

    def to_rows(self) -> list[dict]:
        rows = []
        for (etype, original), e in self._entries.items():
            rows.append({
                "type": etype,
                "original": original,
                "tag": e["tag"],
                "occurrences": e["occurrences"],
                "locations": "; ".join(e["locations"]),
                "confirme": "oui" if e["confirmed"] else "non",
            })
        return rows

    def export_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_rows(), ensure_ascii=False, indent=2),
                        encoding="utf-8")

    def export_csv(self, path: Path) -> None:
        rows = self.to_rows()
        fields = ["type", "original", "tag", "occurrences", "locations", "confirme"]
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
