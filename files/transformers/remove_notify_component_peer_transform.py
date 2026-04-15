import re

class RemoveNotifyComponentPeerTransformer:
    def transform(self, content: str):
        changes = []

        # ---------- FIND ALL CLASSES ----------
        class_pattern = r'class\s+\w+[^{]*\{'
        class_matches = list(re.finditer(class_pattern, content))

        # ---------- HANDLE METHOD OVERRIDES ----------
        method_pattern = r'\b(public|protected)\s+void\s+removeNotify\s*\(\s*ComponentPeer\s+\w+\s*\)\s*\{([\s\S]*?)\}'
        method_matches = list(re.finditer(method_pattern, content))

        for match in reversed(method_matches):
            original_body = match.group(2)

            # Remove super call safely
            cleaned_body = re.sub(
                r'super\.removeNotify\s*\(\s*\)\s*;', '', original_body
            ).strip()

            # Remove original method
            content = content[:match.start()] + content[match.end():]

            # ---------- CASE 1: EMPTY ----------
            if cleaned_body == "":
                changes.append("Removed empty removeNotify(ComponentPeer)")
                continue

            # ---------- FIND CLASS TO INSERT ----------
            insert_pos = None
            for cls in reversed(class_matches):
                if cls.start() < match.start():
                    insert_pos = cls.end()
                    break

            if insert_pos is None:
                continue

            # ---------- CREATE CLEANUP METHOD ----------
            new_method = f"""

    // Auto-migrated from removeNotify(ComponentPeer)
    public void cleanupResources() {{

        // Preserved cleanup logic
        {cleaned_body}
    }}
"""

            content = content[:insert_pos] + new_method + content[insert_pos:]
            changes.append("Converted removeNotify(ComponentPeer) to cleanupResources()")

        # ---------- HANDLE DIRECT CALLS (FIXED) ----------
        call_pattern = r'\b(\w+)\.removeNotify\s*\(\s*[^)]*\)\s*;'
        call_matches = list(re.finditer(call_pattern, content))

        for match in reversed(call_matches):
            full_match = match.group(0)

            replacement = """
        // Removed deprecated removeNotify(ComponentPeer) call
        // Use cleanupResources() if required
        """

            content = content[:match.start()] + replacement + content[match.end():]
            changes.append("Removed removeNotify(ComponentPeer) call")

        return content, changes