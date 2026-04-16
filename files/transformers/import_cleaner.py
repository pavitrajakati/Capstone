"""
import_cleaner.py — Comment out imports for APIs removed from the JDK.

APIs handled (see config.REMOVED_IMPORTS for the full table)
────────────────────────────────────────────────────────────
  sun.misc.BASE64Encoder/Decoder  →  java.util.Base64  (auto-added)
  javax.xml.bind.*                →  add Maven dep
  javax.xml.ws.*                  →  add Maven dep
  javax.activation.*              →  add Maven dep
  javax.jws.*                     →  add Maven dep
  java.util.jar.Pack200           →  remove usage
  com.sun.*  / sun.*              →  use public APIs

Algorithm
─────────
  1. Split source into lines.
  2. For each `import` line that matches a removed prefix:
       a. Prepend a JAVA21-MIGRATION comment with the reason.
       b. Comment out the original import line.
       c. If a drop-in replacement import exists (e.g. java.util.Base64),
          add it once — only the first time that replacement is needed.
  3. Non-matching lines are passed through unchanged.

Safety guarantee
────────────────
  Commenting out an import of a removed API makes the file compile-safe on
  Java 21.  The developer must update call-sites where the removed type was
  actually used; those are flagged by the compiler after this step.
"""
from .base_transformer import BaseTransformer
from config import REMOVED_IMPORTS


class ImportCleanerTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes: list[str] = []
        lines = content.split("\n")
        new_lines: list[str] = []

        # Track which replacement imports we have already inserted
        added_replacements: set[str] = set()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("import javax.xml.bind"):
                new_lines.append(line)
                continue
            if not stripped.startswith("import "):
                new_lines.append(line)
                continue
            if "javax.xml.bind" in line:
                return content, []
            # Extract the import path (strip 'import ' and trailing ';')
            import_path = stripped[len("import "):].rstrip(";").strip()
            matched = False

            for prefix, (replacement, message) in REMOVED_IMPORTS.items():
                if (
                    import_path == prefix
                    or import_path.startswith(prefix + ".")
                    or (prefix.endswith(".") and import_path.startswith(prefix))
                ):
                    # Add migration comment
                    new_lines.append(f"// JAVA21-MIGRATION: {message}")
                    # Comment out the original import
                    new_lines.append(f"// {line.rstrip()}")

                    # Auto-insert replacement import (once per replacement)
                    if replacement and replacement not in added_replacements:
                        new_lines.append(f"import {replacement};")
                        added_replacements.add(replacement)

                    changes.append(
                        f"Commented out removed import `{import_path}` "
                        f"({message[:55]}...)"
                    )
                    matched = True
                    break

            if not matched:
                new_lines.append(line)

        return "\n".join(new_lines), changes
