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
ROOTS = [PROJECT_DIR / "kg", PROJECT_DIR / "kg2"]

with open(PROJECT_DIR / "schema.yaml", "r", encoding="utf-8") as f:
    schema = yaml.safe_load(f.read())

kg = Kg(ROOTS, schema)
app = FastAPI(title="Fact Knowledge Graph")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

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
