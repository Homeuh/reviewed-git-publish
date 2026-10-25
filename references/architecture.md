# Architecture and module responsibilities

This is a **portable, Python standard-library-only Agent Skill**. The Agent
makes semantic decisions and explains changes; the executable gate verifies
fixed Git facts, approved scope and state transitions. Neither the Agent
prompt nor local approval is an authenticated security perimeter.

```text
Developer
   │ request to review and publish
   ▼
Agent / SKILL.md
   │ inspect Git, review diffs, choose commits and exclusions
   ▼
CLI inspect → freeze  ──> external plan + SHA-256 digest
   │                         │
   │                    human reviews
   │                         │ exact approval
   ▼                         ▼
CLI verify / execute ────────┘
   │ validation + drift checks
   ▼
Private candidate indices / reviewed Git trees
   │ per-commit temporary Hook preflight
   ├─ Hook modifies result → STOP, new plan + approval
   ▼
Exact commit chain → one local branch ref transition
   │ synchronize index
   ▼
Optional standard push → remote OID confirmation
```

## Distributed Skill structure

```text
reviewed-git-publish/
├── SKILL.md                 # Agent entrypoint and boundaries
├── README.md                # Default English product overview
├── README.zh-CN.md          # Simplified Chinese product overview
├── agents/openai.yaml       # Host-Agent metadata
├── references/              # Current feature documentation only
│   ├── workflow.md
│   ├── commit-conventions.md
│   ├── hooks.md
│   ├── safety.md
│   ├── architecture.md
│   ├── installation.md
│   └── troubleshooting.md
├── scripts/
│   ├── reviewed_git_publish.py  # Public CLI: inspect/freeze/verify/execute/reconcile
│   ├── manage_skill.py          # Offline install/update/status
│   └── rpg/
│       ├── cli.py               # Dispatch and input/output contract
│       ├── git.py               # Git status, URLs and OIDs
│       ├── snapshot.py          # Worktree/index fingerprint capture
│       ├── plan.py              # Spec validation and digest freeze
│       ├── policy.py            # Optional stricter project rules
│       ├── approval.py          # Exact local confirmation check
│       ├── verifier.py          # Drift detection and read-only reconcile
│       ├── executor.py          # Candidate trees, commits and push
│       ├── hooks.py             # Temporary before-commit Hook preview
│       ├── jsonio.py            # Strict JSON decoding
│       └── errors.py
├── schemas/
└── assets/
```

Runtime supports Python 3.9+ and Git with
`--pathspec-from-file`. No pip dependencies or frontend framework are
required. The directory of consumer-specific code, build tools, tests,
Agent evals, historical iteration notes and optional security experiments
belong to the **development repository**, not the installed Skill.

## Invariants to preserve

- Human-readable intent is semantic; Git publishing is by exact frozen paths
  and blob/tree objects.
- The complete full-message approval digest is checked at execution.
- All before-commit hooks are preflighted before updating the real branch.
- Multiple complete-file commits may originate from staged or unstaged
  changes; partially staged committed files and hunk splitting do not.
- The normal single push destination is frozen and confirmed by OID.
- A failed/uncertain operation never triggers automatic retry.

See [workflow.md](workflow.md) for actual CLI syntax and
[safety.md](safety.md) for the trust model.
