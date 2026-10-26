"""One schema2 identity-gated capture. The original store algorithm is unchanged."""
from pathlib import Path
import argparse,ast,base64,importlib.util,json,os,secrets,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
adapter=load('profile_capture_host',HERE/'host.py');u=adapter.u
post=load('profile_capture_post',HERE/'postboot.py')
TX='protection-capture-profile-20261024-01';REMOTE='/root/charging-management-20261023/'+TX
SOURCE=u.ROOT/'reference/charging-oem-audit-20261023/protection-capture-host-candidate'
PROFILE=u.ROOT/'reference/charging-oem-audit-20261023/protection-observed-2719-profile-candidate'
def worker_source():
 original=(SOURCE/'stage-worker.py').read_text();source=original;c=json.loads((HERE/'cohort-r2-result.json').read_bytes())
 for name,value in dict(VERSION=u.VERSION,MANIFEST=c['target_manifest_sha256'],KO=c['target_protection_sha256'],NOTE=c['target_protection_note_sha256']).items():source=adapter.assigned(source,name,value)
 source=u.replace(source,"r'usb-irq-protection-activate-[a-z0-9-]{8,48}'","r'irq-native-usb-pm-activate-protocol-[a-z0-9-]{8,48}'")
 source=u.replace(source,"fields.get('schema') == '1' and fields.get('attempted') in ('0', '1')",
  "fields.get('schema') == '2' and fields.get('diagnostic_profile') == '1' and fields.get('profile_identity_verified') in ('0','1') and fields.get('attempted') in ('0','1') and fields.get('terminal')==fields.get('attempted')")
 point="need(Path(INSTANCE, 'driver').resolve().as_posix() == '/sys/bus/platform/drivers/samurai-gauge-protection' and\n             Path(INSTANCE).stat().st_ino == self.instance, 'same bound platform instance required')"
 source=u.replace(source,point,"need(Path(MODULE,'parameters/observed_2719_diagnostic').read_text().strip()=='Y','explicit observed2719 profile required')\n        "+point)
 old_funcs={n.name:ast.get_source_segment(original,n) for n in ast.parse(original).body if isinstance(n,ast.FunctionDef)}
 new_funcs={n.name:ast.get_source_segment(source,n) for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)}
 assert all(new_funcs[n]==body for n,body in old_funcs.items() if n not in ['validate_request','cached_header'])
 return source.encode()
def local():
 source=worker_source();scope={'__name__':'profile_capture_local'};exec(compile(source,'<derived-capture>','exec'),scope)
 valid=b'schema=2 diagnostic_profile=1 profile_identity_verified=0 attempted=0 terminal=0\n'
 assert scope['cached_header'](valid)['attempted']=='0';refusals=0
 for bad in [valid.replace(b'schema=2',b'schema=1'),valid.replace(b'diagnostic_profile=1',b'diagnostic_profile=0'),valid.replace(b'diagnostic_profile=1',b'diagnostic_profile=2'),valid.replace(b'terminal=0',b'terminal=1'),valid+b'schema=2']:
  try:scope['cached_header'](bad)
  except ValueError:refusals+=1
 assert refusals==5
 tests=json.loads((PROFILE/'test-result.json').read_bytes());decoder=Path(tests['private_output'])/'frame-decoder-profile'
 assert u.sha(decoder.read_bytes())==tests['decoder_sha256']=='278d854ab14c59ac51c5e79b3920f1d0213f5f81a95861691f1043c0477197ef'
 parser=load('profile_frozen_parser',PROFILE/'parse-saved-profile.py');assert u.sha((PROFILE/'parse-saved-profile.py').read_bytes())==tests['source_files']['parse-saved-profile.py']
 parsed=parser.parse_saved_profile((Path(tests['private_output'])/'observed-before-attempt.txt').read_bytes(),decoder,tests['decoder_sha256'],profile='observed-2719-0056-3')
 assert parsed['header']['attempted']==0
 u.create(u.OUT/'capture-worker-template.py',source)
 u.save(u.OUT/'capture-local-result.json',dict(passed=True,changed_header_positive=1,changed_header_refusals=5,existing_parser_untouched_profile_fixture=True,original_capture_store_algorithm_exact=True,decoder_sha256=tests['decoder_sha256'],worker_sha256=u.sha(source),device_accessed=False))
 return dict(passed=True,new_query_started=False)
def launch():
 pointer=(u.BASE/'boot-adoption-private.json').read_bytes();assert pointer==(u.OUT/'adoption-pointer.json').read_bytes();current=json.loads(pointer)
 assert current['protection_diagnostic_profile']=='observed-2719-0056-3'
 r=u.request();reply=json.loads((u.OUT/'adopt/reply.json').read_bytes());source=(u.OUT/'capture-worker-template.py').read_bytes();assert source==worker_source()
 request=dict(schema='samurai-protection-capture-request-v1',transaction_id=TX,identity={**r['identity'],'boot_id':current['boot_id']},
  adoption=dict(transaction_id=Path(post.GUARD).parent.name.removesuffix('-adopted'),guard_path=post.GUARD,guard_sha256=reply['guard_sha256'],postboot_raw_sha256=current['postboot_raw_sha256'],fresh_validation_sha256=reply['fresh_validation_sha256']),
  worker_sha256=u.sha(source),lease_token=secrets.token_hex(24))
 scope={'__name__':'capture_local'};exec(compile(source,'<derived-capture>','exec'),scope);scope['validate_request'](request)
 raw=(json.dumps(request,indent=2)+'\n').encode()
 wrapper=("import io,sys,runpy\nsys.stdin=io.TextIOWrapper(io.BytesIO("+repr(raw)+"))\nsys.argv=['capture','--execute-stage']\nrunpy.run_path("+repr(REMOTE+'/stage-worker.py')+",run_name='__main__')\n").encode()
 supervisor=(u.POST/'pm-smoke-supervisor.py').read_bytes()
 files={'stage-worker.py':source,'worker.py':wrapper,'supervisor.py':supervisor,'request-private.json':raw}
 packet=dict(root=REMOTE,boot_id=current['boot_id'],request=request,files={n:base64.b64encode(b).decode() for n,b in files.items()},hashes={n:u.sha(b) for n,b in files.items()})
 u.save(u.OUT/'capture-request.json',request);u.create(u.OUT/'capture-wrapper.py',wrapper)
 # Original one-child supervisor, exclusive paths and lease; no kernel rearm.
 code=('PACKET='+repr(packet)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json,os,subprocess,sys,time
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==PACKET['boot_id']
root=Path(PACKET['root']);assert not root.exists();os.umask(0o077);root.mkdir(mode=0o700)
def save(path,raw):
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
for name,value in PACKET['files'].items():
 raw=base64.b64decode(value,validate=True);assert hashlib.sha256(raw).hexdigest()==PACKET['hashes'][name];save(root/name,raw)
r=PACKET['request'];now=time.clock_gettime(time.CLOCK_BOOTTIME)
lease=dict(transaction_id=r['transaction_id'],boot_id=PACKET['boot_id'],token=r['lease_token'],owner='charging',exclusive=True,camera_released=True,bluetooth_released=True,issued_boottime_s=now,expires_boottime_s=now+120)
save(Path('/run')/(r['transaction_id']+'-window-private.json'),(json.dumps(lease)+'\n').encode())
save(root/'launch-private.json',(json.dumps(dict(boot_id=PACKET['boot_id'],worker_sha256=PACKET['hashes']['worker.py']))+'\n').encode())
with (root/'supervisor-stdout-private.txt').open('xb') as out,(root/'supervisor-stderr-private.txt').open('xb') as err:
 child=subprocess.Popen([sys.executable,'-B',str(root/'supervisor.py'),'--supervise',str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,start_new_session=True)
 fields=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split();receipt=dict(pid=child.pid,startticks=int(fields[19]),argv=[v.decode() for v in Path('/proc',str(child.pid),'cmdline').read_bytes().split(bytes([0])) if v])
 save(root/'supervisor-launch-private.json',(json.dumps(receipt)+'\n').encode())
print(json.dumps(dict(launched=True,supervisor=receipt,capture_pending=True)))
'''
 return u.call('capture-launch',code,False)
def fetch():
 code=('REMOTE='+repr(REMOTE)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json
root=Path(REMOTE);files={}
for p in root.rglob('*'):
 if p.is_file():
  raw=p.read_bytes();assert len(raw)<2000000;files[str(p.relative_to(root))]=dict(sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
def process(name):
 receipt=json.loads((root/name).read_bytes());p=Path('/proc',str(receipt['pid']))
 try:
  fields=(p/'stat').read_text().rsplit(')',1)[1].split();argv=[v.decode() for v in (p/'cmdline').read_bytes().split(bytes([0])) if v]
 except FileNotFoundError:return dict(status='absent',receipt=receipt)
 if int(fields[19])!=receipt['startticks']:return dict(status='pid_reused',receipt=receipt)
 return dict(status='zombie' if fields[0]=='Z' else 'live',receipt=receipt,argv=argv)
print(json.dumps(dict(files=files,worker=process('worker-process-private.json'),supervisor=process('supervisor-launch-private.json'),current_boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip())))
'''
 reply=u.call('capture-fetch',code);out=u.OUT/'capture-raw';out.mkdir(mode=0o700)
 for name,row in reply['files'].items():
  p=out/name;assert p.is_relative_to(out);p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(row['base64'],validate=True);assert u.sha(raw)==row['sha256'];u.create(p,raw)
 return dict(terminal=json.loads((out/'worker-terminal-private.json').read_bytes()) if (out/'worker-terminal-private.json').exists() else None,
  result=json.loads((out/'device-stage/result.json').read_bytes()) if (out/'device-stage/result.json').exists() else None)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['local','launch','fetch']);a=p.parse_args();print(json.dumps(globals()[a.action](),indent=2))
