from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
import os

from gnorise.core.cache import FileCache
from gnorise.core.config import IgnoreSystem
from gnorise.parsers.manifest import ManifestParser, PackageManifest
from gnorise.parsers.lockfile import LockfileParser
from gnorise.scanners.ast_analyzer import ASTAnalyzer
from gnorise.core.scorer import DepScore, Evidence, UsageStatus
from gnorise.resolver.alias import AliasResolver
from gnorise.core.awareness import CONFIG_TO_PACKAGES

@dataclass
class UsageInfo:
    status: UsageStatus
    confidence: int
    files: List[Path] = field(default_factory=list)
    reason: Optional[str] = None
    evidence: List[Evidence] = field(default_factory=list)

@dataclass
class ScanResult:
    manifest: PackageManifest
    dependency_graph: Dict[str, Set[str]] = field(default_factory=dict)
    package_usage: Dict[str, UsageInfo] = field(default_factory=dict)

class GnoriseEngine:
    KNOWN_CLI_TOOLS = {
        "eslint", "prettier", "jest", "vitest", "nodemon", "typescript", 
        "vite", "webpack", "babel", "rollup", "husky", "lint-staged"
    }
    
    # Framework Magic whitelists
    KNOWN_FRAMEWORK_DEPS = {
        "next": ["react", "react-dom", "next"],
        "express": ["express"],
        "react": ["react", "react-dom"],
        "vue": ["vue"],
        "svelte": ["svelte"],
    }

    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.cache = FileCache()
        self.ignore_system = IgnoreSystem(root_dir)
        self.ast_analyzer = ASTAnalyzer()
        self.resolver = AliasResolver(root_dir)

    def run_scan(self) -> ScanResult:
        # 1. Parse Manifest
        manifest_path = self.root_dir / "package.json"
        manifest = ManifestParser.parse_package_json(manifest_path)
        
        # 2. Parse Lockfile
        lockfile_path = self.root_dir / "package-lock.json"
        dependency_graph = LockfileParser.parse_package_lock(lockfile_path)
        
        # 3. Detect present config files
        present_configs = set()
        for config_file in CONFIG_TO_PACKAGES:
            if (self.root_dir / config_file).exists():
                present_configs.add(config_file)
        
        config_used_packages = set()
        for config in present_configs:
            config_used_packages.update(CONFIG_TO_PACKAGES[config])
        
        # 4. Analyze Code Usage
        # usage_data[pkg] = {'static': {files}, 'dynamic': {files}, 'uncertain': {files}}
        usage_data: Dict[str, Dict[str, Set[Path]]] = {
            pkg: {'static': set(), 'dynamic': set(), 'uncertain': set()} 
            for pkg in ManifestParser.get_all_dependencies(manifest)
        }
        
        for file_path in self._walk_project():
            if file_path.suffix in (".js", ".jsx", ".ts", ".tsx"):
                imports_dict = self.ast_analyzer.extract_imports(file_path)
                
                for type_key in ['static', 'dynamic', 'uncertain']:
                    for imp in imports_dict[type_key]:
                        # Try to resolve alias or get package name
                        resolved = self.resolver.resolve(imp)
                        
                        if resolved:
                            # It's a project file (alias), skip mapping to node_modules
                            continue
                            
                        # Extract package name (e.g., 'lodash/fp' -> 'lodash')
                        pkg_name = imp
                        if not imp.startswith("."):
                            parts = imp.split("/")
                            if imp.startswith("@") and len(parts) >= 2:
                                pkg_name = f"{parts[0]}/{parts[1]}"
                            else:
                                pkg_name = parts[0]

                        if pkg_name in usage_data:
                            usage_data[pkg_name][type_key].add(file_path)
        
        self.cache.save()
        
        # 5. Intelligent Classification using Scorer
        package_usage: Dict[str, UsageInfo] = {}
        all_deps = ManifestParser.get_all_dependencies(manifest)
        dev_deps = set(manifest.dev_dependencies.keys())

        # Determine if we are in a framework
        active_frameworks = [f for f in self.KNOWN_FRAMEWORK_DEPS if f in all_deps]

        for pkg in all_deps:
            pkg_usage = usage_data.get(pkg, {'static': set(), 'dynamic': set(), 'uncertain': set()})
            
            # Check Framework Magic
            is_framework_managed = any(pkg in self.KNOWN_FRAMEWORK_DEPS[f] for f in active_frameworks)
            
            scorer = DepScore(
                name=pkg, 
                version=manifest.dependencies.get(pkg) or manifest.dev_dependencies.get(pkg, "0.0.0"),
                is_dev=(pkg in dev_deps),
                is_framework_managed=(pkg.lower() in self.KNOWN_CLI_TOOLS or is_framework_managed),
                used_by_config=(pkg in config_used_packages)
            )
            
            status, confidence, evidence = scorer.calculate({
                "static": [str(f.relative_to(self.root_dir)) for f in pkg_usage['static']],
                "dynamic": [str(f.relative_to(self.root_dir)) for f in pkg_usage['dynamic']],
                "uncertain": [str(f.relative_to(self.root_dir)) for f in pkg_usage['uncertain']]
            })
            
            all_files = list(pkg_usage['static'] | pkg_usage['dynamic'])
            
            package_usage[pkg] = UsageInfo(
                status=status,
                confidence=confidence,
                files=all_files,
                reason=evidence[0].explanation if evidence else None,
                evidence=evidence
            )
        
        return ScanResult(
            manifest=manifest,
            dependency_graph=dependency_graph,
            package_usage=package_usage
        )

    def get_dependency_path(self, target: str, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Finds all paths from the root project to the target package."""
        paths = []
        root_deps = graph.get("", set())
        if target in root_deps:
            paths.append(["(root)", target])
            
        visited = set()
        
        def find_paths(current, target, path):
            if current == target:
                paths.append(list(path))
                return
            if current in visited or len(path) > 5:
                return
            
            visited.add(current)
            for neighbor in graph.get(current, set()):
                path.append(neighbor)
                find_paths(neighbor, target, path)
                path.pop()
            visited.remove(current)

        for dep in root_deps:
            if dep != target:
                find_paths(dep, target, ["(root)", dep])
                
        return sorted(paths, key=len)[:3]

    def _walk_project(self):
        for root, dirs, files in os.walk(self.root_dir):
            root_path = Path(root)
            dirs[:] = [d for d in dirs if not self.ignore_system.should_ignore(root_path / d)]
            for file in files:
                file_path = root_path / file
                if not self.ignore_system.should_ignore(file_path):
                    yield file_path
