"""Verify approved snapshots, in-flight invariants and failure state."""
from .errors import GuardError, require
from .git import (git, text_git, changed_paths, remote_oid, remote_url,
                  push_urls, index_has_staged)
from .snapshot import capture, file_state
from .plan import validate_spec
from .policy import enforce_policy

def ensure_baseline(repo, plan):
    spec, snapshot = plan["spec"], plan["snapshot"]
    validate_spec(spec, snapshot["paths"])
    enforce_policy(plan.get("policy"), spec)
    require(capture(repo, spec["remote"], spec["branch"],
                    staging_mode=plan.get("stagingMode", "clean")) == snapshot,
            "approved snapshot drift: refresh plan and obtain new approval")


def ensure_worktree(repo, plan, completed):
    snapshot, spec = plan["snapshot"], plan["spec"]
    require(text_git(repo, "symbolic-ref", "--short", "HEAD") == snapshot["branch"], "branch drift")
    require(remote_url(repo, spec["remote"]) == snapshot["remoteUrl"], "remote URL drift")
    require(push_urls(repo, spec["remote"]) == snapshot["pushUrls"], "push URL drift")
    require(remote_oid(repo, spec["remote"], spec["branch"]) == snapshot["remoteOid"], "remote ref drift")
    remain = set(snapshot["paths"]) - set(completed)
    require(set(changed_paths(repo)) == remain, "worktree changed path drift")
    for name, expected in snapshot["files"].items():
        require(file_state(repo, name) == expected, "changed content/mode drift: " + name)
    require(not index_has_staged(repo), "unexpected staged content")
    require(not git(repo, "ls-files", "-u", "-z"), "unmerged index")


def failure_diagnostics(repo, plan):
    """Best-effort, read-only observation after partial/failed execution."""
    output = {}
    observations = {
        "head": ("rev-parse", "HEAD"),
        "branch": ("symbolic-ref", "--short", "HEAD"),
    }
    for key, argv in observations.items():
        try:
            output[key] = text_git(repo, *argv)
        except (GuardError, OSError):
            output[key] = "unknown"
    try:
        output["staged"] = index_has_staged(repo)
        output["changedPaths"] = changed_paths(repo)
        output["newCommits"] = git(repo, "rev-list", "--reverse",
                                   plan["snapshot"]["head"] + "..HEAD").decode("ascii").splitlines()
    except (GuardError, OSError) as error:
        output["localInspectionError"] = str(error)
    try:
        output["remoteOid"] = remote_oid(repo, plan["spec"]["remote"], plan["spec"]["branch"])
    except (GuardError, OSError) as error:
        output["remoteInspectionError"] = str(error)
    return output


def reconcile(repo, plan):
    """Read-only after-failure observation, NEVER a resume/retry authorization."""
    state = failure_diagnostics(repo, plan)
    original = plan["snapshot"]["head"]
    head = state.get("head", "unknown")
    remote = state.get("remoteOid")
    if "remoteInspectionError" in state or head == "unknown":
        verdict = "unknown"
    elif head == original and remote == plan["snapshot"]["remoteOid"]:
        verdict = "no_observed_publish"
    elif head == original:
        verdict = "remote_changed"
    elif remote == head:
        verdict = "remote_matches_local_head"
    elif remote == plan["snapshot"]["remoteOid"]:
        verdict = "local_commits_not_at_remote"
    else:
        verdict = "remote_diverged_or_unknown"
    state.update({
        "classification": verdict,
        "baselineHead": original,
        "planDigest": plan["planDigest"],
        "action": "STOP: review HEAD, remote OID, index and remaining files; "
                  "never automatically retry, reset, amend or force push. "
                  "Any new publication needs a fresh plan and approval.",
    })
    return state
