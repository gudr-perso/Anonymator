import csv
import io
from dataclasses import dataclass
from pathlib import Path

from anonymator.files.encoding import detect_encoding

_CANDIDATES = [";", "|", ",", "\t"]


@dataclass
class CsvDocument:
    rows: list[list[str]]
    delimiter: str
    encoding: str
    has_header: bool
    line_terminator: str


def sniff_delimiter(sample: str) -> str:
    """Detect CSV delimiter from a text sample.

    Strategy: for each candidate, check that it appears a consistent number of
    times on every non-empty line.  Pick the candidate with the highest
    consistent per-line count.  Falls back to ";" when nothing matches.
    """
    lines = [l for l in sample.splitlines() if l]
    if not lines:
        return ";"

    best_delim = ";"
    best_count = 0

    for delim in _CANDIDATES:
        counts = [line.count(delim) for line in lines]
        if counts and all(c == counts[0] for c in counts) and counts[0] > 0:
            if counts[0] > best_count:
                best_count = counts[0]
                best_delim = delim

    return best_delim


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
