import yaml
import jsonschema
from pathlib import Path
from abc import ABC, abstractmethod
from typing import Dict, Any, List

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

class Kg(KgIface):
    """Knowledge Graph."""

    def __init__(self, roots: List[Path], schema: str):
        """Constructor method to initialize instance attributes."""
        self.roots = roots
        self.schema = schema
        self.data : Dict[str, Any] = {}

    def get_dict(self) -> Dict[str, Any]:
        """Get whole dictionary."""
        return self.data

    def get_fact(self, name: str) -> Dict:
        """Get data about fact from dictionary."""
        return self.data[name]

    def is_loaded(self, fact_name) -> bool:
        """Check if fact loaded into KG memory."""
        return fact_name in self.data

    def find_fact_file(self, fact_name) -> Path:
        """Find fact file across all roots. Returns path or None."""
        found = []
        for root in self.roots:
            path = root / (fact_name + ".yaml")
            if path.exists():
                found.append(path)
        if len(found) > 1:
            print(f"ERROR: fact '{fact_name}' exists in multiple roots:")
            for p in found:
                print(f"  {p}")
            return None
        if len(found) == 0:
            print(f"ERROR: fact '{fact_name}' not found in any root")
            return None
        return found[0]

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
            jsonschema.validate(instance=yaml_data, schema=self.schema)
            print("valid schema")
        except jsonschema.ValidationError as e:
            print(f"ERROR: invalid schema: {e.message}")
            print(f"  at path: {list(e.absolute_path)}")
            return False
        return True
