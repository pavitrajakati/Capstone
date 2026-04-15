import re

class FinalizeTransformer:
    def transform(self, content: str):
        changes = []

        # Regex to match finalize() with optional annotations
        pattern = r'''
            (@Deprecated\(.*?\)\s*)?        # Optional @Deprecated
            (@SuppressWarnings\(.*?\)\s*)?  # Optional @SuppressWarnings
            \s*(public|protected)\s+void\s+finalize\s*\(\s*\)\s*
            \{([\s\S]*?)\}
        '''

        matches = list(re.finditer(pattern, content, re.VERBOSE))

        # Process from bottom → top to avoid shifting issues
        for match in reversed(matches):
            full_match = match.group(0)
            method_body = match.group(4).strip()

            # 🔹 CASE 1: EMPTY finalize → REMOVE
            if method_body == "":
                content = content.replace(full_match, "")
                changes.append("Removed empty finalize() method")
                continue

            # 🔹 CASE 2: NON-EMPTY → CONVERT
            new_method = f"""
    @Override
    public void close() {{
        {method_body}
    }}
    """

            content = content.replace(full_match, new_method)
            changes.append("Converted finalize() to close()")

            # 🔹 FIND CORRECT CLASS FOR THIS METHOD
            # Find nearest class above this method
            class_pattern = r'class\s+(\w+)([^{]*)\{'
            class_matches = list(re.finditer(class_pattern, content))

            for cls in reversed(class_matches):
                if cls.start() < match.start():
                    class_name = cls.group(1)
                    class_decl = cls.group(0)

                    # Add AutoCloseable only if not already present
                    if "AutoCloseable" not in class_decl:
                        new_decl = class_decl.replace(
                            class_name,
                            f"{class_name} implements AutoCloseable"
                        )
                        content = content.replace(class_decl, new_decl, 1)
                        changes.append(f"Added AutoCloseable to class {class_name}")
                    break

        return content, changes