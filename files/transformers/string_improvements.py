"""
string_improvements.py — Modernise legacy String emptiness checks.

`String.isEmpty()` has existed since Java 6 but old codebases often use
`.length() == 0` out of habit.  This transformer replaces the verbose form
with the idiomatic one.

Transformations applied
───────────────────────
  str.length() == 0    →   str.isEmpty()
  str.length() != 0    →  !str.isEmpty()
  0 == str.length()    →   str.isEmpty()
  0 != str.length()    →  !str.isEmpty()

Only simple variable names (word characters) are matched as the receiver.
Chained calls like `list.get(0).length() == 0` are intentionally skipped to
avoid ambiguity.

Safety guarantee
────────────────
  Both forms throw NullPointerException if the receiver is null, and both
  return the same boolean result for non-null strings.  The transformation
  is therefore a drop-in replacement with zero behavioural difference.
"""
import re
from .base_transformer import BaseTransformer


class StringImprovementsTransformer(BaseTransformer):

    # str.length() == 0  →  str.isEmpty()
    _EQ_ZERO  = re.compile(r'\b(\w+)\.length\(\)\s*==\s*0\b')
    # str.length() != 0  →  !str.isEmpty()
    _NEQ_ZERO = re.compile(r'\b(\w+)\.length\(\)\s*!=\s*0\b')
    # 0 == str.length()  →  str.isEmpty()
    _ZERO_EQ  = re.compile(r'\b0\s*==\s*(\w+)\.length\(\)')
    # 0 != str.length()  →  !str.isEmpty()
    _ZERO_NEQ = re.compile(r'\b0\s*!=\s*(\w+)\.length\(\)')

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        result  = content

        result, n = self._EQ_ZERO.subn(r'\1.isEmpty()', result)
        if n:
            changes.append(
                f"Replaced {n}× `.length() == 0` → `.isEmpty()` (Java 6+, idiomatic)"
            )

        result, n = self._NEQ_ZERO.subn(r'!\1.isEmpty()', result)
        if n:
            changes.append(
                f"Replaced {n}× `.length() != 0` → `!.isEmpty()`"
            )

        result, n = self._ZERO_EQ.subn(r'\1.isEmpty()', result)
        if n:
            changes.append(
                f"Replaced {n}× `0 == .length()` → `.isEmpty()`"
            )

        result, n = self._ZERO_NEQ.subn(r'!\1.isEmpty()', result)
        if n:
            changes.append(
                f"Replaced {n}× `0 != .length()` → `!.isEmpty()`"
            )

        return result, changes
