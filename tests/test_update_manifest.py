"""Run with python3 -m unittest discover -s tests on Linux."""
import base64, hashlib, json, os, pathlib, shutil, subprocess, tempfile, unittest
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / 'update.sh').read_text()
VERIFY_BLOCK = SCRIPT[SCRIPT.index('    # >>> manifest-verify'):SCRIPT.index('    # <<< manifest-verify')]
DOMAIN = b"impreza-agent-release-v1\x00"
SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")
PKCS8_PREFIX = bytes.fromhex("302e020100300506032b657004220420")

# RFC 8032 section 7.1 test vectors (public data): the Python verifier
# shipped for OpenSSL 1.1.1 hosts must accept these before anything else.
RFC8032_VECTORS = [
    (
        "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60",
        "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a",
        "",
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b",
    ),
    (
        "4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb",
        "3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c",
        "72",
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00",
    ),
    (
        "c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7",
        "fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025",
        "af82",
        "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a",
    ),
]

P = 2**255 - 19
Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, P - 2, P) % P


def _inv(x):
    return pow(x, P - 2, P)


def _padd(Ph, Qh):
    A = (Ph[1] - Ph[0]) * (Qh[1] - Qh[0]) % P
    B = (Ph[1] + Ph[0]) * (Qh[1] + Qh[0]) % P
    C = 2 * Ph[3] * Qh[3] * _D % P
    D = 2 * Ph[2] * Qh[2] % P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % P, G * H % P, F * G % P, E * H % P)


def _pmul(s, Ph):
    Qh = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Qh = _padd(Qh, Ph)
        Ph = _padd(Ph, Ph)
        s >>= 1
    return Qh


def _pcompress(Ph):
    zinv = _inv(Ph[2])
    x = Ph[0] * zinv % P
    y = Ph[1] * zinv % P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _pdecompress(s):
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= P:
        return None
    u = (y * y - 1) % P
    v = (_D * y * y + 1) % P
    x = pow(u * _inv(v), (P + 3) // 8, P)
    if (x * x - u * _inv(v)) % P != 0:
        x = x * pow(2, (P - 1) // 4, P) % P
    if (x * x - u * _inv(v)) % P != 0:
        return None
    if x == 0 and sign:
        return None
    if x & 1 != sign:
        x = P - x
    return (x, y, 1, x * y % P)


_BASE_POINT = _pdecompress(bytes.fromhex("5866666666666666666666666666666666666666666666666666666666666666"))


def python_ed25519_sign(seed, message):
    """Test-side RFC 8032 signer: used when the host openssl cannot sign
    with -rawin (1.1.1), so the suite signs envelopes there too."""
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= (1 << 254)
    prefix = h[32:]
    big_a = _pcompress(_pmul(a, _BASE_POINT))
    r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little") % Q
    r_point = _pcompress(_pmul(r, _BASE_POINT))
    k = int.from_bytes(hashlib.sha512(r_point + big_a + message).digest(), "little") % Q
    s = (r + k * a) % Q
    return r_point + int.to_bytes(s, 32, "little")


def write_verify_py(directory):
    """Materialize the verifier heredoc exactly as update.sh ships it."""
    start = SCRIPT.index("cat > \"$3/verify.py\" <<'PYMANIFEST'")
    body_start = SCRIPT.index("\n", start) + 1
    body_end = SCRIPT.index("\nPYMANIFEST", body_start)
    path = os.path.join(directory, 'verify.py')
    with open(path, 'w', newline='\n') as handle:
        handle.write(SCRIPT[body_start:body_end] + "\n")
    return path


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
        self.seed = seed
        self.private_pem = os.path.join(directory, 'key.pem')
        subprocess.run(['openssl', 'pkey', '-inform', 'DER', '-in', der_path, '-out', self.private_pem], check=True, capture_output=True)
        pub_der = subprocess.run(['openssl', 'pkey', '-in', self.private_pem, '-pubout', '-outform', 'DER'], check=True, capture_output=True).stdout
        self.public_b64 = base64.b64encode(pub_der[-32:]).decode()

    def sign(self, message):
        # OpenSSL 1.1.1 cannot sign with -rawin either; the test-side
        # RFC 8032 signer covers those hosts (an openssl 3 host still
        # exercises the openssl signer first).
        message_path = os.path.join(self.directory, 'msg.bin')
        signature_path = os.path.join(self.directory, 'sig.bin')
        with open(message_path, 'wb') as handle:
            handle.write(message)
        proc = subprocess.run(['openssl', 'pkeyutl', '-sign', '-inkey', self.private_pem, '-rawin',
                               '-in', message_path, '-out', signature_path], capture_output=True)
        if proc.returncode == 0:
            with open(signature_path, 'rb') as handle:
                return handle.read()
        signature = python_ed25519_sign(self.seed, message)
        with open(signature_path, 'wb') as handle:
            handle.write(signature)
        return signature


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


class PythonEd25519Verifier(unittest.TestCase):
    """The RFC 8032 verifier shipped inside update.sh for OpenSSL 1.1.1
    hosts, tested directly: the standard vectors first, then the same
    refusals the openssl path must produce."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.verify_py = write_verify_py(self._tmp.name)

    def run_ed25519(self, public, message, signature):
        work = tempfile.mkdtemp(dir=self._tmp.name)
        paths = []
        for name, data in (('pub.der', public), ('msg.bin', message), ('sig.bin', signature)):
            path = os.path.join(work, name)
            with open(path, 'wb') as handle:
                handle.write(data)
            paths.append(path)
        return subprocess.run([real_python3(), self.verify_py, 'ed25519'] + paths,
                              capture_output=True, text=True)

    def test_rfc8032_vectors_accepted(self):
        for _, pub, msg, sig in RFC8032_VECTORS:
            with self.subTest(msg=msg):
                proc = self.run_ed25519(SPKI_PREFIX + bytes.fromhex(pub),
                                        bytes.fromhex(msg), bytes.fromhex(sig))
                self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_rfc8032_vector_signature_byte_flips_refused(self):
        _, pub, msg, sig = RFC8032_VECTORS[1]
        raw = bytearray(bytes.fromhex(sig))
        for position in (0, 31, 32, 63):
            with self.subTest(position=position):
                flipped = bytearray(raw)
                flipped[position] ^= 0x01
                proc = self.run_ed25519(SPKI_PREFIX + bytes.fromhex(pub),
                                        bytes.fromhex(msg), bytes(flipped))
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn('signature verification failed', proc.stderr)

    def test_tampered_message_refused(self):
        _, pub, msg, sig = RFC8032_VECTORS[2]
        proc = self.run_ed25519(SPKI_PREFIX + bytes.fromhex(pub),
                                bytes.fromhex(msg) + b'\x00', bytes.fromhex(sig))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('signature verification failed', proc.stderr)

    def test_noncanonical_scalar_refused(self):
        # S >= q must be rejected even though the encoding is 32 bytes.
        _, pub, msg, sig = RFC8032_VECTORS[0]
        signature = bytearray(bytes.fromhex(sig))
        signature[32:] = (Q + 1).to_bytes(32, 'little')
        proc = self.run_ed25519(SPKI_PREFIX + bytes.fromhex(pub),
                                bytes.fromhex(msg), bytes(signature))
        self.assertNotEqual(proc.returncode, 0)

    def test_malformed_trust_key_refused(self):
        _, pub, msg, sig = RFC8032_VECTORS[0]
        for spki in (b'', b'\x30' * 44, SPKI_PREFIX + b'\x00' * 31, SPKI_PREFIX + b'\x00' * 33):
            with self.subTest(len=len(spki)):
                proc = self.run_ed25519(spki, bytes.fromhex(msg), bytes.fromhex(sig))
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn('trust key', proc.stderr)

    def test_all_zero_trust_key_is_a_signature_failure_not_a_shape_failure(self):
        # A well-formed SPKI wrapping 32 zero bytes parses as a key shape;
        # verification must refuse it as a signature, not as a key error.
        _, _, msg, sig = RFC8032_VECTORS[0]
        proc = self.run_ed25519(SPKI_PREFIX + b'\x00' * 32, bytes.fromhex(msg), bytes.fromhex(sig))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('signature verification failed', proc.stderr)

    def test_python_signer_matches_rfc_vectors(self):
        # The test-side signer is held to the RFC vectors too, so the
        # envelopes it builds on OpenSSL 1.1.1 hosts are well formed.
        for seed_hex, _, msg_hex, sig_hex in RFC8032_VECTORS:
            with self.subTest(seed=seed_hex[:8]):
                signature = python_ed25519_sign(bytes.fromhex(seed_hex), bytes.fromhex(msg_hex))
                self.assertEqual(signature.hex(), sig_hex)


class UpdateManifestDispatch(unittest.TestCase):
    """Which verifier runs, and what a refusal says, per openssl version."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.key = Key(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def openssl_without_rawin(self):
        """A stand-in for OpenSSL 1.1.1: no -rawin anywhere, and it records
        every call so the test proves the fallback never asked it to
        verify."""
        bin_dir = os.path.join(self._tmp.name, 'openssl1.1.1')
        os.makedirs(bin_dir, exist_ok=True)
        opensslexe = 'openssl.exe' if os.name == 'nt' else 'openssl'
        shim = os.path.join(bin_dir, opensslexe)
        log = os.path.join(self._tmp.name, 'openssl.calls')
        with open(shim, 'w', newline='\n') as handle:
            handle.write('#!/bin/sh\necho "$*" >> %s\n'
                         'case " $* " in *" -rawin "*) echo "Unknown option: -rawin" >&2; exit 1;; esac\n'
                         'case " $* " in *" -help "*) echo "Usage: pkeyutl [options]"; exit 0;; esac\n'
                         'exit 1\n' % log.replace('\\', '/'))
        os.chmod(shim, 0o755)
        return bin_dir, log

    def openssl3_with_failing_verify(self, message):
        """Answers -help with -rawin present (OpenSSL 3) but fails the
        verify with a distinctive stderr line, the cause the refusal must
        carry instead of hiding it. The key conversion succeeds: the
        failure under test is the signature check."""
        bin_dir = os.path.join(self._tmp.name, 'openssl3-broken')
        os.makedirs(bin_dir, exist_ok=True)
        opensslexe = 'openssl.exe' if os.name == 'nt' else 'openssl'
        shim = os.path.join(bin_dir, opensslexe)
        with open(shim, 'w', newline='\n') as handle:
            handle.write('#!/bin/sh\n'
                         'case " $* " in *" -help "*) echo "Usage: pkeyutl -rawin ..."; exit 0;; esac\n'
                         'case " $* " in *" pkey "*) exit 0;; esac\n'
                         'case " $* " in *" pkeyutl "*) echo "%s" >&2; exit 1;; esac\n'
                         'exit 1\n' % message)
        os.chmod(shim, 0o755)
        return bin_dir

    def run_verify(self, envelope_bytes, bin_dir=None):
        work = tempfile.mkdtemp(dir=self._tmp.name)
        env_path = os.path.join(work, 'manifest.signed.json')
        with open(env_path, 'wb') as handle:
            handle.write(envelope_bytes)
        state_path = os.path.join(work, 'state.json')
        out_dir = os.path.join(work, 'out')
        os.mkdir(out_dir)
        # A real python3 shim on PATH, ahead of the fake-openssl directory:
        # a shell function would not receive the verifier's environment
        # prefixes on POSIX sh (dash exports them only for commands).
        interpreter = shutil.which(real_python3()) or real_python3()
        py_dir = os.path.join(work, 'pybin')
        os.makedirs(py_dir, exist_ok=True)
        py_name = 'python3.exe' if os.name == 'nt' else 'python3'
        with open(os.path.join(py_dir, py_name), 'w', newline='\n') as handle:
            handle.write('#!/bin/sh\nexec "%s" "$@"\n' % interpreter)
        os.chmod(os.path.join(py_dir, py_name), 0o755)
        harness = "%s\nCHANNEL='stable'\nARCH='amd64'\nverify_manifest '%s' '%s' '%s'\n echo RC:$?\n" % (
            VERIFY_BLOCK, env_path, state_path, out_dir)
        env = dict(os.environ)
        env['IMPREZA_RELEASE_PUBLIC_KEY'] = self.key.public_b64
        prefix = py_dir + os.pathsep + (bin_dir + os.pathsep if bin_dir else '')
        env['PATH'] = prefix + os.environ.get('PATH', '')
        harness_path = os.path.join(work, 'harness.sh')
        with open(harness_path, 'w', newline='') as handle:
            handle.write(harness)
        return subprocess.run(['sh', harness_path], capture_output=True, text=True, env=env)

    def test_valid_manifest_verifies_without_rawin_openssl(self):
        bin_dir, log = self.openssl_without_rawin()
        proc = self.run_verify(build_envelope(self.key, valid_payload()), bin_dir=bin_dir)
        self.assertIn('RC:0', proc.stdout, proc.stderr)
        calls = open(log).read() if os.path.exists(log) else ''
        self.assertIn('-help', calls)
        self.assertNotIn('-rawin -', calls.replace('Unknown option: -rawin', ''))

    def test_tampered_payload_refused_without_rawin_openssl(self):
        bin_dir, _ = self.openssl_without_rawin()
        envelope = json.loads(build_envelope(self.key, valid_payload()))
        payload = base64.b64decode(envelope['payload']).decode().replace('0.6.20', '9.9.9')
        envelope['payload'] = base64.b64encode(payload.encode()).decode()
        proc = self.run_verify(json.dumps(envelope).encode(), bin_dir=bin_dir)
        self.assertNotIn('RC:0', proc.stdout)
        self.assertIn('signature verification failed', proc.stderr + proc.stdout)

    def test_swapped_signature_refused_without_rawin_openssl(self):
        # A genuine signature — of a different manifest — must not verify
        # here: the check binds the signature to these exact bytes.
        bin_dir, _ = self.openssl_without_rawin()
        envelope = json.loads(build_envelope(self.key, valid_payload()))
        other = valid_payload(version='0.6.21')
        other_bytes = json.dumps(other, separators=(',', ':')).encode()
        envelope['signature'] = base64.b64encode(self.key.sign(DOMAIN + other_bytes)).decode()
        proc = self.run_verify(json.dumps(envelope).encode(), bin_dir=bin_dir)
        self.assertNotIn('RC:0', proc.stdout)
        self.assertIn('signature verification failed', proc.stderr + proc.stdout)

    def test_fallback_says_why_it_engaged(self):
        # The capability gap is said out loud, on stdout (the caller only
        # shows verify_manifest's stderr on refusal); the real signature
        # failure keeps its own clear message.
        bin_dir, _ = self.openssl_without_rawin()
        proc = self.run_verify(build_envelope(self.key, valid_payload()), bin_dir=bin_dir)
        self.assertIn('RC:0', proc.stdout, proc.stderr)
        self.assertIn('this OpenSSL has no raw Ed25519 support', proc.stdout)
        envelope = json.loads(build_envelope(self.key, valid_payload()))
        payload = base64.b64decode(envelope['payload']).decode().replace('0.6.20', '9.9.9')
        envelope['payload'] = base64.b64encode(payload.encode()).decode()
        proc = self.run_verify(json.dumps(envelope).encode(), bin_dir=bin_dir)
        self.assertNotIn('RC:0', proc.stdout)
        output = proc.stderr + proc.stdout
        self.assertIn('this OpenSSL has no raw Ed25519 support', output)
        self.assertIn('signature verification failed', output)

    def test_openssl_failure_reports_the_cause(self):
        bin_dir = self.openssl3_with_failing_verify('Error: mock signature engine failure XYZ')
        proc = self.run_verify(build_envelope(self.key, valid_payload()), bin_dir=bin_dir)
        self.assertNotIn('RC:0', proc.stdout)
        output = proc.stderr + proc.stdout
        self.assertIn('signature verification failed', output)
        self.assertIn('mock signature engine failure XYZ', output)

    def test_key_conversion_failure_reports_the_cause(self):
        bin_dir = self.openssl3_with_failing_verify('unused')
        # pkey conversion also fails distinctly: make -help pass but the
        # pkey call fail with its own message.
        shim = os.path.join(bin_dir, 'openssl.exe' if os.name == 'nt' else 'openssl')
        with open(shim, 'w', newline='\n') as handle:
            handle.write('#!/bin/sh\n'
                         'case " $* " in *" -help "*) echo "Usage: pkeyutl -rawin ..."; exit 0;; esac\n'
                         'case " $* " in *" pkey "*) echo "Error: mock key parse failure K3Y" >&2; exit 1;; esac\n'
                         'exit 1\n')
        os.chmod(shim, 0o755)
        proc = self.run_verify(build_envelope(self.key, valid_payload()), bin_dir=bin_dir)
        self.assertNotIn('RC:0', proc.stdout)
        output = proc.stderr + proc.stdout
        self.assertIn('trust key unusable', output)
        self.assertIn('mock key parse failure K3Y', output)


if __name__ == '__main__':
    unittest.main()
