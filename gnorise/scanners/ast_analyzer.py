from pathlib import Path
from typing import Set, Dict, List
import tree_sitter_languages
from tree_sitter import Node

class ASTAnalyzer:
    def __init__(self):
        try:
            self.js_parser = tree_sitter_languages.get_parser("javascript")
            self.ts_parser = tree_sitter_languages.get_parser("typescript")
            self.tsx_parser = tree_sitter_languages.get_parser("tsx")
        except Exception:
            self.js_parser = None
            self.ts_parser = None
            self.tsx_parser = None

    def _get_parser(self, file_path: Path):
        ext = file_path.suffix
        if ext == ".js" or ext == ".jsx":
            return self.js_parser
        elif ext == ".ts":
            return self.ts_parser
        elif ext == ".tsx":
            return self.tsx_parser
        return None

    def extract_imports(self, file_path: Path) -> Dict[str, Set[str]]:
        """
        Extract all external package imports from a file.
        Returns: {'static': set(), 'dynamic': set(), 'uncertain': set()}
        """
        parser = self._get_parser(file_path)
        if not parser:
            return {'static': set(), 'dynamic': set(), 'uncertain': set()}

        with open(file_path, "rb") as f:
            tree = parser.parse(f.read())

        results = {'static': set(), 'dynamic': set(), 'uncertain': set()}
        self._traverse_tree(tree.root_node, results)
        
        return {
            'static': self._filter_external_packages(results['static']),
            'dynamic': self._filter_external_packages(results['dynamic']),
            'uncertain': self._filter_external_packages(results['uncertain'])
        }

    def _traverse_tree(self, node: Node, results: Dict[str, Set[str]]):
        if node.type == "import_statement":
            source = node.child_by_field_name("source")
            if source:
                results['static'].add(self._clean_import_path(source.text.decode("utf8")))
        
        elif node.type == "export_statement":
            source = node.child_by_field_name("source")
            if source:
                results['static'].add(self._clean_import_path(source.text.decode("utf8")))

        elif node.type == "call_expression":
            function = node.child_by_field_name("function")
            if function:
                func_name = function.text.decode("utf8")
                if func_name in ("require", "import"):
                    arguments = node.child_by_field_name("arguments")
                    if arguments and arguments.child_count >= 3:
                        first_arg = arguments.children[1]
                        
                        # Check if it's a string literal or a variable/expression
                        if first_arg.type in ("string", "string_fragment"):
                            path = self._clean_import_path(first_arg.text.decode("utf8"))
                            if func_name == "require":
                                results['static'].add(path)
                            else:
                                results['dynamic'].add(path)
                        else:
                            # It's a variable or template literal with interpolation
                            results['uncertain'].add("__dynamic_uncertain__")

        for child in node.children:
            self._traverse_tree(child, results)

    def _clean_import_path(self, path: str) -> str:
        path = path.strip("'\"")
        if path.startswith("."):
            return path
        
        parts = path.split("/")
        if path.startswith("@") and len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"
        return parts[0]

    def _filter_external_packages(self, imports: Set[str]) -> Set[str]:
        return {imp for imp in imports if not imp.startswith(".")}
