def looks_structured(value: str) -> bool:
    """Vrai si la valeur ne contient aucune lettre (nombre, date, code, vide)."""
    return not any(ch.isalpha() for ch in value)


def default_maskable_columns(rows: list[list[str]], has_header: bool) -> set[int]:
    data = rows[1:] if has_header else rows
    width = max((len(r) for r in rows), default=0)
    maskable: set[int] = set()
    for col in range(width):
        for row in data:
            if col < len(row) and not looks_structured(row[col]):
                maskable.add(col)
                break
    return maskable
