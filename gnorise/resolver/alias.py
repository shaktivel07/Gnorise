import json
import re
from pathlib import Path
from typing import Optional, Dict

class AliasResolver:
    def __init__(self, root: Path):
        self.root = root
        self.rules: Dict[str, str] = {}
        self.base_url: Optional[Path] = None
        self._load_tsconfig()
        
    def _load_tsconfig(self):
        cfg = self.root / "tsconfig.json"
        if not cfg.exists():
            return
        try:
            with open(cfg, "r") as f:
                data = json.load(f)
                
            compiler_options = data.get("compilerOptions", {})
            
            # Handle baseUrl
            base_url_val = compiler_options.get("baseUrl")
            if base_url_val:
                self.base_url = self.root / base_url_val
            
            # Handle paths
            paths = compiler_options.get("paths", {})
            for alias, targets in paths.items():
                if not targets:
                    continue
                key = alias.rstrip("/*")
                val = targets[0].rstrip("/*")
                
                # Resolve relative to baseUrl if it exists, otherwise root
                base = self.base_url if self.base_url else self.root
                self.rules[key] = str(base / val)
        except Exception:
            pass
        
    def resolve(self, import_path: str) -> Optional[str]:
        if import_path.startswith("."):
            return None
            
        # 1. Try paths aliases
        for prefix, base in self.rules.items():
            if import_path == prefix or import_path.startswith(prefix + "/"):
                remainder = import_path[len(prefix)+1:] if "/" in import_path else ""
                resolved = Path(base) / remainder
                return str(resolved.absolute())
        
        # 2. Try baseUrl resolution
        if self.base_url:
            potential_path = self.base_url / import_path
            # Check if it points to an actual file or directory
            if potential_path.exists() or (potential_path.with_suffix(".ts")).exists() or (potential_path.with_suffix(".tsx")).exists():
                return str(potential_path.absolute())
                
        return None
