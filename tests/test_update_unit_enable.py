#!/usr/bin/env python3
"""The ingress boot unit's enable result must reach the exit status.

A failed `systemctl enable impreza-agent-ingress.service` inside
update.sh --apply used to read as success (exit 0 with `|| true`): the
customer saw "updated" while the boot window the unit closes came back
on the next reboot. These pins keep the reviewed shape: the documented
exit status 3, the warning that names the unit and the repair command,
the status carried through both success paths, and no silent best-effort
enable. The behavioral proof (stubbed systemctl on a live host) lives in
the delivery's VPS battery; these pins fail fast on textual drift.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPT = (ROOT / "update.sh").read_text(encoding="utf-8")


def pin(name, pattern):
    if not re.search(pattern, SCRIPT):
        print("update.sh lost: %s" % name, file=sys.stderr)
        sys.exit(1)


pin("the exit-status documentation", r"3 when the agent is updated but\s*\n#\s*the ingress boot unit could not be enabled")
pin("the enable attempt is checked, not best-effort", r'if ! systemctl enable impreza-agent-ingress\.service >/dev/null 2>&1; then')
pin("the warning names the unit and the repair", r"WARNING: the agent is updated, but the ingress boot unit could not be enabled.*Repair: systemctl enable impreza-agent-ingress\.service")
pin("the dedicated status variable", r"UNIT_ENABLE_STATUS=3")
pin("the already-current path carries it", r"echo 'Agent is already current\.'\s*\n\s*exit \"\$UNIT_ENABLE_STATUS\"")
pin("the updated path carries it", r"exit \"\$UNIT_ENABLE_STATUS\"\s*\n\}")
if re.search(r"systemctl enable impreza-agent-ingress\.service[^\n]*\|\| true", SCRIPT):
    print("update.sh regressed to a best-effort enable", file=sys.stderr)
    sys.exit(1)
print("update.sh unit-enable pins: ok")
