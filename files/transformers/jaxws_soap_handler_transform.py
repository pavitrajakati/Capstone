import re
from .base_transformer import BaseTransformer


class JAXWSSOAPHandlerTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        original = content

        # ---------------------------------------------------------
        # 1. Replace import javax.xml.ws.handler.soap.* 
        #    -> import jakarta.xml.ws.handler.soap.*
        # ---------------------------------------------------------
        lines = content.split("\n")
        new_lines: list[str] = []

        for line in lines:
            stripped = line.strip()

            # Ignore already-commented lines
            if stripped.startswith("//"):
                new_lines.append(line)
                continue

            if stripped.startswith("import javax.xml.ws.handler.soap."):
                import_path = stripped[len("import "):].rstrip(";").strip()
                replaced_line = line.replace(
                    "import javax.xml.ws.handler.soap.",
                    "import jakarta.xml.ws.handler.soap."
                )
                if replaced_line != line:
                    new_lines.append(replaced_line)
                    changes.append(
                        f"Replaced JAX-WS SOAP handler import `{import_path}` with Jakarta equivalent"
                    )
                    continue

            new_lines.append(line)

        content = "\n".join(new_lines)

        # ---------------------------------------------------------
        # 2. Replace fully qualified package references
        #    Example:
        #    javax.xml.ws.handler.soap.SOAPMessageContext
        #    -> jakarta.xml.ws.handler.soap.SOAPMessageContext
        # ---------------------------------------------------------
        new_content = re.sub(
            r'\bjavax\.xml\.ws\.handler\.soap\.',
            'jakarta.xml.ws.handler.soap.',
            content
        )
        if new_content != content:
            changes.append(
                "Replaced javax.xml.ws.handler.soap package references with jakarta.xml.ws.handler.soap"
            )
        content = new_content

        # ---------------------------------------------------------
        # 3. Add one migration comment if Jakarta package is now used
        # ---------------------------------------------------------
        migration_comment = (
            "// JAVA21-MIGRATION: javax.xml.ws.handler.soap (JAX-WS SOAP handler API) "
            "is not bundled with modern JDKs. Use Jakarta XML Web Services and add "
            "dependency: jakarta.xml.ws:jakarta.xml.ws-api"
        )

        if (
            "jakarta.xml.ws.handler.soap" in content
            and migration_comment not in content
        ):
            content = migration_comment + "\n" + content
            changes.append("Added JAX-WS SOAP handler migration dependency comment")

        # ---------------------------------------------------------
        # 4. Clean repeated blank lines
        # ---------------------------------------------------------
        content = re.sub(r'\n{3,}', '\n\n', content)

        if content == original:
            return content, []

        return content, changes