"""
file_walker.py — Walks the source directory tree.

Responsibilities:
  • Discover all .java files under the source root.
  • Copy non-Java files (resources, XML, properties…) to the
    destination with the exact same relative directory structure.
"""
import shutil
from pathlib import Path
from config import JAVA_EXTENSIONS
from transformers.generational_zgc import GenerationalZGCPatcher


class FileWalker:
    def __init__(self, source: Path, destination: Path) -> None:
        self.source      = source
        self.destination = destination

    # ── Public API ─────────────────────────────────────────────────────────────

    def find_java_files(self) -> list[Path]:
        """Return all .java files under source, sorted for deterministic order."""
        return sorted(
            p for p in self.source.rglob("*")
            if p.is_file() and p.suffix in JAVA_EXTENSIONS
        )

    # Folders to never copy into the destination
    _SKIP_DIRS: set[str] = {
        ".git", ".svn", ".hg",          # version control
        ".idea", ".vscode",             # IDE metadata
        "__pycache__", ".pytest_cache", # Python artefacts
        "target", "build", "out",       # build output
        ".gradle", ".mvn",              # build tool caches
    }

    def _is_skipped(self, path: Path) -> bool:
        """Return True if any part of the path is in the skip list."""
        return any(part in self._SKIP_DIRS for part in path.parts)

    def copy_non_java_files(self) -> None:
        """
        Mirror every non-Java file from source → destination, preserving the
        full directory structure.  Version-control folders (.git etc.) and
        IDE/build artefact folders are skipped to avoid permission errors.
        """
        copied  = 0
        skipped = 0

        for src_file in self.source.rglob("*"):
            if not src_file.is_file():
                continue
            if src_file.suffix in JAVA_EXTENSIONS:
                continue

            rel = src_file.relative_to(self.source)

            if self._is_skipped(rel):
                skipped += 1
                continue

            dst_file = self.destination / rel
            try:
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
                copied += 1
            except PermissionError as e:
                print(f"  [WARN] Permission denied, skipping: {rel}  ({e})")

        if copied:
            print(f"  Copied {copied} non-Java file(s) as-is.")
        if skipped:
            print(f"  Skipped {skipped} file(s) in ignored folders (.git, build, etc.)")

    def patch_config_files(self, verbose: bool = False) -> None:
        """
        Run the Generational ZGC patcher (JEP 439) on all non-Java config
        files in the destination folder that may contain JVM flags.
        """
        patcher = GenerationalZGCPatcher()
        patched = 0

        for dst_file in self.destination.rglob("*"):
            if not dst_file.is_file():
                continue
            if dst_file.suffix not in patcher.EXTENSIONS:
                continue

            try:
                content     = dst_file.read_text(encoding="utf-8", errors="replace")
                new_content, changed = patcher.patch(content)
                if changed:
                    dst_file.write_text(new_content, encoding="utf-8")
                    patched += 1
                    if verbose:
                        rel = dst_file.relative_to(self.destination)
                        print(
                            f"    [GenerationalZGCPatcher] Added `-XX:+ZGenerational` "
                            f"to {rel} (JEP 439, Java 21)"
                        )
            except OSError:
                pass

        if patched:
            print(f"  Applied Generational ZGC flag to {patched} config file(s) (JEP 439).")
