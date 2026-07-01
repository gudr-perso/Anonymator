import json
import re
from dataclasses import dataclass
from pathlib import Path


def compile_pattern(mode: str, pattern: str) -> "re.Pattern | None":
    """Traduit un motif utilisateur en regex ancrée (fullmatch), casse ignorée.

    mode="simple" : # → un chiffre, ? → un caractère, * → n'importe quelle
    suite ; tout autre caractère est échappé littéralement.
    mode="regex"  : le motif est une regex brute.
    Retourne None si la regex (mode expert) est invalide.
    """
    if mode == "simple":
        parts = []
        for ch in pattern:
            if ch == "#":
                parts.append(r"\d")
            elif ch == "?":
                parts.append(".")
            elif ch == "*":
                parts.append(".*")
            else:
                parts.append(re.escape(ch))
        regex = "".join(parts)
    else:
        regex = pattern
    try:
        return re.compile(regex, re.IGNORECASE)
    except re.error:
        return None


@dataclass
class Rule:
    mode: str          # "simple" | "regex"
    pattern: str
    action: str        # "keep" | "mask"
    enabled: bool = True
    note: str = ""


class UserRules:
    def __init__(self, rules: list[Rule]):
        self.rules = rules
        self._compiled: list[tuple[Rule, "re.Pattern"]] = []
        self.invalid: list[Rule] = []
        for r in rules:
            pat = compile_pattern(r.mode, r.pattern)
            if pat is None:
                self.invalid.append(r)
            else:
                self._compiled.append((r, pat))

    def keep_matches(self, value: str) -> bool:
        return any(r.enabled and r.action == "keep" and pat.fullmatch(value)
                   for r, pat in self._compiled)

    def mask_rules(self) -> list[tuple[Rule, "re.Pattern"]]:
        return [(r, pat) for r, pat in self._compiled
                if r.enabled and r.action == "mask"]

    # --- persistance -------------------------------------------------
    @classmethod
    def from_dicts(cls, dicts: list[dict]) -> "UserRules":
        rules = [Rule(mode=d.get("mode", "simple"),
                      pattern=d.get("pattern", ""),
                      action=d.get("action", "keep"),
                      enabled=d.get("enabled", True),
                      note=d.get("note", ""))
                 for d in dicts]
        return cls(rules)

    def to_dicts(self) -> list[dict]:
        return [{"mode": r.mode, "pattern": r.pattern, "action": r.action,
                 "enabled": r.enabled, "note": r.note} for r in self.rules]

    @classmethod
    def load(cls, path: Path,
             fallback_terms: list[str] | None = None) -> "UserRules":
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls.from_dicts(data.get("rules", []))
        rules = [Rule("simple", t, "keep", True, "importé de la liste d'exclusion")
                 for t in (fallback_terms or [])]
        obj = cls(rules)
        obj.save(path)
        return obj

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"rules": self.to_dicts()},
                                   ensure_ascii=False, indent=2),
                        encoding="utf-8")
