"""Separate install/one launch/read-only fetch for the proven normal USB budget."""
from pathlib import Path
import base64, hashlib, importlib.util, json, os, shlex, subprocess, sys

REF=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=BASE/'usb500-default-r1-private'
ROOT='/var/lib/samurai/usb500-default-r1'
OLD='fcfd5052a0cad7ae9c6c581e9ede271899d99e06ad0d4d15309faa6f8ef1ad3e'
NEW='2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a'
MANIFEST='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
sha=lambda b:hashlib.sha256(b).hexdigest()

COMMON=r'''from pathlib import Path
import base64,fcntl,hashlib,json,os,subprocess,sys,time
d=json.loads(sys.stdin.buffer.read());root=Path(d['root']);script=Path('/usr/local/sbin/samurai-usb')
sha=lambda b:hashlib.sha256(b).hexdigest()
def create(p,b,mode=0o600):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
def syncdir(p):
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
assert os.geteuid()==0 and not sys.flags.optimize
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['expected_boot']==Path(d['guard']).read_text().strip()
health_errors=[]
try:
 assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())==d['manifest_sha256']
 assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
 for n,h in d['notes'].items():
  assert sha(Path('/sys/module',n,'notes/.note.gnu.build-id').read_bytes())==h
  assert Path('/sys/module',n,'initstate').read_text().strip()=='live'
except (AssertionError,OSError) as e:
 if d['action']!='fetch':raise
 health_errors.append(type(e).__name__+': '+str(e))
'''

INSTALL=r'''
assert not root.exists()
assert not Path('/run/samurai-dropbear.pid').exists() and not Path('/run/samurai-usb.lock').exists()
assert not script.is_symlink() and sha(script.read_bytes())==d['old_sha256']
st=script.stat();assert (st.st_uid,st.st_gid,st.st_mode&0o7777)==(0,0,0o755)
candidate=base64.b64decode(d['candidate_b64'],validate=True);worker=base64.b64decode(d['worker_b64'],validate=True)
assert sha(candidate)==d['new_sha256'] and sha(worker)==d['worker_sha256']
lock=os.open('/run/lock/samurai-charging.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
os.umask(0o077);root.mkdir(mode=0o700)
create(root/'original-private.sh',script.read_bytes())
create(root/'worker.py',worker)
request={k:d[k] for k in ['expected_boot','guard','manifest_sha256','new_sha256','worker_sha256']}
create(root/'request-private.json',json.dumps(request).encode())
ns={'__name__':'preflight','__file__':str(root/'worker.py')};exec(compile(worker,str(root/'worker.py'),'exec'),ns)
before=ns['snapshot']();ns['healthy'](before,100)
create(root/'install-before-private.json',json.dumps(before).encode())
temp=script.with_name('.samurai-usb-500-r1-next')
create(temp,candidate,0o755);os.chmod(temp,0o755)
q=subprocess.run(['sh','-n',str(temp)],capture_output=True);assert q.returncode==0,q.stderr
create(root/'install-intent-private.json',json.dumps({'old':d['old_sha256'],'new':d['new_sha256']}).encode());syncdir(root)
temp.replace(script);syncdir(script.parent)
assert sha(script.read_bytes())==d['new_sha256']
receipt={'installed':True,'startup_executed':False,'old_sha256':d['old_sha256'],'new_sha256':d['new_sha256']}
create(root/'install-result-private.json',json.dumps(receipt).encode());syncdir(root)
os.close(lock);print(json.dumps(receipt))
'''

LAUNCH=r'''
assert sha(script.read_bytes())==d['new_sha256']
assert sha((root/'worker.py').read_bytes())==d['worker_sha256']
assert json.loads((root/'install-result-private.json').read_bytes())['installed']
assert not Path('/run/samurai-dropbear.pid').exists() and not Path('/run/samurai-usb.lock').exists()
create(root/'launch-intent-private.json',b'{"launch_count":1,"retry":false}');syncdir(root)
with (root/'worker-private.log').open('xb') as log:
 child=subprocess.Popen(['python3','-B',str(root/'worker.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,close_fds=True,start_new_session=True)
 stat=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split()
 receipt={'launch_count':1,'pid':child.pid,'startticks':int(stat[19]),'argv':['python3','-B',str(root/'worker.py')]}
 create(root/'launch-receipt-private.json',json.dumps(receipt).encode());syncdir(root)
print(json.dumps({'launched':True,'launch_count':1,'pid':receipt['pid']}))
'''

FETCH=r'''
files={}
for name in ['activation-state-private.json','before-private.json','samples-private.json','startup-private.log','worker-private.log','install-result-private.json','install-intent-private.json','launch-intent-private.json','launch-receipt-private.json']:
 p=root/name
 if p.exists():files[name]=base64.b64encode(p.read_bytes()).decode()
process={'state':'unknown-no-launch-receipt','replay_permitted':False}
try:
 receipt=json.loads((root/'launch-receipt-private.json').read_bytes());pid=receipt['pid'];p=Path('/proc',str(pid))
 if not p.exists():process={'state':'absent'}
 else:
  stat=(p/'stat').read_text().rsplit(')',1)[1].split()
  process={'state':stat[0],'startticks':int(stat[19]),'same_startticks':int(stat[19])==receipt['startticks'],'cmdline':(p/'cmdline').read_bytes().replace(b'\0',b' ').decode()}
except (OSError,ValueError,KeyError,IndexError) as e:process['observation_error']=type(e).__name__+': '+str(e)
try:script_sha=sha(script.read_bytes())
except OSError as e:script_sha=None;health_errors.append(str(e))
print(json.dumps({'process':process,'files':files,'script_sha256':script_sha,'health_errors':health_errors}))
'''

def create(p,b):
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())

def main():
 assert len(sys.argv)==2 and sys.argv[1] in ['install','launch','fetch']
 action=sys.argv[1]
 endpoint=json.loads((BASE/'eud-boot-activation/eud-boot-r2-live-001/new-endpoint-private.json').read_bytes())
 old=json.loads((OUT/'startup-before-read-private.json').read_bytes());assert old['sha256']==OLD
 raw=json.loads((BASE/'eud-boot-activation/eud-boot-r2-live-001/postboot-r3-01-private/stdout-private.json').read_bytes())['raw']
 notes={n.replace('-','_'):x['loaded_note_sha256'] for n,x in {**raw['charging_modules'],**raw['camera_modules']}.items()}
 notes['s5k3m5']='a52ef87a2388757c542768e5438120d858e785bd334c080b55dec0f532c54d13'
 worker=(REF/'usb500-default-worker.py').read_bytes();candidate=(OUT/'samurai-usb-500-r2-private.sh').read_bytes();assert sha(candidate)==NEW
 request=dict(action=action,root=ROOT,expected_boot=endpoint['observed_new_boot'],guard=endpoint['guard_path'],notes=notes,old_sha256=OLD,new_sha256=NEW,manifest_sha256=MANIFEST,worker_sha256=sha(worker))
 if action=='install':request.update(candidate_b64=base64.b64encode(candidate).decode(),worker_b64=base64.b64encode(worker).decode())
 spec=importlib.util.spec_from_file_location('transport',REF/'eud-postboot-transport.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
 index=1
 while (OUT/f'{action}-{index:02d}-intent-private.json').exists():index+=1
 tag=f'{action}-{index:02d}'
 # A local invocation record is not permission to replay an unknown remote action.
 if action!='fetch':assert index==1,'inspect the original outcome; never replay mutation'
 create(OUT/f'{tag}-intent-private.json',json.dumps({'action':action,'request_sha256':sha(json.dumps(request).encode())}).encode())
 try:q=host.raw_ssh('python3 -c '+shlex.quote(COMMON+{'install':INSTALL,'launch':LAUNCH,'fetch':FETCH}[action]),input=json.dumps(request).encode(),timeout=25,check=False)
 except (OSError,subprocess.SubprocessError) as e:
  create(OUT/f'{tag}-stdout-private.json',getattr(e,'stdout',None) or b'')
  create(OUT/f'{tag}-stderr-private.txt',getattr(e,'stderr',None) or b'')
  create(OUT/f'{tag}-unknown-private.json',json.dumps({'outcome':'unknown','exception':type(e).__name__,'detail':str(e),'mutation_replay_permitted':False}).encode())
  raise
 create(OUT/f'{tag}-stdout-private.json',q.stdout);create(OUT/f'{tag}-stderr-private.txt',q.stderr)
 create(OUT/f'{tag}-terminal-private.json',json.dumps({'returncode':q.returncode}).encode())
 q.check_returncode();result=json.loads(q.stdout)
 if action=='fetch':
  dest=OUT/f'{tag}-files';dest.mkdir(mode=0o700)
  for n,b in result['files'].items():create(dest/n,base64.b64decode(b,validate=True))
  state=json.loads(base64.b64decode(result['files'].get('activation-state-private.json','e30=')))
  print(json.dumps({'process':result['process'],'phase':state.get('phase'),'terminal':state.get('terminal'),'passed':state.get('passed'),'script_sha256':result['script_sha256'],'health_errors':result['health_errors']}))
 else:print(json.dumps(result))

if __name__=='__main__':main()
