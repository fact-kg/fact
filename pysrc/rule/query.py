#!/usr/bin/env python3
"""Interactive rule engine query tool.

Usage:
  python pysrc/rule/query.py --roots kg,kg2,../fact_physics,../fact_math,../fact_computer
  query.bat
"""

import sys
import yaml
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg import Kg
from rule.engine import RuleEngine


HELP_TEXT = """Commands:
  ?X part ?Y                  -- find facts with part relationship
  ?X is ?Y                    -- find facts by type
  ?X has ?prop                -- find facts that have a property
  ?X has ?prop ?val           -- find facts with property matching value
  find <substring>             -- search fact paths by substring
  transitive <fact> [relation] -- follow transitive chain (default: part)
  rules                       -- list loaded inference rules
  help                        -- show this help
  quit                        -- exit

Variables start with ?. Constants are literal fact paths or values.
Multiple conditions: ?X part ?Y AND ?Y part ?Z

Examples:
  ?X part astronomy/universe
  ?X is physics/atom/element
  ?X has wikipedia_url
  transitive astronomy/location/milky_way/solar_system/earth/luna part
"""


def main():
    parser = argparse.ArgumentParser(
        description="Query the knowledge graph with rule inference",
        epilog=HELP_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--roots", default="kg",
        help="Comma-separated list of root directories")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("query", nargs="*", help="Query to run (interactive if omitted)")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    script_dir = Path(__file__).resolve().parent
    project_dir = script_dir.parent.parent

    roots = [project_dir / r.strip() for r in args.roots.split(',')]
    print(f"Loading schema and {len(roots)} roots...")
    with open(project_dir / "schema.yaml", "r", encoding="utf-8") as f:
        schema = yaml.safe_load(f.read())

    kg = Kg(roots, schema)
    print("Loading rules...")
    engine = RuleEngine(kg, roots)
    print(f"Ready. {len(engine.rules)} rules loaded. Type 'help' for commands.")

    if args.query:
        run_query(engine, " ".join(args.query))
        return

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line or line == "quit":
            break
        run_query(engine, line)


def run_query(engine, line):
    parts = line.split()

    if line == "help":
        print(HELP_TEXT)
        return

    # find command: find <substring>
    if parts[0] == "find" and len(parts) >= 2:
        substring = " ".join(parts[1:]).lower()
        matches = [fp for fp in engine.kg.get_dict().keys()
                   if substring in fp.lower()]
        matches.sort()
        if matches:
            for m in matches:
                print(f"  {m}")
            print(f"  ({len(matches)} found)")
        else:
            print("  (no matches)")
        return

    # transitive command: transitive <fact> <relation>
    if parts[0] == "transitive" and len(parts) >= 2:
        fact_path = parts[1]
        relation = parts[2] if len(parts) > 2 else "part"
        results = engine.find_transitive(fact_path, relation)
        if results:
            for r in results:
                print(f"  {r}")
        else:
            print("  (no results)")
        return

    # rules command: list loaded rules
    if line == "rules":
        for r in engine.rules:
            print(f"  {r['path']}: {r['when']} => {r['then']}")
        return

    # pattern query
    results = engine.query(line)
    if results:
        for r in results:
            vals = ", ".join(f"{k}={v}" for k, v in r.items())
            print(f"  {vals}")
        print(f"  ({len(results)} results)")
    else:
        print("  (no results)")


if __name__ == "__main__":
    main()
