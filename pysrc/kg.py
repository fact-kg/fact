import logging
import yaml
import jsonschema
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Annotated, Dict, Any, List
from fact_decorator import fact, fact_link

log = logging.getLogger(__name__)

class KgIface(ABC):
    @abstractmethod
    def get_dict(self) -> Dict[str, Any]:
        """Get whole dictionary."""
        pass

    @abstractmethod
    def load(self, fact_name, force_reload = False) -> int:
        """Load fact info from file."""
        pass

    @abstractmethod
    def is_loaded(self, fact_name) -> bool:
        """Check if fact loaded into KG memory."""
        pass

@fact("app/org/igorlesik/fact/pysrc/kg_module")
class Kg(KgIface):
    """Knowledge Graph."""

    def __init__(self, roots: List[Path], schema: str):
        """Constructor method to initialize instance attributes."""
        self.roots = roots
        self.schema = schema
        self.validator = jsonschema.Draft202012Validator(schema)
        self.data: Annotated[Dict[str, Any], fact_link("app/org/igorlesik/fact/pysrc/kg_module", "data_storage")] = {}

    def get_dict(self) -> Dict[str, Any]:
        """Get whole dictionary."""
        return self.data

    def get_fact(self, name: str) -> Dict:
        """Get data about fact from dictionary."""
        return self.data[name]

    def is_loaded(self, fact_name) -> bool:
        """Check if fact loaded into KG memory."""
        return fact_name in self.data

    @fact("app/org/igorlesik/fact/pysrc/kg_module", "method_find_fact_file")
    def find_fact_file(self, fact_name) -> Path:
        """Find fact file across all roots. Returns path or None."""
        found = []
        for root in self.roots:
            path = root / (fact_name + ".yaml")
            if path.exists():
                found.append(path)
        if len(found) > 1:
            log.error("fact '%s' exists in multiple roots:", fact_name)
            for p in found:
                log.error("  %s", p)
            return None
        if len(found) == 0:
            log.error("fact '%s' not found in any root", fact_name)
            return None
        return found[0]

    @fact("app/org/igorlesik/fact/pysrc/kg_module/load")
    def load(self, fact_name, force_reload = False) -> int:
        if self.is_loaded(fact_name) and not force_reload:
            return 0
        path = self.find_fact_file(fact_name)
        if path is None:
            return 1
        with open(path, "r", encoding="utf-8") as f:
            yaml_str = f.read()
        # YAML array becomes the "def" (definition) list of tags
        self.data[fact_name] = { "def": yaml.safe_load(yaml_str) }
        if not self.validate_schema(self.data[fact_name]["def"]):
            return 1
        return 0

    def validate_schema(self, yaml_data: str) -> bool:
        try:
            self.validator.validate(yaml_data)
            log.debug("valid schema")
        except jsonschema.ValidationError as e:
            log.error("invalid schema: %s", e.message)
            log.error("  at path: %s", list(e.absolute_path))
            return False
        return True
