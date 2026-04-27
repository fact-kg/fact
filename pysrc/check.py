#!/usr/bin/env python3

# xp -a pysrc/kg.py pysrc/check.py astronomy/universe

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

def check_all(kg, kg_dir):
    """Check all facts in kg directory. Returns 0 if all pass."""
    failed = []
    passed = 0
    for yaml_file in sorted(kg_dir.rglob("*.yaml")):
        fact_name = str(yaml_file.relative_to(kg_dir).with_suffix('')).replace('\\', '/')
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
    args = parser.parse_args()

    if not args.all and not args.name:
        parser.error("either provide a fact name or use --all")

    script_dir = Path(__file__).resolve().parent
    kg_dir = script_dir.parent / "kg"

    schema_file = open(script_dir.parent / "schema.yaml", "r", encoding="utf-8")
    if schema_file.closed:
        print(f"ERROR: can't open {schema_file}")
        return 1
    schema = yaml.safe_load(schema_file.read())

    kg = Kg(kg_dir, schema)

    if args.all:
        return check_all(kg, kg_dir)

    fact_name = args.name
    print(f"Checking fact '{fact_name}'")
    print(f"KG path: {kg_dir}")

    file_path = kg_dir / (fact_name + ".yaml")
    if file_path.exists():
        print(f"The path exists: {file_path}")
    else:
        print(f"ERROR: the path does NOT exist: {file_path}")
        return 1

    return check_one(kg, fact_name)

if __name__ == "__main__":
    import sys
    sys.exit(main())
