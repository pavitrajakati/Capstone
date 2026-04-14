"""
config.py — Central configuration for the Java 8→21 transformer.

All pattern data, removed APIs, and tunable constants live here so
that individual transformers stay clean and don't hard-code values.
"""

# ── File handling ──────────────────────────────────────────────────────────────
JAVA_EXTENSIONS: set[str] = {".java"}


# ── Wrapper types whose constructors were deprecated in Java 9 ─────────────────
# new Integer(x) → Integer.valueOf(x)  etc.
# Excludes Boolean (handled separately for TRUE/FALSE literals).
DEPRECATED_WRAPPER_TYPES: list[str] = [
    "Integer",
    "Long",
    "Double",
    "Float",
    "Short",
    "Byte",
    "Character",
]


# ── Removed / strongly-encapsulated imports ────────────────────────────────────
# Key   : import prefix (startswith match)
# Value : (replacement_import | None,  human-readable migration note)
REMOVED_IMPORTS: dict[str, tuple[str | None, str]] = {
    "sun.misc.BASE64Encoder": (
        "java.util.Base64",
        "sun.misc.BASE64Encoder was removed in Java 9. "
        "Use java.util.Base64.getEncoder() / encodeToString().",
    ),
    "sun.misc.BASE64Decoder": (
        "java.util.Base64",
        "sun.misc.BASE64Decoder was removed in Java 9. "
        "Use java.util.Base64.getDecoder() / decode().",
    ),
    "javax.xml.bind": (
        None,
        "javax.xml.bind (JAXB) removed from JDK in Java 11 (JEP 320). "
        "Add Maven/Gradle dep: jakarta.xml.bind:jakarta.xml.bind-api",
    ),
    "javax.xml.ws": (
        None,
        "javax.xml.ws (JAX-WS) removed from JDK in Java 11 (JEP 320). "
        "Add Maven/Gradle dep: jakarta.xml.ws:jakarta.xml.ws-api",
    ),
    "javax.activation": (
        None,
        "javax.activation removed from JDK in Java 11 (JEP 320). "
        "Add Maven/Gradle dep: jakarta.activation:jakarta.activation-api",
    ),
    "javax.jws": (
        None,
        "javax.jws removed from JDK in Java 11 (JEP 320). "
        "Add Maven/Gradle dep: jakarta.jws:jakarta.jws-api",
    ),
    "java.util.jar.Pack200": (
        None,
        "Pack200 API removed in Java 14 (JEP 367). Remove Pack200 usage entirely.",
    ),
    "com.sun.": (
        None,
        "com.sun.* internal APIs are strongly encapsulated since Java 16 (JEP 396/403). "
        "Switch to documented public APIs.",
    ),
    "sun.": (
        None,
        "sun.* internal APIs are strongly encapsulated since Java 16 (JEP 396/403). "
        "Switch to documented public APIs.",
    ),
}


# ── Collections factory replacements (for CollectionsFactoryTransformer) ───────
# Maps old Collections.* call → (new expression, java version introduced)
COLLECTIONS_EMPTY_MAP: dict[str, tuple[str, str]] = {
    "Collections.emptyList()": ("List.of()",  "Java 9 JEP 269"),
    "Collections.emptySet()":  ("Set.of()",   "Java 9 JEP 269"),
    "Collections.emptyMap()":  ("Map.of()",   "Java 9 JEP 269"),
}

COLLECTIONS_SINGLETON_MAP: dict[str, tuple[str, str]] = {
    "Collections.singletonList": ("List.of",  "Java 9 JEP 269"),
    "Collections.singleton":     ("Set.of",   "Java 9 JEP 269"),
    "Collections.singletonMap":  ("Map.of",   "Java 9 JEP 269"),
}


# ── Removed method call signatures (for DeprecatedMethodsTransformer) ──────────
# Each entry: (description, migration_hint)
# The actual regex patterns are in deprecated_methods.py.
REMOVED_METHOD_INFO: dict[str, tuple[str, str]] = {
    "thread_stop_throwable": (
        "Thread.stop(Throwable) removed in Java 11",
        "Use Thread.interrupt() with cooperative cancellation instead.",
    ),
    "runtime_run_finalizers": (
        "Runtime.runFinalizersOnExit() removed in Java 11",
        "Do not rely on finalizers; remove this call.",
    ),
    "system_run_finalizers": (
        "System.runFinalizersOnExit() removed in Java 11",
        "Do not rely on finalizers; remove this call.",
    ),
}
