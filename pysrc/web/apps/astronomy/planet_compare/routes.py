import sys
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent.parent))

from kg import Kg
from fact import Fact

router = APIRouter(prefix="/apps/astronomy/planet_compare")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

PLANETS_PATH = "astronomy/location/milky_way/solar_system"

def get_kg():
    from pysrc.web.server import kg, ROOTS
    return kg, ROOTS

def load_fact_info(kg, path, ROOTS):
    has_fact = any((root / (path + ".yaml")).exists() for root in ROOTS)
    if not has_fact or kg.load(path) != 0:
        return None
    fact = Fact(kg, path)
    if fact.construct() != 0:
        return None
    return kg.get_fact(path).get("info", {})

def collect_values(info):
    values = {}
    for type_name, attrs in info.get("val_as", {}).items():
        for attr, val in attrs.items():
            values[attr] = val
    return values

def find_unit_for_property(kg, fact_info, prop_name, ROOTS):
    """Follow type chain to find the unit type for a property."""
    for type_name in fact_info.get("type", []):
        if type_name in ("str", "num"):
            continue
        type_info = load_fact_info(kg, type_name, ROOTS)
        if type_info is None:
            continue
        has = type_info.get("has", {})
        if prop_name in has:
            return has[prop_name].get("type", "")
        unit = find_unit_for_property(kg, type_info, prop_name, ROOTS)
        if unit:
            return unit
    return ""

@router.get("/")
def planet_compare(request: Request):
    from pysrc.web.server import kg, ROOTS, list_children

    children = list_children(PLANETS_PATH)
    items = []
    all_properties = set()
    first_info = None

    for c in children:
        info = load_fact_info(kg, c["path"], ROOTS)
        if info is None:
            continue
        values = collect_values(info)
        if values:
            items.append({"name": c["name"], "path": c["path"], "props": values})
            all_properties.update(values.keys())
            if first_info is None:
                first_info = info

    properties = sorted(all_properties)

    units = {}
    if first_info:
        for prop in properties:
            unit_path = find_unit_for_property(kg, first_info, prop, ROOTS)
            if unit_path:
                units[prop] = unit_path.rsplit("/", 1)[-1]

    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse({"properties": properties, "units": units, "items": [
            {"name": i["name"], "path": i["path"], "values": i["props"]}
            for i in items
        ]})

    return templates.TemplateResponse(request, "planet_compare.html", {
        "properties": properties,
        "units": units,
        "items": items,
    })
