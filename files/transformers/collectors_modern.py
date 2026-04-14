"""
collectors_modern.py — Replace verbose Collector forms with concise Java 16+ equivalents.

Transformations applied
───────────────────────
  .collect(Collectors.toUnmodifiableList())  →  .toList()
  .stream().collect(Collectors.toUnmodifiableList())  →  .stream().toList()

Why SAFE
─────────
  `Stream.toList()` (JEP 356, Java 16) returns an unmodifiable List —
  IDENTICAL contract to `Collectors.toUnmodifiableList()`.
  Both throw UnsupportedOperationException on mutation.
  Both allow null elements.
  The element order is preserved in the same way.

  IMPORTANT — NOT applied:
    .collect(Collectors.toList())  ←  NOT replaced.
    `Collectors.toList()` returns a MUTABLE list; `Stream.toList()` is
    UNMODIFIABLE.  Replacing it would silently break code that later
    adds/removes elements.  This transformer is intentionally conservative.

Why MORE EFFICIENT
───────────────────
  `Stream.toList()` was specifically designed as a more efficient terminal
  operation — it avoids the overhead of the Collector abstraction layer and
  can size the internal array more precisely, reducing allocations.

Import management
─────────────────
  After replacing, if `Collectors` is no longer referenced anywhere in the
  file, the `import java.util.stream.Collectors` import is commented out
  with an explanatory note.  `import java.util.stream.*` wildcards are
  left untouched.
"""
import re
from .base_transformer import BaseTransformer


# Matches .collect(Collectors.toUnmodifiableList()) with optional whitespace
_PATTERN = re.compile(
    r'\.collect\s*\(\s*Collectors\s*\.\s*toUnmodifiableList\s*\(\s*\)\s*\)'
)

# Matches import of Collectors (specific, not wildcard)
_IMPORT_COLLECTORS = re.compile(
    r'^(\s*)(import\s+java\.util\.stream\.Collectors\s*;)',
    re.MULTILINE,
)


class CollectorsModernTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []

        result, n = _PATTERN.subn('.toList()', content)

        if not n:
            return content, []

        changes.append(
            f"Replaced {n}× `.collect(Collectors.toUnmodifiableList())` → `.toList()` "
            f"(Java 16+, JEP 356 — same unmodifiable contract, lower overhead)"
        )

        # If Collectors is no longer used anywhere, comment out its import
        remaining_collectors = re.search(r'\bCollectors\b', result)
        if not remaining_collectors:
            result, ni = _IMPORT_COLLECTORS.subn(
                r'\1// JAVA21-MIGRATION: Collectors no longer used — import removed\n\1// \2',
                result,
            )
            if ni:
                changes.append(
                    "Commented out `import java.util.stream.Collectors` — no longer referenced"
                )

        return result, changes
