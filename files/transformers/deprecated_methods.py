"""
deprecated_methods.py — Comment out method calls that were REMOVED from the JDK.

Removed APIs handled
────────────────────
  Thread.stop(Throwable)          Removed Java 11  — use interrupt()
  Runtime.runFinalizersOnExit()   Removed Java 11  — remove finalizer reliance
  System.runFinalizersOnExit()    Removed Java 11  — remove finalizer reliance

Why comment-out instead of auto-rewrite?
─────────────────────────────────────────
  These APIs require a design change (e.g. cooperative cancellation patterns).
  Auto-rewriting would silently change program logic.  Instead we preserve the
  original statement as a comment so the developer sees exactly what must be
  addressed, with a clear TODO explaining the required change.

Safety guarantee
────────────────
  The commented-out line is never executed, so no behaviour change can occur
  from the transformation itself.  A TODO comment is added directly above it.
"""
import re
from .base_transformer import BaseTransformer


# Each entry: (compiled_regex, short_label, todo_message)
_REMOVED: list[tuple[re.Pattern, str, str]] = [
    (
        # Thread.stop(new SomeException(...)) or thread.stop(someThrowable)
        # We distinguish from no-arg stop() by requiring a non-empty argument.
        re.compile(
            r'(?P<indent>[ \t]*)'
            r'(?P<stmt>'
            r'(?:\w[\w.]*\s*\.\s*)?'     # optional receiver
            r'stop\s*\('
            r'(?P<arg>[^;)]+)'           # at least one argument
            r'\)\s*;)',
            re.MULTILINE,
        ),
        "Thread.stop(Throwable)",
        "Thread.stop(Throwable) was REMOVED in Java 11. "
        "Use Thread.interrupt() with a cooperative cancellation flag.",
    ),
    (
        re.compile(
            r'(?P<indent>[ \t]*)'
            r'(?P<stmt>'
            r'Runtime\s*\.\s*(?:getRuntime\s*\(\s*\)\s*\.\s*)?'
            r'runFinalizersOnExit\s*\([^;]*\)\s*;)',
            re.MULTILINE,
        ),
        "Runtime.runFinalizersOnExit()",
        "Runtime.runFinalizersOnExit() was REMOVED in Java 11. "
        "Do not rely on finalizers; remove this call.",
    ),
    (
        re.compile(
            r'(?P<indent>[ \t]*)'
            r'(?P<stmt>System\s*\.\s*runFinalizersOnExit\s*\([^;]*\)\s*;)',
            re.MULTILINE,
        ),
        "System.runFinalizersOnExit()",
        "System.runFinalizersOnExit() was REMOVED in Java 11. "
        "Do not rely on finalizers; remove this call.",
    ),
]


class DeprecatedMethodsTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        result  = content

        for pattern, label, todo in _REMOVED:
            def _replace(m: re.Match, _todo: str = todo) -> str:
                indent = m.group("indent")
                stmt   = m.group("stmt")
                return (
                    f"{indent}// TODO(Java21-migration): {_todo}\n"
                    f"{indent}// REMOVED: {stmt}"
                )

            new_result, n = pattern.subn(_replace, result)
            if n:
                changes.append(
                    f"Commented out {n}× removed call `{label}` — see TODO in code"
                )
                result = new_result

        return result, changes
