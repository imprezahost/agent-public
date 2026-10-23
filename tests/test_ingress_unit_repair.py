"""Behavioral updater tests: private fake root, public RFC test vector only.

No host service, registration, real credential, network or package install.
Run on Linux with Python unittest discovery.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_update_manifest import (RFC8032_VECTORS, python_ed25519_sign,
                                  valid_payload)

REPO = Path(__file__).resolve().parents[1]
EXPECTED = (REPO / "tests/fixtures/ingress-unit.service").read_text()


@unittest.skipUnless(sys.platform.startswith("linux"), "POSIX fake-root updater")
class IngressRepair(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name in ("usr/local/bin", "etc/impreza-agent", "etc/systemd/system",
                     "var/lib/impreza-agent", "run/lock", "shim", "releases/stable/0.6.36"):
            (self.root / name).mkdir(parents=True)
        self.unit = self.root / "etc/systemd/system/impreza-agent-ingress.service"
        self.calls = self.root / "calls"
        self.config = self.root / "etc/impreza-agent/config.toml"
        self.config.write_text("identity = 'synthetic-existing-identity'\n")
        self.app = self.root / "var/lib/impreza-agent/app-canary"
        self.app.write_text("synthetic app state stays here")
        (self.root / "var/lib/impreza-agent/ingress.json").write_text("{}")
        self.program = "#!/bin/sh\necho 'impreza-agent version 0.6.36'\n"
        self.current = self.root / "usr/local/bin/impreza-agent"
        self.write_exe(self.current, self.program.replace("0.6.36", "0.6.35"))
        self.script = (REPO / "update.sh").read_text()
        # A modeled old unit; the complete unit fixture also runs on baseline.
        self.legacy = "\n".join(line for line in EXPECTED.splitlines()
                                 if line not in ("PartOf=docker.service", "RemainAfterExit=yes",
                                                 "ExecReload=/usr/local/bin/impreza-agent ingress reload")
                                 and not line.startswith(("# The unit stays", "# reloaded;", "# every Docker", "# validating every")))+"\n"
        self.shim("id", "echo 0\n")
        self.shim("uname", 'case "$1" in -s) echo Linux;; -m) echo x86_64;; esac\n')
        self.shim("sleep", "exit 0\n")
        self.shim("python3", "exec "+shlex.quote(sys.executable)+' "$@"\n')
        # Exercise the real updater's shipped RFC verifier, not a stubbed accept.
        self.shim("openssl", "echo 'Usage: pkeyutl'; exit 0\n")
        actual_stat = shutil.which("stat")
        self.assertIsNotNone(actual_stat)
        self.shim("stat", 'if [ "$1" = -c ] && [ "$2" = "%u:%a" ]; then\n'
                  'm=$('+shlex.quote(actual_stat)+' -c %a "$3"); echo "0:$m"\nelse exec '
                  +shlex.quote(actual_stat)+' "$@"; fi\n')
        r = shlex.quote(str(self.root))
        self.shim("systemctl", 'echo "$*" >> '+shlex.quote(str(self.calls))+"\n"
                  + 'ROOT='+r+'\ncase "$1" in\n'
                  'cat) exit 0;;\n'
                  'show) case "$*" in\n'
                  '*ExecStart*) echo "$ROOT/usr/local/bin/impreza-agent run";;\n'
                  '*MainPID*) echo 100;; *NRestarts*) echo 0;;\n'
                  '*NeedDaemonReload*) echo no;;\n'
                  '*DropInPaths*) [ ! -d "$ROOT/etc/systemd/system/impreza-agent-ingress.service.d" ] || echo operator.conf;;\n'
                  'esac; exit 0;;\n'
                  'is-enabled) exit 0;;\n'
                  'is-active) case "$*" in *impreza-agent-ingress.service*) [ -f "$ROOT/active" ];; *) exit 0;; esac;;\n'
                  'start) case "$*" in *impreza-agent-ingress.service*) touch "$ROOT/active";; esac; exit 0;;\n'
                  '*) exit 0;; esac\n')

    def write_exe(self, path, text):
        path.write_text(text)
        path.chmod(0o755)

    def shim(self, name, text):
        self.write_exe(self.root / "shim" / name, "#!/bin/sh\n"+text)

    def rooted(self, text):
        for prefix in ("/etc/systemd/system", "/etc/impreza-agent", "/usr/local/bin",
                       "/var/lib/impreza-agent", "/run/lock"):
            text = text.replace(prefix, str(self.root)+prefix)
        return text

    def prepare_release(self, bad=None):
        release = self.root / "releases/stable"
        data = self.program.encode()
        artifact = {"name": "impreza-agent-linux-amd64",
                    "sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
        if bad == "size": artifact["size"] += 1
        if bad == "digest": artifact["sha256"] = "a"*64
        if bad == "version": data = data.replace(b"0.6.36", b"0.6.34")
        if bad == "version":
            artifact.update(sha256=hashlib.sha256(data).hexdigest(), size=len(data))
        (release / "0.6.36" / artifact["name"]).write_bytes(data)
        payload = json.dumps(valid_payload(version="0.6.36", artifacts={"amd64": artifact}),
                             separators=(",", ":")).encode()
        seed, public, _, _ = RFC8032_VECTORS[0]  # Published test vector, not a credential.
        # Retain the exact envelope framing of the existing test helper.
        from test_update_manifest import build_envelope
        class PublicVector:
            def sign(self, message):
                return python_ed25519_sign(bytes.fromhex(seed), message)
        raw = build_envelope(PublicVector(), json.loads(payload))
        (release / "manifest.signed.json").write_bytes(raw)
        return base64.b64encode(bytes.fromhex(public)).decode()

    def run_update(self, bad=None, mode="--apply"):
        public = self.prepare_release(bad)
        script = self.root / "update.sh"
        script.write_text(self.rooted(self.script))
        env = dict(os.environ)
        env.pop("IMPREZA_AGENT_VERSION", None)
        env.update(PATH=str(self.root / "shim")+os.pathsep+os.environ.get("PATH", ""),
                   IMPREZA_RELEASE_PUBLIC_KEY=public,
                   IMPREZA_AGENT_RELEASE_BASE=str(self.root / "releases"),
                   IMPREZA_AGENT_CHANNEL="stable")
        p = subprocess.run(["sh", str(script), mode], env=env,
                           capture_output=True, text=True, timeout=45)
        self.assertEqual(self.config.read_text(), "identity = 'synthetic-existing-identity'\n")
        self.assertEqual(self.app.read_text(), "synthetic app state stays here")
        return p

    def assert_complete(self):
        self.assertEqual(self.unit.read_text(), self.rooted(EXPECTED))

    def test_update_old_unit_preserves_identity_apps_and_starts_only_if_needed(self):
        self.unit.write_text(self.rooted(self.legacy))
        p = self.run_update()
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assert_complete()
        calls = self.calls.read_text()
        self.assertEqual(calls.count("start impreza-agent-ingress.service"), 1)
        self.assertNotIn("restart impreza-agent-ingress.service", calls)

    def test_complete_current_unit_is_not_rewritten_or_restarted(self):
        self.unit.write_text(self.rooted(EXPECTED))
        self.current.write_text(self.program)
        (self.root / "active").touch()
        before = self.unit.stat().st_mtime_ns
        p = self.run_update()
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assertEqual(self.unit.stat().st_mtime_ns, before)
        calls = self.calls.read_text()
        self.assertNotIn("daemon-reload", calls)
        self.assertNotIn("start impreza-agent-ingress.service", calls)
        self.assertNotIn("stop impreza-agent.service", calls)

    def test_missing_unit_is_repaired_by_the_real_update_entry(self):
        p = self.run_update()
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assert_complete()

    def test_sync_failure_preserves_the_previous_unit_and_binary(self):
        self.unit.write_text(self.rooted(self.legacy))
        before = self.unit.read_bytes(), self.current.read_bytes()
        self.shim("sync", "exit 1\n")
        p = self.run_update()
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(before, (self.unit.read_bytes(), self.current.read_bytes()))
        self.assertEqual(list(self.unit.parent.glob(".impreza-ingress.*")), [])

    def test_bad_artifacts_leave_unit_and_binary_untouched(self):
        for bad in ("size", "digest", "version"):
            with self.subTest(bad=bad):
                self.unit.write_text(self.rooted(self.legacy))
                before = self.unit.read_bytes(), self.current.read_bytes(), self.unit.stat().st_mtime_ns
                p = self.run_update(bad)
                self.assertNotEqual(p.returncode, 0)
                self.assertEqual(before, (self.unit.read_bytes(), self.current.read_bytes(), self.unit.stat().st_mtime_ns))
                if self.calls.exists(): self.assertNotIn("daemon-reload", self.calls.read_text())

    def test_custom_file_and_operator_dropin_are_preserved(self):
        self.unit.write_text("# operator customization\n")
        before = self.current.read_bytes()
        p = self.run_update()
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(self.unit.read_text(), "# operator customization\n")
        self.assertEqual(self.current.read_bytes(), before)
        self.unit.write_text(self.rooted(self.legacy))
        dropins = self.unit.with_name(self.unit.name+".d")
        dropins.mkdir()
        override = dropins / "operator.conf"
        override.write_text("# private operator choice\n")
        p = self.run_update()
        self.assertEqual(p.returncode, 3, p.stdout+p.stderr)
        self.assertEqual(override.read_text(), "# private operator choice\n")
        self.assertNotIn("start impreza-agent-ingress.service", self.calls.read_text())

    def test_symlink_unit_refuses_without_following_target(self):
        target = self.root / "foreign"
        target.write_text("foreign state")
        self.unit.symlink_to(target)
        p = self.run_update()
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(target.read_text(), "foreign state")

    def test_fresh_install_repair_renderer_uses_complete_unit(self):
        # Exercises the actual shared installer repair code, not a copied renderer.
        # Full one-click bootstrap/systemd admission remains a separate real proof.
        source = (REPO / "install.sh").read_text()
        start = source.index("    # >>> ingress-unit-repair")
        end = source.index("    # <<< ingress-unit-repair", start)
        work = self.root / "work"
        work.mkdir()
        script = self.root / "fresh-unit.sh"
        script.write_text("set -eu\nTMP="+shlex.quote(str(work))+"\n"+
                          self.rooted(source[start:end])+"\nrepair_ingress_unit\n")
        env = dict(os.environ, PATH=str(self.root / "shim")+os.pathsep+os.environ.get("PATH", ""))
        p = subprocess.run(["sh", str(script)], env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stdout+p.stderr)
        self.assert_complete()


if __name__ == "__main__":
    unittest.main()
