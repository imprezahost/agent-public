"""Run with python3 -m unittest discover -s tests on Linux."""
import hashlib, pathlib, subprocess, tempfile, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/'update.sh').read_text()
PARSER=SCRIPT[SCRIPT.index('    read_metadata() {'):SCRIPT.index('    if [ -n "${IMPREZA_AGENT_VERSION:-}" ]')]
class ReleaseMetadata(unittest.TestCase):
 def parse(self,data,kind):
  with tempfile.NamedTemporaryFile() as f:
   f.write(data);f.flush()
   return subprocess.run(['sh','-c',PARSER+'\nread_metadata "$1" "$2"','fixture',f.name,kind],capture_output=True)
 def test_version_line_endings(self):
  for ending in [b'',b'\n',b'\r\n']:
   with self.subTest(ending=ending):
    p=self.parse(b'0.6.16'+ending,'version');self.assertEqual(p.returncode,0);self.assertEqual(p.stdout,b'0.6.16\n')
 def test_checksum_line_endings(self):
  for ending in [b'',b'\n',b'\r\n']:
   p=self.parse(b'a'*64+ending,'checksum');self.assertEqual(p.returncode,0);self.assertEqual(p.stdout,b'a'*64+b'\n')
 def test_malformed_versions(self):
  for data in [b'',b'\n',b'\xef\xbb\xbf0.6.16\n',b' 0.6.16\n',b'0.6.16 \n',b'0.6.16\nother\n',b'other\n0.6.16\n',b'0.6.16\n\n',b'0.\r6.16\n',b'0.6.16\r\r\n',b'0.6.16\x00\n',b'../0.6.16',b'0.6.16/../../other',b'0.6.16;echo x',b'$(id)',b'0.6',b'v0.6.16']:
   with self.subTest(data=data):self.assertNotEqual(self.parse(data,'version').returncode,0)
 def test_malformed_checksums(self):
  for data in [b'',b'a'*63,b'a'*65,b'A'*64,b'a'*64+b'\n'+b'b'*64,b'a'*64+b'\n\n',b'a'*64+b' file',b'a'*30+b'\r'+b'a'*34,b'a'*64+b'\x00']:
   with self.subTest(data=data):self.assertNotEqual(self.parse(data,'checksum').returncode,0)
 def test_release_metadata_bytes(self):
  for p in (ROOT/'releases').rglob('*'):
   if not p.is_file() or not (p.name=='version.txt' or p.suffix=='.sha256'):continue
   raw=p.read_bytes();self.assertNotIn(b'\r',raw,str(p));self.assertEqual(self.parse(raw,'version' if p.name=='version.txt' else 'checksum').returncode,0,str(p))
 def test_stable_artifacts(self):
  base=ROOT/'releases/stable';version=(base/'version.txt').read_text().strip()
  for arch in ['amd64','arm64']:
   name='impreza-agent-linux-'+arch
   for location in [version,'latest']:
    p=base/location/name;self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),p.with_suffix('.sha256').read_text().strip())
if __name__=='__main__':unittest.main()
