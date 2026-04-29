#!/usr/bin/env python3

import sys
import ast
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg import Kg
from fact import Fact

def find_class_info_in_fact(kg, fact_name):
    """Extract class_name, methods, and parent classes from a constructed fact."""
    fact_data = kg.get_fact(fact_name)
    info = fact_data.get("info", {})
    has = info.get("has", {})

    class_name = None
    source_file = None
    methods = []
    parent_classes = []

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
        elif attr.get("type") == "computer/sw/lang/python/class":
            val_as = attr.get("val_as", {})
            pc = val_as.get("computer/sw/lang/python/class", {})
            parent_name = pc.get("name")
            if parent_name:
                parent_classes.append(parent_name)

    return source_file, class_name, methods, parent_classes

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

def find_class_bases_in_source(source_path, class_name):
    """Parse Python source and extract base class names from a class using AST."""
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return [
                base.id for base in node.bases
                if isinstance(base, ast.Name)
            ]

    return None

def find_module_facts(kg, program_fact_name):
    """Follow has references from a program fact to find verifiable modules."""
    info = kg.get_fact(program_fact_name).get("info", {})
    has = info.get("has", {})
    modules = []
    for attr_name, attr in has.items():
        attr_type = attr.get("type", "")
        if attr_type and attr_type not in ("str", "num", "list"):
            if kg.load(attr_type) != 0:
                continue
            fact = Fact(kg, attr_type)
            if fact.construct() != 0:
                continue
            module_has = kg.get_fact(attr_type).get("info", {}).get("has", {})
            has_class = "class_name" in module_has
            has_methods = any(
                v.get("type") == "computer/sw/lang/python/class_method"
                for v in module_has.values() if isinstance(v, dict)
            )
            if has_class and has_methods:
                modules.append(attr_type)
    return modules

def verify_module(kg, fact_name, src_root):
    """Verify a single module fact against source. Returns number of errors."""
    source_file, class_name, fact_methods, fact_parents = find_class_info_in_fact(kg, fact_name)

    if not source_file:
        print(f"  ERROR: fact '{fact_name}' has no source_file attribute")
        return 1
    if not class_name:
        print(f"  ERROR: fact '{fact_name}' has no class_name attribute")
        return 1

    source_path = src_root / source_file
    if not source_path.exists():
        print(f"  ERROR: source file not found: {source_path}")
        return 1

    print(f"Verifying {class_name} in {source_file}")

    errors = 0

    if fact_parents:
        print(f"  Fact declares parent classes: {', '.join(fact_parents)}")
        actual_bases = find_class_bases_in_source(source_path, class_name)
        if actual_bases is None:
            print(f"  ERROR: class '{class_name}' not found in {source_file}")
            return 1
        for p in fact_parents:
            if p not in actual_bases:
                print(f"  FAIL: parent class '{p}' declared in fact but not in source")
                errors += 1
            else:
                print(f"  OK: parent class '{p}'")

    print(f"  Fact declares {len(fact_methods)} methods: {', '.join(fact_methods)}")

    actual_methods = find_class_methods_in_source(source_path, class_name)

    if actual_methods is None:
        print(f"  ERROR: class '{class_name}' not found in {source_file}")
        return 1

    print(f"  Source has {len(actual_methods)} public methods: {', '.join(actual_methods)}")

    for m in fact_methods:
        if m not in actual_methods:
            print(f"  FAIL: method '{m}' declared in fact but missing from source")
            errors += 1

    for m in actual_methods:
        if m not in fact_methods:
            print(f"  WARN: method '{m}' exists in source but not declared in fact")

    return errors

def main():
    parser = argparse.ArgumentParser(
        description="Verify Python source code against facts")
    parser.add_argument("name",
        help="Fact path to a program or module, e.g. app/org/igorlesik/fact/pysrc")
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
        print("ERROR: can't open schema.yaml")
        return 1

    kg = Kg(roots, schema)

    if kg.load(args.name) != 0:
        print(f"ERROR: could not load fact '{args.name}'")
        return 1

    fact = Fact(kg, args.name)
    if fact.construct() != 0:
        print(f"ERROR: could not construct fact '{args.name}'")
        return 1

    info = kg.get_fact(args.name).get("info", {})
    has = info.get("has", {})

    if "class_name" in has:
        errors = verify_module(kg, args.name, src_root)
    else:
        modules = find_module_facts(kg, args.name)
        if not modules:
            print(f"No verifiable modules found in '{args.name}'")
            return 0
        print(f"Found {len(modules)} verifiable module(s)\n")
        errors = 0
        for module in modules:
            errors += verify_module(kg, module, src_root)
            print()

    if errors > 0:
        print(f"VERIFICATION FAILED: {errors} error(s)")
        return 1

    print("VERIFICATION PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
