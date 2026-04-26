import json
from pathlib import Path
from typing import Dict, List, Optional, Set

class LockfileParser:
    @staticmethod
    def parse_package_lock(path: Path) -> Dict[str, Set[str]]:
        """
        Parse package-lock.json and return a mapping of package -> set of its dependencies.
        Supports lockfileVersion 2 and 3.
        """
        if not path.exists():
            return {}

        with open(path, "r") as f:
            data = json.load(f)

        dependency_graph: Dict[str, Set[str]] = {}
        
        # lockfileVersion 2/3 uses 'packages'
        packages = data.get("packages", {})
        for pkg_path, pkg_data in packages.items():
            # Remove 'node_modules/' prefix
            pkg_name = pkg_path.replace("node_modules/", "")
            
            # Use empty string as the key for the root project
            if pkg_path == "":
                pkg_name = ""
            elif "/" in pkg_name and not pkg_name.startswith("@"):
                pkg_name = pkg_name.split("/")[-1]
            
            deps = pkg_data.get("dependencies", {})
            dev_deps = pkg_data.get("devDependencies", {})
            
            all_deps = set(deps.keys()) | set(dev_deps.keys())
            dependency_graph[pkg_name] = all_deps

        return dependency_graph
