from pathlib import Path
from anonymator.files.encoding import detect_encoding

def read_text(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    enc = detect_encoding(data)
    return data.decode(enc), enc

def write_text(text: str, encoding: str, path: Path) -> None:
    path.write_bytes(text.encode(encoding))
