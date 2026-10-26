"""Render concrete481 queries; never sends or executes them."""
import ast

def render(work,plan,mapping,modes,directories,bundle_hash,gate,charging):
 prefix='''from pathlib import Path
from datetime import datetime,timezone
import hashlib,io,json,os,shutil,subprocess,sys,tarfile,runpy,re,time
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
'''
 prefix+='root=Path('+repr(plan['target_root'])+')\nWINDOW='+repr(plan['window_id'])+'\nplan='+repr(plan)+'\nexpected='+repr(mapping)+'\nmodes='+repr(modes)+'\n'
 checked=prefix+gate+'\n'+charging+'\ngate(plan)\nassert os.geteuid()==0\n'
 stage=checked+'''assert not root.exists(), 'No restaging of a previous/unknown attempt'
assert charging()==plan['handoff']['charging']
assert shutil.disk_usage('/').free>=plan['minimum_target_free_bytes']
versions={}
for block in Path('/lib/apk/db/installed').read_text().split('\\n\\n'):
    fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
    if fields.get('P') in plan['cohort']['rollback_packages']:versions[fields['P']]=fields['V']
assert versions==plan['cohort']['rollback_packages']
for path,row in plan['package_files']['rollback'].items():
    p=Path(path)
    if 'symlink' in row:assert p.is_symlink() and os.readlink(p)==row['symlink']
    else:assert p.is_file() and not p.is_symlink() and sha(p)==row['sha256']
for family in ['modules','profiles']:
    for row in plan['cohort'][family]:
        p=Path(row['path']);assert p.is_file() and not p.is_symlink() and str(p.resolve())==row['resolved_path'] and sha(p)==row['rollback_sha256']
for row in plan['cohort']['modules']:assert sha('/sys/module/'+row['name']+'/notes/.note.gnu.build-id')==row['rollback_note_sha256']
data=sys.stdin.buffer.read(64*1024*1024);assert hashlib.sha256(data).hexdigest()==BUNDLE_HASH
os.umask(0o077);root.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
    members=archive.getmembers();assert len(members)==len(expected)+len(DIRECTORIES)
    assert {m.name for m in members}==set(expected)|set(DIRECTORIES)
    for name in DIRECTORIES:(root/name).mkdir(mode=0o700)
    for member in members:
        assert member.uid==member.gid==0 and member.mode==(0o700 if member.isdir() else modes[member.name])
        if member.isdir():assert member.name in DIRECTORIES;continue
        assert member.isfile() and member.name in expected
        content=archive.extractfile(member).read();assert hashlib.sha256(content).hexdigest()==expected[member.name]
        destination=root/member.name;destination.write_bytes(content);destination.chmod(modes[member.name])
(root/'staged-private.json').write_text(json.dumps({'passed':True,'files_sha256':expected})+chr(10))
print(json.dumps({'staged':True,'root':str(root)}))
'''.replace('BUNDLE_HASH',repr(bundle_hash)).replace('DIRECTORIES',repr(directories))
 launch=checked+'''assert root.is_dir() and not (root/'launch-private.json').exists() and not (root/'state-private.json').exists()
assert json.loads((root/'staged-private.json').read_text())['files_sha256']==expected
for name,digest in expected.items():assert sha(root/name)==digest
assert charging()==plan['handoff']['charging']
os.umask(0o077)
fd=os.open(root/'launch-private.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
out=(root/'worker-stdout-private.txt').open('xb');err=(root/'worker-stderr-private.txt').open('xb')
p=subprocess.Popen(['/usr/bin/python3','-B',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,cwd=root)
ticks=Path('/proc',str(p.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
record={'pid':p.pid,'start_ticks':ticks,'launched':True};os.write(fd,(json.dumps(record)+chr(10)).encode());os.fsync(fd);os.close(fd)
print(json.dumps(record))
'''
 observe=prefix+'''def live(record):
    if not record:return False
    path=Path('/proc',str(record['pid']),'stat')
    try:
        values=path.read_text().rsplit(')',1)[1].split();return values[19]==str(record['start_ticks']) and values[0]!='Z'
    except FileNotFoundError:return False
record=None;state=None;error=None
if root.exists():
    try:
        record=json.loads((root/'launch-private.json').read_text()) if (root/'launch-private.json').exists() else None
        state=json.loads((root/'state-private.json').read_text()) if (root/'state-private.json').exists() else None
    except (ValueError,OSError) as exception:error=repr(exception)
result={'root_exists':root.exists(),'launch':record,'state':state,'worker_live':live(record),'active_child_live':live(state.get('active_child')) if state else False,'read_error':error}
print(json.dumps(result))
'''
 collect=observe.rsplit('print(json.dumps(result))',1)[0]+'''assert not result['worker_live'] and not result['active_child_live'], 'Inspect same handle until owned children exit'
assert state and state['terminal'], 'Preserve failure logs; no collection of an unknown live transaction'
excluded={'forward','rollback','cache','tmp','worker.py','default-probe.py','probe-log-audit.py','pipeline-fixture','pipeline-smoke','gst-sustained','user-launcher.py'}
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as archive:
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if relative.parts[0] in excluded or not path.is_file() or path.is_symlink():continue
        content=path.read_bytes();member=tarfile.TarInfo(relative.as_posix());member.uid=member.gid=0;member.mode=0o600;member.size=len(content);archive.addfile(member,io.BytesIO(content))
'''
 for name,source in [('stage',stage),('launch',launch),('observe',observe),('collect',collect)]:
  ast.parse(source);(work/(name+'-query.py')).write_text(source)
