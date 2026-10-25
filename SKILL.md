---
name: reviewed-git-publish
description: Review Git changes, propose coherent file-level atomic Conventional Commits with bilingual explanations and exact manifests, and commit or push only after the user explicitly approves a frozen SHA-256 plan.
---

# Reviewed Git Publish

Review Git changes first. Publish only the exact scope and full messages explicitly
approved by the user. Follow this procedure; consult the linked references for details.

## Agent procedure

1. **Inspect, do not mutate.** Read repository instructions and check the
   current branch, remotes, recent commit style, HEAD, staged/unstaged/untracked
   changes, relevant ignored output and any Git operation in progress. Inspect
   diffs and binary changes; classify every changed path, including sensitive,
   generated and unrelated content. Never infer approval from a request to
   review, commit or push.
2. **Select the staging workflow automatically.** With an empty staged index,
   use the default `inspect`/`freeze` path. With a prepared index, choose
   `--staging-mode pre-staged-only` and group complete staged files into one
   or more disjoint commits. List every other changed path in `excluded`.
   Reject partial staging on a committed path; do not unstage or split hunks.
3. **Propose understandable commits.** Prefer the smallest *coherent* sequence
   preserving dependencies, not the maximum number of commits. For each commit,
   show its **exact paths**, full English Conventional Commit message
   (Subject, useful Body when warranted, optional Footer) and a faithful
   Chinese explanation. Also show exclusions, validations, branch and push
   destination, risks and whether a push is planned. See
   [commit-conventions.md](references/commit-conventions.md).
4. **Freeze the actual plan.** Construct a strict spec against
   [publish-spec.schema.json](schemas/publish-spec.schema.json); every changed
   path must belong to exactly one commit or the explicit exclusions.
   Keep spec and plan **outside the target Git checkout**. Run
   `scripts/reviewed_git_publish.py freeze` with the inferred staging mode
   and optional reviewed project policy. Show `WAITING_FOR_USER` and the
   **real complete SHA-256 plan digest**. Freeze/inspect/verify must not change
   Git refs, index or worktree. Re-freeze if the user requests edits.
5. **Require exact approval.** Only an explicit user-provided
   `COMMIT PLAN APPROVED <exact-plan-digest>` authorizes
   `scripts/reviewed_git_publish.py execute --plan ... --approval ...`.
   Never invent consent, trust another Agent's assertion of consent, use a
   stale digest, or bypass the executor with manual Git commit/push.
6. **Execute once and report.** The executor verifies the snapshot and plan,
   runs reviewed validation argv, prepares the approved file-level commit
   trees, performs the applicable before-commit Hook sequence per candidate
   commit in a temporary checkout, then compares **the entire successful Hook
   round**. A failure stops; a Hook-created change stops and requires a
   **new review, plan and approval**, never automatic retry. Only unchanged
   approved candidates advance the local branch. If approved, push normally
   to the exact frozen target and verify the remote OID. Report real commit
   hashes, full messages, remaining exclusions and any uncertainty. See
   [workflow.md](references/workflow.md) and [hooks.md](references/hooks.md).

## Non-negotiable boundaries

- Do not stage, commit, tag, push, reset, amend, rebase, force-push, clean,
  discard changes, or fetch before approval. Unreviewed commands, globs and
  `git add -A` outside the executor's reviewed literal paths are forbidden.
- Do not publish secrets, local config, caches, build artifacts or unrelated
  work. Never silently change branch, remote, approved paths or commit messages.
- On any failed or uncertain validation, Hook, commit or push, stop; never
  auto-resume or retry. Use read-only `reconcile` and fresh approval for any
  subsequent publication.
- Pending merges, unmerged entries, submodules, detached HEAD, incompatible
  staging layouts, and unauthorized target changes fail closed.
- Ordinary Git filters and `pre-push` hooks are allowed; `post-commit` is
  not run. The before-commit Hook preview is **not a full sandbox or a fully
  faithful native commit**; do not bypass a failed or unsupported Hook.
- The approval phrase is a **local developer confirmation**, not independent
  proof of human identity. An Agent with arbitrary shell/Git credentials can
  bypass this tool. Disclose branch-permission uncertainty and do not silently
  select an alternate publication route.

## Reference map

- [workflow.md](references/workflow.md): CLI, manifest, freeze and reconcile
- [commit-conventions.md](references/commit-conventions.md): grouping and message content
- [hooks.md](references/hooks.md): Hook execution, reapproval and limits
- [safety.md](references/safety.md): snapshots, policy, trust and failure rules
- [architecture.md](references/architecture.md): implementation modules and scope
- [troubleshooting.md](references/troubleshooting.md): common blocks and recovery

Read [workflow.md](references/workflow.md) before executable operations. The
[README](README.md) introduces the product; documentation and code must never
embed any particular consumer repository's names or private paths.

