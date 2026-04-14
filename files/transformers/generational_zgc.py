"""
generational_zgc.py — JEP 439 (Java 21): Generational ZGC.

JEP 439 is a JVM-level feature, not a Java source code change.
It activates Generational ZGC by adding a JVM flag:

  -XX:+UseZGC                    ← already present (enables ZGC)
  -XX:+ZGenerational             ← NEW flag to add (enables generational mode)

This transformer scans NON-Java configuration files for existing ZGC flags
and adds the Generational flag where missing.

Files scanned
─────────────
  *.properties          jvm.options=-XX:+UseZGC
  *.xml  (Maven)        <jvmArg>-XX:+UseZGC</jvmArg>
  *.gradle              jvmArgs '-XX:+UseZGC'
  *.gradle.kts          jvmArgs("-XX:+UseZGC")
  *.sh / *.bat          java -XX:+UseZGC ...
  *.yaml / *.yml        JAVA_OPTS: "-XX:+UseZGC"
  *.conf                -XX:+UseZGC

Safety guarantee
────────────────
  ✔  -XX:+ZGenerational is ADDITIVE — it does not remove or override any
     existing flag.  If the flag is already present, the file is skipped.
  ✔  Only lines that already contain -XX:+UseZGC are touched.
  ✔  The flag is inserted IMMEDIATELY AFTER -XX:+UseZGC on the same line
     OR on the very next line for readability.
  ✔  This transformer is called separately by main.py for non-Java files.

Usage (called from main.py, not from the Java pipeline)
────────────────────────────────────────────────────────
  from transformers.generational_zgc import GenerationalZGCPatcher
  patcher = GenerationalZGCPatcher()
  new_content, changed = patcher.patch(content)
"""
import re


_ZGC_FLAG       = '-XX:+UseZGC'
_GEN_FLAG       = '-XX:+ZGenerational'

# Matches a line containing -XX:+UseZGC but NOT already -XX:+ZGenerational
_LINE_WITH_ZGC  = re.compile(
    r'^(?P<before>.*)'
    r'(?P<flag>' + re.escape(_ZGC_FLAG) + r')'
    r'(?P<after>.*)$',
    re.MULTILINE,
)


class GenerationalZGCPatcher:
    """
    Not a BaseTransformer subclass — operates on config files, not Java source.
    Called directly from file_walker for non-Java files.
    """

    # File extensions this patcher handles
    EXTENSIONS = {
        '.properties', '.xml', '.gradle', '.kts',
        '.sh', '.bat', '.yaml', '.yml', '.conf', '.env',
    }

    def patch(self, content: str) -> tuple[str, bool]:
        """
        Returns (new_content, was_changed).
        If -XX:+ZGenerational is already present anywhere, returns unchanged.
        """
        if _GEN_FLAG in content:
            return content, False   # already has the flag

        if _ZGC_FLAG not in content:
            return content, False   # ZGC not used — nothing to do

        def _replace(m: re.Match) -> str:
            before = m.group('before')
            after  = m.group('after')
            # Insert the new flag right after the existing UseZGC flag
            return f'{before}{_ZGC_FLAG} {_GEN_FLAG}{after}'

        new_content, n = _LINE_WITH_ZGC.subn(_replace, content)
        return new_content, n > 0
