import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from kg import Kg
from fact import Fact

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

config_path = PROJECT_DIR / "fact-server.yaml"
with open(config_path, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f.read())

ROOTS = [PROJECT_DIR / r["path"] for r in config["roots"]]

with open(PROJECT_DIR / "schema.yaml", "r", encoding="utf-8") as f:
    schema = yaml.safe_load(f.read())

kg = Kg(ROOTS, schema)
app = FastAPI(title="Fact Knowledge Graph")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

from pysrc.web.apps.astronomy.planet_compare.routes import router as planet_compare_router
from pysrc.web.apps.physics.element_table.routes import router as element_table_router
from pysrc.web.apps.physics.unit_converter.routes import router as unit_converter_router
from pysrc.web.apps.math.polynomial_plot.routes import router as polynomial_plot_router
from pysrc.web.apps.math.expression_diagram.routes import router as expression_diagram_router
from pysrc.web.apps.computer.algorithm_viewer.routes import router as algorithm_viewer_router
app.include_router(planet_compare_router)
app.include_router(element_table_router)
app.include_router(unit_converter_router)
app.include_router(polynomial_plot_router)
app.include_router(expression_diagram_router)
app.include_router(algorithm_viewer_router)

from rule.engine import RuleEngine
rule_engine = RuleEngine(kg, ROOTS)


@app.get("/query")
def query(q: str = ""):
    if not q:
        return JSONResponse({"error": "provide ?q= parameter", "results": []})
    parts = q.strip().split()

    # find command
    if parts[0] == "find" and len(parts) >= 2:
        substring = " ".join(parts[1:]).lower()
        matches = [fp for fp in kg.get_dict().keys() if substring in fp.lower()]
        matches.sort()
        return JSONResponse({"query": q, "results": matches})

    # transitive command
    if parts[0] == "transitive" and len(parts) >= 2:
        fact_path = parts[1]
        relation = parts[2] if len(parts) > 2 else "part"
        results = rule_engine.find_transitive(fact_path, relation)
        return JSONResponse({"query": q, "results": results})

    # rules command
    if q.strip() == "rules":
        rules = [{"path": r["path"], "when": r["when"], "then": r["then"]}
                 for r in rule_engine.rules]
        return JSONResponse({"rules": rules})

    # pattern query
    results = rule_engine.query(q)
    return JSONResponse({"query": q, "results": results})


def make_breadcrumb(path):
    parts = path.split("/")
    crumbs = []
    for i in range(len(parts)):
        partial = "/".join(parts[:i+1])
        crumbs.append(f'<a href="/fact/{partial}">{parts[i]}</a>')
    return " / ".join(crumbs)

def list_children(path):
    children = set()
    for root in ROOTS:
        child_dir = root / path
        if child_dir.is_dir():
            for f in child_dir.iterdir():
                if f.name.startswith("."):
                    continue
                if f.suffix == ".yaml":
                    children.add(path + "/" + f.stem)
                elif f.is_dir():
                    children.add(path + "/" + f.name)
    return [{"path": c, "name": c.rsplit("/", 1)[-1]} for c in sorted(children)]

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    paths = set()
    for root in ROOTS:
        for p in root.iterdir():
            if p.name.startswith("."):
                continue
            if p.is_dir() or p.suffix == ".yaml":
                name = str(p.relative_to(root)).replace('\\', '/')
                if p.suffix == ".yaml":
                    name = name[:-5]
                paths.add(name)
    return templates.TemplateResponse(request, "index.html", {
        "paths": sorted(paths),
    })

@app.get("/fact/{path:path}")
def get_fact(path: str, request: Request):
    has_fact = any((root / (path + ".yaml")).exists() for root in ROOTS)

    if has_fact and kg.load(path) == 0:
        fact = Fact(kg, path)
        fact.construct()
        data = kg.get_fact(path)

        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(data["info"])

        info = data["info"]
        return templates.TemplateResponse(request, "fact.html", {
            "path": path,
            "name": path.rsplit("/", 1)[-1],
            "breadcrumb": make_breadcrumb(path),
            "types": info.get("type", []),
            "val_as": info.get("val_as", {}),
            "has": info.get("has", {}),
            "parts": info.get("part", []),
            "children": list_children(path),
        })

    children = list_children(path)
    if children:
        return templates.TemplateResponse(request, "browse.html", {
            "path": path,
            "name": path.rsplit("/", 1)[-1],
            "breadcrumb": make_breadcrumb(path),
            "children": children,
        })

    return templates.TemplateResponse(request, "404.html", {
        "path": path,
    }, status_code=404)

@app.get("/search", response_class=HTMLResponse)
def search(request: Request, q: str = ""):
    if not q:
        return templates.TemplateResponse(request, "search.html", {
            "query": "",
            "results": [],
        })
    q_lower = q.lower()
    results = []
    for root in ROOTS:
        for yaml_file in root.rglob("*.yaml"):
            fact_path = str(yaml_file.relative_to(root).with_suffix('')).replace('\\', '/')
            if q_lower in fact_path.lower():
                results.append({"path": fact_path, "name": fact_path.rsplit("/", 1)[-1]})
    results.sort(key=lambda r: r["path"])

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(results)

    return templates.TemplateResponse(request, "search.html", {
        "query": q,
        "results": results,
    })

@app.get("/graph/{path:path}")
def get_graph(path: str, request: Request):
    has_fact = any((root / (path + ".yaml")).exists() for root in ROOTS)

    if not has_fact or kg.load(path) != 0:
        return templates.TemplateResponse(request, "404.html", {
            "path": path,
        }, status_code=404)

    fact = Fact(kg, path)
    fact.construct()
    info = kg.get_fact(path).get("info", {})

    nodes = [{"id": path, "label": path.rsplit("/", 1)[-1], "group": "current"}]
    edges = []
    seen = {path}

    for t in info.get("type", []):
        if t not in ("str", "num") and t not in seen:
            nodes.append({"id": t, "label": t.rsplit("/", 1)[-1], "group": "type"})
            edges.append({"from": path, "to": t, "label": "is"})
            seen.add(t)

    for attr, val in info.get("has", {}).items():
        t = val.get("type", "")
        if t and t not in ("str", "num", "list") and t not in seen:
            nodes.append({"id": t, "label": t.rsplit("/", 1)[-1], "group": "has"})
            edges.append({"from": path, "to": t, "label": f"has: {attr}"})
            seen.add(t)

    for p in info.get("part", []):
        if p not in seen:
            nodes.append({"id": p, "label": p.rsplit("/", 1)[-1], "group": "part"})
            edges.append({"from": path, "to": p, "label": "part"})
            seen.add(p)

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"nodes": nodes, "edges": edges})

    return templates.TemplateResponse(request, "graph.html", {
        "path": path,
        "name": path.rsplit("/", 1)[-1],
        "breadcrumb": make_breadcrumb(path),
        "graph_data": {"nodes": nodes, "edges": edges},
    })
