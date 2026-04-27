#!/usr/bin/env python3

import yaml
import argparse
from pathlib import Path

from kg import Kg
from fact import Fact

def check_one(kg, fact_name):
    """Check a single fact. Returns 0 on success."""
    if 0 != kg.load(fact_name):
        print(f"ERROR: could not load '{fact_name}'")
        return 1
    fact = Fact(kg, fact_name)
    if 0 != fact.construct():
        print(f"ERROR: can not construct '{fact_name}'")
        return 2
    return 0

def check_all(kg, roots):
    """Check all facts across all roots. Returns 0 if all pass."""
    failed = []
    passed = 0
    for root in roots:
        for yaml_file in sorted(root.rglob("*.yaml")):
            fact_name = str(yaml_file.relative_to(root).with_suffix('')).replace('\\', '/')
            if 0 != check_one(kg, fact_name):
                failed.append(fact_name)
            else:
                passed += 1
    print(f"\n{passed + len(failed)} checked, {passed} passed, {len(failed)} failed")
    if failed:
        for f in failed:
            print(f"  FAIL: {f}")
        return 1
    return 0

def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Check a fact")
    parser.add_argument("name", nargs='?', help="Fact path, e.g. math/function")
    parser.add_argument("--all", action="store_true", help="Check all facts in kg directory")
    parser.add_argument("--roots", default="kg",
        help="Comma-separated list of root directories (default: kg)")
    args = parser.parse_args()

    if not args.all and not args.name:
        parser.error("either provide a fact name or use --all")

    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent

    roots = [project_dir / r.strip() for r in args.roots.split(',')]
    for root in roots:
        if not root.is_dir():
            print(f"ERROR: root directory does not exist: {root}")
            return 1

    try:
        with open(project_dir / "schema.yaml", "r", encoding="utf-8") as schema_file:
            schema = yaml.safe_load(schema_file.read())
    except FileNotFoundError:
        print(f"ERROR: can't open {project_dir / 'schema.yaml'}")
        return 1

    kg = Kg(roots, schema)

    if args.all:
        return check_all(kg, roots)

    fact_name = args.name
    print(f"Checking fact '{fact_name}'")

    fact_path = kg.find_fact_file(fact_name)
    if fact_path is None:
        return 1
    print(f"The path exists: {fact_path}")

    return check_one(kg, fact_name)

if __name__ == "__main__":
    import sys
    sys.exit(main())
