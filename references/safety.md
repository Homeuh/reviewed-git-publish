# Safety boundaries, frozen snapshots and policy

## Freeze and integrity

Before the user's exact `COMMIT PLAN APPROVED <digest>` confirmation,
`inspect`, `freeze` and `verify` are read-only. They never stage,
fetch, commit, tag, push or write refs. Keep the plan and input spec outside
the checkout.

The SHA-256 digest covers: baseline HEAD, checked-out branch, changed path
list and changed file bytes/mode/type, staged Git index entries, effective
fetch and **single frozen push URL**, observed remote ref OID, commit order,
full English messages, Chinese descriptions, exact path manifests, excluded
paths, validation argv, optional policy and push decision. It does **not**
fingerprint ignored files or all otherwise clean tracked files.

Any drift of approved state (including Hook executable state) invalidates
the old plan. A normal push uses only the reviewed push destination and
`HEAD:refs/heads/<branch>`, never force push, deletion or tag operations.
Git provider permissions and branch protection are external.

## Unsupported states and unsafe files

Reject unresolved merges, unmerged index entries, Git submodule gitlinks,
detached HEAD, unauthorized target branches, ambiguous multiple push URLs,
partial staged edits on a committed path, and sensitive committed paths
such as secrets or credentials. Never expand a frozen file set.

Do not auto-reset, rebase, amend, `git clean`, force-push, or retry on
uncertain execution. On an error, report the local HEAD and staged state,
changed files, completed commits and remote result. Use read-only
`reconcile`, followed by a **fresh plan and approval** for any further
publication. A branch ref is atomically updated once after candidate
preparation, but its subsequent index synchronization is a separate step;
unexpected failures may require manual diagnosis.

Project-specific validations and Git filters/hooks execute trusted commands;
this is not an OS isolation boundary. Avoid running on a checkout with
concurrent external changes. Local human confirmation is not authenticated
identity: an Agent with unrestricted Git access can bypass it. The Skill
does not claim independently secure approval or privileged production
publisher credentials.

## Optional additional project policy

The user may explicitly provide a stricter JSON policy following
[publish-policy.schema.json](../schemas/publish-policy.schema.json) and
[policy.example.json](../assets/policy.example.json).

```bash
python3 -B scripts/reviewed_git_publish.py freeze \
  --repo /path/to/repo --spec /outside/spec.json \
  --policy /outside/policy.json --output /outside/plan.json
```

Supported settings include exact allowed remotes, glob-style allowed
branches, whether push is allowed, required validations, blocked path
patterns and maximum commit count. These can **only add restrictions**,
never relax hard safety constraints. The policy content and validations
are bound to the plan digest and revalidated at execution.
