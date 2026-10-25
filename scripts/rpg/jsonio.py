"""Strict JSON decoding for human-reviewed plans and policy files.

Reject duplicate field names at any nesting depth and nonstandard JSON
constants (NaN, Infinity). Otherwise displayed JSON may disagree with the
object that the executor ultimately processes.
"""
import json
from pathlib import Path

from .errors import GuardError


def _pairs_unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise GuardError("duplicate JSON field: " + key)
        value[key] = item
    return value


def _reject_constant(value):
    raise GuardError("nonstandard JSON constant: " + value)


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"),
                          object_pairs_hook=_pairs_unique,
                          parse_constant=_reject_constant)
    except (ValueError, UnicodeError) as error:
        raise GuardError("invalid JSON: " + str(error)) from error
