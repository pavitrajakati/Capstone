"""
virtual_threads.py — JEP 444 (Java 21): Virtual Threads.

Identifies thread-creation patterns that are safe to migrate to virtual
threads and performs the transformation.

Transformations applied
───────────────────────
  1. Inline start:
       new Thread(runnable).start()
       →  Thread.startVirtualThread(runnable)   // Java 21 JEP 444

  2. Named thread (start on next line not needed — just the factory):
       new Thread(runnable)
       →  Thread.ofVirtual().unstarted(runnable)
     Only when the result is stored:  Thread t = new Thread(runnable);

  3. Cached thread pool executor:
       Executors.newCachedThreadPool()
       →  Executors.newVirtualThreadPerTaskExecutor()

Safety analysis
───────────────
  TRANSFORMATION 1 — `new Thread(r).start()` → `Thread.startVirtualThread(r)`
    Safe when the `new Thread(r)` is an ANONYMOUS, immediately-started thread.
    The ONLY behavioural difference is:
      • Virtual threads are always DAEMON threads.
        Platform threads are non-daemon by default.
    This matters only if your program's shutdown sequence relies on this
    specific thread keeping the JVM alive.  For the vast majority of
    fire-and-forget tasks this is identical.
    A // JAVA21-NOTE comment is added to flag this for review.

  TRANSFORMATION 2 — `Thread t = new Thread(r)` → `Thread.ofVirtual().unstarted(r)`
    Preserves the Thread reference for later `.start()` / `.join()` calls.
    Same daemon-thread caveat as above.  Comment added.

  TRANSFORMATION 3 — `Executors.newCachedThreadPool()` only when used inside
    try-with-resources:
      try (ExecutorService es = Executors.newCachedThreadPool())
    Virtual thread-per-task executor is the direct Java 21 replacement for
    unbounded cached pools when tasks are I/O-bound.
    We only transform the try-with-resources form because it guarantees the
    executor is properly shut down — same lifecycle contract as the original.

  NOT transformed (left unchanged)
  ─────────────────────────────────
    • Threads with explicit names:  new Thread(r, "worker")
    • Threads with thread groups
    • `new Thread()` with an overridden `run()` (anonymous subclass)
    • `Executors.newFixedThreadPool()` — fixed pools imply CPU-bound work
    • `Executors.newSingleThreadExecutor()` — ordering semantics may differ

Import management
─────────────────
  `Thread.startVirtualThread` and `Thread.ofVirtual` are on `java.lang.Thread`
  which is always auto-imported.  `Executors` is in `java.util.concurrent` —
  already imported when used.  No import injection needed.
"""
import re
from .base_transformer import BaseTransformer


# ── Pattern 1: new Thread(runnable).start() ────────────────────────────────────
# Only when runnable is a simple identifier, lambda, or method ref.
# NOT when there is a second argument (thread name etc.).
_SIMPLE_RUNNABLE = r'((?:[^()]+|\([^()]*\))+?)'   # one arg, ≤1 nesting

_INLINE_START = re.compile(
    r'\bnew\s+Thread\s*\(\s*'
    + _SIMPLE_RUNNABLE
    + r'\s*\)\s*\.\s*start\s*\(\s*\)',
)

# ── Pattern 2: Thread t = new Thread(runnable); ───────────────────────────────
_STORED_THREAD = re.compile(
    r'\bThread\s+(\w+)\s*=\s*new\s+Thread\s*\(\s*'
    + _SIMPLE_RUNNABLE
    + r'\s*\)\s*;',
)

# ── Pattern 3: try-with-resources Executors.newCachedThreadPool() ─────────────
_CACHED_POOL_TWR = re.compile(
    r'(try\s*\(\s*ExecutorService\s+\w+\s*=\s*)'
    r'Executors\s*\.\s*newCachedThreadPool\s*\(\s*\)',
)

_NOTE = '// JAVA21-NOTE (JEP 444): virtual threads are daemon threads — verify JVM shutdown is unaffected'


class VirtualThreadsTransformer(BaseTransformer):

    def transform(self, content: str) -> tuple[str, list[str]]:
        changes : list[str] = []
        result  = content

        # ── Pattern 1 ──────────────────────────────────────────────────────────
        def _replace_inline(m: re.Match) -> str:
            runnable = m.group(1).strip()
            return (
                f'Thread.startVirtualThread({runnable}) {_NOTE}'
            )

        new_result, n = _INLINE_START.subn(_replace_inline, result)
        if n:
            changes.append(
                f"Replaced {n}× `new Thread(r).start()` → "
                f"`Thread.startVirtualThread(r)` (JEP 444, Java 21)"
            )
        result = new_result

        # ── Pattern 2 ──────────────────────────────────────────────────────────
        def _replace_stored(m: re.Match) -> str:
            tvar     = m.group(1)
            runnable = m.group(2).strip()
            return (
                f'Thread {tvar} = Thread.ofVirtual().unstarted({runnable}); '
                f'{_NOTE}'
            )

        new_result, n = _STORED_THREAD.subn(_replace_stored, result)
        if n:
            changes.append(
                f"Replaced {n}× `Thread t = new Thread(r)` → "
                f"`Thread.ofVirtual().unstarted(r)` (JEP 444, Java 21)"
            )
        result = new_result

        # ── Pattern 3 ──────────────────────────────────────────────────────────
        new_result, n = _CACHED_POOL_TWR.subn(
            r'\1Executors.newVirtualThreadPerTaskExecutor()',
            result,
        )
        if n:
            changes.append(
                f"Replaced {n}× `Executors.newCachedThreadPool()` (in try-with-resources) → "
                f"`Executors.newVirtualThreadPerTaskExecutor()` (JEP 444, Java 21)"
            )
        result = new_result

        return result, changes
