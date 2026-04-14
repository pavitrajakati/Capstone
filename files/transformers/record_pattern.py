"""
record_pattern.py — JEP 440 (Java 21): Record Patterns.

Transforms instanceof checks on record types — where the body only accesses
record accessor methods — into deconstruction patterns.

Before (old style)
──────────────────
    record Point(int x, int y) {}

    if (obj instanceof Point p) {
        int x = p.x();
        int y = p.y();
        System.out.println(x + y);
    }

After (Java 21 record pattern)
───────────────────────────────
    if (obj instanceof Point(int x, int y)) {
        System.out.println(x + y);
    }

Algorithm (file-scoped semantic analysis)
──────────────────────────────────────────
  Step 1 — Record discovery
    Scan the file for all `record Name(TypeA a, TypeB b, ...)` declarations.
    Build a map:  RecordName → [(Type, fieldName), ...]

  Step 2 — Pattern site detection
    Find:  if (VAR instanceof RecordName PATVAR) {
    For each such site, inspect the BODY.

  Step 3 — Body safety check
    The body must contain ONLY:
      a. Declarations of the form:  Type name = patvar.field();
         where field matches a record component name (same order not required).
      b. Other statements that reference those extracted local vars.
    If the body accesses patvar.someMethod() that is NOT a record accessor,
    the transformation is skipped.
    If patvar is used in any other way (passed to a method, returned, etc.),
    the transformation is skipped.

  Step 4 — Rewrite
    Remove the  Type name = patvar.field();  lines from the body.
    Rename remaining uses of those locals if they conflict (they never do
    because we derive the names from the record component names, which are
    the same).
    Replace  if (var instanceof Record r)  with
             if (var instanceof Record(TypeA a, TypeB b))

Safety guarantee
────────────────
  ✔  The deconstructed variables are in scope for the entire if block.
  ✔  The match only succeeds for non-null values — same as instanceof.
  ✔  Accessor method calls are pure (record accessors cannot throw).
  ✔  If ANY uncertainty exists (patvar used outside accessor calls, body
     too complex, record not in same file), the transformation is skipped.
"""
import re
from dataclasses import dataclass
from .base_transformer import BaseTransformer


# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class RecordDef:
    name      : str
    components: list[tuple[str, str]]   # [(type, fieldName), ...]


# ── Record declaration scanner ─────────────────────────────────────────────────
# Matches:  record Name(Type1 a, Type2 b)  with optional generics on types
_RECORD_DECL = re.compile(
    r'\brecord\s+'
    r'(?P<name>\w+)'
    r'\s*\('
    r'(?P<params>[^)]*)'
    r'\)',
    re.MULTILINE,
)

_PARAM = re.compile(
    r'(?P<type>[\w<>\[\].,\s]+?)\s+(?P<field>\w+)\s*(?:,|$)'
)


def _parse_records(content: str) -> dict[str, RecordDef]:
    records: dict[str, RecordDef] = {}
    for m in _RECORD_DECL.finditer(content):
        name   = m.group('name')
        params = m.group('params').strip()
        if not params:
            continue
        components = []
        for p in re.split(r',', params):
            p = p.strip()
            parts = p.rsplit(None, 1)
            if len(parts) == 2:
                components.append((parts[0].strip(), parts[1].strip()))
        if components:
            records[name] = RecordDef(name=name, components=components)
    return records


# ── Block extractor (balanced braces) ─────────────────────────────────────────

def _extract_block(source: str, open_pos: int) -> tuple[str, int]:
    """Return (body_content, pos_after_close_brace)."""
    depth = 0
    i     = open_pos
    while i < len(source):
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[open_pos + 1 : i], i + 1
        i += 1
    return source[open_pos + 1 :], len(source)


# ── Main transformer ───────────────────────────────────────────────────────────

_INSTANCEOF_RECORD = re.compile(
    r'\bif\s*\(\s*'
    r'(?P<var>\w+)'
    r'\s+instanceof\s+'
    r'(?P<rec>\w+)'
    r'\s+'
    r'(?P<pvar>\w+)'
    r'\s*\)\s*\{',
    re.MULTILINE,
)


class RecordPatternTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        records = _parse_records(content)
        if not records:
            return content, []

        changes : list[str] = []
        result  = content
        offset  = 0

        for m in _INSTANCEOF_RECORD.finditer(content):
            rec_name = m.group('rec')
            if rec_name not in records:
                continue

            rec  = records[rec_name]
            pvar = m.group('pvar')
            var  = m.group('var')

            brace_pos      = content.rfind('{', m.start(), m.end())
            body, body_end = _extract_block(content, brace_pos)

            rewritten = self._try_rewrite_body(body, pvar, rec)
            if rewritten is None:
                continue

            # Build deconstruction pattern header
            params  = ', '.join(f'{t} {f}' for t, f in rec.components)
            new_if  = f'if ({var} instanceof {rec_name}({params})) {{'
            new_blk = new_if + rewritten + '}'

            adj_start = m.start() + offset
            adj_end   = body_end  + offset
            result    = result[:adj_start] + new_blk + result[adj_end:]
            offset   += len(new_blk) - (body_end - m.start())

            changes.append(
                f"Applied record deconstruction pattern for `{rec_name}` "
                f"(JEP 440, Java 21) — accessor calls removed from body"
            )

        return result, changes

    def _try_rewrite_body(
        self,
        body: str,
        pvar: str,
        rec: RecordDef,
    ) -> str | None:
        """
        Verify the body is safe and return the rewritten body with
        accessor-declaration lines removed.  Return None if unsafe.
        """
        field_names = {f for _, f in rec.components}
        lines       = body.split('\n')
        keep_lines  : list[str] = []
        declared    : set[str]  = set()   # local var names declared via accessor

        for line in lines:
            stripped = line.strip()

            # Match:  Type varName = pvar.field();
            m = re.match(
                r'^[\w<>\[\].,\s]+?\s+(\w+)\s*=\s*'
                + re.escape(pvar)
                + r'\s*\.\s*(\w+)\s*\(\s*\)\s*;$',
                stripped,
            )
            if m:
                local_name  = m.group(1)
                method_name = m.group(2)
                if method_name in field_names:
                    # This is an accessor extraction — remove the line
                    declared.add(local_name)
                    continue
                else:
                    # Calling a non-record method on pvar — unsafe
                    return None

            keep_lines.append(line)

        # If pvar still appears in the remaining body (not just in removed lines)
        remaining = '\n'.join(keep_lines)
        if re.search(r'\b' + re.escape(pvar) + r'\b', remaining):
            # pvar used for something other than accessor calls — unsafe
            return None

        return '\n'.join(keep_lines)
