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
explicit type with value, or shorthand.

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
```

### part

Declares loose affiliation to a container or domain. Weak tag. Used to prevent
God objects — allows expressing that a fact belongs to a domain without implying
the domain owns or defines it.

Renamed from `belongs` in earlier design.

```yaml
- part: astronomy/universe
```
