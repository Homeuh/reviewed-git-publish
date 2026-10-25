"""Commit plumbing with a private index; no force, amend or reset."""
import os
from pathlib import Path
import subprocess
import tempfile
from contextlib import nullcontext

from .approval import verify_local_confirmation
from .errors import GuardError, require
from .git import git, text_git, decode_path, changed_paths, index_has_staged, remote_oid
from .hooks import prepare_hooks
from .verifier import ensure_baseline, ensure_worktree

def stage_tree(repo, paths, base_tree):
    """Stage exact approved working-tree paths in a disposable private index."""
    with tempfile.TemporaryDirectory(prefix="rpg-stage-") as temp:
        env = {"GIT_INDEX_FILE": str(Path(temp) / "index")}
        git(repo, "read-tree", base_tree, env_extra=env)
        input_bytes = b"\0".join(os.fsencode(":(literal)" + path) for path in paths) + b"\0"
        git(repo, "add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul",
            input_bytes=input_bytes, env_extra=env)
        changed = {decode_path(x) for x in git(
            repo, "diff", "--cached", "--name-only", "-z", "--no-renames",
            base_tree, env_extra=env).split(b"\0") if x}
        require(changed == set(paths), "staged manifest mismatch: " + repr(sorted(changed)))
        git(repo, "diff", "--cached", "--check", base_tree, env_extra=env)
        return text_git(repo, "write-tree", env_extra=env)


def staged_entries(repo):
    """Capture Git index object IDs without consulting changed working files."""
    entries = {}
    for record in git(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        meta, separator, path = record.partition(b"\t")
        require(bool(separator), "invalid staged Git index")
        fields = meta.split(b" ")
        require(len(fields) == 3 and fields[2] == b"0", "unmerged index")
        entries[decode_path(path)] = meta
    return entries


def staged_index_tree(repo, paths, base_tree, entries):
    """Construct each reviewed commit from the original staged blob objects."""
    with tempfile.TemporaryDirectory(prefix="rpg-staged-") as temp:
        env = {"GIT_INDEX_FILE": str(Path(temp) / "index")}
        git(repo, "read-tree", base_tree, env_extra=env)
        updates = []
        for path in paths:
            encoded = os.fsencode(path)
            meta = entries.get(path, b"0 " + b"0" * 40 + b" 0")
            updates.append(meta + b"\t" + encoded + b"\0")
        git(repo, "update-index", "-z", "--index-info",
            input_bytes=b"".join(updates), env_extra=env)
        changed = {decode_path(x) for x in git(
            repo, "diff", "--cached", "--name-only", "-z", "--no-renames",
            base_tree, env_extra=env).split(b"\0") if x}
        require(changed == set(paths), "staged manifest mismatch: " + repr(sorted(changed)))
        git(repo, "diff", "--cached", "--check", base_tree, env_extra=env)
        return text_git(repo, "write-tree", env_extra=env)



def apply_reviewed_hook_updates(repo, plan, preview):
    """After approval preserve safe formatter outputs for the next review."""
    updates = preview["updates"]
    committed = {path for item in plan["spec"]["commits"] for path in item["paths"]}
    require(set(updates).issubset(committed),
            "hook changed files outside approved commit paths: " +
            repr(sorted(set(updates) - committed)) +
            "; live checkout unchanged, review manually")
    for name, update in updates.items():
        require(update["kind"] in ("file", "missing"),
                "hook produced non-regular output: " + name)
        path = repo
        for component in name.split("/"):
            path = path / component
            require(not path.is_symlink(), "cannot sync hook output through symlink: " + name)
        require(path.parent.is_dir(), "hook preview target parent missing: " + name)
    if not updates:
        return
    ensure_baseline(repo, plan)
    for name, update in updates.items():
        target = repo / name
        if update["kind"] == "missing":
            if target.exists():
                target.unlink()
        else:
            target.write_bytes(update["data"])
            target.chmod(update["mode"])
    # Stage only the originally approved paths, never excluded paths.
    paths = sorted(committed)
    specs = b"\0".join(os.fsencode(":(literal)" + name) for name in paths) + b"\0"
    git(repo, "add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul",
        input_bytes=specs)

def execute(repo, plan, approval, *, run_push_hooks=True, run_commit_hooks=True):
    verify_local_confirmation(plan, approval)
    ensure_baseline(repo, plan)
    spec, snapshot = plan["spec"], plan["snapshot"]
    # Validate before any index, ref, or working-tree mutation. Commands are explicit argv,
    # and must be reviewed as part of the frozen plan.
    for argv in spec["validations"]:
        result = subprocess.run(argv, cwd=str(repo), check=False)
        require(result.returncode == 0, "validation failed: " + repr(argv))
        ensure_baseline(repo, plan)
    staged_mode = plan.get("stagingMode") == "pre-staged-only"
    index_entries = staged_entries(repo) if staged_mode else None
    base_tree = text_git(repo, "rev-parse", "HEAD^{tree}")
    planned = []
    # First prepare ALL candidate trees without modifying the live index/refs.
    # This supports multiple atomic commits from the fully staged file set.
    for item in spec["commits"]:
        tree = (staged_index_tree(repo, item["paths"], base_tree, index_entries)
                if staged_mode else stage_tree(repo, item["paths"], base_tree))
        planned.append((tree, item["message"], item["paths"]))
        base_tree = tree
        ensure_baseline(repo, plan)
    # In a temporary Git checkout, run a full per-commit before-commit hook
    # sequence; compare all results only after the successful round.
    hook_result = (prepare_hooks(repo, planned, snapshot["head"]) if run_commit_hooks
                   else {"hooks": [], "changed": False})
    ensure_baseline(repo, plan)
    if hook_result["changed"]:
        apply_reviewed_hook_updates(repo, plan, hook_result)
        require(False, "hook changed reviewed files/index/message; STOP, "
                "refreeze and obtain fresh approval; no automatic retry. "
                "Changes to approved paths were restaged where applicable. "
                "Details: " + repr(hook_result["deviations"]) +
                " proposed messages: " + repr(hook_result["messages"]))
    old = snapshot["head"]
    commits = []
    for tree, message, paths in planned:
        new = text_git(repo, "commit-tree", tree, "-p", old, "-F", "-",
                       input_bytes=(message + "\n").encode("utf-8"))
        require(text_git(repo, "show", "-s", "--format=%B", new) == message,
                "full commit message mismatch")
        actual = {decode_path(x) for x in git(
            repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z",
            "--no-renames", new).split(b"\0") if x}
        require(actual == set(paths), "committed paths mismatch")
        commits.append(new)
        old = new
    # One compare-and-swap ref transition for the entire prepared commit chain.
    # If preparation/hooks failed, HEAD and the live index are still untouched.
    ensure_baseline(repo, plan)
    git(repo, "update-ref", "refs/heads/" + spec["branch"], old, snapshot["head"])
    # Synchronize the actual index only after the approved HEAD has advanced.
    git(repo, "read-tree", old)
    require(text_git(repo, "rev-parse", "HEAD") == old, "HEAD update verification failed")
    ensure_worktree(repo, plan, [
        name for item in spec["commits"] for name in item["paths"]])
    require(set(changed_paths(repo)) == set(spec["excluded"]), "unexpected remaining changes")
    result = {"commits": commits, "branch": spec["branch"], "remote": spec["remote"],
              "pushed": False, "remaining": spec["excluded"],
              "hooksExecuted": hook_result["hooks"]}
    if spec["push"]:
        ensure_worktree(repo, plan, [name for item in spec["commits"] for name in item["paths"]])
        pushed_oid = text_git(repo, "rev-parse", "HEAD")
        # The ordinary local flow retains pre-push hooks. Only the isolated
        # publisher prototype opts out of unreviewed hook execution.
        require(len(snapshot["pushUrls"]) == 1, "ambiguous frozen push destination")
        hooks_dir = tempfile.TemporaryDirectory(prefix="rpg-publisher-no-hooks-") if not run_push_hooks else nullcontext(None)
        with hooks_dir as empty_hooks:
            command = ["git", "-C", str(repo)]
            if empty_hooks is not None:
                command += ["-c", "core.hooksPath=" + empty_hooks]
            command += ["push", snapshot["pushUrls"][0],
                        "HEAD:refs/heads/" + spec["branch"]]
            push = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  env={**os.environ, "GIT_TERMINAL_PROMPT": "0",
                                       "GIT_OPTIONAL_LOCKS": "0"})
        # Always query the real remote ref: a timeout/disconnect may mask success.
        # Query the same reviewed target, not a possibly changed remote name.
        actual_remote = remote_oid(repo, spec["remote"], spec["branch"],
                                   url=snapshot["pushUrls"][0])
        if actual_remote != pushed_oid:
            raise GuardError("push unconfirmed (exit=" + str(push.returncode) +
                             "); remote=" + repr(actual_remote) + "; local=" + pushed_oid +
                             "; do not retry automatically")
        result["pushed"] = True
        result["remoteOid"] = actual_remote
    return result

