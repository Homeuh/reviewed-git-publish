# Reviewed workflow and executable CLI

## 1. Inspect Git without changing the repository

Use Python 3.9+ and Git with `--pathspec-from-file` support. The CLI lives at
`scripts/reviewed_git_publish.py`, and commands accept `--repo` pointing to
the exact Git worktree root.

```bash
python3 -B scripts/reviewed_git_publish.py inspect \
  --repo /path/to/repo --branch main --remote origin
```

The Agent should already have reviewed repository instructions, staged and
unstaged diffs, untracked files, relevant ignored files, configured remotes,
branch/HEAD, recent commit conventions, binary files and unresolved operations.
Identify secrets, local environment files, generated output and unrelated
changes. No staging or remote mutation is authorized at this step.

When a nonempty index is already staged, choose the corresponding inspection
and freeze mode automatically:

```bash
python3 -B scripts/reviewed_git_publish.py inspect \
  --repo /path/to/repo --branch main --remote origin \
  --staging-mode pre-staged-only
```

Partial staging on a committed path is unsupported. Never silently reset or
unstage a developer's files.

## 2. Create a complete external spec

Prepare JSON following
[publish-spec.schema.json](../schemas/publish-spec.schema.json).
Every changed path must appear exactly once: either in a commit's `paths`
or in `excluded`. Paths are exact filenames, not directories, ranges or
globs. Different commits can use different sets of complete files.

Illustrative specification (adapt to the actual observed repository):

```json
{
  "remote": "origin",
  "branch": "main",
  "push": true,
  "commits": [
    {
      "message": "feat(web): improve navigation\n\nKeep route behavior consistent across screens.",
      "chinese": "改善导航逻辑，并保持现有路由行为",
      "paths": ["src/navigation.ts"]
    },
    {
      "message": "fix(api): handle missing session\n\nAvoid retrying requests with an expired session.",
      "chinese": "修复会话缺失时的请求处理",
      "paths": ["src/api.ts"]
    }
  ],
  "excluded": [".env.local"],
  "validations": [["python3", "-B", "-m", "compileall", "-q", "src"]]
}
```

Validation commands are **reviewed literal argv arrays**, not shell strings.
They may execute arbitrary project code, so inspect them. All spec/plan paths
must remain **outside** the target Git checkout to avoid snapshot drift.

## 3. Freeze, present and wait for approval

```bash
python3 -B scripts/reviewed_git_publish.py freeze \
  --repo /path/to/repo \
  --spec /outside/review-spec.json \
  --output /outside/review-plan.json
```

Add `--staging-mode pre-staged-only` if the Git index is already prepared.
Add `--policy /path/to/policy.json` only for an explicit reviewed policy
(see [safety.md](safety.md)). The plan is immutable and digest-bound.
Freeze never silently overwrites an existing output plan.

Show a concise bilingual summary including every exact committed/excluded
path, order, full English message (including Body), Chinese explanation,
validations, target branch, push decision and relevant risks. Show the
**complete real 64-character** `planDigest` and `WAITING_FOR_USER`.
The user may request revisions, in which case freeze a new plan; do not
recycle approval.

## 4. Verify and execute only the user's exact approved plan

```bash
python3 -B scripts/reviewed_git_publish.py verify \
  --repo /path/to/repo --plan /outside/review-plan.json

python3 -B scripts/reviewed_git_publish.py execute \
  --repo /path/to/repo --plan /outside/review-plan.json \
  --approval "COMMIT PLAN APPROVED <actual-plan-digest>"
```

Only accept that confirmation when explicitly supplied by the user. The CLI
checks its exact match; no standalone `APPROVED`, inferred intent or Agent
assertion is sufficient. Executing validates the frozen snapshot, performs
approved validations, constructs exact commit trees, checks the entire
successful before-commit Hook round, then creates the ordered chain and
advances the local branch in one checked ref update. The real index is
synchronized afterward. The normal push, if approved, targets the frozen
single effective push URL with `HEAD:refs/heads/<branch>` and checks the
resulting remote OID. See [hooks.md](hooks.md) for Hook changes and reapproval.

## 5. Diagnose failure without automatically retrying

```bash
python3 -B scripts/reviewed_git_publish.py reconcile \
  --repo /path/to/repo --plan /outside/review-plan.json
```

This **read-only** command reports observed HEAD, changes, local commits and
remote OID. Classifications include `no_observed_publish`,
`local_commits_not_at_remote`, `remote_matches_local_head`,
`remote_changed`, `remote_diverged_or_unknown`, and `unknown`.
The classification does not prove this Skill wrote the remote commit.
Never reset, force-push, retry or resume using the original approval.

Keep technical details (HEAD, index, fetch/push URLs, remote OID, upstream,
branch protection uncertainty) available, but default to a concise human
review. Full trust and failure invariants: [safety.md](safety.md).
