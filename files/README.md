# Java 8 → 21 Source Transformer

A multi-file Python tool that scans any Java project folder and automatically
migrates source files to idiomatic Java 21, **preserving identical runtime
behaviour** and **never increasing algorithmic complexity**.

---

## Project Structure

```
java_transformer/
├── main.py                          ← CLI entry point
├── config.py                        ← All constants & removed-API table
├── file_walker.py                   ← Folder traversal & non-Java file copy
├── java_transformer.py              ← Pipeline orchestrator
├── reporter.py                      ← Change logging & summary
└── transformers/
    ├── __init__.py
    ├── base_transformer.py          ← Abstract base (contract)
    ├── wrapper_constructors.py      ← new Integer() → Integer.valueOf()
    ├── deprecated_methods.py        ← Comments out removed method calls
    ├── import_cleaner.py            ← Comments out removed/encapsulated imports
    ├── diamond_operator.py          ← new ArrayList<String>() → new ArrayList<>()
    ├── instanceof_pattern.py        ← instanceof + cast → pattern variable
    └── string_improvements.py      ← .length()==0 → .isEmpty()
```

---

## Quick Start

```bash
# Install (no third-party deps — stdlib only)
python --version   # requires Python 3.10+

# Basic usage
python main.py  /path/to/old-java-project  /path/to/output

# Preview changes without writing files
python main.py  ./src  ./out  --dry-run

# Show every individual change
python main.py  ./src  ./out  --verbose
```

---

## What Gets Changed

| Transformer | Example Before | Example After | Java Version |
|---|---|---|---|
| **WrapperConstructors** | `new Integer(42)` | `Integer.valueOf(42)` | Java 9 |
| **WrapperConstructors** | `new Boolean(true)` | `Boolean.TRUE` | Java 9 |
| **DiamondOperator** | `new ArrayList<String>()` | `new ArrayList<>()` | Java 7 |
| **InstanceofPattern** | `if (x instanceof Foo) { Foo f=(Foo)x; … }` | `if (x instanceof Foo f) { … }` | Java 16 |
| **StringImprovements** | `s.length() == 0` | `s.isEmpty()` | Java 6 |
| **ImportCleaner** | `import javax.xml.bind.*;` | Commented out + migration note | Java 11 |
| **DeprecatedMethods** | `thread.stop(ex);` | Commented out + TODO | Java 11 |

---

## What Does NOT Get Changed

The tool is deliberately conservative.  It will **not** touch:

- Logic, algorithms, or control flow
- `Arrays.asList()` → `List.of()` — skipped because `List.of` rejects `null` elements
- `str.trim()` → `str.strip()` — skipped because Unicode behaviour differs
- Multi-catch merging — too complex to detect safely
- Try-with-resources conversion — requires control-flow analysis
- Anonymous classes (diamond operator skipped for them in < Java 9 targets)
- Any pattern where the transformation could change output or throw new exceptions

---

## What Gets Commented Out (Not Auto-Fixed)

Some removals require **design changes** that cannot be automated safely:

| Removed API | Action | Java Version Removed |
|---|---|---|
| `Thread.stop(Throwable)` | Commented out + TODO | Java 11 |
| `Runtime.runFinalizersOnExit()` | Commented out + TODO | Java 11 |
| `System.runFinalizersOnExit()` | Commented out + TODO | Java 11 |
| `import javax.xml.bind.*` | Commented out + Maven dep note | Java 11 |
| `import sun.misc.BASE64Encoder` | Commented out + `import java.util.Base64;` added | Java 9 |

---

## Adding a New Transformer

1. Create `transformers/my_transformer.py` that extends `BaseTransformer`.
2. Implement `transform(self, content) -> tuple[str, list[str]]`.
3. Add it to the pipeline list in `java_transformer.py`.

**Rule**: Every transformer must guarantee identical runtime semantics.
When in doubt, return the original content unchanged.

---

## Requirements

- Python 3.10+ (uses `match`-free syntax, but `str | None` type hints need 3.10)
- No third-party libraries — stdlib only (`re`, `pathlib`, `shutil`, `argparse`)
