#!/usr/bin/env python3
"""Install or update this portable Skill with atomic rename and retained backups.

Only the explicitly selected --target Skills directory may be modified.
No Git operations, package downloads or external Python libraries are used.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import zipfile


NAME = "reviewed-git-publish"
HERE = Path(__file__).resolve().parents[1]
REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "scripts/reviewed_git_publish.py",
    "scripts/rpg/__init__.py",
    "schemas/publish-spec.schema.json",
)


def require(ok, error):
    if not ok:
        raise ValueError(error)


def version(root):
    version_file = root / "scripts" / "rpg" / "__init__.py"
    require(version_file.is_file(), "Skill version file missing: " + str(root))
    found = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$',
                      version_file.read_text(encoding="utf-8"), re.M)
    require(found, "Skill version could not be read")
    return found.group(1)


def checked_source(path):
    require(path.is_dir() and not path.is_symlink(), "source must be an unpacked Skill directory")
    for filename in REQUIRED:
        require((path / filename).is_file(), "missing Skill file: " + filename)
    for item in path.rglob("*"):
        require(not item.is_symlink(), "Skill source contains unsupported symlink: " + str(item))
    require((path / "SKILL.md").read_text(encoding="utf-8").startswith(
        "---\nname: reviewed-git-publish\n"), "unexpected Skill identity")
    return path


@contextmanager
def source_directory(source):
    """Accept either a source Skill directory or the deterministic ZIP build."""
    path = Path(source).expanduser().resolve()
    if path.is_dir():
        yield checked_source(path)
        return
    require(path.is_file() and path.suffix.lower() == ".zip",
            "source must be a Skill directory or .zip package")
    with tempfile.TemporaryDirectory(prefix="rpg-unpack-") as workspace:
        unpack = Path(workspace)
        with zipfile.ZipFile(path) as package:
            for entry in package.infolist():
                name = PurePosixPath(entry.filename)
                require(not name.is_absolute() and ".." not in name.parts and
                        bool(name.parts) and name.parts[0] == NAME and
                        all(part not in ("", ".") for part in name.parts),
                        "unsafe archive entry: " + entry.filename)
                mode = (entry.external_attr >> 16) & 0o170000
                require(mode in (0, stat.S_IFDIR, stat.S_IFREG),
                        "archive contains unsafe file type: " + entry.filename)
                extracted = unpack.joinpath(*name.parts)
                require(extracted.is_relative_to(unpack), "archive escapes extraction directory")
                if entry.is_dir():
                    extracted.mkdir(parents=True, exist_ok=True)
                else:
                    require(entry.file_size <= 8 * 1024 * 1024,
                            "archive entry exceeds file limit")
                    extracted.parent.mkdir(parents=True, exist_ok=True)
                    require(not extracted.exists(), "duplicate archive entry: " + entry.filename)
                    extracted.write_bytes(package.read(entry))
        yield checked_source(unpack / NAME)


def status(source, target):
    dest = target / NAME
    require(not dest.is_symlink(), "installed Skill must not be a symlink")
    present = dest.is_dir()
    if dest.exists():
        require(present, "existing target is not a Skill directory")
        checked_source(dest)
    return {"skill": NAME, "sourceVersion": version(source),
            "installedVersion": version(dest) if present else None,
            "installed": present, "destination": str(dest)}


def install_or_update(action, source, target):
    info = status(source, target)
    dest = target / NAME
    require(not source == dest and not source.is_relative_to(dest) and
            not dest.is_relative_to(source),
            "source and destination may not overlap")
    if action == "install":
        require(not info["installed"], "Skill already installed; use update")
    else:
        require(info["installed"], "Skill not installed; use install")
        require(info["installedVersion"] != info["sourceVersion"],
                "same version already installed; refusing unnecessary overwrite")
    target.mkdir(parents=True, exist_ok=True)
    # Stage on same filesystem as destination; rename is atomic.
    stage = Path(tempfile.mkdtemp(prefix="." + NAME + ".stage-", dir=target))
    backup = None
    old_moved = False
    try:
        prepared = stage / NAME
        shutil.copytree(source, prepared, symlinks=False,
                        ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache",
                                                       ".mypy_cache", ".DS_Store",
                                                       "*.pyc", "*.pyo"))
        checked_source(prepared)
        if action == "update":
            backups = target.parent / ".skill-backups" / NAME
            backups.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = backups / (info["installedVersion"] + "-" + stamp)
            counter = 0
            while backup.exists():
                counter += 1
                backup = backups / (info["installedVersion"] + "-" + stamp + "-" + str(counter))
            os.replace(dest, backup)
            old_moved = True
        os.replace(prepared, dest)
    except Exception:
        if old_moved and backup is not None and backup.exists() and not dest.exists():
            os.replace(backup, dest)
        raise
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    info["action"] = action
    if backup is not None:
        info["backup"] = str(backup)
    info["installedVersion"] = version(dest)
    info["installed"] = True
    return info


def main():
    parser = argparse.ArgumentParser(description="Install, update or inspect the portable Reviewed Git Publish Skill")
    parser.add_argument("action", choices=("install", "update", "status"))
    parser.add_argument("--target", required=True,
                        help="the containing skills directory, such as PROJECT/.agents/skills")
    parser.add_argument("--source", default=str(HERE),
                        help="unpacked Skill directory or deterministic ZIP (default: this Skill)")
    args = parser.parse_args()
    raw_target = Path(args.target).expanduser()
    require(not raw_target.is_symlink(), "target Skills directory may not be a symlink")
    target = raw_target.resolve()
    with source_directory(args.source) as source:
        result = status(source, target) if args.action == "status" else (
            install_or_update(args.action, source, target))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as error:
        print("SKILL MANAGEMENT BLOCKED: " + str(error), file=sys.stderr)
        sys.exit(2)
