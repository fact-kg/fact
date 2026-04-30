Review Python source code against its linked facts.

## Instructions

For each source file given as argument (or all `pysrc/*.py` if none given):

1. Find all `@fact(...)` decorators and `fact_link(...)` annotations
2. For each link, read the referenced fact from `kg/` or `kg2/`
3. Read the code around the decorated element
4. Check semantically whether the code matches the fact's description
   and attributes — not just structural link validity, but meaning
5. Report mismatches, suggest fact updates if the code drifted

## What to check

- Does the code element do what the fact's description says?
- If the fact has `has` attributes, do they match what the code actually has?
- Are there `@fact` decorators that should be added to new code elements?
- Are there facts that reference code elements that were removed or renamed?

## Output

For each source file, report:
- OK items briefly (one line each)
- Mismatches with explanation and suggested fix
- Missing links (code without `@fact` that probably should have one)

## When this runs

- Automatically by Claude when adding/removing/renaming `@fact`-decorated elements
- Manually by user when facts about Python code change
