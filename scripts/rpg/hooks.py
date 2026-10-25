"""Prepared commit hooks in a disposable Git checkout.

This is a compatibility preview for the standard pre-commit, prepare-commit-msg
and commit-msg phase, not a security sandbox. Project hooks remain trusted.
The caller passes fully prepared, reviewed trees and exact messages.
"""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import stat

from .errors import GuardError, require
from .git import git, text_git, decode_path


HOOKS = ("pre-commit", "prepare-commit-msg", "commit-msg")


def hook_directory(repo):
    configured = text_git(repo, "config", "--path", "--get", "core.hooksPath", ok=(0, 1))
    if configured:
        raw = Path(configured).expanduser()
        return (raw if raw.is_absolute() else repo / raw).resolve()
    raw = Path(text_git(repo, "rev-parse", "--git-path", "hooks"))
    return (raw if raw.is_absolute() else repo / raw).resolve()


def hook_fingerprint(repo):
    import hashlib
    directory = hook_directory(repo)
    states = {}
    for hook in HOOKS:
        file = directory / hook
        if file.is_file() and os.access(file, os.X_OK):
            contents = file.read_bytes()
            states[hook] = [hashlib.sha256(contents).hexdigest(),
                            file.stat().st_mode & 0o777]
        else:
            states[hook] = None
    return {"hooksDir": str(directory), "hooks": states}


def active_hooks(repo):
    directory = hook_directory(repo)
    return {h: directory / h for h in HOOKS
            if (directory / h).is_file() and os.access(directory / h, os.X_OK)}


def worktree_state(path):
    if path.is_symlink():
        return ("symlink", os.readlink(path))
    if not path.exists():
        return ("missing",)
    info = path.lstat()
    if stat.S_ISREG(info.st_mode):
        return ("file", hashlib.sha256(path.read_bytes()).hexdigest(),
                bool(info.st_mode & 0o111))
    return ("unsupported",)


def overlay_future_paths(repo, scratch, future_paths):
    """Keep not-yet-committed reviewed files at their real workspace versions.

    An actual developer's worktree contains *all* edits even when only
    commit 1 is staged; without this overlay, repo-wide format hooks would
    repeatedly 'modify' files intended for later commits.
    """
    for name in sorted(future_paths):
        original, target = repo / name, scratch / name
        if original.is_symlink():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink() or target.is_file():
                target.unlink()
            target.symlink_to(os.readlink(original))
        elif original.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.is_symlink():
                target.unlink()
            shutil.copy2(original, target)
        elif not original.exists():
            if target.is_symlink() or target.is_file():
                target.unlink()


def prepare_hooks(repo, commits, base_head):
    """Run each applicable before-commit hook once in a temporary checkout.

    commits: sequence of (tree OID, approved full message, exact paths).
    Any change to the candidate index, tracked or untracked working files, or
    message is collected and rejected AFTER the entire successful hook round.
    Hook failures stop immediately. No hook is invoked in the real checkout.
    """
    available = active_hooks(repo)
    if not available:
        return {"hooks": [], "changed": False}
    deviations = []
    updates = {}
    messages = []
    all_paths = {name for _, _, paths in commits for name in paths}
    completed_paths = set()
    with tempfile.TemporaryDirectory(prefix="rpg-hook-preview-") as tmp:
        scratch = Path(tmp) / "checkout"
        # Local object alternates are read-only from this clone; object writes
        # and HEAD updates occur in scratch, not in the real repository.
        git(repo, "clone", "--quiet", "--shared", "--no-checkout", "--",
            str(repo), str(scratch))
        git(scratch, "checkout", "--quiet", "--detach", base_head)
        hooks_dir = scratch / ".git" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        configured_dir = text_git(repo, "config", "--path", "--get",
                                  "core.hooksPath", ok=(0, 1))
        if not configured_dir:
            for hook, path in available.items():
                shutil.copy2(path, hooks_dir / hook)
        # A configured Husky/Lefthook path may depend on sibling helpers.
        # Execute the original absolute hook file with the scratch cwd.
        # Keep effective local filters for checkout/working-tree consistency.
        # Do not copy credentials or unrelated local repository config.
        pairs = git(repo, "config", "--null", "--get-regexp", r"^filter\.", ok=(0, 1))
        for record in pairs.split(b"\0"):
            if not record:
                continue
            key, sep, value = record.partition(b"\n")
            require(bool(sep), "invalid Git filter config")
            git(scratch, "config", key.decode("utf-8"), value.decode("utf-8"))
        git(scratch, "config", "user.name",
            text_git(repo, "config", "--get", "user.name", ok=(0, 1)) or "Publisher")
        git(scratch, "config", "user.email",
            text_git(repo, "config", "--get", "user.email", ok=(0, 1)) or "publisher@invalid.example")
        head = base_head
        for number, (tree, message, paths) in enumerate(commits, 1):
            # Set both index and checked-out files to the exact reviewed tree.
            git(scratch, "read-tree", "--reset", "-u", tree)
            overlay_future_paths(repo, scratch, all_paths - completed_paths - set(paths))
            def names(*args):
                return {decode_path(x) for x in git(scratch, *args).split(b"\0") if x}
            watched = {name: worktree_state(scratch / name) for name in all_paths}
            before_dirty = names("diff", "--name-only", "-z")
            before_untracked = names("ls-files", "--others", "--exclude-standard", "-z")
            message_file = scratch / ".git" / "RPG_COMMIT_EDITMSG"
            message_file.write_text(message + "\n", encoding="utf-8")
            env = os.environ.copy()
            env.pop("GIT_INDEX_FILE", None)
            env.pop("GIT_WORK_TREE", None)
            env.pop("GIT_DIR", None)
            env["GIT_TERMINAL_PROMPT"] = "0"
            env["GIT_EDITOR"] = ":"
            for hook in HOOKS:
                if hook not in available:
                    continue
                args = [str(available[hook]) if configured_dir else
                        str(hooks_dir / hook)]
                if hook == "prepare-commit-msg":
                    args.extend((str(message_file), "message"))
                elif hook == "commit-msg":
                    args.append(str(message_file))
                result = subprocess.run(args, cwd=str(scratch), env=env,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                require(result.returncode == 0,
                        "hook failed (commit " + str(number) + ", " + hook + "): " +
                        result.stderr.decode("utf-8", "replace")[-2000:])
            actual_tree = text_git(scratch, "write-tree")
            staged_changed = names("diff", "--cached", "--name-only", "-z", tree)
            after_dirty = names("diff", "--name-only", "-z")
            after_untracked = names("ls-files", "--others", "--exclude-standard", "-z")
            changed_paths = (staged_changed | (after_dirty - before_dirty) |
                             (after_untracked - before_untracked) |
                             {name for name, expected in watched.items()
                              if worktree_state(scratch / name) != expected})
            actual_message = message_file.read_text(encoding="utf-8").rstrip("\n")
            if actual_tree != tree or changed_paths or actual_message != message:
                deviations.append({"commit": number, "paths": sorted(changed_paths),
                                   "treeChanged": actual_tree != tree,
                                   "messageChanged": actual_message != message})
                if actual_message != message:
                    messages.append({"commit": number, "newMessage": actual_message})
                for name in sorted(changed_paths):
                    file = scratch / name
                    if file.is_symlink():
                        updates[name] = {"kind": "symlink"}
                    elif file.is_file():
                        require(file.stat().st_size <= 8 * 1024 * 1024,
                                "hook changed oversized file: " + name)
                        updates[name] = {"kind": "file", "data": file.read_bytes(),
                                         "mode": file.stat().st_mode & 0o777}
                    elif not file.exists():
                        updates[name] = {"kind": "missing"}
                    else:
                        updates[name] = {"kind": "unsupported"}
            # Advance only the SCRATCH history, so the following commit's Hook
            # sees the correct parent and stage-specific index content.
            new = text_git(scratch, "commit-tree", tree, "-p", head, "-F", "-",
                           input_bytes=(message + "\n").encode("utf-8"))
            git(scratch, "update-ref", "HEAD", new, head)
            head = new
            completed_paths.update(paths)
        return {"hooks": sorted(available), "changed": bool(deviations),
                "deviations": deviations, "updates": updates,
                "messages": messages}
