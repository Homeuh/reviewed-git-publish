# File-level atomic commits and message conventions

## Group by meaning, not by file count

- Prefer **one coherent feature or fix per commit**. Related modifications
  across many files may belong to one commit; unrelated changes should not
  be combined merely because they touch the same layer.
- Keep each complete changed file in at most one commit. Automatically splitting
  hunks or assigning portions of the same file to multiple commits is out of
  scope. If unrelated edits share a file, either document them in one justified
  commit or ask the developer to separate them before freezing.
- Ensure intermediate commits preserve required dependencies and are reasonably
  buildable. Propose the smallest number of useful commits, not as many as possible.
- Respect the existing staged index: in `pre-staged-only`, all staged paths
  must be partitioned across commits, while other changes are explicitly
  excluded. Never silently stage or unstage before approval.

## Conventional Commit

Subject:

```text
<type>(<scope>): <imperative English summary>
```

The scope is optional; valid types are `feat`, `fix`, `docs`, `test`,
`refactor`, `perf`, `build`, `ci`, `chore`, and `revert`.
Use `!` only for an actual breaking change.

Write a useful Body for non-trivial changes after a blank line, explaining
**why** the change exists, **what** changed in meaningful terms and important
behavioral impact. A Footer may reference issues or breaking changes.
The complete message, not just the subject, is frozen and validated.

```text
refactor(web): simplify navigation orchestration

- Consolidate duplicated route selection logic
- Preserve existing URL and navigation behavior
- Isolate workspace state for easier maintenance

Refs: #42
```

For a trivial typo, a clear Subject alone is sufficient:

```text
docs: correct setup command
```

Avoid listing every changed line or copying `git diff` into the Body; Git
already preserves code-level detail. Explain the intent, constraints and
compatibility decisions instead.

## Bilingual review contract

The published Commit Message is **English**. The plan also stores a
nonempty **Chinese explanation** for each commit, so a reviewer can judge
the intent without interpreting the code and message solely in English.
The UI should show the full approved message, exact paths and Chinese
explanation, and cannot hide an excluded/committed path behind a glob.

Never rewrite approved messages after freeze without a new digest and approval.
Project-specific commitlint conventions can add stricter validations; they
cannot relax frozen scope rules.
