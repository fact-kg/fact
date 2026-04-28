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
