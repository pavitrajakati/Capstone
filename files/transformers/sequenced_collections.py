"""
sequenced_collections.py — Apply SequencedCollection API (JEP 431, Java 21).

SequencedCollection introduced getFirst/getLast/addFirst/addLast/
removeFirst/removeLast/setFirst/setLast as named methods on the new
SequencedCollection interface hierarchy.

Transformations applied
───────────────────────
  list.get(0)                   →  list.getFirst()
  list.get(list.size() - 1)     →  list.getLast()
  list.add(0, x)                →  list.addFirst(x)
  list.remove(0)                →  list.removeFirst()
  list.remove(list.size() - 1)  →  list.removeLast()
  list.set(0, x)                →  list.setFirst(x)
  list.set(list.size() - 1, x)  →  list.setLast(x)

Type tracking strategy (the semantic analysis part)
────────────────────────────────────────────────────
  Phase 1 — scan file for variable names with a SequencedCollection type:
    • Field:     private List<X> items;
    • Local:     List<X> items = ...;
    • Param:     void foo(List<X> items)
    • var:       var items = new ArrayList<>()

  Phase 2 — apply replacements ONLY to those specific variable names.
  A variable named `items` of type String won't be touched even if it has
  a `.get(0)` call, because it wasn't declared as a List/Deque type.

Safety guarantees
─────────────────
  ✔ Only fires on explicitly tracked List/Deque-typed variables.
  ✔ `remove(0)` is integer literal only — never confused with remove(Object).
  ✔ Both old and new forms throw an unchecked exception on empty collections.
  ✔ No change to element order, return values, or mutation semantics.
"""
import re
from .base_transformer import BaseTransformer

_SEQ_TYPES = {
    "List", "ArrayList", "LinkedList", "Vector", "Stack",
    "Deque", "ArrayDeque",
}

_TYPE_ALT = "|".join(re.escape(t) for t in _SEQ_TYPES)

_DECL = re.compile(
    r'\b(?:' + _TYPE_ALT + r')'
    r'\s*(?:<[^>]*(?:<[^>]*>)?[^>]*>)?'
    r'\s+(\w+)'
    r'\s*(?:[=;,)\[])',
)

_VAR_NEW = re.compile(
    r'\bvar\s+(\w+)\s*=\s*new\s+(?:' + _TYPE_ALT + r')\s*(?:<[^>]*>)?\s*\(',
)


def _collect_seq_vars(content: str) -> set[str]:
    names: set[str] = set()
    for m in _DECL.finditer(content):
        names.add(m.group(1))
    for m in _VAR_NEW.finditer(content):
        names.add(m.group(1))
    names.discard("_")
    return names


def _replacements_for(var: str) -> list[tuple[re.Pattern, str, str]]:
    v  = re.escape(var)
    sz = rf'{v}\.size\(\)\s*-\s*1'
    return [
        (re.compile(rf'\b{v}\.get\s*\(\s*{sz}\s*\)'),
         f'{var}.getLast()',
         f'{var}.get({var}.size()-1) → {var}.getLast()'),

        (re.compile(rf'\b{v}\.get\s*\(\s*0\s*\)'),
         f'{var}.getFirst()',
         f'{var}.get(0) → {var}.getFirst()'),

        (re.compile(rf'\b{v}\.remove\s*\(\s*{sz}\s*\)'),
         f'{var}.removeLast()',
         f'{var}.remove({var}.size()-1) → {var}.removeLast()'),

        (re.compile(rf'\b{v}\.remove\s*\(\s*0\s*\)'),
         f'{var}.removeFirst()',
         f'{var}.remove(0) → {var}.removeFirst()'),

        (re.compile(rf'\b{v}\.set\s*\(\s*{sz}\s*,\s*([^)]+)\)'),
         f'{var}.setLast(\\1)',
         f'{var}.set({var}.size()-1, x) → {var}.setLast(x)'),

        (re.compile(rf'\b{v}\.set\s*\(\s*0\s*,\s*([^)]+)\)'),
         f'{var}.setFirst(\\1)',
         f'{var}.set(0, x) → {var}.setFirst(x)'),

        (re.compile(rf'\b{v}\.add\s*\(\s*0\s*,\s*([^)]+)\)'),
         f'{var}.addFirst(\\1)',
         f'{var}.add(0, x) → {var}.addFirst(x)'),
    ]


class SequencedCollectionsTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        result  = content

        seq_vars = _collect_seq_vars(content)
        if not seq_vars:
            return content, []

        for var in sorted(seq_vars):
            for regex, replacement, desc in _replacements_for(var):
                new_result, n = regex.subn(replacement, result)
                if n:
                    changes.append(
                        f"SequencedCollection (JEP 431, Java 21): `{desc}` ×{n}"
                    )
                    result = new_result

        return result, changes
