from datetime import datetime
from pathlib import Path

def anonymized_path(source: Path, output_dir: Path, when: datetime) -> Path:
    stamp = when.strftime("%Y%m%d%H%M%S")
    return output_dir / f"{source.stem}_ano_{stamp}{source.suffix}"
