"""Explicitly stage OR launch one fresh, preflight-bound 451/452 transaction."""
from pathlib import Path
import argparse,ast,datetime,hashlib,io,json,shlex,tarfile
import host,storage

HERE=Path(__file__).resolve().parent
def validate_archive(payload,files):
    with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as archive:
        members=archive.getmembers()
        assert len(members)==len(files) and {m.name for m in members}==set(files)
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
        for member in members:
            assert hashlib.sha256(archive.extractfile(member).read()).digest()==hashlib.sha256(Path(files[member.name]).read_bytes()).digest()

parser=argparse.ArgumentParser()
parser.add_argument('kind',choices=['comparison','diagnostic'])
parser.add_argument('action',choices=['stage','launch'])
parser.add_argument('--attempt',default='r1')
parser.add_argument('--handoff',type=Path,required=True)
args=parser.parse_args()
storage.mount.mounted_build()
assert args.attempt.startswith('r') and args.attempt[1:].isdigit() and 1<=int(args.attempt[1:])<=20
stage=451 if args.kind=='comparison' else 452
prefix='k451-proxy-comparison-' if stage==451 else 'k452-full-diagnostic-'
window=prefix+args.attempt
private=Path('/mnt/e/edk2-samurai-out')/('kernel'+str(stage))
work=private/(args.kind+'-prepared-'+args.attempt)
handoff=json.loads(args.handoff.read_text())
assert handoff['schema']=='samurai-camera-handoff-v1' and handoff['window_id']==window
assert handoff['window_owner']=='camera' and handoff['fresh_preflight_verified'] is True
issued=datetime.datetime.fromisoformat(handoff['issued_at_utc'].replace('Z','+00:00'))
assert issued.tzinfo and 0<= (datetime.datetime.now(datetime.timezone.utc)-issued).total_seconds()<600,'Use a current preflight'
digest=lambda raw:hashlib.sha256(raw).hexdigest()
handoff_sha=digest(args.handoff.read_bytes())
proof=json.loads((work/'proof.json').read_text())
assert proof['boot_guard']==handoff['boot_guard_path']
files=json.loads((work/'payload-files-private.json').read_text())
manifest=json.loads((work/'manifest.json').read_text())
assert set(files)==set(manifest)|{'manifest.json'}
assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in files)
assert all(digest(Path(files[n]).read_bytes())==h for n,h in manifest.items())
assert manifest['handoff-private.json']==handoff_sha
assert manifest['baseline-private.json']==handoff['formal_baseline_sha256']
if args.attempt!='r1':
    worker=Path(files['worker.py']).read_text()
    assert 'start_uptime=time.monotonic()' in worker
    assert "start_uptime=float(Path('/proc/uptime').read_text().split()[0])" not in worker
plan=json.loads((HERE.parent/('kernel'+str(stage))/(args.kind+'-plan-validation.json')).read_text())
assert plan['passed'] and plan['ready_for_manual_stage'] and plan['payload_generated'] and plan['window_id']==window
root='/var/lib/samurai/'+window
common='''from pathlib import Path
import hashlib,io,json,os,runpy,subprocess,sys,tarfile,time
root=Path(ROOT)
handoff=HANDOFF
assert Path(handoff['boot_guard_path']).read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert hashlib.sha256(Path('/usr/share/samurai-charging/manifest.json').read_bytes()).hexdigest()==handoff['charging']['manifest_sha256']
assert hashlib.sha256(Path('/usr/lib/libcamera.so.0.7.2').read_bytes()).hexdigest()==handoff['formal_library_sha256']
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
'''.replace('ROOT',repr(root)).replace('HANDOFF',repr(handoff))
if args.action=='stage':
    payload=(work/(args.kind+'-payload.tar.gz')).read_bytes()
    validate_archive(payload,files)
    code=common+'''
assert not root.exists() and not root.is_symlink(), 'Never replay or overwrite a transaction'
raw=sys.stdin.buffer.read();assert hashlib.sha256(raw).hexdigest()==PAYLOAD
with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
 members=archive.getmembers()
 assert len(members)==len(NAMES) and {m.name for m in members}==NAMES
 assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts for m in members)
 os.umask(0o077);root.mkdir(mode=0o700)
 for member in members:
  target=root/member.name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  with target.open('xb') as output:
   output.write(archive.extractfile(member).read());output.flush();os.fsync(output.fileno())
 for name,expected in json.loads((root/'manifest.json').read_text()).items():
  assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
 for name in ['pipeline-fixture','user-launcher.py','gst-sustained','proxy-old/camss_ipa_proxy','proxy-new/camss_ipa_proxy','proxy/camss_ipa_proxy']:
  if (root/name).exists():(root/name).chmod(0o700)
 assert hashlib.sha256((root/'handoff-private.json').read_bytes()).hexdigest()==HANDOFF_SHA
 print(json.dumps(dict(staged=True,launched=False,root=str(root),passed=True)))
'''.replace('PAYLOAD',repr(digest(payload))).replace('NAMES',repr(set(files))).replace('HANDOFF_SHA',repr(handoff_sha))
else:
    payload=None
    code=common+'''
assert root.is_dir() and not root.is_symlink()
assert hashlib.sha256((root/'handoff-private.json').read_bytes()).hexdigest()==HANDOFF_SHA
for name,expected in json.loads((root/'manifest.json').read_text()).items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected
assert not (root/'state.json').exists() and not (root/'launch-private.log').exists(), 'Never relaunch'
functions=runpy.run_path(str(root/BODY))
assert functions['charging']()==handoff['charging']
with (root/'launch-private.log').open('xb') as output:
 child=subprocess.Popen(['python3','-B',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
 time.sleep(.1)
 if child.poll() is not None:raise RuntimeError('Worker ended during launch; inspect retained log/state, never replay')
 fields=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
 result=dict(root=str(root),pid=child.pid,start_ticks=int(fields[19]),launched=True,passed=True)
 (root/'launch-private.json').write_text(json.dumps(result)+chr(10))
 print(json.dumps(result))
'''.replace('HANDOFF_SHA',repr(handoff_sha)).replace('BODY',repr('capture-body-comparison.py' if stage==451 else 'capture-common-private.py'))
ast.parse(code)
(work/(args.action+'-remote-private.py')).write_text(code)
q=host.raw_ssh('python3 -c '+shlex.quote(code),input=payload,timeout=60)
(work/(args.action+'-stdout-private.txt')).write_bytes(q.stdout)
(work/(args.action+'-stderr-private.txt')).write_bytes(q.stderr)
q.check_returncode()
result=json.loads(q.stdout)
result.update(stage=stage,action=args.action,handoff_sha256=handoff_sha)
(private/(args.kind+'-'+args.action+'-'+args.attempt+'-private.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
