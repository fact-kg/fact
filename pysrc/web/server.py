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

THEME_JS = """<script>
function toggleTheme(){var h=document.documentElement,c=h.getAttribute('data-theme'),n=c==='dark'?'light':c==='light'?'dark':(window.matchMedia('(prefers-color-scheme:dark)').matches?'light':'dark');h.setAttribute('data-theme',n);localStorage.setItem('theme',n)}
(function(){var s=localStorage.getItem('theme');if(s)document.documentElement.setAttribute('data-theme',s)})();
</script>"""

def page(title, content, breadcrumb=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — Fact KG</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
  {THEME_JS}
</head>
<body>
  <header class="container">
    <nav>
      <ul><li><strong><a href="/">Fact KG</a></strong></li></ul>
      <ul><li>{breadcrumb}</li><li><a href="#" onclick="toggleTheme();return false">Toggle theme</a></li></ul>
    </nav>
  </header>
  <main class="container">
    {content}
  </main>
</body>
</html>"""

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
    return sorted(children)

@app.get("/", response_class=HTMLResponse)
def index():
    paths = set()
    for root in ROOTS:
        for p in root.iterdir():
            if p.is_dir() or p.suffix == ".yaml":
                name = str(p.relative_to(root)).replace('\\', '/')
                if p.suffix == ".yaml":
                    name = name[:-5]
                paths.add(name)
    links = [f'<li><a href="/fact/{p}">{p}</a></li>' for p in sorted(paths)]
    content = f"<h1>Knowledge Graph</h1><ul>{''.join(links)}</ul>"
    return page("Home", content)

@app.get("/fact/{path:path}")
def get_fact(path: str, request: Request):
    breadcrumb = make_breadcrumb(path)

    has_fact = any((root / (path + ".yaml")).exists() for root in ROOTS)

    if has_fact and kg.load(path) == 0:
        fact = Fact(kg, path)
        fact.construct()
        data = kg.get_fact(path)

        if "application/json" in request.headers.get("accept", ""):
            return JSONResponse(data["info"])

        info = data["info"]
        html = f"<h1>{path.rsplit('/', 1)[-1]}</h1>"

        types = info.get('type', [])
        type_links = [f'<a href="/fact/{t}">{t}</a>' if t not in ('str', 'num') else t for t in types]
        html += f"<p><mark>is: {', '.join(type_links)}</mark></p>"

        if info.get("val_as"):
            html += "<h3>Values</h3><table><thead><tr><th>Property</th><th>As type</th><th>Value</th></tr></thead><tbody>"
            for type_name, attrs in info["val_as"].items():
                for attr, val in attrs.items():
                    html += f'<tr><td><b>{attr}</b></td><td><a href="/fact/{type_name}">{type_name}</a></td><td>{val}</td></tr>'
            html += "</tbody></table>"

        if info.get("has"):
            html += "<h3>Properties</h3><table><thead><tr><th>Name</th><th>Type</th><th>Value</th></tr></thead><tbody>"
            for attr, val in info["has"].items():
                t = val.get("type", "")
                v = val.get("val", "")
                if t not in ("str", "num", "list", ""):
                    t = f'<a href="/fact/{t}">{t}</a>'
                overrides = ""
                if "val_as" in val:
                    overrides = f"<br><small>{val['val_as']}</small>"
                html += f"<tr><td><b>{attr}</b></td><td>{t}</td><td>{v}{overrides}</td></tr>"
            html += "</tbody></table>"

        if info.get("part"):
            html += "<h3>Part of</h3><ul>"
            for p in info["part"]:
                html += f'<li><a href="/fact/{p}">{p}</a></li>'
            html += "</ul>"

        children = list_children(path)
        if children:
            html += "<h3>Children</h3><ul>"
            for c in children:
                label = c.rsplit('/', 1)[-1]
                html += f'<li><a href="/fact/{c}">{label}</a></li>'
            html += "</ul>"

        return HTMLResponse(page(path, html, breadcrumb))

    children = list_children(path)
    if children:
        links = [f'<li><a href="/fact/{c}">{c.rsplit("/", 1)[-1]}</a></li>' for c in children]
        content = f"<h1>{path.rsplit('/', 1)[-1]}</h1><ul>{''.join(links)}</ul>"
        return HTMLResponse(page(path, content, breadcrumb))

    return HTMLResponse(page("Not found", f"<h1>Not found: {path}</h1>"), status_code=404)
