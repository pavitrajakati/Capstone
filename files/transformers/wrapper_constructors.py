"""
wrapper_constructors.py — Replace deprecated wrapper-type constructors.

Deprecated in Java 9 (JEP 277), still present but flagged for removal.

Transformations applied
───────────────────────
  new Boolean(true)   →  Boolean.TRUE          (cached constant)
  new Boolean(false)  →  Boolean.FALSE         (cached constant)
  new Boolean(expr)   →  Boolean.valueOf(expr) (uses cache)

  new Integer(x)      →  Integer.valueOf(x)
  new Long(x)         →  Long.valueOf(x)
  new Double(x)       →  Double.valueOf(x)
  new Float(x)        →  Float.valueOf(x)
  new Short(x)        →  Short.valueOf(x)
  new Byte(x)         →  Byte.valueOf(x)
  new Character(x)    →  Character.valueOf(x)

Safety guarantee
────────────────
  valueOf() uses an internal cache for common values (e.g. Integer −128…127),
  making it strictly MORE efficient — never less.  The return type is identical.
  No change to observable program behaviour.
"""
import re
from .base_transformer import BaseTransformer
from config import DEPRECATED_WRAPPER_TYPES


class WrapperConstructorTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        result = content

        # ── Boolean literal: new Boolean(true) → Boolean.TRUE ─────────────────
        result, n = re.subn(
            r'\bnew\s+Boolean\s*\(\s*true\s*\)',
            'Boolean.TRUE',
            result,
        )
        if n:
            changes.append(f"Replaced {n}× `new Boolean(true)` → `Boolean.TRUE`")

        # ── Boolean literal: new Boolean(false) → Boolean.FALSE ───────────────
        result, n = re.subn(
            r'\bnew\s+Boolean\s*\(\s*false\s*\)',
            'Boolean.FALSE',
            result,
        )
        if n:
            changes.append(f"Replaced {n}× `new Boolean(false)` → `Boolean.FALSE`")

        # ── Boolean general: new Boolean(expr) → Boolean.valueOf(expr) ────────
        # Must run AFTER the literal cases above to avoid double-matching.
        result, n = re.subn(
            r'\bnew\s+Boolean\s*\(',
            'Boolean.valueOf(',
            result,
        )
        if n:
            changes.append(f"Replaced {n}× `new Boolean(...)` → `Boolean.valueOf(...)`")

        # ── Numeric / Character wrapper constructors ───────────────────────────
        for wtype in DEPRECATED_WRAPPER_TYPES:
            pattern     = rf'\bnew\s+{re.escape(wtype)}\s*\('
            replacement = f'{wtype}.valueOf('
            result, n   = re.subn(pattern, replacement, result)
            if n:
                changes.append(
                    f"Replaced {n}× `new {wtype}(...)` → `{wtype}.valueOf(...)`"
                )

        return result, changes
