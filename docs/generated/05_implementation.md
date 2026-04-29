## Python Implementation

The Python source code for the fact checker tool is located in the `pysrc/`
directory. It consists of three modules and a source verifier.

### Checker

Command-line entry point for checking facts (`pysrc/check.py`). Validates
schema, referential integrity, and fact construction. Supports `--all` to check
all facts and `--roots` for specifying multiple root directories.

### Knowledge Graph Module

The knowledge graph module (`pysrc/kg.py`) loads YAML fact files from multiple
root directories into memory. It validates each fact against the JSON Schema
defined in `schema.yaml` and detects duplicate facts across roots.

The module provides the `Kg` class (inherits from `KgIface`) with the following
methods:

- `load` — load a fact from file into memory
- `find_fact_file` — find a fact file across all roots
- `validate_schema` — validate a fact against the JSON Schema
- `is_loaded` — check if a fact is already in memory
- `get_fact` — get a loaded fact's data
- `get_dict` — get the entire loaded fact dictionary

### Fact Module

The fact module (`pysrc/fact.py`) constructs a fact by parsing its `is`,
`has`, and `part` tags. It validates type references and builds the fact's
internal representation.

The module provides the `Fact` class with the following methods:

- `construct` — construct fact, create fields
- `construct_what_it_is` — process `is` tags
- `construct_tag_is` — construct what a fact is
- `parse_construct_tag_is_dict` — parse `is` dict form
- `parse_construct_tag_is_as_type` — parse `as` property overrides
- `construct_what_it_part` — process `part` tags
- `construct_tag_part` — construct what a fact belongs to
- `construct_what_it_has` — process `has` tags
- `construct_tag_has` — construct what a fact has
- `parse_construct_tag_has_dict` — parse `has` dict form

### Source Verifier

The source verifier (`pysrc/pyprogverify/verify.py`) validates Python source
code against facts using AST analysis. It checks that classes, methods, parent
classes, and `@fact` decorator links declared in facts match the actual source
code. No runtime import of the target code is performed.
