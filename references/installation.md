# Installation and updates

**Skill runtime:** Python 3.9+ and Git with `--pathspec-from-file`.
No non-standard Python packages required.

## Recommended: Skills CLI

With Node.js 22.20+ on your machine, open the target project and run:

```bash
npx skills add Homeuh/reviewed-git-publish
```

Choose your Agent interactively. For a particular Agent or global scope:

```bash
npx skills add Homeuh/reviewed-git-publish -a codex
npx skills add Homeuh/reviewed-git-publish -a antigravity
npx skills add Homeuh/reviewed-git-publish -g
```

Discovery-only check (no installation):

```bash
npx skills add Homeuh/reviewed-git-publish --list
```

The CLI downloads from the GitHub repository branch, discovers the
root `SKILL.md`, and installs the accompanying scripts and references.
Default scope is the current project. Use `npx skills check` and
`npx skills update` for subsequent CLI-managed updates. This method
does not use the GitHub Release ZIP and can differ from a pinned release.

## Agent-assisted installation

Give a coding Agent with terminal access a prompt such as:

> Install the `reviewed-git-publish` Skill from
> https://github.com/Homeuh/reviewed-git-publish into the current project.
> Read `SKILL.md` and inspect executable code before installing. Prefer
> `npx skills add Homeuh/reviewed-git-publish --skill reviewed-git-publish`;
> if Node.js is unavailable, use the official ZIP and Python installer.
> Ask before overwriting an existing Skill, and verify installed files.
> Do not run the publishing executor, commit, or push during installation.

Do not interpret the prompt as automatic approval to execute arbitrary
commands. The Agent must have suitable tools, permissions, and user approval
for installation.

## Alternative: verified Release ZIP

Unpack the Release ZIP into `reviewed-git-publish/`. From inside that
folder, install into the directory where your Agent discovers Skills:

```bash
python3 -B scripts/manage_skill.py install \
  --target /path/to/project/.agents/skills
python3 -B scripts/manage_skill.py status \
  --target /path/to/project/.agents/skills
```

For a **newer** verified ZIP:

```bash
python3 -B scripts/manage_skill.py update \
  --target /path/to/project/.agents/skills \
  --source /path/to/new-reviewed-git-publish.zip
```

Omit `--source` to use the unpacked Skill containing the installer.
The Python installer makes no network requests, Git staging, commits or pushes.
It rejects unsafe ZIP content, source symlinks, overlapping source/target,
and same-version overwrite. An existing installed version is moved under
`.agents/.skill-backups/reviewed-git-publish/` before replacement; the
new copy is staged on the same filesystem and renamed into place.

The packaging builder and release tests remain development-only, **not
shipped in the Skill ZIP**. A maintainer should build a deterministic
archive, verify its SHA-256, and test it in a disposable installation
target. Consult [troubleshooting.md](troubleshooting.md) for errors.
