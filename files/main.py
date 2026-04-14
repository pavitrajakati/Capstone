#!/usr/bin/env python3
"""
Java 8→21 Transformer — Entry Point
=====================================
Usage:
  python main.py <source_dir> <dest_dir>
  python main.py <source_dir> <dest_dir> --dry-run
  python main.py <source_dir> <dest_dir> --verbose
"""
import argparse
import sys
from pathlib import Path

from file_walker import FileWalker
from java_transformer import JavaTransformer
from reporter import Reporter


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transform Java source files (8–20) to idiomatic Java 21.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py ./src  ./src_java21
  python main.py ./src  ./out  --dry-run
  python main.py ./src  ./out  --verbose
        """,
    )
    parser.add_argument("source",      help="Source folder containing Java files")
    parser.add_argument("destination", help="Destination folder for transformed output")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what would change without writing any files",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print every individual change per file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source).resolve()
    dest   = Path(args.destination).resolve()

    if not source.exists():
        print(f"[ERROR] Source directory does not exist: {source}", file=sys.stderr)
        sys.exit(1)

    if not source.is_dir():
        print(f"[ERROR] Source path is not a directory: {source}", file=sys.stderr)
        sys.exit(1)

    if source == dest:
        print("[ERROR] Source and destination must be different directories.", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("  Java 8→21 Source Transformer")
    print("=" * 60)
    print(f"  Source      : {source}")
    print(f"  Destination : {dest}")
    print(f"  Dry run     : {args.dry_run}")
    print(f"  Verbose     : {args.verbose}")
    print()

    walker      = FileWalker(source, dest)
    transformer = JavaTransformer(verbose=args.verbose)
    reporter    = Reporter(verbose=args.verbose)

    java_files = walker.find_java_files()

    if not java_files:
        print("No .java files found in source directory.")
        sys.exit(0)

    print(f"Found {len(java_files)} Java file(s). Processing...\n")

    for java_file in java_files:
        rel_path  = java_file.relative_to(source)
        dest_file = dest / rel_path

        try:
            original = java_file.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"  [WARN] Could not read {rel_path}: {e}", file=sys.stderr)
            continue

        transformed, changes = transformer.transform(original, str(rel_path))
        reporter.record(str(rel_path), changes)

        if not args.dry_run:
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            dest_file.write_text(transformed, encoding="utf-8")

    if not args.dry_run:
        walker.copy_non_java_files()
        walker.patch_config_files(verbose=args.verbose)

    reporter.print_summary(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
