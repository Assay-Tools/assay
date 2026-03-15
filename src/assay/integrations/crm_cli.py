"""CLI wrapper for Assay CRM — for use by heartbeat agents via bash.

Agents invoke this to look up contacts, log interactions, and manage
do_not_contact flags without needing to import Python directly.

Usage:
    cd /Users/aj/git/assay
    python -m assay.integrations.crm_cli lookup <email>
    python -m assay.integrations.crm_cli log-received <email> <subject> [body_snippet]
    python -m assay.integrations.crm_cli log-sent <email> <subject> [body_snippet]
    python -m assay.integrations.crm_cli mark-dnc <email> [reason]

Output: JSON to stdout. Exit 0 = success, 1 = bad args, 2 = CRM unavailable.

lookup output (contact exists):
    {"found": true, "id": "...", "email": "...", "status": "...",
     "tags": [...], "notes": "...", "is_do_not_contact": false}

lookup output (contact not in CRM):
    {"found": false, "email": "..."}

All write commands output:
    {"ok": true, "action": "...", "email": "..."}
"""

import json
import sys


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: python -m assay.integrations.crm_cli <command> [args]", file=sys.stderr)
        sys.exit(1)

    command = args[0]

    if command == "lookup":
        if len(args) < 2:
            print("Usage: crm_cli lookup <email>", file=sys.stderr)
            sys.exit(1)
        from assay.integrations.crm import get_contact
        email = args[1]
        result = get_contact(email)
        if result is None:
            print(json.dumps({"found": False, "email": email}))
        else:
            print(json.dumps(result))

    elif command == "log-received":
        if len(args) < 3:
            print("Usage: crm_cli log-received <email> <subject> [body]", file=sys.stderr)
            sys.exit(1)
        from assay.integrations.crm import on_email_received
        email, subject = args[1], args[2]
        body = args[3] if len(args) > 3 else ""
        on_email_received(email, subject, body)
        print(json.dumps({"ok": True, "action": "log-received", "email": email}))

    elif command == "log-sent":
        if len(args) < 3:
            print("Usage: crm_cli log-sent <email> <subject> [body]", file=sys.stderr)
            sys.exit(1)
        from assay.integrations.crm import log_email_sent
        email, subject = args[1], args[2]
        body = args[3] if len(args) > 3 else ""
        log_email_sent(email, subject, body)
        print(json.dumps({"ok": True, "action": "log-sent", "email": email}))

    elif command == "mark-dnc":
        if len(args) < 2:
            print("Usage: crm_cli mark-dnc <email> [reason]", file=sys.stderr)
            sys.exit(1)
        from assay.integrations.crm import mark_do_not_contact
        email = args[1]
        reason = args[2] if len(args) > 2 else ""
        mark_do_not_contact(email, reason)
        print(json.dumps({"ok": True, "action": "mark-dnc", "email": email}))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
