"""Fail-closed publisher errors."""

class GuardError(Exception):
    """Publishing was blocked before or during an unsafe operation."""


def require(condition, message):
    if not condition:
        raise GuardError(message)

