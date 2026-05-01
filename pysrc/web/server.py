import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

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

@app.get("/", response_class=HTMLResponse)
def index():
    paths = []
    for root in ROOTS:
        for p in sorted(root.iterdir()):
            if p.is_dir() or p.suffix == ".yaml":
                name = str(p.relative_to(root)).replace('\\', '/')
                if p.suffix == ".yaml":
                    name = name[:-5]
                paths.append(name)
    links = [f'<li><a href="/fact/{p}">{p}</a></li>' for p in sorted(set(paths))]
    return f"<html><body><h1>Fact KG</h1><ul>{''.join(links)}</ul></body></html>"

@app.get("/fact/{path:path}")
def get_fact(path: str, request: Request):
    if kg.load(path) == 0:
        fact = Fact(kg, path)
        fact.construct()
        data = kg.get_fact(path)

        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(data["info"])

        info = data["info"]
        html = f"<h1>{path}</h1>"
        types = info.get('type', [])
        type_links = [f'<a href="/fact/{t}">{t}</a>' if t not in ('str', 'num') else t for t in types]
        html += f"<p><b>Type:</b> {', '.join(type_links)}</p>"

        if info.get("val_as"):
            html += "<h2>Values</h2><ul>"
            for type_name, attrs in info["val_as"].items():
                for attr, val in attrs.items():
                    html += f"<li><b>{attr}</b> (as {type_name}): {val}</li>"
            html += "</ul>"

        if info.get("has"):
            html += "<h2>Properties</h2><ul>"
            for attr, val in info["has"].items():
                if "val" in val:
                    html += f"<li><b>{attr}:</b> {val['val']}"
                elif "type" in val:
                    t = val["type"]
                    html += f'<li><b>{attr}:</b> <a href="/fact/{t}">{t}</a>'
                if "val_as" in val:
                    html += f" (overrides: {val['val_as']})"
                html += "</li>"
            html += "</ul>"

        if info.get("part"):
            html += "<h2>Part of</h2><ul>"
            for p in info["part"]:
                html += f'<li><a href="/fact/{p}">{p}</a></li>'
            html += "</ul>"

        children = set()
        for root in ROOTS:
            child_dir = root / path
            if child_dir.is_dir():
                for f in child_dir.iterdir():
                    if f.suffix == ".yaml":
                        children.add(path + "/" + f.stem)
                    elif f.is_dir():
                        children.add(path + "/" + f.name)
        if children:
            html += "<h2>Children</h2><ul>"
            for c in sorted(children):
                html += f'<li><a href="/fact/{c}">{c}</a></li>'
            html += "</ul>"

        return HTMLResponse(f"<html><body>{html}</body></html>")

    children = set()
    for root in ROOTS:
        child_dir = root / path
        if child_dir.is_dir():
            for f in child_dir.iterdir():
                if f.suffix == ".yaml":
                    children.add(path + "/" + f.stem)
                elif f.is_dir():
                    children.add(path + "/" + f.name)
    if children:
        links = [f'<li><a href="/fact/{c}">{c}</a></li>' for c in sorted(children)]
        return HTMLResponse(f"<html><body><h1>{path}</h1><ul>{''.join(links)}</ul></body></html>")

    return HTMLResponse(f"<html><body><h1>Not found: {path}</h1></body></html>", status_code=404)
