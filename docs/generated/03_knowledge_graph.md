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
