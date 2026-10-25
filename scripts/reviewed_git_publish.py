#!/usr/bin/env python3
"""Compatible executable entrypoint for Reviewed Git Publish (Python 3.9+)."""
import sys
from rpg.cli import main
from rpg.errors import GuardError

if __name__ == "__main__":
    try:
        main()
    except (GuardError, OSError, ValueError, KeyError, TypeError) as error:
        print("BLOCKED: " + str(error), file=sys.stderr)
        sys.exit(2)

