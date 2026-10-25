"""Local confirmation; not proof of authentic human identity."""
from .errors import require


def verify_local_confirmation(plan, approval):
    expected = "COMMIT PLAN APPROVED " + plan["planDigest"]
    require(approval.strip() == expected, "explicit matching approval required: " + expected)
