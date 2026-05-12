#!/usr/bin/env python3

import sys
import logging
import yaml
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg import Kg
from fact import Fact
from expression import load_fact_info
from algo_executor import AlgorithmExecutor


def run_test(kg, test_path):
    info = load_fact_info(kg, test_path)
    if info is None:
        return False, f"Cannot load test: {test_path}"

    val_as = info.get("val_as", {}).get("computer/test/case", {})
    description = val_as.get("description", test_path)
    subject = val_as.get("subject", "")
    expected = val_as.get("expected_result")

    if not subject:
        return False, f"{description}: no subject"

    has = info.get("has", {})
    inputs = {}
    for attr, val in has.items():
        if "val" in val:
            inputs[attr] = val["val"]

    try:
        executor = AlgorithmExecutor(kg)
        result = executor.execute(subject, inputs)
    except Exception as e:
        return False, f"{description}: execution error: {e}"

    if expected is not None and result != expected:
        return False, f"{description}: expected {expected}, got {result}"

    return True, f"{description}: OK"


def main():
    parser = argparse.ArgumentParser(description="Run fact-based tests")
    parser.add_argument("fact", nargs='?', help="Fact path to find tests for")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--roots", default="kg",
        help="Comma-separated list of root directories")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    if not args.all and not args.fact:
        parser.error("either provide a fact path or use --all")

    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent.parent

    roots = [project_dir / r.strip() for r in args.roots.split(',')]
    for root in roots:
        if not root.is_dir():
            print(f"ERROR: root directory does not exist: {root}")
            return 1

    with open(project_dir / "schema.yaml", "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f.read())

    kg = Kg(roots, schema)

    passed = 0
    failed = 0
    failures = []

    if args.all:
        for root in roots:
            for yaml_file in root.rglob("*.yaml"):
                fact_path = str(yaml_file.relative_to(root).with_suffix('')).replace('\\', '/')
                if '/test/' not in fact_path:
                    continue
                ok, msg = run_test(kg, fact_path)
                if ok:
                    passed += 1
                else:
                    failed += 1
                    failures.append(msg)
                if args.verbose:
                    print(f"  {'PASS' if ok else 'FAIL'}: {msg}")
    else:
        fact_path = args.fact
        for root in roots:
            test_dir = root / fact_path / "test"
            if not test_dir.is_dir():
                continue
            for yaml_file in test_dir.rglob("*.yaml"):
                test_path = str(yaml_file.relative_to(root).with_suffix('')).replace('\\', '/')
                ok, msg = run_test(kg, test_path)
                if ok:
                    passed += 1
                else:
                    failed += 1
                    failures.append(msg)
                print(f"  {'PASS' if ok else 'FAIL'}: {msg}")

    print(f"\n{passed + failed} tests, {passed} passed, {failed} failed")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
