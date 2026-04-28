## Usage

The checker is a command-line tool for validating facts.

### Check a single fact

```bash
python.exe pysrc/check.py math/function
```

### Check all facts in the default root

```bash
python.exe pysrc/check.py --all
```

### Check all facts across multiple roots

```bash
python.exe pysrc/check.py --roots kg,kg2 --all
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | File or load error |
| 2 | Schema validation error |
| 3 | Fact construction error |
