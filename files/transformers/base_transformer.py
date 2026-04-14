"""
base_transformer.py — Abstract base class every transformer must extend.

Contract that ALL subclasses must uphold
────────────────────────────────────────
  ✔  Input and output Java programs must behave identically at runtime.
  ✔  Time and space complexity of the transformed code must NOT increase.
  ✔  Only change what is strictly necessary (no cosmetic rewrites).
  ✔  If in doubt, leave the code unchanged.
"""
from abc import ABC, abstractmethod


class BaseTransformer(ABC):

    @abstractmethod
    def transform(self, content: str) -> tuple[str, list[str]]:
        """
        Args:
            content: Full Java source file as a UTF-8 string.

        Returns:
            (new_content, changes)
            where `changes` is a list of human-readable descriptions of
            every modification made (empty list = no changes).
        """
