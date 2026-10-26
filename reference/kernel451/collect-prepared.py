"""Collect bounded terminal logs/JSON/CSV from one exact camera transaction."""
from pathlib import Path
import argparse,hashlib,io,json,shlex,tarfile
import host,storage

HERE=Path(__file__).resolve().parent
def unpack(payload,target):
 with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as archive:
  members=archive.getmembers()
  assert len(members)==len({m.name for m in members})
  directories={'disabled-120/captures','trace-window/captures','A1/captures','B/captures','A2/captures'}
  assert all((m.isfile() and Path(m.name).suffix in ['.csv','.json','.log','.txt'] or (m.isdir() and m.name in directories)) and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and m.size<=64*1024*1024 for m in members)
  assert not target.exists()
  target.mkdir(mode=0o700)
  for member in members:
   path=target/member.name;path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
   if member.isdir():
    path.mkdir(mode=0o700,exist_ok=True);continue
   with path.open('xb') as output:output.write(archive.extractfile(member).read())
 return len(members)

parser=argparse.ArgumentParser()
parser.add_argument('kind',choices=['comparison','diagnostic'])
parser.add_argument('--attempt',default='r1')
parser.add_argument('--handoff',type=Path,required=True)
args=parser.parse_args()
storage.mount.mounted_build()
assert args.attempt.startswith('r') and args.attempt[1:].isdigit() and 1<=int(args.attempt[1:])<=20
stage=451 if args.kind=='comparison' else 452
window=('k451-proxy-comparison-' if stage==451 else 'k452-full-diagnostic-')+args.attempt
handoff=json.loads(args.handoff.read_text())
assert handoff['schema']=='samurai-camera-handoff-v1' and handoff['window_id']==window and handoff['window_owner']=='camera' and handoff['fresh_preflight_verified'] is True
digest=hashlib.sha256(args.handoff.read_bytes()).hexdigest()
private=Path('/mnt/e/edk2-samurai-out')/('kernel'+str(stage))
target=private/('runtime-collected-'+args.attempt)
assert not target.exists(), 'Keep existing collection; never silently overwrite'
source='''from pathlib import Path
import hashlib,json,sys,tarfile
root=Path(ROOT)
assert hashlib.sha256((root/'handoff-private.json').read_bytes()).hexdigest()==DIGEST
handoff=json.loads((root/'handoff-private.json').read_text())
assert Path(handoff['boot_guard_path']).read_bytes()==Path('/proc/sys/kernel/random/boot_id').read_bytes()
state=json.loads((root/'state.json').read_text());assert state['terminal']
worker=Path('/proc',str(state['pid']))
if worker.exists():assert worker.joinpath('stat').read_text().rsplit(')',1)[1].split()[0]=='Z'
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz',compresslevel=1) as archive:
 for path in root.rglob('*'):
  if path.is_file() and not path.is_symlink() and path.suffix in ['.csv','.json','.log','.txt']:
   assert path.stat().st_size<=64*1024*1024
   archive.add(path,arcname=str(path.relative_to(root)),recursive=False)
  elif path.is_dir() and not path.is_symlink() and str(path.relative_to(root)) in ['disabled-120/captures','trace-window/captures','A1/captures','B/captures','A2/captures']:
   archive.add(path,arcname=str(path.relative_to(root)),recursive=False)
'''.replace('ROOT',repr('/var/lib/samurai/'+window)).replace('DIGEST',repr(digest))
q=host.raw_ssh('python3 -B -c '+shlex.quote(source),timeout=60)
(private/(args.kind+'-collect-'+args.attempt+'-stderr-private.txt')).write_bytes(q.stderr)
q.check_returncode()
bundle=private/(args.kind+'-collected-'+args.attempt+'-private.tar.gz')
assert not bundle.exists();bundle.write_bytes(q.stdout)
members=unpack(q.stdout,target)
print(json.dumps(dict(stage=stage,window_id=window,members=members,root=str(target),archive_sha256=hashlib.sha256(q.stdout).hexdigest(),passed=True)))
