#!/usr/bin/env python3

import logging
import yaml
import argparse
from pathlib import Path

from rich.console import Console
from kg import Kg
from fact import Fact
from fact_decorator import fact

@fact("app/org/igorlesik/fact/pysrc/checker/check_one")
def check_one(kg, fact_name, skip_schema_check=False):
    """Check a single fact. Returns 0 on success."""
    if 0 != kg.load(fact_name, skip_schema_check=skip_schema_check):
        logging.error("could not load '%s'", fact_name)
        return 1
    fact = Fact(kg, fact_name)
    if 0 != fact.construct():
        logging.error("can not construct '%s'", fact_name)
        return 2
    return 0

@fact("app/org/igorlesik/fact/pysrc/checker/check_all")
def check_all(kg, roots, use_progress=False, new_only_ts=None):
    """Check all facts across all roots. Returns 0 if all pass."""
    failed = []
    passed = 0
    checked = 0
    skipped = 0

    def process_file(yaml_file, root):
        nonlocal passed, skipped
        fact_name = str(yaml_file.relative_to(root).with_suffix('')).replace('\\', '/')
        skip_schema = False
        if new_only_ts is not None:
            if yaml_file.stat().st_mtime <= new_only_ts:
                skip_schema = True
                skipped += 1
        if 0 != check_one(kg, fact_name, skip_schema_check=skip_schema):
            failed.append(fact_name)
        else:
            passed += 1

    if use_progress:
        console = Console()
        status = console.status("Checking facts...")
        with status:
            for root in roots:
                for yaml_file in root.rglob("*.yaml"):
                    checked += 1
                    status.update(f"Checking facts... {checked}")
                    process_file(yaml_file, root)
    else:
        for root in roots:
            for yaml_file in root.rglob("*.yaml"):
                checked += 1
                process_file(yaml_file, root)

    summary = f"\n{passed + len(failed)} checked, {passed} passed, {len(failed)} failed"
    if new_only_ts is not None:
        summary += f", {skipped} schema-skipped"
    print(summary)
    if failed:
        for f in failed:
            print(f"  FAIL: {f}")
        return 1
    return 0

@fact("app/org/igorlesik/fact/pysrc/checker", "function_main")
def main():
    """Main entry point."""

    parser = argparse.ArgumentParser(
        description="Check a fact")
    parser.add_argument("name", nargs='?', help="Fact path, e.g. math/function")
    parser.add_argument("--all", action="store_true", help="Check all facts in kg directory")
    parser.add_argument("--roots", default="kg",
        help="Comma-separated list of root directories (default: kg)")
    parser.add_argument("--new-only", action="store_true",
        help="Skip schema check for files unchanged since last successful run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show info messages")
    parser.add_argument("--debug", action="store_true", help="Show all debug messages")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    elif args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

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

    import time
    import sys
    t0 = time.perf_counter()

    def deep_sizeof(obj, seen=None):
        if seen is None:
            seen = set()
        obj_id = id(obj)
        if obj_id in seen:
            return 0
        seen.add(obj_id)
        size = sys.getsizeof(obj)
        if isinstance(obj, dict):
            for k, v in obj.items():
                size += deep_sizeof(k, seen) + deep_sizeof(v, seen)
        elif isinstance(obj, (list, tuple, set, frozenset)):
            for item in obj:
                size += deep_sizeof(item, seen)
        return size

    last_check_file = project_dir / ".last_check"
    new_only_ts = None
    if args.new_only:
        if last_check_file.exists():
            new_only_ts = last_check_file.stat().st_mtime
        else:
            new_only_ts = 0

    if args.all:
        use_progress = not args.verbose and not args.debug
        result = check_all(kg, roots, use_progress, new_only_ts=new_only_ts)
        elapsed = time.perf_counter() - t0
        mem = deep_sizeof(kg.data)
        print(f"Time: {elapsed:.3f}s, KG memory: {mem / 1048576:.1f} MB")
        if result == 0:
            last_check_file.touch()
        return result

    fact_name = args.name
    print(f"Checking fact '{fact_name}'")

    fact_path = kg.find_fact_file(fact_name)
    if fact_path is None:
        return 1
    print(f"The path exists: {fact_path}")

    result = check_one(kg, fact_name)
    elapsed = time.perf_counter() - t0
    mem = sys.getsizeof(kg.data) + sum(sys.getsizeof(v) for v in kg.data.values())
    print(f"Time: {elapsed:.3f}s, KG memory: {mem / 1048576:.1f} MB")
    return result

if __name__ == "__main__":
    import sys
    sys.exit(main())
