"""Default local-only. Adopt actual passed Image501 postboot evidence once."""
from pathlib import Path,PurePosixPath
import argparse,ast,base64,hashlib,importlib.util,json,os,re,subprocess,sys
if sys.flags.optimize:raise RuntimeError('optimized Python disables adoption checks')
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
sha=lambda b:hashlib.sha256(b).hexdigest()
PEER='fe80::62:bcff:fe28:a101%29'
def create(p,raw):
 with Path(p).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 fd=os.open(Path(p).parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
def save(p,v):create(p,json.dumps(v,indent=2).encode())
def sources():
 pins=json.loads((HERE/'source-pins.json').read_bytes());out={}
 for n,r in pins.items():
  value=Path(r['path']).read_bytes();assert sha(value)==r['sha256'];out[n]=value
 ast.parse(out['postboot_device']);assert b'/dev/mem' not in out['postboot_device'] and b'mmap' not in out['postboot_device']
 return pins,out
def load_device():
 pins,raw=sources();s=importlib.util.spec_from_file_location('image501_reviewed_postboot',pins['postboot_device']['path'])
 m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m,raw
def review(context_path,observed):
 context_path,observed=Path(context_path),Path(observed);context=json.loads(context_path.read_bytes())
 assert context['schema']=='samurai-image501-fastboot-context-v1'
 tx=context['transaction_id'];assert re.fullmatch(r'image501-[a-z0-9-]{8,64}',tx)
 assert observed.is_relative_to(context_path.parent) and context_path.parent.name==tx
 guard_fact=context['files']['guard'];assert PurePosixPath(guard_fact['path']).name==guard_fact['path']=='guard-private.json'
 guard_raw=(context_path.parent/guard_fact['path']).read_bytes();guard=json.loads(guard_raw)
 assert sha(guard_raw)==guard_fact['sha256']==context['guard_sha256']
 assert guard['transaction_id']==tx and guard['token']==context['token'] and guard['boot_id']==context['old_boot_id']
 m,src=load_device();fixed=json.loads(src['activation_contract'])['fixed_guard_fields']
 assert all(guard[k]==v for k,v in fixed.items())
 report_raw=(observed/'stdout-private.json').read_bytes();report=json.loads(report_raw)
 receiver=json.loads((observed/'receiver-result-private.json').read_bytes())
 assert receiver['passed'] is True and receiver['transport_exit']==0 and report['result']['passed'] is True
 assert report['schema']=='samurai-image501-postboot-readonly-v1' and report['transaction_id']==tx
 assert report['context_sha256']==sha(context_path.read_bytes()) and report['guard_sha256']==sha(guard_raw)
 executed=(observed/'executed-device-source.py').read_bytes();first,body=executed.split(b'\n',1)
 assert body==src['postboot_device']
 node=ast.parse(first).body[0];assert isinstance(node,ast.Assign) and node.targets[0].id=='POSTBOOT_REQUEST'
 request=json.loads(base64.b64decode(ast.literal_eval(node.value.args[0].args[0]),validate=True))
 assert request['schema']==report['schema'] and request['context_sha256']==report['context_sha256'] and request['guard']==guard
 assert request['guard_sha256']==sha(guard_raw) and request['original_key_transport_verified'] is True and request['new_endpoint']==PEER
 assert m.audit(report['raw'],request)['passed'] is True
 r=report['raw'];before,after=r['identity_before'],r['identity_after']
 assert before==after and before['boot_id']!=guard['boot_id'] and before['uname']['version'].startswith('#501 ')
 notes={n.replace('-','_'):v['loaded_note_sha256'] for n,v in {**r['charging_modules'],**r['camera_modules']}.items()}
 notes['s5k3m5']=m.SENSOR468_NOTE
 adopted={'schema':'samurai-image501-adoption-v1','transaction_id':tx,'boot':before['boot_id'],
  'old_boot':guard['boot_id'],'release':before['uname']['release'],'version':before['uname']['version'],
  'rootfs':before['rootfs']['sha256'],'serial_sha256':before['serial_sha256'],
  'compatible_sha256':sha(base64.b64decode(before['compatible_b64'],validate=True)),
  'guard':'/var/lib/samurai/'+tx+'-adopted/boot-id-private.txt','notes':notes,
  'manifest':fixed['charging_manifest_sha256'],'candidate_boot_sha256':fixed['candidate_boot_sha256'],
  'candidate_logdump_sha256':fixed['candidate_logdump_sha256'],'postboot_raw_sha256':sha(report_raw),
  'startup500_sha256':fixed['startup500_sha256'],'postboot_request':request}
 return adopted,src
def payload(d,src):
 # Reuse the actual frozen collector + audit to revalidate all facts immediately
 # before guard creation. Its former main block is not executed separately.
 prefix=src['postboot_device'].split(b"\nif __name__=='__main__':",1)[0]
 tail=r'''
request=ADOPTION['postboot_request'];fresh={};collect(request,fresh);verified=audit(fresh,request)
assert verified['passed'] and fresh['identity_before']==fresh['identity_after']
assert fresh['identity_before']['boot_id']==ADOPTION['boot']
assert os.uname().version==ADOPTION['version'] and os.uname().version.startswith('#501 ')
p=Path(ADOPTION['guard']);assert not p.exists() and not p.parent.exists()
os.umask(0o077);p.parent.mkdir(mode=0o700)
proof={'raw':fresh,'result':verified,'postboot_raw_sha256':ADOPTION['postboot_raw_sha256']}
for name,raw in [('fresh-validation-private.json',json.dumps(proof,indent=2).encode()),('boot-id-private.txt',(ADOPTION['boot']+'\n').encode())]:
 with (p.parent/name).open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
fd=os.open(p.parent,os.O_RDONLY|os.O_DIRECTORY)
try:os.fsync(fd)
finally:os.close(fd)
assert p.read_text().strip()==ADOPTION['boot']
print(json.dumps({'guard_created':True,'old_guards_preserved':True,'transaction_id':ADOPTION['transaction_id'],
 'boot_id':ADOPTION['boot'],'guard':ADOPTION['guard'],'candidate_pair_verified':True,
 'postboot_raw_sha256':ADOPTION['postboot_raw_sha256'],'fresh_validation_passed':True,'charging_controls_written':False}),flush=True)
'''
 return b'import sys\nif sys.flags.optimize:raise RuntimeError("optimized Python disables adoption checks")\n'+('ADOPTION='+repr(d)+'\n').encode()+prefix+tail.encode()
def publish(txdir,out,d,reply):
 assert all(reply[k]==v for k,v in {'guard_created':True,'old_guards_preserved':True,'transaction_id':d['transaction_id'],'boot_id':d['boot'],'guard':d['guard'],'candidate_pair_verified':True,'postboot_raw_sha256':d['postboot_raw_sha256'],'fresh_validation_passed':True}.items())
 pointer=BASE/'boot-adoption-private.json';before=(out/'boot-adoption-before-image501-private.json').read_bytes()
 assert pointer.read_bytes()==before,'global adoption changed; do not overwrite another owner'
 adoption=dict(guard_path=d['guard'],original_key_verified=True,baseline481_verified=True,charging_manifest_sha256=d['manifest'],
  candidate_boot_sha256=d['candidate_boot_sha256'],candidate_logdump_sha256=d['candidate_logdump_sha256'],
  Image501_verified=True,postboot_raw_sha256=d['postboot_raw_sha256'])
 endpoint=dict(kind='usb-ipv6',peer=PEER,interface_index=29,host_key_alias='169.254.42.1',original_key_verified=True,
  observed_new_boot=d['boot'],guard_path=d['guard'],postboot_Image501_passed=True)
 save(out/'new-endpoint-private.json',endpoint);save(out/'adoption-pointer-private.json',adoption)
 temp=BASE/(d['transaction_id']+'-adoption-next-private.json');create(temp,json.dumps(adoption,indent=2).encode());temp.replace(pointer)
 fd=os.open(BASE,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return adoption
def adopt(context,observed,window_confirmed=False):
 assert window_confirmed is True
 d,src=review(context,observed);txdir=Path(context).parent;out=txdir/'adoption-01-private';assert not out.exists()
 pointer_raw=(BASE/'boot-adoption-private.json').read_bytes();previous=json.loads(pointer_raw)
 assert previous['guard_path']==d['postboot_request']['guard']['old_boot_guard_path']
 assert previous['candidate_boot_sha256']==d['postboot_request']['guard']['rollback_boot_sha256']
 out.mkdir(mode=0o700);create(out/'boot-adoption-before-image501-private.json',pointer_raw)
 save(out/'adopt-request-private.json',d);code=payload(d,src);create(out/'executed-adoption-source.py',code)
 pins,_=sources();s=importlib.util.spec_from_file_location('image501_original_key',pins['strict_key_transport']['path'])
 host=importlib.util.module_from_spec(s);s.loader.exec_module(host)
 argv=[host.SSH,'-6','-T',*host.OPTIONS,'-o','HostKeyAlias=169.254.42.1','root@'+PEER,'python3 -']
 save(out/'dispatch-intent-private.json',{'request_count':1,'argv':argv,'payload_sha256':sha(code),'no_replay':True})
 with (out/'adopt-stdout-private.json').open('xb') as stdout,(out/'adopt-stderr-private.txt').open('xb') as stderr:
  child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=stdout,stderr=stderr,close_fds=True)
  # Wait this exact child to its real terminal; never timeout-kill or redispatch.
  try:child.communicate(input=code)
  finally:child.wait()
  stdout.flush();stderr.flush();os.fsync(stdout.fileno());os.fsync(stderr.fileno())
 save(out/'adopt-transport-terminal-private.json',{'pid':child.pid,'terminal':True,'returncode':child.returncode})
 assert child.returncode==0,'preserve original result and only inspect; do not repeat adoption'
 reply=json.loads((out/'adopt-stdout-private.json').read_bytes());result=publish(txdir,out,d,reply)
 save(out/'adoption-result-private.json',{'passed':True,'guard_created':True,'old_pointer_backup_preserved':True,'old_guards_preserved':True,'pointer':result})
 return {'adopted':True,'no_hardware_or_charge_control_write':True,'private_directory':str(out)}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--context');p.add_argument('--postboot-directory');p.add_argument('--execute-adopt',action='store_true');p.add_argument('--window-confirmed',action='store_true');a=p.parse_args()
 if not a.execute_adopt:sources();print(json.dumps({'checked':True,'device_accessed':False,'new_identity_or_pins_generated':False}));return
 print(json.dumps(adopt(a.context,a.postboot_directory,a.window_confirmed)))
if __name__=='__main__':main()
