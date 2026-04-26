import os
from pathlib import Path
from typing import List, Set
import fnmatch

class IgnoreSystem:
    DEFAULT_IGNORES = {
        "node_modules",
        ".git",
        ".svn",
        ".hg",
        "dist",
        "build",
        ".next",
        ".nuxt",
        "vendor",
        ".gnorise",
        "__pycache__",
        ".venv",
        "venv",
        "env",
    }

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.ignore_patterns: Set[str] = self.DEFAULT_IGNORES.copy()
        self._load_ignore_file()

    def _load_ignore_file(self):
        ignore_file = self.root_dir / ".gnoriseignore"
        if ignore_file.exists():
            with open(ignore_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        self.ignore_patterns.add(line)

    def should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored based on the patterns."""
        try:
            relative_path = path.relative_to(self.root_dir)
        except ValueError:
            # Path is not under root_dir, probably shouldn't happen in normal use
            return True

        parts = relative_path.parts
        for part in parts:
            for pattern in self.ignore_patterns:
                if fnmatch.fnmatch(part, pattern):
                    return True
        return False
