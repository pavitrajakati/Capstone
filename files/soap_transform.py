import re
from .base_transformer import BaseTransformer


class SOAPTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        original = content

        dependency_needed = False

        # ---------------------------------------------------------
        # 1. Replace import javax.xml.soap.* -> import jakarta.xml.soap.*
        # ---------------------------------------------------------
        lines = content.split("\n")
        new_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Do not touch already-commented lines
            if stripped.startswith("//"):
                new_lines.append(line)
                continue

            if stripped.startswith("import javax.xml.soap."):
                import_path = stripped[len("import "):].rstrip(";").strip()
                replaced_line = line.replace(
                    "import javax.xml.soap.",
                    "import jakarta.xml.soap."
                )
                if replaced_line != line:
                    new_lines.append(replaced_line)
                    dependency_needed = True
                    changes.append(
                        f"Replaced SOAP import `{import_path}` with Jakarta equivalent"
                    )
                    continue

            new_lines.append(line)

        content = "\n".join(new_lines)

        # ---------------------------------------------------------
        # 2. Replace fully qualified package references
        #    Example:
        #    javax.xml.soap.SOAPMessage -> jakarta.xml.soap.SOAPMessage
        # ---------------------------------------------------------
        new_content = re.sub(
            r'\bjavax\.xml\.soap\.',
            'jakarta.xml.soap.',
            content
        )
        if new_content != content:
            changes.append("Replaced javax.xml.soap package references with jakarta.xml.soap")
            dependency_needed = True
        content = new_content

        # ---------------------------------------------------------
        # 3. Add ONE migration comment if Jakarta SOAP is now used
        # ---------------------------------------------------------
        migration_comment = (
            "// JAVA21-MIGRATION: javax.xml.soap (SAAJ) is not bundled with modern JDKs. "
            "Use Jakarta SOAP and add dependency: jakarta.xml.soap:jakarta.xml.soap-api"
        )

        if ("jakarta.xml.soap" in content) and (migration_comment not in content):
            content = migration_comment + "\n" + content
            changes.append("Added SOAP migration dependency comment")

        # ---------------------------------------------------------
        # 4. Clean extra blank lines
        # ---------------------------------------------------------
        content = re.sub(r'\n{3,}', '\n\n', content)

        if content == original:
            return content, []

        return content, changes