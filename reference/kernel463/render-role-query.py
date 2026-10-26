"""Render a read-only role/FD witness query. There is deliberately no SSH mode."""
from pathlib import Path
import argparse,ast,hashlib,json
HERE=Path(__file__).resolve().parent
def render(handoff,baseline,identity):
 source='from pathlib import Path\nimport datetime,hashlib,json,os,re,shutil,stat,subprocess,time\n'
 source+='handoff='+repr(handoff)+'\nbaseline='+repr(baseline)+'\nexpected='+repr(identity)+'\n'
 source+=r'''
assert handoff is not None and baseline is not None and expected is not None,'Fresh outer camera transaction and live application identity required'
assert handoff['window_owner']=='camera' and handoff['fresh_preflight_verified'] is True
issued=datetime.datetime.fromisoformat(handoff['issued_at_utc'].replace('Z','+00:00'))
assert 0<=(datetime.datetime.now(datetime.timezone.utc)-issued).total_seconds()<600
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot.decode().strip()==baseline['boot_id'].strip()
assert Path(handoff['boot_guard_path']).read_bytes()==boot
pid=expected['pid'];assert type(pid) is int and pid>1
proc=Path('/proc',str(pid))
def identity():
 fields=(proc/'stat').read_text().rsplit(')',1)[1].split();assert fields[0]!='Z'
 status=dict(line.split(':',1) for line in (proc/'status').read_text().splitlines() if ':' in line)
 uids=list(map(int,status['Uid'].split()));assert uids==[10000]*4
 assert (proc/'exe').stat().st_size<=32*1024*1024
 with (proc/'exe').open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
 return dict(pid=pid,start_ticks=int(fields[19]),uid=uids[0],cap_eff=int(status['CapEff'],16),exe_sha256=digest)
before=identity();assert before==expected
started=time.monotonic_ns()
media=shutil.which('media-ctl');assert media,'No media-ctl; do not guess topology'
graphs=[]
nodes=sorted(p for p in Path('/dev').glob('media*') if re.fullmatch(r'media\d+',p.name))
assert 0<len(nodes)<=8
for device in nodes:
 assert stat.S_ISCHR(device.stat().st_mode)
 run=subprocess.run([media,'-p','-d',str(device)],capture_output=True,timeout=5,check=True)
 assert len(run.stdout)<=2*1024*1024
 if re.search(r'^driver\s+qcom-camss\s*$',run.stdout.decode(),re.M):
  graphs.append(dict(device=str(device),text=run.stdout.decode()))
assert len(graphs)==1
videos={p.name:dict(name=(p/'name').read_text().strip(),dev=(p/'dev').read_text().strip()) for p in Path('/sys/class/video4linux').glob('video*')}
fds=[]
for fd in (proc/'fd').iterdir():
 try:
  st=fd.stat()
  if stat.S_ISCHR(st.st_mode):fds.append(dict(fd=int(fd.name),target=os.readlink(fd),major=os.major(st.st_rdev),minor=os.minor(st.st_rdev)))
 except (FileNotFoundError,ProcessLookupError):pass
after=identity();assert before==after and Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
print(json.dumps(dict(schema='samurai-full-role-observation-v1',window_id=handoff['window_id'],boot_id=boot.decode().strip(),
 graph=graphs[0],video_nodes=videos,identity=before,character_fds=fds,same_process_before_after=True,
 mono_start_ns=started,mono_end_ns=time.monotonic_ns(),phone_changed=False)))
'''
 ast.parse(source)
 return source
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--handoff',type=Path);parser.add_argument('--baseline',type=Path);parser.add_argument('--identity',type=Path)
 parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 assert bool(args.handoff)==bool(args.baseline)==bool(args.identity)
 values=[json.loads(p.read_text()) if p else None for p in [args.handoff,args.baseline,args.identity]]
 if args.handoff:
  assert hashlib.sha256(args.baseline.read_bytes()).hexdigest()==values[0]['formal_baseline_sha256']
 source=render(*values)
 assert not args.output.exists(),'Keep previous query; choose a new file'
 with args.output.open('x') as stream:stream.write(source)
 print(json.dumps(dict(rendered=True,phone_accessed=False,query_sha256=hashlib.sha256(source.encode()).hexdigest(),live_handoff_and_identity_required=True)))
if __name__=='__main__':main()
