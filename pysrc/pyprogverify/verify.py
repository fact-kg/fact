#!/usr/bin/env python3

import sys
import ast
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg import Kg
from fact import Fact

def find_methods_in_fact(kg, fact_name):
    """Extract class_name and method names from a constructed fact."""
    fact_data = kg.get_fact(fact_name)
    info = fact_data.get("info", {})
    has = info.get("has", {})

    class_name = None
    source_file = None
    methods = []

    for attr_name, attr in has.items():
        if attr_name == "class_name":
            class_name = attr.get("val")
        elif attr_name == "source_file":
            source_file = attr.get("val")
        elif attr.get("type") == "computer/sw/lang/python/class_method":
            val_as = attr.get("val_as", {})
            cm = val_as.get("computer/sw/lang/python/class_method", {})
            method_name = cm.get("name")
            if method_name:
                methods.append(method_name)

    return source_file, class_name, methods

def find_class_methods_in_source(source_path, class_name):
    """Parse Python source and extract method names from a class using AST."""
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                n.name for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not n.name.startswith('_')
            ]

    return None

def main():
    parser = argparse.ArgumentParser(
        description="Verify Python source code against facts")
    parser.add_argument("name", help="Fact path, e.g. app/org/igorlesik/fact/pysrc/kg_module")
    parser.add_argument("--roots", default="kg",
        help="Comma-separated list of root directories (default: kg)")
    parser.add_argument("--src-root", default=".",
        help="Root directory for resolving source_file paths (default: .)")
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent.parent.parent
    roots = [project_dir / r.strip() for r in args.roots.split(',')]
    src_root = Path(args.src_root).resolve()

    try:
        with open(project_dir / "schema.yaml", "r", encoding="utf-8") as f:
            import yaml
            schema = yaml.safe_load(f.read())
    except FileNotFoundError:
        print(f"ERROR: can't open schema.yaml")
        return 1

    kg = Kg(roots, schema)

    if kg.load(args.name) != 0:
        print(f"ERROR: could not load fact '{args.name}'")
        return 1

    fact = Fact(kg, args.name)
    if fact.construct() != 0:
        print(f"ERROR: could not construct fact '{args.name}'")
        return 1

    source_file, class_name, fact_methods = find_methods_in_fact(kg, args.name)

    if not source_file:
        print("ERROR: fact has no source_file attribute")
        return 1
    if not class_name:
        print("ERROR: fact has no class_name attribute")
        return 1

    source_path = src_root / source_file
    if not source_path.exists():
        print(f"ERROR: source file not found: {source_path}")
        return 1

    print(f"Verifying {class_name} in {source_file}")
    print(f"  Fact declares {len(fact_methods)} methods: {', '.join(fact_methods)}")

    actual_methods = find_class_methods_in_source(source_path, class_name)

    if actual_methods is None:
        print(f"ERROR: class '{class_name}' not found in {source_file}")
        return 1

    print(f"  Source has {len(actual_methods)} public methods: {', '.join(actual_methods)}")

    errors = 0

    for m in fact_methods:
        if m not in actual_methods:
            print(f"  FAIL: method '{m}' declared in fact but missing from source")
            errors += 1

    for m in actual_methods:
        if m not in fact_methods:
            print(f"  WARN: method '{m}' exists in source but not declared in fact")

    if errors > 0:
        print(f"\nVERIFICATION FAILED: {errors} error(s)")
        return 1

    print("\nVERIFICATION PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
