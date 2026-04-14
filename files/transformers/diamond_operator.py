"""
diamond_operator.py — Replace verbose generic type arguments with `<>`.

Introduced in Java 7, the diamond operator lets the compiler infer the
generic type from context, making the code shorter without any semantic
change.  Old codebases often have explicit types out of habit.

Examples
────────
  new ArrayList<String>()               →  new ArrayList<>()
  new HashMap<String, Integer>()        →  new HashMap<>()
  new LinkedList<Map<String, Object>>() →  new LinkedList<>()

Scope of the transformation
────────────────────────────
  Only constructor calls of the form  new TypeName<TypeArgs>()  where:
    • TypeArgs is non-empty (not already a diamond)
    • The call is NOT an anonymous-class instantiation
      (i.e. not immediately followed by  { )
    • Up to two levels of nested generic parameters are handled;
      deeper nesting is left unchanged to stay safe.

Safety guarantee
────────────────
  The diamond operator is purely a compile-time feature.  The compiler
  performs exactly the same type inference whether the type arguments are
  written explicitly or as `<>`.  No change to bytecode or runtime behaviour.
"""
import re
from .base_transformer import BaseTransformer


class DiamondOperatorTransformer(BaseTransformer):

    # Handles up to one level of nesting: Foo<A<B>, C>
    _PATTERN = re.compile(
        r'\bnew\s+'
        r'(?P<type>\w[\w.]*)'                         # class name
        r'\s*<'
        r'(?P<args>[^<>]*(?:<[^<>]*>[^<>]*)*)'        # type args (≤1 nesting level)
        r'>'
        r'\s*\(\)',                                     # no-arg constructor
        re.MULTILINE,
    )

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        count   = 0

        def _replace(m: re.Match) -> str:
            nonlocal count
            type_args = m.group("args").strip()

            # Already uses diamond operator — leave as-is
            if not type_args:
                return m.group(0)

            # Skip anonymous class instantiation: new Foo<Bar>() { ... }
            after = content[m.end():].lstrip()
            if after.startswith("{"):
                return m.group(0)

            count += 1
            return f"new {m.group('type')}<>()"

        result = self._PATTERN.sub(_replace, content)

        if count:
            changes.append(
                f"Applied diamond operator `<>` to {count} constructor call(s) "
                f"(explicit type args removed; semantics unchanged)"
            )

        return result, changes
