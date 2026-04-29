# Fact — Knowledge Representation System

**Generated from facts on: 2026-04-29**

## Table of Contents

- [Overview](#overview)
- [Knowledge Graph](#knowledge-graph)
  - [Fact Format](#fact-format)
- [Tags](#tags)
  - [is](#is)
  - [has](#has)
  - [part](#part)
- [Python Implementation](#python-implementation)
  - [Checker](#checker)
  - [Knowledge Graph Module](#knowledge-graph-module)
  - [Fact Module](#fact-module)
  - [Source Verifier](#source-verifier)
- [Usage](#usage)

## Overview

Fact is a knowledge representation application — a YAML-based knowledge graph
system where facts are written as YAML files with semantic tags. Designed to be
human-readable, LLM-native, and schema-light. Uses file path as ontology and
taxonomy.

The system consists of two main parts:

- **Knowledge Graph** — the collection of facts, their format, and the rules
  governing their structure.
- **Python Implementation** — the tooling that loads, validates, and checks
  facts for consistency.

## Knowledge Graph

The knowledge graph is a collection of facts stored as YAML files in root
directories. Multiple roots merge into one unified namespace. File path encodes
taxonomy and serves as fact identity.

For example, the fact at `math/number/integer.yaml` is referenced as
`math/number/integer`. The directory structure implies that `integer` is a
concept under `number`, which is under `math`.

### Fact Format

Facts are stored as YAML files. Each file is an array of tags. Tags are: `is`,
`has`, `part`.

A minimal fact looks like:

```yaml
- is: universe
```

A more complete fact with properties and affiliation:

```yaml
- is:
    type: astronomy/star
    as:
      - astronomy/object:
          mass:
            value: 1.989e30
- has:
    description: The Sun is the star at the center of the Solar System.
- part: astronomy/universe
```

## Tags

A tag is a key in a fact's YAML array that declares a relationship. Tags are
classified as strong (symbolic ground truth) or weak (loose).

| Tag | Meaning | Strength |
|------|------------------------------|----------|
| `is` | Identity / type declaration | Strong |
| `has` | Property / attribute | Strong |
| `part` | Affiliation to container | Weak |

### is

Declares identity or type. Strong tag (symbolic ground truth).

The `is` tag has several forms:

- Simple string identity: `- is: universe`
- Typed reference: `- is: { type: astronomy/star }`
- Typed with value: `- is: { type: str, value: astronomical object }`
- Typed with property overrides via `as`:
  ```yaml
  - is:
      type: astronomy/star
      as:
        - astronomy/object:
            mass:
              value: 1.989e30
  ```

### has

Declares a property or attribute. Strong tag (symbolic ground truth). Each `has`
entry contains exactly one attribute. Attribute can be a typed reference,
explicit type with value, or shorthand. Supports `as` to set property values on
the declared type, symmetric with the `as` mechanism in the `is` tag.

Examples:

```yaml
# Shorthand — type deduced from value
- has:
    description: connects accelerators

# Explicit type
- has:
    mass:
      type: num

# Explicit type with value
- has:
    version:
      type: str
      value: "1.0"

# Type referencing another fact
- has:
    switch:
      type: computer/com/ualink/switch

# Type with property overrides via as
- has:
    method_load:
      type: computer/sw/lang/python/class_method
      as:
        - computer/sw/lang/python/class_method:
            name:
              value: load
```

### part

Declares loose affiliation to a container or domain. Weak tag. Used to prevent
God objects — allows expressing that a fact belongs to a domain without implying
the domain owns or defines it.

Renamed from `belongs` in earlier design.

```yaml
- part: astronomy/universe
```

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

## Usage

### Checking facts

The checker is a command-line tool for validating facts.

```bash
# Check a single fact
python.exe pysrc/check.py math/function

# Check all facts in the default root
python.exe pysrc/check.py --all

# Check all facts across multiple roots
python.exe pysrc/check.py --roots kg,kg2 --all
```

Exit codes:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | File or load error |
| 2 | Schema validation error |
| 3 | Fact construction error |

### Verifying source code against facts

The verifier checks that Python source code matches its fact descriptions.

```bash
# Verify all modules of a program
python.exe pysrc/pyprogverify/verify.py --roots=kg,kg2 --src-root=. app/org/igorlesik/fact/pysrc

# Verify a single module
python.exe pysrc/pyprogverify/verify.py --roots=kg,kg2 --src-root=. app/org/igorlesik/fact/pysrc/kg_module
```

The verifier checks:
- Class existence and name
- Parent class (inheritance) matches
- Public method names match
- `@fact` decorator bidirectional link
