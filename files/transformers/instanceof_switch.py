"""
instanceof_switch.py — JEP 441 (Java 21): Pattern Matching for switch.

Converts multi-branch if/else-if instanceof chains into switch expressions.

Before (old style)
──────────────────
    if (shape instanceof Circle c) {
        return c.radius() * 2;
    } else if (shape instanceof Rectangle r) {
        return r.width() * r.height();
    } else {
        return 0;
    }

After (Java 21)
───────────────
    return switch (shape) {
        case Circle c    -> c.radius() * 2;
        case Rectangle r -> r.width() * r.height();
        default          -> 0;
    };

Safety rules
────────────
  1. All branches check the SAME variable (simple identifier).
  2. At least 2 instanceof branches required.
  3. Each branch body: EXACTLY ONE statement (return expr; or expr;).
  4. All branches consistently return-based or expression-based.
  5. Branches scanned SEQUENTIALLY — else-if branches never re-processed.
"""
import re
from .base_transformer import BaseTransformer


def _extract_block(source: str, open_pos: int) -> tuple[str, int]:
    depth, i = 0, open_pos
    while i < len(source):
        if   source[i] == '{': depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0:
                return source[open_pos + 1 : i], i + 1
        i += 1
    return source[open_pos + 1:], len(source)


def _single_stmt(block: str) -> str | None:
    stripped = block.strip()
    if '{' in stripped or '}' in stripped:
        return None
    parts = [p.strip() for p in stripped.split(';') if p.strip()]
    return parts[0] if len(parts) == 1 else None


def _is_return(stmt: str) -> tuple[bool, str]:
    m = re.match(r'^return\s+(.+)$', stmt, re.DOTALL)
    return (True, m.group(1).strip()) if m else (False, stmt)


def _indentation(source: str, pos: int) -> str:
    line_start = source.rfind('\n', 0, pos) + 1
    indent = []
    for ch in source[line_start:pos]:
        if ch in (' ', '\t'):
            indent.append(ch)
        else:
            break
    return ''.join(indent)


_IF_INST_RE = re.compile(
    r'\bif\s*\(\s*'
    r'(?P<var>\w+)\s+instanceof\s+'
    r'(?P<type>\w+(?:\.\w+)*)\s+'
    r'(?P<pvar>\w+)'
    r'\s*\)\s*\{',
    re.MULTILINE,
)

_ELSEIF_INST_RE = re.compile(
    r'\}\s*else\s+if\s*\(\s*'
    r'(?P<var>\w+)\s+instanceof\s+'
    r'(?P<type>\w+(?:\.\w+)*)\s+'
    r'(?P<pvar>\w+)'
    r'\s*\)\s*\{',
    re.MULTILINE,
)

_ELSE_RE = re.compile(r'\}\s*else\s*\{', re.MULTILINE)


class InstanceofSwitchTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        result  = content
        processed_ends: list[int] = []
        scan_pos = 0

        while True:
            m = _IF_INST_RE.search(content, scan_pos)
            if not m:
                break

            if any(m.start() < end for end in processed_ends):
                scan_pos = m.end()
                continue

            chain_var = m.group('var')
            replacement, orig_end, n_branches = self._try_convert(content, m, chain_var)

            if replacement is None:
                scan_pos = m.end()
                continue

            offset = len(result) - len(content)
            adj_s  = m.start() + offset
            adj_e  = orig_end  + offset
            result = result[:adj_s] + replacement + result[adj_e:]

            processed_ends.append(orig_end)
            scan_pos = orig_end
            changes.append(
                f"Converted {n_branches}-branch instanceof if/else chain on "
                f"`{chain_var}` -> switch expression (JEP 441, Java 21)"
            )

        return result, changes

    def _try_convert(self, source: str, first_match: re.Match, chain_var: str) -> tuple[str | None, int, int]:
        branches: list[tuple[str, str, str]] = []
        default : str | None = None
        is_ret  : bool | None = None

        brace_open   = source.index('{', first_match.end() - 1)
        body, pos    = _extract_block(source, brace_open)
        stmt         = _single_stmt(body)
        if stmt is None:
            return None, 0, 0
        ret, expr    = _is_return(stmt)
        is_ret       = ret
        branches.append((first_match.group('type'), first_match.group('pvar'), expr))

        while True:
            m2 = _ELSEIF_INST_RE.match(source, pos - 1)
            if m2 and m2.group('var') == chain_var:
                brace_open  = source.index('{', m2.end() - 1)
                body, pos   = _extract_block(source, brace_open)
                stmt        = _single_stmt(body)
                if stmt is None:
                    return None, 0, 0
                ret2, expr2 = _is_return(stmt)
                if ret2 != is_ret:
                    return None, 0, 0
                branches.append((m2.group('type'), m2.group('pvar'), expr2))
                continue

            m3 = _ELSE_RE.match(source, pos - 1)
            if m3:
                brace_open  = source.index('{', m3.end() - 1)
                body, pos   = _extract_block(source, brace_open)
                stmt        = _single_stmt(body)
                if stmt is None:
                    return None, 0, 0
                ret3, expr3 = _is_return(stmt)
                if ret3 != is_ret:
                    return None, 0, 0
                default = expr3
            break

        if len(branches) < 2:
            return None, 0, 0

        indent = _indentation(source, first_match.start())
        inner  = indent + '    '
        prefix = 'return ' if is_ret else ''

        max_w = max(len(f'case {t} {v}') for t, v, _ in branches)
        if default is not None:
            max_w = max(max_w, len('default'))

        lines = [f'{prefix}switch ({chain_var}) {{']
        for typ, pvar, expr in branches:
            lbl = f'case {typ} {pvar}'
            pad = ' ' * (max_w - len(lbl))
            lines.append(f'{inner}{lbl}{pad} -> {expr};')
        if default is not None:
            pad = ' ' * (max_w - len('default'))
            lines.append(f'{inner}default{pad} -> {default};')
        lines.append(f'{indent}}};')

        return '\n'.join(lines), pos, len(branches)
