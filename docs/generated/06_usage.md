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
