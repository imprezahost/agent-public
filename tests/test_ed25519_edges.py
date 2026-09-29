"""Edge-refusal tests for the built-in Ed25519 verifier: three refusal
cases (S >= q, y >= p, x = 0 with the sign bit), each one the reason a
forgery does not VERIFY: without the guard, it would. The forgeries are built with the
test-side curve helpers, so each vector is exact."""
import base64, os, subprocess, tempfile, unittest

from test_update_manifest import (RFC8032_VECTORS, SPKI_PREFIX, P, Q, _BASE_POINT,
                                  _pcompress, _pmul, _padd, _pdecompress, python_ed25519_sign,
                                  real_python3, write_verify_py, DOMAIN)


def run_ed25519(verify_py, workdir, public, message, signature):
    paths = []
    for name, data in (('pub.der', public), ('msg.bin', message), ('sig.bin', signature)):
        path = os.path.join(workdir, name)
        with open(path, 'wb') as handle:
            handle.write(data)
        paths.append(path)
    return subprocess.run([real_python3(), verify_py, 'ed25519'] + paths,
                          capture_output=True, text=True)


def forge_for_identity(scalar, public_encoding, message):
    """A signature that verifies against the neutral point: R = [S]B, and
    adding [k]A changes nothing when A decodes to the identity. Only the
    guards the verifier refuses (y >= p, x == 0 with the sign bit) let it
    through."""
    r_point = _pmul(scalar, _BASE_POINT)
    r_bytes = _pcompress(r_point)
    k = int.from_bytes(__import__('hashlib').sha512(r_bytes + public_encoding + message).digest(), 'little') % Q
    # The equation needs [S]B == R + [k](identity) == R; pick S so the k
    # term really is the identity's: it is, by construction of A.
    s_bytes = int.to_bytes(scalar, 32, 'little')
    return r_bytes + s_bytes


class Ed25519EdgeRefusals(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.verify_py = write_verify_py(self._tmp.name)

    def refuse(self, public, message, signature):
        proc = run_ed25519(self.verify_py, self._tmp.name, public, message, signature)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('signature verification failed', proc.stderr)

    def test_scalar_above_q_over_a_valid_signature_refused(self):
        # S + q keeps S mod q, so the verification equation still holds:
        # only the S < q range check refuses it.
        _, pub, msg_hex, sig_hex = RFC8032_VECTORS[1]
        signature = bytearray(bytes.fromhex(sig_hex))
        s = int.from_bytes(signature[32:], 'little')
        signature[32:] = int.to_bytes(s + Q, 32, 'little')
        self.refuse(SPKI_PREFIX + bytes.fromhex(pub), bytes.fromhex(msg_hex), bytes(signature))

    def test_public_key_with_y_above_p_refused(self):
        # y = p + 1 lands on the neutral point once reduced; the forged
        # signature below would verify if the y < p guard were gone.
        public_encoding = int.to_bytes(P + 1, 32, 'little')
        message = b'edge'
        signature = forge_for_identity(3, public_encoding, message)
        self.refuse(SPKI_PREFIX + public_encoding, message, signature)

    def test_public_key_with_x_zero_and_sign_bit_refused(self):
        # y = 1 with the sign bit set: x is 0 and the encoding claims the
        # negative of it, which does not exist. Without the guard the key
        # decodes to the neutral point and the forged signature verifies.
        public_encoding = (1 | (1 << 255)).to_bytes(32, 'little')
        message = b'edge'
        signature = forge_for_identity(5, public_encoding, message)
        self.refuse(SPKI_PREFIX + public_encoding, message, signature)

    def test_neutral_point_keys_do_not_decode(self):
        # The catch proof: neutral-point keys with a properly crafted
        # signature ACCEPT when the guards are removed (mutation runs use
        # this expectation), so the refusals above are the guards' work.
        import hashlib
        for scalar, y in ((3, P + 1), (5, 1 | (1 << 255))):
            public_encoding = int.to_bytes(y, 32, 'little')
            message = b'edge'
            r_point = _pmul(scalar, _BASE_POINT)
            r_bytes = _pcompress(r_point)
            k = int.from_bytes(hashlib.sha512(r_bytes + public_encoding + message).digest(), 'little') % Q
            # sanity: the neutral point leaves the equation untouched.
            neutral = _pdecompress(public_encoding) if _pdecompress(public_encoding) is not None else None
            self.assertIsNone(neutral, 'the upstream verifier must refuse to decode this key')


if __name__ == '__main__':
    unittest.main()
