# Reviewed Git Publish

> Let your AI Agent review and organize Git changes like a careful code reviewer—and publish only what you explicitly approve.

<p align="right">
  <a href="./README.md">English</a> |
  <a href="./README.zh-CN.md">简体中文</a>
</p>

Reviewed Git Publish is a reusable Agent Skill for developers who have finished
coding locally and want help reviewing changes, creating readable Git history,
and pushing approved commits safely.

Simply ask:

> Review my current changes, group them into meaningful commits, show me the exact files and commit messages, and push only after I approve.

The Agent interprets diffs, plans coherent commits, and explains its reasoning.
The bundled Python executor freezes the actual Git state, validates approval,
and operates on **exact file manifests** rather than broad staging patterns.
Approval is an explicit **local developer confirmation**, not an independently
authenticated human signature.

## Features

| Capability | What it does |
|---|---|
| **Git change review** | Inspects staged, unstaged, and untracked changes; flags sensitive, generated, or unrelated files |
| **File-level atomic commits** | Groups whole files into one or more meaningful commits based on purpose, without unnecessary fragmentation |
| **Readable Commit Messages** | Proposes English Conventional Commit Subjects, useful Bodies/Footers for substantial changes, and Chinese review explanations |
| **Exact include/exclude scope** | Shows every path belonging to each commit and all excluded paths; preserves unrelated working-tree changes |
| **Frozen plans and approval** | Captures HEAD, changed contents, Git index, remote target, full messages, and other state in a SHA-256-bound plan |
| **Git Hook preflight** | Runs applicable before-commit Hooks per candidate commit in order and checks the entire successful round together |
| **Reapproval when needed** | Stops when Hooks change approved files or messages; requests a new plan and approval rather than silently retrying |
| **Normal push and verification** | Uses the approved destination, preserves the native `pre-push` Hook, and confirms the final remote OID |
| **Failure diagnosis** | Provides read-only `reconcile` reports for local-only commits, remote differences, and uncertain outcomes |

## How it works

```text
Developer's natural-language request
      │
      ▼
Agent inspects Git state and code diffs
      │
      ▼
Propose coherent commit groups, full messages, excluded files
      │
      ▼
Executor freezes exact paths, index, branch, remote → SHA-256
      │
      ▼
WAITING_FOR_USER — developer reviews and approves
      │
      ├─ Declined / needs changes → revise and freeze a new plan
      │
      ▼
Snapshot drift checks and approved validations
      │
      ▼
Private candidate Git trees + before-commit Hook preflight
      │
      ├─ Hook failure or changes → stop; refreeze and reapprove if appropriate
      │
      ▼
Create approved commit chain with one local branch ref update
      │
      ▼
If push was approved: normal push + remote OID verification
```

This separates **semantic decisions by the Agent** (what belongs together
and why) from **deterministic checks by the Git executor** (what may actually
be committed). See [Architecture](references/architecture.md) and
[Workflow](references/workflow.md) for the implementation boundaries.

## Example review plan

A single work session might become:

```text
Commit 1
  feat(web): improve workspace navigation

  Consolidate route-selection logic without changing public behavior.

  Files: src/navigation.ts
  Chinese review: 整理导航逻辑，保持现有路由行为

Commit 2
  fix(api): handle expired sessions

  Return a controlled error for requests with an expired session.

  Files: src/api.ts
  Chinese review: 修复会话过期时的接口处理

Excluded: .env.local (local environment settings)
Target: origin/main
Status: WAITING_FOR_USER
Digest: <actual 64-character SHA-256 from the frozen plan>
```

A simple fix may use a single-line Commit Subject; a Body is not mandatory.
Automatic Hunk-level splitting is intentionally unsupported. Meaningful
intent and traceable Git history matter more than creating extra commits.

## Quick start

**Requirements:** Python 3.9+ and Git supporting `--pathspec-from-file`.
No third-party Python packages or specific frontend/backend framework required.

Unpack the release ZIP to get a `reviewed-git-publish/` directory, then run
these commands **inside that directory**:

```bash
python3 -B scripts/manage_skill.py install \
  --target /path/to/your-repo/.agents/skills

python3 -B scripts/manage_skill.py status \
  --target /path/to/your-repo/.agents/skills
```

Ask your Agent to review the repository using this Skill. It should show
the real complete SHA-256 plan digest. Only after reviewing the full scope,
provide explicit approval:

```text
COMMIT PLAN APPROVED <actual 64-character plan digest>
```

To update to a newer release:

```bash
python3 -B scripts/manage_skill.py update \
  --target /path/to/your-repo/.agents/skills \
  --source /path/to/new-reviewed-git-publish.zip
```

The installer does **not** stage, commit, or push Git changes. Updates retain
a backup of the previous installation. See
[Installation and updates](references/installation.md).

## Project structure

```text
reviewed-git-publish/
├── SKILL.md                       Agent instructions and approval boundaries
├── README.md                      Default English overview
├── README.zh-CN.md                Simplified Chinese overview
├── agents/openai.yaml             Agent metadata
├── references/                    Current feature-based documentation
│   ├── workflow.md
│   ├── commit-conventions.md
│   ├── hooks.md
│   ├── safety.md
│   ├── architecture.md
│   ├── installation.md
│   └── troubleshooting.md
├── scripts/
│   ├── reviewed_git_publish.py    inspect / freeze / verify / execute / reconcile
│   ├── manage_skill.py            install / update / status
│   └── rpg/                       Git, plan, approval, validation, Hook, execution
├── schemas/                       JSON schemas for plans and optional policies
└── assets/                        Example generic policy
```

The distributed Skill includes only what normal users need.
The development workspace separately retains tests, Agent evaluations,
build tools, historical research, and experimental publisher prototypes.
See [Architecture](references/architecture.md) for module responsibilities.

## Safety and limitations

- `inspect`, `freeze`, and `verify` are read-only before approval. The
  plan must live **outside the target Git checkout**. No unapproved staging,
  committing, or pushing.
- The digest binds the **whole approved plan**, not just a Commit Subject.
  A change to approved contents or the push destination invalidates approval.
- Partially staged edits on the same committed path, unresolved conflicts,
  submodules, and detached HEAD are unsupported publication states.
- Before-commit Hooks are preflighted in a **temporary checkout**, so Hooks
  relying on `node_modules`, Husky, or custom local environment setup may
  not run identically to native `git commit`. `post-commit` does not run;
  normal `pre-push` does.
- SHA-256 protects **agreement between the approved plan and the state to
  be executed**. An Agent with unrestricted shell access and Git credentials
  could still bypass the local tool. Local approval is not independent identity
  authentication or production-grade access isolation.
- There is no automatic retry, force push, reset, amend, rebase, or history
  rewriting. Failed or uncertain states require inspection and a new plan.

See [Safety](references/safety.md) and
[Troubleshooting](references/troubleshooting.md) for details.

## Documentation

- [Workflow and CLI](references/workflow.md)
- [Commit conventions](references/commit-conventions.md)
- [Git Hooks and reapproval](references/hooks.md)
- [Safety model](references/safety.md)
- [Architecture and module responsibilities](references/architecture.md)
- [Installation and updates](references/installation.md)
- [Troubleshooting](references/troubleshooting.md)

