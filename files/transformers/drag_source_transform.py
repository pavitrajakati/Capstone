import re

class DragSourceContextTransformer:
    def transform(self, content: str):
        changes = []

        pattern = r'(\b\w+\b)\.createDragSourceContext\s*\(([\s\S]*?)\)\s*;'
        matches = list(re.finditer(pattern, content))

        for match in reversed(matches):
            obj = match.group(1)  # e.g., "source"
            full_match = match.group(0)

            replacement = f"""
        // Auto-replaced deprecated createDragSourceContext()
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
        );
        """

            content = content[:match.start()] + replacement + content[match.end():]

            changes.append("Replaced createDragSourceContext() with startDrag() template")

        return content, changes