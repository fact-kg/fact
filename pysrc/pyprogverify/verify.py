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

def find_class_in_source(source_path, class_name):
    """Parse Python source and extract methods and base classes in one pass."""
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            methods = [
                n.name for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not n.name.startswith('_')
            ]
            bases = [
                base.id for base in node.bases
                if isinstance(base, ast.Name)
            ]
            return methods, bases

    return None, None

def find_fact_decorators_in_source(source_path):
    """Find all @fact(...) decorators on classes and functions. Returns {name: fact_path}."""
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    result = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call)
                    and isinstance(dec.func, ast.Name)
                    and dec.func.id == "fact"
                    and dec.args
                    and isinstance(dec.args[0], ast.Constant)):
                    result[node.name] = dec.args[0].value
    return result

def find_top_level_functions_in_source(source_path):
    """Find top-level function names in a Python source file."""
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    return [
        node.name for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith('_')
    ]

def find_function_info_in_fact(kg, fact_name):
    """Extract inline function names and referenced function facts."""
    fact_data = kg.get_fact(fact_name)
    info = fact_data.get("info", {})
    has = info.get("has", {})

    source_file = None
    inline_functions = []
    referenced_functions = []

    for attr_name, attr in has.items():
        if attr_name == "source_file":
            source_file = attr.get("val")
        elif attr.get("type") == "computer/sw/lang/python/function":
            val_as = attr.get("val_as", {})
            fn = val_as.get("computer/sw/lang/python/function", {})
            fn_name = fn.get("name")
            if fn_name:
                inline_functions.append(fn_name)
        else:
            attr_type = attr.get("type", "")
            if attr_type and attr_type not in ("str", "num", "list"):
                if kg.is_loaded(attr_type):
                    ref_data = kg.get_fact(attr_type)
                    if "info" not in ref_data:
                        Fact(kg, attr_type).construct()
                    ref_info = ref_data.get("info", {})
                    ref_types = ref_info.get("type", [])
                    if "computer/sw/lang/python/function" in ref_types:
                        ref_as = ref_info.get("val_as", {})
                        fn = ref_as.get("computer/sw/lang/python/function", {})
                        fn_name = fn.get("name")
                        if fn_name:
                            referenced_functions.append((fn_name, attr_type))

    return source_file, inline_functions, referenced_functions

def find_module_facts(kg, program_fact_name):
    """Follow has references from a program fact to find verifiable modules."""
    info = kg.get_fact(program_fact_name).get("info", {})
    has = info.get("has", {})
    modules = []
    for attr_name, attr in has.items():
        attr_type = attr.get("type", "")
        if attr_type and attr_type not in ("str", "num", "list"):
            fact_data = kg.get_fact(attr_type) if kg.is_loaded(attr_type) else None
            if fact_data is None:
                if kg.load(attr_type) != 0:
                    continue
                fact_data = kg.get_fact(attr_type)
            if "info" not in fact_data:
                fact = Fact(kg, attr_type)
                if fact.construct() != 0:
                    continue
            module_has = fact_data.get("info", {}).get("has", {})
            has_class = "class_name" in module_has
            has_methods = any(
                v.get("type") == "computer/sw/lang/python/class_method"
                for v in module_has.values() if isinstance(v, dict)
            )
            has_functions = any(
                v.get("type") == "computer/sw/lang/python/function"
                for v in module_has.values() if isinstance(v, dict)
            )
            has_func_refs = any(
                v.get("type", "") not in ("str", "num", "list", "")
                and kg.is_loaded(v.get("type", ""))
                and "computer/sw/lang/python/function" in kg.get_fact(v["type"]).get("info", {}).get("type", [])
                for v in module_has.values() if isinstance(v, dict)
            )
            if (has_class and has_methods) or has_functions or has_func_refs:
                modules.append(attr_type)
    return modules

def verify_module(kg, fact_name, src_root, results):
    """Verify a single module fact against source. Returns number of errors."""
    source_file, class_name, fact_methods, fact_parents = find_class_info_in_fact(kg, fact_name)
    fn_source_file, inline_functions, referenced_functions = find_function_info_in_fact(kg, fact_name)

    src_file = source_file or fn_source_file
    if not src_file:
        console.print(f"  [red]ERROR:[/red] fact '{fact_name}' has no source_file attribute")
        return 1

    source_path = src_root / src_file
    if not source_path.exists():
        console.print(f"  [red]ERROR:[/red] source file not found: {source_path}")
        return 1

    errors = 0
    decorators = find_fact_decorators_in_source(source_path)

    if class_name:
        console.print(f"\n[bold]Verifying class {class_name}[/bold] in {src_file}")

        actual_methods, actual_bases = find_class_in_source(source_path, class_name)

        if actual_methods is None:
            console.print(f"  [red]ERROR:[/red] class '{class_name}' not found in {src_file}")
            return 1

        if class_name in decorators:
            dec_path = decorators[class_name]
            if dec_path == fact_name:
                console.print(f"  [green]OK[/green]    @fact decorator matches")
                results.append(("decorator", class_name, "@fact", "OK"))
            else:
                console.print(f"  [red]FAIL[/red]  @fact decorator says '{dec_path}', expected '{fact_name}'")
                results.append(("decorator", class_name, "@fact", "FAIL"))
                errors += 1
        else:
            console.print(f"  [yellow]WARN[/yellow]  no @fact decorator on class '{class_name}'")
            results.append(("decorator", class_name, "@fact", "WARN"))

        if fact_parents:
            for p in fact_parents:
                if p not in actual_bases:
                    console.print(f"  [red]FAIL[/red]  parent class '{p}'")
                    results.append(("parent", class_name, p, "FAIL"))
                    errors += 1
                else:
                    console.print(f"  [green]OK[/green]    parent class '{p}'")
                    results.append(("parent", class_name, p, "OK"))

        for m in fact_methods:
            if m not in actual_methods:
                console.print(f"  [red]FAIL[/red]  method '{m}'")
                results.append(("method", class_name, m, "FAIL"))
                errors += 1
            else:
                console.print(f"  [green]OK[/green]    method '{m}'")
                results.append(("method", class_name, m, "OK"))

        for m in actual_methods:
            if m not in fact_methods:
                console.print(f"  [yellow]WARN[/yellow]  method '{m}' in source but not in fact")
                results.append(("method", class_name, m, "WARN"))

    if inline_functions or referenced_functions:
        module_label = fact_name.rsplit('/', 1)[-1]
        console.print(f"\n[bold]Verifying functions[/bold] in {src_file}")
        actual_functions = find_top_level_functions_in_source(source_path)

        for fn_name in inline_functions:
            if fn_name in decorators:
                dec_path = decorators[fn_name]
                if dec_path == fact_name:
                    console.print(f"  [green]OK[/green]    @fact decorator on '{fn_name}'")
                    results.append(("decorator", module_label, fn_name, "OK"))
                else:
                    console.print(f"  [red]FAIL[/red]  @fact decorator on '{fn_name}' says '{dec_path}', expected '{fact_name}'")
                    results.append(("decorator", module_label, fn_name, "FAIL"))
                    errors += 1
            else:
                console.print(f"  [yellow]WARN[/yellow]  no @fact decorator on function '{fn_name}'")
                results.append(("decorator", module_label, fn_name, "WARN"))

            if fn_name in actual_functions:
                console.print(f"  [green]OK[/green]    function '{fn_name}'")
                results.append(("function", module_label, fn_name, "OK"))
            else:
                console.print(f"  [red]FAIL[/red]  function '{fn_name}' declared in fact but missing from source")
                results.append(("function", module_label, fn_name, "FAIL"))
                errors += 1

        for fn_name, ref_fact in referenced_functions:
            if fn_name in decorators:
                dec_path = decorators[fn_name]
                if dec_path == ref_fact:
                    console.print(f"  [green]OK[/green]    @fact decorator on '{fn_name}'")
                    results.append(("decorator", module_label, fn_name, "OK"))
                else:
                    console.print(f"  [red]FAIL[/red]  @fact decorator on '{fn_name}' says '{dec_path}', expected '{ref_fact}'")
                    results.append(("decorator", module_label, fn_name, "FAIL"))
                    errors += 1
            else:
                console.print(f"  [yellow]WARN[/yellow]  no @fact decorator on function '{fn_name}'")
                results.append(("decorator", module_label, fn_name, "WARN"))

            if fn_name in actual_functions:
                console.print(f"  [green]OK[/green]    function '{fn_name}'")
                results.append(("function", module_label, fn_name, "OK"))
            else:
                console.print(f"  [red]FAIL[/red]  function '{fn_name}' declared in fact but missing from source")
                results.append(("function", module_label, fn_name, "FAIL"))
                errors += 1

    return errors

def print_summary(results, errors):
    table = Table(title="Verification Summary")
    table.add_column("Type", style="dim")
    table.add_column("Module")
    table.add_column("Name")
    table.add_column("Status")

    for kind, cls, name, status in results:
        if status == "OK":
            style = "green"
        elif status == "FAIL":
            style = "red bold"
        else:
            style = "yellow"
        table.add_row(kind, cls, name, f"[{style}]{status}[/{style}]")

    console.print()
    console.print(table)

    if errors > 0:
        console.print(f"\n[red bold]VERIFICATION FAILED: {errors} error(s)[/red bold]")
    else:
        console.print(f"\n[green bold]VERIFICATION PASSED[/green bold]")

def main():
    parser = argparse.ArgumentParser(
        description="Verify Python source code against facts")
    parser.add_argument("name",
        help="Fact path to a program or module, e.g. app/org/igorlesik/fact/pysrc")
    parser.add_argument("--roots", default="kg",
        help="Comma-separated list of root directories (default: kg)")
    parser.add_argument("--src-root", default=".",
        help="Root directory for resolving source_file paths (default: .)")
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

    if kg.load(args.name) != 0:
        console.print(f"[red]ERROR:[/red] could not load fact '{args.name}'")
        return 1

    fact = Fact(kg, args.name)
    if fact.construct() != 0:
        console.print(f"[red]ERROR:[/red] could not construct fact '{args.name}'")
        return 1

    info = kg.get_fact(args.name).get("info", {})
    has = info.get("has", {})

    results = []
    errors = 0

    if "class_name" in has:
        errors = verify_module(kg, args.name, src_root, results)
    else:
        modules = find_module_facts(kg, args.name)
        if not modules:
            console.print(f"No verifiable modules found in '{args.name}'")
            return 0
        console.print(f"Found [bold]{len(modules)}[/bold] verifiable module(s)")
        for module in modules:
            errors += verify_module(kg, module, src_root, results)

    print_summary(results, errors)

    return 1 if errors > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
