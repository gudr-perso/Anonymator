import csv
import io
from dataclasses import dataclass
from pathlib import Path

from anonymator.files.encoding import detect_encoding

_PRIMARY = [";", "|", "\t"]
_FALLBACK = [","]


@dataclass
class CsvDocument:
    rows: list[list[str]]
    delimiter: str
    encoding: str
    has_header: bool
    line_terminator: str


def sniff_delimiter(sample: str) -> str:
    """Choisit le séparateur consistant (même nombre >0 sur chaque ligne non vide).
    Priorité aux séparateurs structurels (;, |, tab) ; la virgule (souvent une
    virgule décimale en français) n'est retenue que si aucun structurel ne convient.
    Défaut ";"."""
    lines = [l for l in sample.splitlines() if l]
    if not lines:
        return ";"

    def best_consistent(candidates):
        best_delim, best_count = None, 0
        for delim in candidates:
            counts = [line.count(delim) for line in lines]
            if all(c == counts[0] for c in counts) and counts[0] > best_count:
                best_delim, best_count = delim, counts[0]
        return best_delim

    return best_consistent(_PRIMARY) or best_consistent(_FALLBACK) or ";"


def read_csv(path: Path) -> CsvDocument:
    data = path.read_bytes()
    encoding = detect_encoding(data)
    text = data.decode(encoding)
    line_terminator = "\r\n" if "\r\n" in text else "\n"
    sample = text[:4096]
    delimiter = sniff_delimiter(sample)
    try:
        has_header = csv.Sniffer().has_header(sample)
    except csv.Error:
        has_header = False
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    rows = [row for row in reader]
    return CsvDocument(rows, delimiter, encoding, has_header, line_terminator)


def write_csv(doc: CsvDocument, path: Path) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter=doc.delimiter,
                        lineterminator=doc.line_terminator,
                        quoting=csv.QUOTE_MINIMAL)
    writer.writerows(doc.rows)
    path.write_bytes(buffer.getvalue().encode(doc.encoding))
