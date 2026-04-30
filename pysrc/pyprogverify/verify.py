#!/usr/bin/env python3

import sys
import ast
import logging
import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kg import Kg
from fact import Fact

console = Console()

def extract_fact_link_from_annotation(annotation):
    """Extract fact_link(...) args from an Annotated[..., fact_link(...)] annotation."""
    if not (isinstance(annotation, ast.Subscript)
            and isinstance(annotation.value, ast.Name)
            and annotation.value.id == "Annotated"):
        return None
    if not isinstance(annotation.slice, ast.Tuple):
        return None
    for elt in annotation.slice.elts:
        if (isinstance(elt, ast.Call)
            and isinstance(elt.func, ast.Name)
            and elt.func.id == "fact_link"
            and elt.args
            and isinstance(elt.args[0], ast.Constant)):
            fact_path = elt.args[0].value
            field = elt.args[1].value if len(elt.args) > 1 and isinstance(elt.args[1], ast.Constant) else None
            return fact_path, field
    return None

def find_fact_links_in_source(source_path):
    """Find all @fact decorators and fact_link annotations. Returns list of (element_name, fact_path, field_or_None)."""
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    links = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "fact"
                    and dec.args
                    and isinstance(dec.args[0], ast.Constant)):
                    fact_path = dec.args[0].value
                    field = dec.args[1].value if len(dec.args) > 1 and isinstance(dec.args[1], ast.Constant) else None
                    links.append((node.name, fact_path, field))
        if isinstance(node, ast.AnnAssign) and node.target:
            result = extract_fact_link_from_annotation(node.annotation)
            if result:
                fact_path, field = result
                if isinstance(node.target, ast.Attribute):
                    name = f"self.{node.target.attr}"
                elif isinstance(node.target, ast.Name):
                    name = node.target.id
                else:
                    continue
                links.append((name, fact_path, field))
    return links

def verify_source(source_path, kg, results):
    """Verify all @fact links in a source file. Returns number of errors."""
    links = find_fact_links_in_source(source_path)

    if not links:
        console.print(f"  No @fact decorators found in {source_path.name}")
        return 0

    console.print(f"\n[bold]Verifying[/bold] {source_path.name}")

    errors = 0

    for name, fact_path, field in links:
        if kg.load(fact_path) != 0:
            console.print(f"  [red]FAIL[/red]  {name} -> fact '{fact_path}' not found")
            results.append(("link", source_path.name, f"{name} -> {fact_path}", "FAIL"))
            errors += 1
            continue

        fact = Fact(kg, fact_path)
        if fact.construct() != 0:
            console.print(f"  [red]FAIL[/red]  {name} -> fact '{fact_path}' failed to construct")
            results.append(("link", source_path.name, f"{name} -> {fact_path}", "FAIL"))
            errors += 1
            continue

        if field is None:
            console.print(f"  [green]OK[/green]    {name} -> {fact_path}")
            results.append(("link", source_path.name, f"{name} -> {fact_path}", "OK"))
        else:
            has = kg.get_fact(fact_path).get("info", {}).get("has", {})
            if field in has:
                console.print(f"  [green]OK[/green]    {name} -> {fact_path}.{field}")
                results.append(("link", source_path.name, f"{name} -> {fact_path}.{field}", "OK"))
            else:
                console.print(f"  [red]FAIL[/red]  {name} -> {fact_path}.{field} (field not found)")
                results.append(("link", source_path.name, f"{name} -> {fact_path}.{field}", "FAIL"))
                errors += 1

    return errors

def print_summary(results, errors):
    table = Table(title="Verification Summary")
    table.add_column("Type", style="dim")
    table.add_column("File")
    table.add_column("Link")
    table.add_column("Status")

    for kind, file, link, status in results:
        if status == "OK":
            style = "green"
        elif status == "FAIL":
            style = "red bold"
        else:
            style = "yellow"
        table.add_row(kind, file, link, f"[{style}]{status}[/{style}]")

    console.print()
    console.print(table)

    if errors > 0:
        console.print(f"\n[red bold]VERIFICATION FAILED: {errors} error(s)[/red bold]")
    else:
        console.print(f"\n[green bold]VERIFICATION PASSED[/green bold]")

def main():
    parser = argparse.ArgumentParser(
        description="Verify Python source code against facts")
    parser.add_argument("sources", nargs='+',
        help="Python source files to verify")
    parser.add_argument("--roots", default="kg",
        help="Comma-separated list of root directories (default: kg)")
    parser.add_argument("--src-root", default=".",
        help="Root directory for resolving source paths (default: .)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show info messages")
    parser.add_argument("--debug", action="store_true", help="Show all debug messages")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")
    elif args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    project_dir = Path(__file__).resolve().parent.parent.parent
    roots = [project_dir / r.strip() for r in args.roots.split(',')]
    src_root = Path(args.src_root).resolve()

    try:
        with open(project_dir / "schema.yaml", "r", encoding="utf-8") as f:
            import yaml
            schema = yaml.safe_load(f.read())
    except FileNotFoundError:
        console.print("[red]ERROR:[/red] can't open schema.yaml")
        return 1

    kg = Kg(roots, schema)

    results = []
    errors = 0

    for src in args.sources:
        source_path = src_root / src
        if not source_path.exists():
            console.print(f"[red]ERROR:[/red] source file not found: {source_path}")
            errors += 1
            continue
        errors += verify_source(source_path, kg, results)

    print_summary(results, errors)

    return 1 if errors > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
