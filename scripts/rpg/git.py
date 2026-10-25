"""Git-only inspection and remote observations."""
import os
from pathlib import Path
import re
import subprocess

from .errors import GuardError, require

HEX_RE = re.compile(r"^[0-9a-f]{40,64}$")

def git(repo, *args, input_bytes=None, env_extra=None, ok=(0,)):
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0" if env_extra is None else "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(["git", "-C", str(repo), *args], input=input_bytes,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    if result.returncode not in ok:
        raise GuardError("git " + " ".join(args[:3]) + ": " + result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def decode_path(data):
    return data.decode("utf-8", "surrogateescape")


def text_git(repo, *args, **kwargs):
    return git(repo, *args, **kwargs).decode("utf-8", "replace").strip()


def changed_paths(repo):
    raw = git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignore-submodules=none")
    entries = raw.split(b"\0")
    result = set()
    i = 0
    while i < len(entries):
        record = entries[i]
        i += 1
        if not record:
            continue
        require(len(record) >= 4 and record[2:3] == b" ", "invalid porcelain record")
        result.add(decode_path(record[3:]))
        if b"R" in record[:2] or b"C" in record[:2]:
            require(i < len(entries) and bool(entries[i]), "invalid rename/copy record")
            result.add(decode_path(entries[i]))
            i += 1
    return sorted(result)


def remote_oid(repo, remote, branch, url=None):
    """Read a remote ref, optionally pinning the exact frozen push URL."""
    if url is None:
        urls = push_urls(repo, remote)
        require(len(urls) == 1 and bool(urls[0]), "exactly one push URL is required")
        url = urls[0]
    require(isinstance(url, str) and bool(url), "invalid pinned push URL")
    out = git(repo, "ls-remote", "--heads", url, "refs/heads/" + branch)
    rows = out.decode("ascii", "replace").strip().splitlines()
    require(len(rows) <= 1, "ambiguous remote ref")
    if not rows:
        return None
    oid, sep, ref = rows[0].partition("\t")
    require(sep == "\t" and HEX_RE.fullmatch(oid) and ref == "refs/heads/" + branch, "unexpected remote response")
    return oid


def remote_url(repo, remote):
    return text_git(repo, "remote", "get-url", remote)


def push_urls(repo, remote):
    return git(repo, "remote", "get-url", "--push", "--all", remote).decode("utf-8", "replace").splitlines()


def index_has_staged(repo):
    return bool(git(repo, "diff", "--cached", "--name-only", "-z", "--no-renames"))


def assert_staged_only(repo):
    """Allow excluded working-tree changes, never partially staged commit paths.

    The complete staged index must become one commit; every other changed path
    must be explicitly excluded in the reviewed plan. No index mutation occurs.
    """
    staged = sorted(decode_path(x) for x in
                    git(repo, "diff", "--cached", "--name-only", "-z", "--no-renames").split(b"\0") if x)
    require(bool(staged), "staged-only mode requires staged changes")
    unstaged = {decode_path(x) for x in
                git(repo, "diff", "--name-only", "-z", "--no-renames").split(b"\0") if x}
    require(not unstaged.intersection(staged),
            "staged-only mode refuses partial staging or unstaged changes to committed paths")
    require(set(staged).issubset(changed_paths(repo)),
            "staged-only manifest differs from working-tree status")
    return staged


def assert_git_ready(repo, allow_staged=False):
    require((repo / ".git").exists() or text_git(repo, "rev-parse", "--is-inside-work-tree") == "true",
            "not a worktree")
    if not allow_staged:
        require(not index_has_staged(repo), "existing staged changes require pre-staged-only mode")
    require(not git(repo, "ls-files", "-u", "-z"), "unmerged index entries")
    for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD"):
        path = text_git(repo, "rev-parse", "--git-path", marker)
        if not Path(path).is_absolute():
            path = str(repo / path)
        require(not Path(path).exists(), "operation in progress: " + marker)
    require(not any(line.startswith(b"160000 ") for line in git(repo, "ls-files", "--stage", "-z").split(b"\0")),
            "submodule gitlinks are unsupported")

