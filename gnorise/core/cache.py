import hashlib
import json
from pathlib import Path
from typing import Dict, Optional

class FileCache:
    def __init__(self, cache_dir: Path = Path(".gnorise/cache")):
        self.cache_dir = cache_dir
        self.cache_file = cache_dir / "file_hashes.json"
        self.hashes: Dict[str, str] = {}
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self.hashes = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.hashes = {}

    def save(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        with open(self.cache_file, "w") as f:
            json.dump(self.hashes, f, indent=2)

    def _file_key(self, file_path: Path) -> str:
        """Fast key based on path, mtime, and size."""
        stat = file_path.stat()
        return f"{file_path.absolute()}:{stat.st_mtime_ns}:{stat.st_size}"

    def is_changed(self, file_path: Path) -> bool:
        """Check if a file has changed since the last scan."""
        path_str = str(file_path.absolute())
        current_key = self._file_key(file_path)
        
        if path_str not in self.hashes:
            return True
        
        return self.hashes[path_str] != current_key

    def update(self, file_path: Path):
        """Update the stored key for a file."""
        path_str = str(file_path.absolute())
        self.hashes[path_str] = self._file_key(file_path)
