"""Worktree and index snapshots, drift verification."""
import hashlib
import os
from pathlib import Path
import stat

from .errors import GuardError, require
from .git import (git, text_git, changed_paths, remote_url, push_urls,
                  remote_oid, index_has_staged, assert_git_ready, assert_staged_only)
from .hooks import hook_fingerprint

def checked_path(path):
    require(isinstance(path, str) and bool(path) and "\0" not in path, "invalid path")
    require(not any(0xD800 <= ord(char) <= 0xDFFF for char in path),
            "non-UTF-8 file paths are unsupported")
    require(not path.startswith("/") and "\\" not in path and not path.startswith("-"), "unsafe path: " + path)
    require(all(part not in ("", ".", "..", ".git") for part in path.split("/")), "unsafe path: " + path)
    return path


def require_outside_repo(file_path, repo, label):
    target = Path(file_path).resolve()
    require(target != repo and repo not in target.parents, label + " must be outside repo")


def file_state(root, name):
    path = root / name
    try:
        info = path.lstat()
    except FileNotFoundError:
        return {"kind": "missing"}
    if stat.S_ISLNK(info.st_mode):
        content = os.fsencode(os.readlink(path))
        kind = "symlink"
    elif stat.S_ISREG(info.st_mode):
        with open(path, "rb") as stream:
            hash_state = hashlib.sha256()
            while True:
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                hash_state.update(chunk)
        return {"kind": "file", "sha256": hash_state.hexdigest(),
                "size": info.st_size, "executable": bool(info.st_mode & 0o111)}
    else:
        raise GuardError("unsupported changed file type: " + name)
    return {"kind": kind, "sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}


def capture(repo, remote, branch, check_ready=True, staging_mode="clean"):
    require(staging_mode in ("clean", "pre-staged-only"), "unsupported staging mode")
    staged = None
    if check_ready:
        assert_git_ready(repo, allow_staged=staging_mode == "pre-staged-only")
        if staging_mode == "pre-staged-only":
            staged = assert_staged_only(repo)
    head = text_git(repo, "rev-parse", "HEAD")
    current_branch = text_git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    require(current_branch == branch, "target branch must match checked-out branch")
    names = changed_paths(repo)
    for name in names:
        checked_path(name)
    result = {
        "head": head,
        "branch": current_branch,
        "remote": remote,
        "remoteUrl": remote_url(repo, remote),
        "pushUrls": push_urls(repo, remote),
        "remoteOid": remote_oid(repo, remote, branch),
        "indexSha256": hashlib.sha256(git(repo, "ls-files", "--stage", "-z")).hexdigest(),
        "hookState": hook_fingerprint(repo),
        "paths": names,
        "files": {name: file_state(repo, name) for name in names},
    }
    if staging_mode == "pre-staged-only":
        # Index + all changed paths are fingerprinted even when exclusions exist.
        result["stagedPaths"] = staged if staged is not None else assert_staged_only(repo)
    return result

