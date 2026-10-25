"""Reviewable exact manifests, plan digests and schema invariants."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from .errors import require
from .git import git
from .jsonio import load_json
from .snapshot import capture, checked_path
from .policy import enforce_policy, validate_policy

VERSION = 1
COMMIT_RE = re.compile(r"^(feat|fix|docs|test|refactor|perf|build|ci|chore|revert)(\([a-zA-Z0-9_.-]+\))?(!)?: .{1,100}$")
SENSITIVE_RE = re.compile(r"(^|/)(\.env($|\.)|id_rsa|id_ed25519|credentials?(\.|$)|.*\.(pem|p12|pfx|key)$)", re.I)

def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(data):
    return hashlib.sha256(canonical(data)).hexdigest()


def validate_spec(spec, names):
    require(isinstance(spec, dict), "spec must be JSON object")
    require(set(spec) == {"remote", "branch", "commits", "excluded", "validations", "push"},
            "spec fields must be remote, branch, commits, excluded, validations, push")
    remote, branch = spec["remote"], spec["branch"]
    require(isinstance(remote, str) and re.fullmatch(r"[A-Za-z0-9_.-]+", remote), "invalid remote")
    require(isinstance(branch, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", branch)
            and ".." not in branch and "@{" not in branch and not branch.endswith(("/", ".", ".lock"))
            and "//" not in branch, "invalid branch")
    require(isinstance(spec["push"], bool), "push must be boolean")
    commits = spec["commits"]
    excluded = spec["excluded"]
    validations = spec["validations"]
    require(isinstance(commits, list) and bool(commits), "at least one commit required")
    require(isinstance(excluded, list), "excluded must be list")
    require(isinstance(validations, list), "validations must be list")
    seen = set()
    for item in commits:
        require(isinstance(item, dict) and set(item) == {"message", "chinese", "paths"}, "invalid commit fields")
        message = item["message"]
        require(isinstance(message, str) and bool(message) and len(message) <= 8192 and
                "\0" not in message and "\r" not in message and
                COMMIT_RE.fullmatch(message.split("\n")[0]) is not None and
                (("\n" not in message) or
                 (message.split("\n", 1)[1].startswith("\n") and
                  bool(message.split("\n", 2)[2].strip()) and
                  message == message.rstrip("\n"))),
                "invalid Conventional Commit message/body")
        require(isinstance(item["chinese"], str) and bool(item["chinese"].strip()), "Chinese review required")
        require(isinstance(item["paths"], list) and bool(item["paths"]), "empty manifest")
        for path in item["paths"]:
            checked_path(path)
            require(path not in seen, "duplicate commit path: " + path)
            require(not SENSITIVE_RE.search(path), "sensitive path blocked: " + path)
            seen.add(path)
    for path in excluded:
        checked_path(path)
        require(path not in seen, "excluded path is also committed: " + path)
        require(path not in excluded[:excluded.index(path)], "duplicate exclusion: " + path)
        seen.add(path)
    require(seen == set(names), "manifest/exclusions mismatch: missing=" +
            repr(sorted(set(names)-seen)) + " extra=" + repr(sorted(seen-set(names))))
    for argv in validations:
        require(isinstance(argv, list) and bool(argv) and all(
            isinstance(arg, str) and bool(arg) for arg in argv), "validations must be argv arrays")
    return True


def freeze(repo, spec, policy=None, staging_mode="clean"):
    require(isinstance(spec, dict), "spec required")
    require("remote" in spec and "branch" in spec, "missing remote/branch")
    require(staging_mode in ("clean", "pre-staged-only"), "unsupported staging mode")
    snapshot = capture(repo, spec["remote"], spec["branch"], staging_mode=staging_mode)
    validate_spec(spec, snapshot["paths"])
    enforce_policy(policy, spec)
    require(snapshot["paths"], "no changes to publish")
    if staging_mode == "pre-staged-only":
        require({name for item in spec["commits"] for name in item["paths"]} ==
                set(snapshot["stagedPaths"]),
                "staged-only commit paths must exactly match the staged index; "
                "all other changes must be explicitly excluded")
    # A different target OID must be a known local ancestor, not merely a syntactically valid OID.
    if snapshot["remoteOid"] and snapshot["remoteOid"] != snapshot["head"]:
        result = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor",
                                 snapshot["remoteOid"], snapshot["head"]], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        require(result.returncode == 0, "remote branch is not a known ancestor of HEAD")
    plan = {"schemaVersion": VERSION, "spec": spec, "snapshot": snapshot,
            "approvalMode": "local-untrusted"}
    if policy is not None:
        plan["policy"] = policy
    if staging_mode == "pre-staged-only":
        plan["stagingMode"] = "pre-staged-only"
    plan["planDigest"] = digest(plan)
    return plan


def load_plan(path):
    plan = load_json(path)
    expected = {"schemaVersion", "spec", "snapshot", "approvalMode", "planDigest"}
    optional = {"policy", "stagingMode"}
    require(isinstance(plan, dict) and expected.issubset(plan) and
            set(plan).issubset(expected | optional), "invalid plan fields")
    require(plan["schemaVersion"] == VERSION and plan["approvalMode"] == "local-untrusted", "unsupported plan")
    saved = dict(plan)
    saved.pop("planDigest")
    require(digest(saved) == plan["planDigest"], "plan digest corrupted")
    require(re.fullmatch(r"[0-9a-f]{64}", plan["planDigest"]) is not None, "invalid digest")
    require(plan.get("stagingMode", "clean") in ("clean", "pre-staged-only"),
            "unsupported staging mode")
    if plan.get("stagingMode") == "pre-staged-only":
        snapshot = plan["snapshot"]
        require(isinstance(snapshot, dict) and isinstance(snapshot.get("stagedPaths"), list),
                "missing frozen staged paths")
        require({name for item in plan["spec"]["commits"] for name in item["paths"]} ==
                set(snapshot["stagedPaths"]),
                "staged-only plan does not match frozen staged index")
    if "policy" in plan:
        validate_policy(plan["policy"])
        enforce_policy(plan["policy"], plan["spec"])
    return plan

