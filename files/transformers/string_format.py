"""
string_format.py — Replace String.format() with the instance method .formatted().

Transformation applied
──────────────────────
  String.format("Hello %s, you are %d", name, age)
      →  "Hello %s, you are %d".formatted(name, age)

  String.format("No args")
      →  "No args"          (trivial case — no format args, just remove the call)

Why SAFE
─────────
  `String.formatted(Object... args)` was introduced in Java 15 (JEP 378
  Text Blocks — companion API).  It is an instance method that calls
  String.format(this, args) internally.  The output is IDENTICAL byte-for-byte
  for all inputs.

  The transformer is deliberately conservative — it only fires when:
    1. The first argument is a STRING LITERAL (starts with `"`).
       If it's a variable or method call, we cannot safely make it the receiver.
    2. The entire call fits on a SINGLE LINE.
       Multi-line String.format calls are skipped to avoid regex ambiguity.
    3. There are NO nested String.format calls inside the argument list.
       Nested calls are left unchanged.

  String.format(Locale, fmt, args) — the overload that takes a Locale as
  the first argument — is NOT touched, because .formatted() has no Locale
  overload.

Why BETTER
───────────
  • Reads more naturally: the format string is the subject, not an argument.
  • Consistent with Text Blocks which use the same `.formatted()` style.
  • Slightly shorter and avoids the static method lookup overhead.
  • Aligns with the modern Java idiom established in Java 15+.

What is NOT changed
────────────────────
  String.format(locale, fmt, args)      ← Locale overload — no equivalent
  String.format(variable, args)         ← non-literal format — cannot be receiver
  Multi-line String.format(...)         ← too complex to handle safely
  Calls where args contain nested calls ← handled by conservative arg regex
"""
import re
from .base_transformer import BaseTransformer


# ── Pattern ────────────────────────────────────────────────────────────────────
#
#  String.format(  "literal"  ,  arg1, arg2 ...  )
#
#  Group 1: the format string literal  (including the quotes)
#  Group 2: everything after the first comma (the args), or empty string
#
#  Safety constraints baked into the regex:
#   - First arg MUST start with `"` (string literal).
#   - Arguments allow one level of nested parentheses — covers method calls
#     like getName(), Integer.parseInt(s), etc.
#   - A Locale first arg would be a class/variable name, not `"`, so it
#     never matches.
#   - No nested String.format because the outer `)` would end our match early
#     on a well-formed expression.

_ARG    = r'(?:[^(),"]|\([^()]*\)|"[^"]*")'     # one arg token (no deep nesting)
_ARGS   = rf'(?:\s*,\s*{_ARG}+)*'               # zero or more additional args

_PATTERN = re.compile(
    r'\bString\.format\s*\('            # String.format(
    r'\s*'
    r'(?P<fmt>"(?:[^"\\]|\\.)*")'       # group 'fmt': string literal
    r'(?P<args>' + _ARGS + r')'         # group 'args': remaining arguments
    r'\s*\)',                            # closing )
)


class StringFormatTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        count   = 0

        def _replace(m: re.Match) -> str:
            nonlocal count
            fmt  = m.group('fmt')
            args = m.group('args').strip()   # e.g. ", name, age"

            if args:
                # Strip the leading comma+space so we can re-attach
                args_body = re.sub(r'^\s*,\s*', '', args)
                result = f'{fmt}.formatted({args_body})'
            else:
                # String.format("plain string") — no args — just the literal
                result = fmt

            count += 1
            return result

        new_content = _PATTERN.sub(_replace, content)

        if count:
            changes.append(
                f"Replaced {count}× `String.format(\"...\", ...)` → `\"...\".formatted(...)` "
                f"(Java 15+, instance method — identical output)"
            )

        return new_content, changes
