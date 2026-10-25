"""Optional project-specific *additional* restrictions. No policy can relax core rules."""
import fnmatch
import json
from pathlib import Path

from .errors import require
from .jsonio import load_json

POLICY_KEYS = {
    "policyVersion", "allowedRemotes", "allowedBranches", "allowPush",
    "requireValidations", "blockedPaths", "maxCommits"
}


def validate_policy(policy):
    require(isinstance(policy, dict) and set(policy) == POLICY_KEYS,
            "policy must contain exactly: " + ", ".join(sorted(POLICY_KEYS)))
    require(type(policy["policyVersion"]) is int and policy["policyVersion"] == 1,
            "unsupported policyVersion")
    for key in ("allowedRemotes", "allowedBranches", "blockedPaths"):
        values = policy[key]
        require(isinstance(values, list) and all(
            isinstance(x, str) and bool(x) and "\0" not in x for x in values),
            "invalid " + key)
        require(len(values) == len(set(values)), "duplicate " + key)
    require(bool(policy["allowedRemotes"]) and bool(policy["allowedBranches"]),
            "policy requires nonempty allowed remotes and branches")
    for key in ("allowPush", "requireValidations"):
        require(type(policy[key]) is bool, key + " must be a boolean")
    require(type(policy["maxCommits"]) is int and policy["maxCommits"] > 0,
            "maxCommits must be a positive integer")


def load_policy(path):
    # Explicit JSON: Python stdlib only, cross-platform; never execute project code.
    value = load_json(path)
    validate_policy(value)
    return value


def enforce_policy(policy, spec):
    if policy is None:
        return
    validate_policy(policy)
    require(spec["remote"] in policy["allowedRemotes"], "policy blocks remote")
    require(any(fnmatch.fnmatchcase(spec["branch"], pattern)
                for pattern in policy["allowedBranches"]), "policy blocks branch")
    require(not spec["push"] or policy["allowPush"], "policy blocks push")
    require(not policy["requireValidations"] or bool(spec["validations"]),
            "policy requires at least one validation")
    require(len(spec["commits"]) <= policy["maxCommits"], "policy limits commit count")
    for item in spec["commits"]:
        for path in item["paths"]:
            require(not any(fnmatch.fnmatchcase(path, pattern)
                            for pattern in policy["blockedPaths"]),
                    "policy blocks path: " + path)
