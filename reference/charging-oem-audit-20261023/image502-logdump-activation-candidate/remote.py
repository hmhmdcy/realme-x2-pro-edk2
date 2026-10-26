"""Executed only as stdin python3 - by an explicit controller action."""
from pathlib import Path
import sys
if sys.flags.optimize:raise RuntimeError("optimized interpreter is unsupported")
import base64,hashlib,json,os,re,runpy,subprocess,sys,time
sha=lambda raw:hashlib.sha256(raw).hexdigest()
OWNER=Path('/run/samurai-image502-notify-activation-owner-private.json')

def create(p,raw):
 with Path(p).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(Path(p).parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)

def proc(receipt):
 try:
  p=Path('/proc',str(receipt['pid']));fields=(p/'stat').read_text().rsplit(')',1)[1].split()
  argv=[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]
  ticks=int(fields[19])
  status='pid_reused' if ticks!=receipt['startticks'] else 'zombie' if fields[0]=='Z' else 'alive' if argv==receipt['argv'] else 'unknown'
  return dict(receipt,status=status,observed_argv=argv)
 except FileNotFoundError:return dict(receipt,status='absent')
 except (OSError,KeyError,ValueError,IndexError):return dict(receipt,status='unknown')

def check_run_tmpfs():
 rows=[line.split() for line in Path('/proc/mounts').read_text().splitlines()]
 assert any(r[1]=='/run' and r[2]=='tmpfs' for r in rows),'/run must be tmpfs'

def guard_ns(d):
 raw=base64.b64decode(d['guard_fragment_base64'],validate=True);assert sha(raw)==d['guard_fragment_sha256']
 code=raw.decode().split('\nassert len(sys.argv)==4')[0]
 ns={'Path':Path,'json':json,'os':os};exec(compile(code,'pinned-read-only-guard','exec'),ns);return ns

def fresh(d,root,ns):
 owner=json.loads(OWNER.read_bytes());assert all(owner[k]==d[k] for k in ['transaction_id','token','expected_boot'])
 raw=(root/'guard-private.json').read_bytes();assert sha(raw)==d['guard_sha256']
 meta,output,phase=ns['validate_activation_guard'](root/'guard-private.json',allow_inhibit=d['action'] in ['inspect-restart','restart'])
 assert all(meta[k]==d[k] for k in ['transaction_id','token'])
 assert meta['boot_id']==d['expected_boot'];return meta,output,phase

def main(d):
 os.umask(0o077);tx=d['transaction_id'];assert re.fullmatch(r'image502-notify-live-001',tx)
 assert re.fullmatch(r'[0-9a-f]{32,64}',d['token'])
 root=Path('/root/charging-management-20261023')/tx;output=Path('/var/lib/samurai')/tx
 phase=Path('/run')/(tx+'-reboot-phase-private.json');action=d['action']
 if action=='fetch':
  files={};errors=[];processes={}
  def retain(name,p):
   if not p.exists():return
   if not p.is_file() or p.is_symlink() or p.stat().st_size>20000000:errors.append('not retained: '+name);return
   raw=p.read_bytes();files[name]={'base64':base64.b64encode(raw).decode(),'sha256':sha(raw)}
  for prefix,path in [('remote-',root),('quiesce-',output)]:
   if path.exists():
    for p in sorted(path.iterdir()):retain(prefix+p.name,p)
  retain('run-phase-private.json',phase)
  retain('run-restart-log-private.txt',Path('/run')/(tx+'-restart.log'))
  for name in ['quiesce','restart']:
   p=root/(name+'-process-private.json')
   if p.exists():
    receipt=json.loads(p.read_bytes());assert receipt['transaction_id']==tx and receipt['token']==d['token']
    processes[name]=proc(receipt)
  boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
  print(json.dumps({'files':files,'processes':processes,'errors':errors,'boot_id':boot,
   'same_old_boot':boot==d['expected_boot'],'no_cleanup_or_control_action':True}),flush=True);return
 assert d['execute'] and d['window_confirmed']
 check_run_tmpfs();ns=guard_ns(d)
 if action=='prepare':
  assert not root.exists() and not output.exists() and not phase.exists()
  # Refuse old/live mutators by their actual process command lines. Ordinary
  # permanent service binaries are outside these finite transaction roots.
  for p in Path('/proc').glob('[0-9]*/cmdline'):
   if p.parent.name==str(os.getpid()):continue
   try:raw=p.read_bytes()
   except (FileNotFoundError,ProcessLookupError):continue
   if b'python' in raw and any(x in raw for x in [b'/root/charging-',b'/var/lib/samurai/camera-',b'/var/lib/samurai/k481-']):
    raise ValueError('prior transaction process still exists; inspect rather than overlap')
  boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
  assert boot==d['expected_boot']==Path(d['fixed']['old_boot_guard_path']).read_text().strip()
  board={'serial_sha256':sha(Path('/sys/devices/soc0/serial_number').read_bytes()),
   'compatible_sha256':sha(Path('/sys/firmware/devicetree/base/compatible').read_bytes())}
  assert board==d['expected_board']
  meta={**d['fixed'],'transaction_id':tx,'token':d['token'],'boot_id':boot,
   'kernel_version':os.uname().version,'rootfs_release_sha256':sha(Path('/etc/samurai-rootfs-release').read_bytes()),
   'soc_serial_sha256':board['serial_sha256'],'compatible_sha256':board['compatible_sha256']}
  assert os.uname().release==d['expected_release'] and os.uname().version==d['expected_version']
  assert meta['rootfs_release_sha256']==d['expected_rootfs_sha256']
  assert set(d['files'])=={'eud-quiesce.py','eud-restart.py','camera481-expected-private.json'}
  create(OWNER,json.dumps({k:d[k] for k in ['transaction_id','token','expected_boot']}).encode())
  root.mkdir(mode=0o700)
  for name,row in d['files'].items():
   raw=base64.b64decode(row['base64'],validate=True);assert sha(raw)==row['sha256'];create(root/name,raw)
  raw=json.dumps(meta,indent=2).encode();create(root/'guard-private.json',raw)
  d={**d,'guard_sha256':sha(raw)};fresh(d,root,ns)
  proof={'prepared':True,'transaction_id':tx,'token':d['token'],'guard_sha256':sha(raw),
   'guard_base64':base64.b64encode(raw).decode(),'hardware_writes':0,'boot_id':boot}
  create(root/'prepare-result-private.json',json.dumps(proof).encode())
  print(json.dumps(proof),flush=True);return
 meta,output,phase=fresh(d,root,ns)
 for name,digest in d['worker_hashes'].items():assert sha((root/name).read_bytes())==digest
 if action=='inspect-restart':
  sys.argv=[str(root/'eud-restart.py'),'--guard',str(root/'guard-private.json'),'--inspect']
  runpy.run_path(str(root/'eud-restart.py'),run_name='__main__');return
 assert action in ['quiesce','restart']
 if action=='quiesce':assert not output.exists()
 else:
  s=json.loads((output/'state-private.json').read_bytes());summary=json.loads((output/'summary.json').read_bytes())
  assert s['terminal'] and s['exit_code']==0 and summary['taint']==0
  assert all(s[k]==summary[k]==meta[k] for k in ['transaction_id','token','boot_id'])
  q=json.loads((root/'quiesce-process-private.json').read_bytes());assert q['pid']==s['pid']
  assert proc(q)['status'] in ['absent','zombie']
 name='eud-'+action+'.py';option='--commit-quiesce' if action=='quiesce' else '--commit-restart2-bootloader'
 argv=['python3','-B',str(root/name),'--guard',str(root/'guard-private.json'),option]
 create(root/(action+'-intent-private.json'),json.dumps({'transaction_id':tx,'token':d['token'],'argv':argv,'request_count':1}).encode())
 log=root/'quiesce.log' if action=='quiesce' else Path('/run')/(tx+'-restart.log')
 with log.open('xb') as f:
  child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=f,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
 p=Path('/proc',str(child.pid));fields=(p/'stat').read_text().rsplit(')',1)[1].split()
 actual=[x.decode() for x in (p/'cmdline').read_bytes().split(bytes([0])) if x]
 assert actual==argv,'worker started but argv unproved; fetch only'
 receipt={'transaction_id':tx,'token':d['token'],'boot_id':meta['boot_id'],'pid':child.pid,
  'startticks':int(fields[19]),'argv':actual,'worker_sha256':d['worker_hashes'][name]}
 create(root/(action+'-process-private.json'),json.dumps(receipt).encode())
 print(json.dumps({'launched':True,'process':receipt,'restart_outcome_unproved':action=='restart'}),flush=True)

if __name__=='__main__':main(CONFIG)
