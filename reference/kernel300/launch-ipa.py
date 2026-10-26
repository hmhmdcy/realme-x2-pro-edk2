"""Upload and launch the private, opt-in candidate once on the guarded boot."""
from pathlib import Path
import base64,hashlib,json,re,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
bundle=json.loads((HERE/'ipa-bundle-validation.json').read_text());archive=P/bundle['archive_file']
run=sys.argv[1] if len(sys.argv)>1 else 'r1';assert re.fullmatch(r'r[1-9][0-9]*',run)
assert hashlib.sha256(archive.read_bytes()).hexdigest()==bundle['archive_sha256']
mode=sys.argv[2] if len(sys.argv)>2 else 'isolated';assert mode in ['isolated','direct']
force='1' if mode=='isolated' else '0'
code=f'''
from pathlib import Path
import hashlib,io,json,os,subprocess,sys,tarfile
root=Path('/var/lib/samurai/k300-ipa-{run}');assert not root.exists()
raw=sys.stdin.buffer.read();assert hashlib.sha256(raw).hexdigest()=={bundle['archive_sha256']!r}
expected={bundle['files']!r}
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
 assert set(tar.getnames())==set(expected)
 for item in tar.getmembers():
  assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
  b=tar.extractfile(item).read();assert len(b)==expected[item.name]['bytes'] and hashlib.sha256(b).hexdigest()==expected[item.name]['sha256']
 root.mkdir(mode=0o700);stage=root/'bundle';stage.mkdir(mode=0o700)
 tar.extractall(stage,filter='data')
worker=root/'worker-private.py';worker.write_bytes(__import__('base64').b64decode({base64.b64encode((HERE/'native-ipa.py').read_bytes()).decode()!r}))
with (root/'launch-private.log').open('xb') as log:
 child=subprocess.Popen(['python3',str(worker),str(root)],env=dict(os.environ,CAMSS_TEST_FORCE_ISOLATION={force!r}),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 fields=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
 receipt=dict(pid=child.pid,start_ticks=fields[19]);(root/'launch-identity-private.json').write_text(json.dumps(receipt)+chr(10));print(json.dumps(receipt))
'''
q=host.ssh('python3 -c '+shlex.quote(code),input=archive.read_bytes(),timeout=40)
(P/f'ipa-{run}-launch-private.json').write_bytes(q.stdout);print(q.stdout.decode())
