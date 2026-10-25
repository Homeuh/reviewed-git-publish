# Installation and updates

**Requirements:** Python 3.9+ and Git with `--pathspec-from-file`.

Unpack the official ZIP into a `reviewed-git-publish/` folder. From inside
that folder, install to the exact directory where your Agent discovers
Skills (for example the target repository's `.agents/skills`):

```bash
python3 -B scripts/manage_skill.py install \
  --target /path/to/project/.agents/skills
python3 -B scripts/manage_skill.py status \
  --target /path/to/project/.agents/skills
```

To update from a **newer** installed release or a verified downloaded ZIP:

```bash
python3 -B scripts/manage_skill.py update \
  --target /path/to/project/.agents/skills \
  --source /path/to/new-reviewed-git-publish.zip
```

Omit `--source` to use the unpacked Skill containing the installer.
The installer makes no network requests, Git staging, commits or pushes.
It rejects unsafe ZIP content, source symlinks, overlap with the
destination and same-version overwrite. An existing installed version
is moved into `.agents/.skill-backups/reviewed-git-publish/` before
replacement; the new copy is staged on the same filesystem and renamed
into place. Backups remain available if a previous version is needed.

The packaging builder and release tests are developer tools, **not shipped
in the Skill ZIP**. A developer should generate a deterministic archive,
verify its SHA-256 and test installing it into a disposable target before
distribution. Consult [troubleshooting.md](troubleshooting.md) for errors.
