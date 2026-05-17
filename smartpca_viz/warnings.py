"""Warning collection utility."""

from __future__ import annotations

import sys


class WarningCollector:
    """Collects warnings with context and provides formatted output."""

    def __init__(self) -> None:
        self.messages: list[str] = []

    def add(self, message: str) -> None:
        self.messages.append(message)
        print(f"WARNING: {message}", file=sys.stderr)

    def extend(self, messages: list[str]) -> None:
        for message in messages:
            self.add(message)

    def has_warnings(self) -> bool:
        return len(self.messages) > 0
