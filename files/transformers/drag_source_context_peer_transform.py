import re

class DragSourceContextPeerTransformer:
    def transform(self, content: str):
        changes = []

        # Pattern for createDragSourceContext(...)
        pattern = r'(\b\w+\b)\.createDragSourceContext\s*\(([\s\S]*?)\)'

        matches = list(re.finditer(pattern, content))

        for match in reversed(matches):
            obj = match.group(1)
            full_call = match.group(0)

            # Check if assigned (logic depends on result)
            before = content[:match.start()]
            is_assigned = re.search(r'=\s*$', before.strip().split('\n')[-1])

            # ✅ CASE 1: NOT ASSIGNED → Safe replace with startDrag()
            if not is_assigned:
                replacement = f"""
        // Auto-replaced removed API: createDragSourceContext(...)
        {obj}.startDrag(
            null,
            DragSource.DefaultCopyDrop,
            null,
            new DragSourceListener() {{
                public void dragDropEnd(DragSourceDropEvent dsde) {{}}
                public void dragEnter(DragSourceDragEvent dsde) {{}}
                public void dragExit(DragSourceEvent dse) {{}}
                public void dragOver(DragSourceDragEvent dsde) {{}}
                public void dropActionChanged(DragSourceDragEvent dsde) {{}}
            }}
        )
        """

                changes.append("Replaced createDragSourceContext() with startDrag()")

            # ⚠️ CASE 2: ASSIGNED → Needs fallback
            else:
                replacement = f"""
        // WARNING: Removed API createDragSourceContext() used in assignment
        // Returning null to preserve compilation — manual fix required
        null
        """

                changes.append("Replaced createDragSourceContext() with null (assignment case)")

            # Replace safely
            content = content[:match.start()] + replacement + content[match.end():]

        return content, changes