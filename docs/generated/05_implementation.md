## Python Implementation

The Python source code for the fact checker tool is located in the `pysrc/`
directory. It consists of three modules.

### Checker

Command-line entry point for checking facts (`pysrc/check.py`). Validates
schema, referential integrity, and fact construction. Supports `--all` to check
all facts and `--roots` for specifying multiple root directories.

### Knowledge Graph Module

The knowledge graph module (`pysrc/kg.py`) loads YAML fact files from multiple
root directories into memory. It validates each fact against the JSON Schema
defined in `schema.yaml` and detects duplicate facts across roots.

The module provides the `Kg` class with the following methods:

- `load` — load a fact from file into memory
- `find_fact_file` — find a fact file across all roots
- `validate_schema` — validate a fact against the JSON Schema
- `is_loaded` — check if a fact is already in memory
- `get_fact` — get a loaded fact's data
- `get_dict` — get the entire loaded fact dictionary

### Fact Entity

The fact entity module (`pysrc/fact.py`) constructs a fact by parsing its `is`,
`has`, and `part` tags. It validates type references and builds the fact's
internal representation.
