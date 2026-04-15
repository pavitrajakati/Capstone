import re
from .base_transformer import BaseTransformer

class JAXBUtilRemovalTransformer(BaseTransformer):

    def transform(self, content: str):
        changes = []

        # 1. Replace util package with jakarta
        new_content = re.sub(
            r'import\s+javax\.xml\.bind\.util\.',
            'import jakarta.xml.bind.util.',
            content
        )
        if new_content != content:
            changes.append("Replaced javax.xml.bind.util with jakarta.xml.bind.util")
        content = new_content

        # 2. Add migration comment if JAXB util is used
        if "jakarta.xml.bind.util" in content:
            if "JAXB util requires dependency" not in content:
                content = (
                    "// JAVA21-MIGRATION: Add dependency: jakarta.xml.bind:jakarta.xml.bind-api\n"
                    + content
                )
                changes.append("Added JAXB dependency comment")

        return content, changes