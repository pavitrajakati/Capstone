"""
instanceof_pattern.py — Apply Java 16 pattern matching for instanceof.

Converts the classic "check then cast" idiom into a concise pattern variable.

Before (Java 8–15 style)
────────────────────────
    if (obj instanceof SomeType) {
        SomeType var = (SomeType) obj;
        var.doSomething();
    }

After (Java 16+ pattern matching)
──────────────────────────────────
    if (obj instanceof SomeType var) {
        var.doSomething();
    }

Conditions required for the transformation to fire
────────────────────────────────────────────────────
  1. The `if` condition is a simple `x instanceof T` (no &&, ||, !)
  2. The FIRST statement in the block is exactly  T varName = (T) x;
  3. `T` and `x` in the cast must match the instanceof check exactly
     (enforced via regex back-references — no false positives).
  4. The type `T` is a simple or dotted name (no raw generics like List<X>
     since `instanceof List<X>` is illegal Java anyway).

Safety guarantee
────────────────
  The Java Language Specification guarantees that pattern variables behave
  identically to the old local variable inside the true branch.  The cast
  line is removed (it was already a no-op after the instanceof check).
  No change to program output or complexity.
"""
import re
from .base_transformer import BaseTransformer


# ── Pattern explanation ────────────────────────────────────────────────────────
#
#  if ( <obj> instanceof <type> ) {
#      <type>  <var>  =  ( <type> ) <obj> ;
#
#  Named backreferences  (?P=type)  and  (?P=obj)  ensure the type and object
#  variable match exactly across the two lines.
#
_PATTERN = re.compile(
    r'if\s*\(\s*'
    r'(?P<obj>\w+)'                     # checked object variable
    r'\s+instanceof\s+'
    r'(?P<type>\w+(?:\.\w+)*)'          # simple or qualified type name (no generics)
    r'\s*\)\s*\{'                       # closing ) and opening {
    r'(?P<nl>[^\S\n]*\n)'              # newline after {
    r'(?P<indent>[ \t]+)'              # leading whitespace of cast line
    r'(?P=type)\s+'                     # same type (backreference)
    r'(?P<var>\w+)'                     # new variable name
    r'\s*=\s*'
    r'\((?P=type)\)\s*'                 # explicit cast to same type
    r'(?P=obj)'                         # same object (backreference)
    r'\s*;'
    r'[^\S\n]*\n?',                    # optional trailing whitespace/newline
    re.MULTILINE,
)


class InstanceofPatternTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        count   = 0

        def _replace(m: re.Match) -> str:
            nonlocal count
            count += 1
            obj = m.group("obj")
            typ = m.group("type")
            var = m.group("var")
            nl  = m.group("nl")
            # Merge two lines → one; the cast line is removed entirely.
            return f"if ({obj} instanceof {typ} {var}) {{{nl}"

        result = _PATTERN.sub(_replace, content)

        if count:
            changes.append(
                f"Applied instanceof pattern matching {count}× "
                f"— explicit cast line removed (Java 16+, JEP 394)"
            )

        return result, changes
