import re

class RemoveNotifyTransformer:
    def transform(self, content: str):
        changes = []

        # Find all classes
        class_pattern = r'class\s+\w+[^{]*\{'
        class_matches = list(re.finditer(class_pattern, content))

        # Find removeNotify methods
        method_pattern = r'\b(public|protected)\s+void\s+removeNotify\s*\(\s*\)\s*\{([\s\S]*?)\}'
        method_matches = list(re.finditer(method_pattern, content))

        for match in reversed(method_matches):
            original_body = match.group(2)

            # Clean body (remove super call)
            cleaned_body = re.sub(
                r'super\.removeNotify\s*\(\s*\)\s*;', '', original_body
            ).strip()

            # Remove entire method always
            content = content[:match.start()] + content[match.end():]

            # ---------- CASE 1: ONLY super.removeNotify() ----------
            if cleaned_body == "":
                changes.append("Removed redundant removeNotify() (only super call)")
                continue

            # ---------- CASE 2: HAS REAL LOGIC ----------
            insert_pos = None
            for cls in reversed(class_matches):
                if cls.start() < match.start():
                    insert_pos = cls.end()
                    break

            if insert_pos is None:
                continue

            new_method = f"""

    // Auto-migrated from removeNotify()
    public void cleanupResources() {{

        // Preserved cleanup logic
        {cleaned_body}
    }}
"""

            content = content[:insert_pos] + new_method + content[insert_pos:]
            changes.append("Converted removeNotify() to cleanupResources()")

        return content, changes