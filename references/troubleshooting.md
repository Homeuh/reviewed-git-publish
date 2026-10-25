# Troubleshooting (local developer workflow)

Always keep the frozen plan outside the target checkout. Never use
`git reset`, `--force`, or unreviewed `git add` to work around failures.

| Symptom | Explanation | Next action |
|---|---|---|
| `WAITING_FOR_USER` | Changes reviewed, not yet approved | Review the exact file list, exclusions and message, then approve **the real 64-character plan digest** |
| `approved snapshot drift` | HEAD, index, files, Hook state, remote URL or remote OID changed | Inspect actual changes, generate a new plan outside the repo, approve the new digest |
| `existing staged changes` | Default clean-index mode was selected despite a prepared index | The Agent should inspect/freeze with `--staging-mode pre-staged-only`; don't unstage user files |
| Partial/hunk staging rejected | Same file has both staged and unstaged edits | Review the intended content first; don't automatically discard hunks |
| Hook fails | Hook returned non-zero; no commit must be created in that attempt | Read the Hook error, fix its underlying cause, then refreeze/reapprove |
| Hook changed approved file or message | A full Hook preflight completed with differences | Review the restaged formatter result and proposed message, freeze fresh, explicitly reapprove; do **not** retry with old digest |
| Hook changed an unapproved path | It is not safe to copy arbitrary output to the real checkout | Manually inspect the Hook script and proposal, then request a new plan |
| Hook tool missing in temporary checkout | Hook requires ignored dependencies or absolute checkout setup not present in the isolated preflight | Run/resolve project setup manually; current compatibility preflight is not a faithful full checkout of ignored dependencies |
| `push unconfirmed` | Remote does not match intended local commit OID, perhaps rejected by `pre-push` or server | Run read-only `reconcile`; inspect local and remote refs, obtain a new approval before any fresh attempt |
| `same version already installed` | Versioned updater refuses to overwrite existing installation with equal version | Install a newer release instead; don't delete the old Skill to bypass checks |
| Skill update failed | Installer refused unsafe content or interrupted during copy | Installed directory is preserved until the final rename; if updating, previous version is backed up under `.agents/.skill-backups/` |

## How to inspect without mutating Git

From inside the unpacked Skill directory:

```bash
python3 -B scripts/reviewed_git_publish.py --help
python3 -B scripts/manage_skill.py status --target /path/to/project/.agents/skills
```

With an existing frozen external plan:

```bash
python3 -B scripts/reviewed_git_publish.py verify --repo /path/to/git/repo --plan /outside/plan.json
python3 -B scripts/reviewed_git_publish.py reconcile --repo /path/to/git/repo --plan /outside/plan.json
```

`reconcile` reports state only; it does not resume or approve execution.
Local SHA-256 confirmation is a developer convenience, not proof of an
independently authenticated human.
