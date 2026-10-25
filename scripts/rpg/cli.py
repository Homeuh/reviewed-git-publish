"""Public stable CLI actions: inspect, freeze, verify, execute."""
import argparse
import json
from pathlib import Path
import sys

from .errors import GuardError, require
from .git import text_git
from .jsonio import load_json
from .snapshot import capture, require_outside_repo
from .plan import freeze, load_plan
from .policy import load_policy
from .verifier import ensure_baseline, failure_diagnostics, reconcile
from .executor import execute

def main():
    parser = argparse.ArgumentParser(description="Review-controlled Git publisher (local approval mode)")
    parser.add_argument("action", choices=["inspect", "freeze", "verify", "execute", "reconcile"])
    parser.add_argument("--repo", default=".")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch")
    parser.add_argument("--spec", help="JSON input for freeze")
    parser.add_argument("--policy", help="optional strict project policy JSON for freeze")
    parser.add_argument("--staging-mode", choices=["clean", "pre-staged-only"], default="clean",
                        help="use approved staged file set, with one or more complete-file commits")
    parser.add_argument("--plan", help="frozen JSON for verify/execute")
    parser.add_argument("--output", help="write freeze JSON here; must be outside repo")
    parser.add_argument("--approval", help="exact user-provided phrase and SHA-256 digest")
    args = parser.parse_args()
    require(not args.policy or args.action == "freeze", "--policy is only accepted with freeze")
    require(args.staging_mode == "clean" or args.action in ("inspect", "freeze"),
            "--staging-mode is only accepted with inspect/freeze")
    repo = Path(args.repo).resolve()
    require(text_git(repo, "rev-parse", "--is-inside-work-tree") == "true", "not a Git worktree")
    require(Path(text_git(repo, "rev-parse", "--show-toplevel")).resolve() == repo,
            "repo must be the Git worktree root")
    if args.action == "inspect":
        require(args.branch, "--branch required")
        output = capture(repo, args.remote, args.branch, staging_mode=args.staging_mode)
    elif args.action == "freeze":
        require(args.spec and args.output, "--spec and --output required")
        require_outside_repo(args.spec, repo, "spec input")
        require_outside_repo(args.output, repo, "plan output")
        spec = load_json(args.spec)
        output_path = Path(args.output).resolve()
        policy = load_policy(args.policy) if args.policy else None
        output = freeze(repo, spec, policy=policy, staging_mode=args.staging_mode)
        require(not output_path.exists(), "refuse to overwrite plan")
        with open(output_path, "x", encoding="utf-8") as stream:
            json.dump(output, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
    else:
        require(args.plan, "--plan required")
        require_outside_repo(args.plan, repo, "plan input")
        plan = load_plan(args.plan)
        if args.action == "verify":
            ensure_baseline(repo, plan)
            output = {"valid": True, "planDigest": plan["planDigest"]}
        elif args.action == "reconcile":
            output = reconcile(repo, plan)
        else:
            require(args.approval, "--approval required")
            try:
                output = execute(repo, plan, args.approval)
            except (GuardError, OSError, ValueError, KeyError, TypeError):
                print("PUBLISH_STATE: " + json.dumps(reconcile(repo, plan),
                                                     ensure_ascii=False, sort_keys=True), file=sys.stderr)
                raise
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))

