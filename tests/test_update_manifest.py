"""Run with python3 -m unittest discover -s tests on Linux."""
import base64, hashlib, json, os, pathlib, subprocess, tempfile, unittest
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'update.sh').read_text()
VERIFY_BLOCK = SCRIPT[SCRIPT.index('    # >>> manifest-verify'):SCRIPT.index('    # <<< manifest-verify')]
DOMAIN = b"impreza-agent-release-v1\x00"
SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
PKCS8_PREFIX = bytes.fromhex("302e020100300506032b657004220420")


def real_python3():
    """Return a working python3 executable, shimming the Windows Store stub."""
    for candidate in ['python3', 'python']:
        try:
            proc = subprocess.run([candidate, '--version'], capture_output=True, text=True)
            if proc.returncode == 0 and 'Python' in (proc.stdout + proc.stderr):
                return candidate
        except OSError:
            continue
    raise RuntimeError('no python interpreter found')


def python3_shim(directory):
    """On hosts where python3 is a broken stub, wrap the real interpreter."""
    if os.name != 'nt':
        return None
    shim_dir = os.path.join(directory, 'shim')
    os.makedirs(shim_dir, exist_ok=True)
    shim = os.path.join(shim_dir, 'python3')
    interpreter = subprocess.run(['where', 'python'], capture_output=True, text=True).stdout.splitlines()
    target = interpreter[0].strip() if interpreter else None
    if not target:
        return None
    with open(shim, 'w') as handle:
        handle.write('#!/bin/sh\nexec "%s" "$@"\n' % target.replace('\\', '/'))
    return shim_dir


class Key:
    def __init__(self, directory):
        self.directory = directory
        seed = os.urandom(32)
        der = PKCS8_PREFIX + seed
        der_path = os.path.join(directory, 'key.der')
        with open(der_path, 'wb') as handle:
            handle.write(der)
        self.private_pem = os.path.join(directory, 'key.pem')
        subprocess.run(['openssl', 'pkey', '-inform', 'DER', '-in', der_path, '-out', self.private_pem], check=True, capture_output=True)
        pub_der = subprocess.run(['openssl', 'pkey', '-in', self.private_pem, '-pubout', '-outform', 'DER'], check=True, capture_output=True).stdout
        self.public_b64 = base64.b64encode(pub_der[-32:]).decode()

    def sign(self, message):
        message_path = os.path.join(self.directory, 'msg.bin')
        signature_path = os.path.join(self.directory, 'sig.bin')
        with open(message_path, 'wb') as handle:
            handle.write(message)
        subprocess.run(['openssl', 'pkeyutl', '-sign', '-inkey', self.private_pem, '-rawin',
                        '-in', message_path, '-out', signature_path], check=True, capture_output=True)
        with open(signature_path, 'rb') as handle:
            return handle.read()


def build_envelope(key, payload_dict):
    payload = json.dumps(payload_dict, separators=(',', ':')).encode()
    signature = key.sign(DOMAIN + payload)
    return json.dumps({"format": 1, "payload": base64.b64encode(payload).decode(), "signature": base64.b64encode(signature).decode()}, separators=(',', ':')).encode()


def valid_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "schema": 1,
        "channel": "stable",
        "version": "0.6.20",
        "seq": 1,
        "previous": None,
        "released_at": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "expires_at": (now + timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        "min_agent_version": "0.6.0",
        "artifacts": {
            "amd64": {"name": "impreza-agent-linux-amd64", "sha256": 'a' * 64, "size": 12345},
            "arm64": {"name": "impreza-agent-linux-arm64", "sha256": 'c' * 64, "size": 12346},
        },
    }
    payload.update(overrides)
    return payload


class UpdateManifestVerification(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.key = Key(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def run_verify(self, envelope_bytes, state=None, channel='stable', arch='amd64', key_b64=None):
        work = tempfile.mkdtemp(dir=self._tmp.name)
        env_path = os.path.join(work, 'manifest.signed.json')
        with open(env_path, 'wb') as handle:
            handle.write(envelope_bytes)
        state_path = os.path.join(work, 'state.json')
        if state is not None:
            with open(state_path, 'w') as handle:
                json.dump(state, handle)
        out_dir = os.path.join(work, 'out')
        os.mkdir(out_dir)
        harness = "%s\nCHANNEL='%s'\nARCH='%s'\nverify_manifest '%s' '%s' '%s'\n echo RC:$?\n" % (
            VERIFY_BLOCK, channel, arch, env_path, state_path, out_dir)
        env = dict(os.environ)
        env['IMPREZA_RELEASE_PUBLIC_KEY'] = key_b64 or self.key.public_b64
        shim_dir = python3_shim(self._tmp.name)
        if shim_dir:
            env['PATH'] = shim_dir + os.pathsep + env['PATH']
        # A file, not sh -c: on Windows the command line is re-quoted by
        # list2cmdline and the MSYS runtime, which can mangle the heredoc.
        harness_path = os.path.join(work, 'harness.sh')
        with open(harness_path, 'w', newline='') as handle:
            handle.write(harness)
        proc = subprocess.run(['sh', harness_path], capture_output=True, text=True, env=env)
        verified = {}
        verified_path = os.path.join(out_dir, 'verified.env')
        if os.path.exists(verified_path):
            for line in pathlib.Path(verified_path).read_text().splitlines():
                name, _, value = line.partition('=')
                verified[name] = value
        return proc, verified, out_dir

    def test_valid_manifest_passes(self):
        proc, verified, out_dir = self.run_verify(build_envelope(self.key, valid_payload()))
        self.assertIn('RC:0', proc.stdout, proc.stderr)
        self.assertEqual(verified.get('MANIFEST_VERSION'), '0.6.20')
        self.assertEqual(verified.get('MANIFEST_SHA256'), 'a' * 64)
        self.assertEqual(verified.get('MANIFEST_MIN_AGENT'), '0.6.0')
        state = json.loads(pathlib.Path(os.path.join(out_dir, 'state.candidate.json')).read_text())
        self.assertEqual(state['seq'], 1)
        self.assertEqual(state['channel'], 'stable')

    def test_tampered_payload_refused(self):
        envelope = json.loads(build_envelope(self.key, valid_payload()))
        payload = base64.b64decode(envelope['payload']).decode()
        payload = payload.replace('0.6.20', '9.9.9')
        envelope['payload'] = base64.b64encode(payload.encode()).decode()
        proc, verified, _ = self.run_verify(json.dumps(envelope).encode())
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('signature', proc.stderr + proc.stdout)

    def test_signature_by_other_key_refused(self):
        other = Key(tempfile.mkdtemp(dir=self._tmp.name))
        proc, _, _ = self.run_verify(build_envelope(other, valid_payload()))
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)

    def test_expired_manifest_refused(self):
        now = datetime.now(timezone.utc)
        payload = valid_payload(
            released_at=(now - timedelta(days=8)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            expires_at=(now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        proc, _, _ = self.run_verify(build_envelope(self.key, payload))
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('expired', proc.stderr + proc.stdout)

    def test_future_release_refused(self):
        now = datetime.now(timezone.utc)
        payload = valid_payload(
            released_at=(now + timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            expires_at=(now + timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        proc, _, _ = self.run_verify(build_envelope(self.key, payload))
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('future', proc.stderr + proc.stdout)

    def test_validity_window_capped(self):
        now = datetime.now(timezone.utc)
        payload = valid_payload(expires_at=(now + timedelta(days=9)).strftime('%Y-%m-%dT%H:%M:%SZ'))
        proc, _, _ = self.run_verify(build_envelope(self.key, payload))
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('validity', proc.stderr + proc.stdout)

    def test_channel_mismatch_refused(self):
        proc, _, _ = self.run_verify(build_envelope(self.key, valid_payload(channel='beta')))
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('channel', proc.stderr + proc.stdout)

    def test_state_rollback_refused(self):
        proc, _, _ = self.run_verify(
            build_envelope(self.key, valid_payload(seq=2, previous='f' * 64)),
            state={"seq": 5, "envelope_sha256": 'e' * 64, "version": "0.6.21", "channel": "stable"})
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('rollback', proc.stderr + proc.stdout)

    def test_state_equivocation_refused(self):
        envelope = build_envelope(self.key, valid_payload(seq=4, previous='f' * 64))
        digest = hashlib.sha256(envelope).hexdigest()
        proc, _, _ = self.run_verify(
            envelope,
            state={"seq": 4, "envelope_sha256": 'e' * 64, "version": "0.6.20", "channel": "stable"})
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('equivocation', proc.stderr + proc.stdout)
        self.assertNotEqual(digest, 'e' * 64)

    def test_state_allows_forward_sequence(self):
        envelope = build_envelope(self.key, valid_payload(seq=7, previous='f' * 64))
        digest = hashlib.sha256(envelope).hexdigest()
        proc, _, _ = self.run_verify(
            envelope,
            state={"seq": 5, "envelope_sha256": 'e' * 64, "version": "0.6.19", "channel": "stable"})
        self.assertIn('RC:0', proc.stdout, proc.stderr)

    def test_tampered_payload_is_refused_by_the_signature_first(self):
        # A forged manifest that would also break the chain and the expiry
        # rules is refused by the signature, before any of its fields is
        # interpreted: the refusal says nothing about the local chain state.
        state = {"seq": 5, "envelope_sha256": 'e' * 64, "version": "0.6.19", "channel": "stable"}
        envelope = json.loads(build_envelope(self.key, valid_payload(seq=6, previous='e' * 64)))
        forged = json.loads(base64.b64decode(envelope['payload']))
        forged.update(seq=6, previous='f' * 64, expires_at='2020-01-01T00:00:00Z')
        envelope['payload'] = base64.b64encode(json.dumps(forged, separators=(',', ':')).encode()).decode()
        proc, verified, out_dir = self.run_verify(json.dumps(envelope).encode(), state=state)
        output = proc.stderr + proc.stdout
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('signature verification failed', output)
        for semantic in ('predecessor', 'expired', 'rollback', 'equivocation'):
            self.assertNotIn(semantic, output)
        self.assertEqual(verified, {})
        self.assertFalse(os.path.exists(os.path.join(out_dir, 'state.candidate.json')))

    def test_adjacent_sequence_requires_saved_predecessor(self):
        state = {"seq": 5, "envelope_sha256": 'e' * 64, "version": "0.6.19", "channel": "stable"}
        wrong = build_envelope(self.key, valid_payload(seq=6, previous='f' * 64))
        proc, _, _ = self.run_verify(wrong, state=state)
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('predecessor mismatch', proc.stderr + proc.stdout)
        right = build_envelope(self.key, valid_payload(seq=6, previous='e' * 64))
        proc, _, _ = self.run_verify(right, state=state)
        self.assertIn('RC:0', proc.stdout, proc.stderr)

    def test_state_allows_same_sequence_same_digest(self):
        envelope = build_envelope(self.key, valid_payload(seq=3, previous='f' * 64))
        digest = hashlib.sha256(envelope).hexdigest()
        proc, _, _ = self.run_verify(
            envelope,
            state={"seq": 3, "envelope_sha256": digest, "version": "0.6.20", "channel": "stable"})
        self.assertIn('RC:0', proc.stdout, proc.stderr)

    def test_malformed_shapes_refused(self):
        cases = [
            b'',
            b'{}',
            b'not json',
            json.dumps({"format": 2, "payload": "", "signature": ""}).encode(),
            json.dumps({"format": 1, "payload": "!!!!", "signature": "AAAA"}).encode(),
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                proc, _, _ = self.run_verify(raw)
                self.assertNotIn('RC:0', proc.stdout, proc.stderr)

    def test_unknown_payload_fields_refused(self):
        payload = valid_payload()
        payload['surprise'] = 1
        proc, _, _ = self.run_verify(build_envelope(self.key, payload))
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('payload shape', proc.stderr + proc.stdout)

    def test_artifact_rules_enforced(self):
        cases = [
            valid_payload(artifacts={"amd64": {"name": "wrong", "sha256": 'a' * 64, "size": 10}}),
            valid_payload(artifacts={"amd64": {"name": "impreza-agent-linux-amd64", "sha256": 'A' * 64, "size": 10}}),
            valid_payload(artifacts={"amd64": {"name": "impreza-agent-linux-amd64", "sha256": 'a' * 64, "size": 0}}),
            valid_payload(artifacts={}),
            valid_payload(version='0.6'),
            valid_payload(min_agent_version='latest'),
            valid_payload(seq=0),
        ]
        for payload in cases:
            with self.subTest(version=payload['version'], seq=payload['seq']):
                proc, _, _ = self.run_verify(build_envelope(self.key, payload))
                self.assertNotIn('RC:0', proc.stdout, proc.stderr)

    def test_missing_arch_artifact_refused(self):
        proc, _, _ = self.run_verify(build_envelope(self.key, valid_payload()), arch='riscv64')
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('architecture', proc.stderr + proc.stdout)

    def test_pinned_production_key_still_decodable(self):
        # The default pinned key must be a valid raw Ed25519 public key;
        # verification with it must fail only on signature, not on key shape.
        pinned = "HismnHv7rcB/AWSrzalz/+c3t921VQ1gmHVJlNx0gfQ="
        proc, _, _ = self.run_verify(build_envelope(self.key, valid_payload()), key_b64=pinned)
        self.assertNotIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('signature verification failed', proc.stderr + proc.stdout)
        decoded = base64.b64decode(pinned)
        self.assertEqual(len(decoded), 32)
        # The DER wrapper the script builds must be accepted by openssl.
        with tempfile.NamedTemporaryFile(suffix='.der', delete=False) as handle:
            handle.write(SPKI_PREFIX + decoded)
            der = handle.name
        try:
            result = subprocess.run(['openssl', 'pkey', '-pubin', '-inform', 'DER', '-in', der], capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        finally:
            os.unlink(der)


if __name__ == '__main__':
    unittest.main()
