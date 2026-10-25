# Git Hook compatibility and reapproval

## Commit preparation

Once an exact plan is approved and validations pass, the executor builds **all**
candidate file-level Git trees before changing the real branch. It then
preflights the following existing executable hooks **for each candidate
commit**, in order, in a temporary local checkout:

1. `pre-commit` — may lint or format candidate files.
2. `prepare-commit-msg` — may adjust the proposed full message.
3. `commit-msg` — may validate or adjust the message.

No new approval is requested **between** successful hooks or planned commits.
A nonzero Hook exit stops immediately; later hooks do not run.

After every hook in the successful round has executed, the executor compares
the candidate Git index, relevant working files and entire commit messages
against the approved trees and messages.

- **No differences:** Create the already approved commit objects, update the
  real branch once and synchronize the real index. If pushing was authorized,
  normal Git push runs the native `pre-push` Hook.
- **Changes limited to approved regular-file paths:** No commit or push.
  Copy safe formatter results to the real worktree, precisely restage only
  approved paths and report message suggestions. Start **new review, freeze
  and explicit approval**. An originally clean-index checkout may now need
  `--staging-mode pre-staged-only`.
- **Changes outside the approved path set, unsupported file types or a Hook
  failure:** No commit or push; report details. Unsupported changes are
  not copied into the real checkout.
- **No retry loops.** Each approved plan authorizes a single preparation
  round. A formatter that repeatedly writes timestamps will continue to
  require human investigation, not a retry counter.

## What this does not guarantee

This is **not a sandbox or complete native `git commit` emulation**. Hooks
execute with reviewed candidate trees in a temporary clone, which may not
contain ignored dependencies or setup files (notably `node_modules` with
Husky/lint-staged). A project Hook can also write outside its working
directory; treat hooks as trusted local programs. An executable `core.hooksPath`
is supported, but its shell/context assumptions may still require adaptation.

The final commit objects use `commit-tree`, therefore `post-commit` and
other after-commit hooks are **not** run. Normal local Git attributes, custom
filters, Git LFS and native `pre-push` remain enabled. The application
cannot promise to replicate every Git hook manager or configuration.
If a Hook depends on unavailable files, do not silently bypass it.

The approved scope must remain identical even if hooks would otherwise
modify it. Any authorized change requires another digest-bound approval.
