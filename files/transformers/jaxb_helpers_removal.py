import re
from .base_transformer import BaseTransformer

class JAXBHelpersRemovalTransformer(BaseTransformer):

    def transform(self, content: str):
        changes = []
        original = content

        # 1. Remove helpers import
        new_content = re.sub(
            r'import\s+javax\.xml\.bind\.helpers\..*;\n?',
            '',
            content
        )
        if new_content != content:
            changes.append("Removed javax.xml.bind.helpers import")
        content = new_content

        # 2. Replace javax.xml.bind → jakarta.xml.bind
        new_content = re.sub(
            r'import\s+javax\.xml\.bind\.',
            'import jakarta.xml.bind.',
            content
        )
        if new_content != content:
            changes.append("Replaced javax.xml.bind with jakarta.xml.bind")
        content = new_content

        # 3. Replace Base64 encode
        new_content = re.sub(
            r'DatatypeConverter\.printBase64Binary\((.*?)\)',
            r'Base64.getEncoder().encodeToString(\1)',
            content
        )
        if new_content != content:
            changes.append("Replaced DatatypeConverter.printBase64Binary with Base64 encoder")
        content = new_content

        # 4. Replace Base64 decode
        new_content = re.sub(
            r'DatatypeConverter\.parseBase64Binary\((.*?)\)',
            r'Base64.getDecoder().decode(\1)',
            content
        )
        if new_content != content:
            changes.append("Replaced DatatypeConverter.parseBase64Binary with Base64 decoder")
        content = new_content

        # 5. Add Base64 import if needed
        if ("Base64.getEncoder()" in content or "Base64.getDecoder()" in content):
            if "import java.util.Base64;" not in content:
                content = "import java.util.Base64;\n" + content
                changes.append("Added import java.util.Base64")

        return content, changes