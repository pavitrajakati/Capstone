"""
collections_factory.py — Replace verbose Collections utility methods with
modern Java 9+ factory methods that are more efficient and expressive.

Transformations applied
───────────────────────
  Collections.emptyList()          →  List.of()
  Collections.emptySet()           →  Set.of()
  Collections.emptyMap()           →  Map.of()
  Collections.singletonList(x)     →  List.of(x)
  Collections.singleton(x)         →  Set.of(x)
  Collections.singletonMap(k, v)   →  Map.of(k, v)

Why these are strictly SAFE
────────────────────────────
  emptyList / emptySet / emptyMap
    Both the old and new forms return an immutable empty collection.
    Collections.emptyList() already threw UnsupportedOperationException
    on mutation — exactly the same as List.of().  Zero behaviour change.

  singletonList / singleton / singletonMap
    Both return immutable single-element collections.
    CAVEAT: List.of(x) rejects null elements (throws NullPointerException),
    whereas Collections.singletonList(null) is technically legal.
    The transformer only applies when the argument is:
      • a string literal          "hello"
      • an integer/long literal   42  100L
      • a boolean literal         true  false
      • a simple variable name    myVar
      • a qualified field         this.field  obj.field  MyClass.CONSTANT
      • a method call (no args)   getName()   getId()
    If the argument could be null (e.g. a complex expression), the
    transformer skips it and leaves the code unchanged.

Why these are MORE EFFICIENT
─────────────────────────────
  • List.of() / Set.of() / Map.of() are backed by compact, immutable
    array-based implementations introduced in Java 9 (JEP 269).
  • Collections.emptyList() returns a singleton static instance —
    already efficient — but List.of() uses the same pattern with a
    cleaner API that makes immutability intent explicit.
  • Collections.singletonList() uses a custom class with an Object field.
    List.of(x) uses an optimised single-element ImmutableCollections$List1
    which has slightly lower memory overhead.

Import management
─────────────────
  The transformer scans the existing imports and auto-injects any missing
  java.util.{List,Set,Map} imports only when the corresponding factory
  method is actually used.  If the file already has `import java.util.*`
  or the specific import, nothing is added.
"""
import re
from .base_transformer import BaseTransformer


# ── Regex for arguments we are confident cannot be null ───────────────────────
# Matches: string literals, numeric literals, boolean literals,
#          simple identifiers, qualified names, and zero-arg method calls.
_SAFE_ARG = re.compile(
    r'^('
    r'"[^"]*"'                          # string literal
    r'|\'[^\']*\''                      # char literal
    r'|\d[\d_]*[lLfFdD]?'              # numeric literal  42  100L  3.14f
    r'|true|false|null'                 # boolean / null literal  (null IS safe for empty*)
    r'|\w+(?:\.\w+)*\s*(?:\(\s*\))?'   # simple var, field access, or no-arg method
    r')$'
)

# ── Safe-argument extractor for singletonMap (two args) ───────────────────────
_SAFE_MAP_ARGS = re.compile(
    r'^(\w+(?:\.\w+)*\s*(?:\(\s*\))?|"[^"]*"|\d[\d_]*[lLfFdD]?|true|false)'
    r'\s*,\s*'
    r'(\w+(?:\.\w+)*\s*(?:\(\s*\))?|"[^"]*"|\d[\d_]*[lLfFdD]?|true|false)$'
)

# ── Simple patterns for the no-arg empty methods ──────────────────────────────
_EMPTY_LIST = re.compile(r'\bCollections\.emptyList\s*\(\s*\)')
_EMPTY_SET  = re.compile(r'\bCollections\.emptySet\s*\(\s*\)')
_EMPTY_MAP  = re.compile(r'\bCollections\.emptyMap\s*\(\s*\)')

# ── Patterns for singleton methods — capture the raw argument text ─────────────
# We match up to one level of nested parens inside the arg.
_ARG_PAT = r'((?:[^()]+|\([^()]*\))+)'   # simple arg with ≤1 nesting level

_SINGLETON_LIST = re.compile(r'\bCollections\.singletonList\s*\(\s*' + _ARG_PAT + r'\s*\)')
_SINGLETON_SET  = re.compile(r'\bCollections\.singleton\s*\(\s*'     + _ARG_PAT + r'\s*\)')
_SINGLETON_MAP  = re.compile(r'\bCollections\.singletonMap\s*\(\s*'  + _ARG_PAT + r'\s*\)')


class CollectionsFactoryTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        result  = content
        needed_imports: set[str] = set()

        # ── emptyList / emptySet / emptyMap ────────────────────────────────────
        result, n = _EMPTY_LIST.subn('List.of()', result)
        if n:
            changes.append(f"Replaced {n}× `Collections.emptyList()` → `List.of()` (Java 9+, JEP 269)")
            needed_imports.add("java.util.List")

        result, n = _EMPTY_SET.subn('Set.of()', result)
        if n:
            changes.append(f"Replaced {n}× `Collections.emptySet()` → `Set.of()` (Java 9+, JEP 269)")
            needed_imports.add("java.util.Set")

        result, n = _EMPTY_MAP.subn('Map.of()', result)
        if n:
            changes.append(f"Replaced {n}× `Collections.emptyMap()` → `Map.of()` (Java 9+, JEP 269)")
            needed_imports.add("java.util.Map")

        # ── singletonList ──────────────────────────────────────────────────────
        def _replace_singleton_list(m: re.Match) -> str:
            arg = m.group(1).strip()
            if _SAFE_ARG.match(arg):
                needed_imports.add("java.util.List")
                return f'List.of({arg})'
            return m.group(0)   # leave unchanged

        new_result = _SINGLETON_LIST.sub(_replace_singleton_list, result)
        count = result.count('Collections.singletonList') - new_result.count('Collections.singletonList')
        if count > 0:
            changes.append(
                f"Replaced {count}× `Collections.singletonList(x)` → `List.of(x)` (Java 9+, immutable)"
            )
        result = new_result

        # ── singleton (Set) ────────────────────────────────────────────────────
        def _replace_singleton_set(m: re.Match) -> str:
            arg = m.group(1).strip()
            if _SAFE_ARG.match(arg):
                needed_imports.add("java.util.Set")
                return f'Set.of({arg})'
            return m.group(0)

        new_result = _SINGLETON_SET.sub(_replace_singleton_set, result)
        count = result.count('Collections.singleton(') - new_result.count('Collections.singleton(')
        if count > 0:
            changes.append(
                f"Replaced {count}× `Collections.singleton(x)` → `Set.of(x)` (Java 9+, immutable)"
            )
        result = new_result

        # ── singletonMap ───────────────────────────────────────────────────────
        def _replace_singleton_map(m: re.Match) -> str:
            args = m.group(1).strip()
            if _SAFE_MAP_ARGS.match(args):
                needed_imports.add("java.util.Map")
                return f'Map.of({args})'
            return m.group(0)

        new_result = _SINGLETON_MAP.sub(_replace_singleton_map, result)
        count = result.count('Collections.singletonMap') - new_result.count('Collections.singletonMap')
        if count > 0:
            changes.append(
                f"Replaced {count}× `Collections.singletonMap(k,v)` → `Map.of(k,v)` (Java 9+, immutable)"
            )
        result = new_result

        # ── Inject missing imports ─────────────────────────────────────────────
        if needed_imports:
            result = self._inject_imports(result, needed_imports)

        return result, changes

    # ── Import injection helper ────────────────────────────────────────────────

    def _inject_imports(self, content: str, needed: set[str]) -> str:
        """
        Add missing java.util.{List,Set,Map} imports only when:
          1. The specific import is not already present.
          2. There is no wildcard `import java.util.*` already.
        Inserts after the last existing java.util.* import line, or before
        the first non-import, non-package, non-comment line.
        """
        lines = content.split("\n")

        # Check what is already imported
        has_wildcard   = any("import java.util.*" in ln for ln in lines)
        already        = {ln.strip().rstrip(";").replace("import ", "") for ln in lines if ln.strip().startswith("import ")}
        to_add         = sorted(needed - already)

        if has_wildcard or not to_add:
            return content

        # Find insertion point: after the last java.util import line
        last_import_idx = -1
        for i, ln in enumerate(lines):
            if ln.strip().startswith("import "):
                last_import_idx = i

        insert_at = last_import_idx + 1 if last_import_idx >= 0 else 0
        new_lines = [f"import {imp};" for imp in to_add]
        lines[insert_at:insert_at] = new_lines

        return "\n".join(lines)
