import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field

class PackageManifest(BaseModel):
    name: Optional[str] = None
    version: Optional[str] = None
    dependencies: Dict[str, str] = Field(default_factory=dict)
    dev_dependencies: Dict[str, str] = Field(default_factory=dict, alias="devDependencies")
    
    class Config:
        populate_by_name = True

class ManifestParser:
    @staticmethod
    def parse_package_json(path: Path) -> PackageManifest:
        """Parse package.json and return a PackageManifest object."""
        if not path.exists():
            raise FileNotFoundError(f"package.json not found at {path}")
            
        with open(path, "r") as f:
            data = json.load(f)
            return PackageManifest(**data)

    @staticmethod
    def get_all_dependencies(manifest: PackageManifest) -> Set[str]:
        """Return a set of all dependency names (prod + dev)."""
        return set(manifest.dependencies.keys()) | set(manifest.dev_dependencies.keys())
