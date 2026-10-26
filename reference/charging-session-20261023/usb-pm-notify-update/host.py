"""One USB PM-notification update. Original stage, supervision and SSH ownership."""
from pathlib import Path
import argparse,ast,base64,hashlib,importlib.util,json,os,secrets,sys
sys.dont_write_bytecode=True
if sys.flags.optimize:raise RuntimeError('nonoptimized Python required')
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=BASE/'usb-pm-notify-update-live-20261024-01'
TX='irq-native-usb-pm-stage-notify-20261024-01'
REMOTE='/root/charging-management-20261023/'+TX
VERSION='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
LEAF=ROOT/'reference/charging-oem-audit-20261023/usb-input-pm-notify-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def need(ok,msg):
 if not ok:raise RuntimeError(msg)
def load(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def save(path,obj):
 with path.open('x') as f:json.dump(obj,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def create(path,raw):
 with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
POST=HERE.parent/'irq-native-usb-pm-postboot-host-candidate'
sys.path.insert(0,str(POST))
import host as transport_host
import adopt
def call(label,code,readonly=True):
 ast.parse(code);out=OUT/label;out.mkdir(mode=0o700)
 create(out/'executed-source.py',code)
 if readonly:reply=transport_host.PROFILE.send_readonly(out,code,collection=True)
 else:reply=adopt.transfer(out,code,transport_host,transport_host.PEER)
 save(out/'reply.json',reply);return reply
def replace(source,old,new,count=1):
 need(source.count(old)==count,'unexpected derivation: '+old[:100]);return source.replace(old,new)
def bind():
 need(not OUT.exists(),'intent exists; observe original only')
 c=json.loads((LEAF/'cohort-result.json').read_bytes());ko=json.loads((LEAF/'ko-result.json').read_bytes())
 need(c['passed'] and c['target_usb_sha256']==ko['module_sha256']=='ebfcb45d436f0f08dcaf4e400ea18b18cf3bd208863de33444e76c20faab4624','current r2 build')
 need(ko['passed'] and not ko['diagnostics'] and all(x['terminal'] and x['returncode']==0 for x in ko['commands']),'clean actual build')
 previous=BASE/'irq-native-usb-pm-activation/irq-native-usb-pm-activate-live-20261024-01/pm-adoption-01-private'
 a=json.loads((previous/'adopt-request-private.json').read_bytes());pointer=(BASE/'boot-adoption-private.json').read_bytes()
 need(pointer==(previous/'adoption-pointer-private.json').read_bytes(),'actual current adoption')
 need(a['boot']=='a13eab37-b5b3-4365-b1bd-8a7345290ae0' and a['manifest']==c['source_manifest_sha256'] and a['version']==VERSION,'source504')
 os.umask(0o077);OUT.mkdir(mode=0o700)
 create(OUT/'previous-pointer.json',pointer)
 raw=call('cache-read',('EXPECTED='+repr(a['boot'])+'\n').encode()+br'''
from pathlib import Path
import hashlib,json
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==EXPECTED
p=Path('/sys/devices/platform/samurai-gauge-protection/mac_evidence');raw=p.read_bytes()
first=dict(x.split('=',1) for x in raw.decode().splitlines()[0].split())
assert (first['attempted'],first['terminal']) in [('0','0'),('1','1')]
print(json.dumps(dict(sha256=hashlib.sha256(raw).hexdigest(),first=first)))
''')
 source=(ROOT/'reference/charging-oem-audit-20261023/irq-native-usb-pm-stage-candidate/stage-worker.py').read_text()
 original=sha(source.encode())
 for old,new in [
 ("VERSION='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'","VERSION="+repr(VERSION)),
 ("OLD='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'","OLD="+repr(c['source_manifest_sha256'])),
 ("USB_OLD='7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f'","USB_OLD="+repr(c['source_usb_sha256'])),
 ("USB_NEW='d04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037'","USB_NEW="+repr(c['target_usb_sha256'])),
 ("'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d'",repr(c['source_module_note_sha256'])),
 ("MAC_CACHE_SHA='02c98143301bb5db896c6f535f490495428df8b8c6fd6ab3cdc69ca507a545a8'","MAC_CACHE_SHA="+repr(raw['sha256'])),
 ("'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'",repr(c['retained_logdump_sha256'])),
 ("COHORT='89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01'","COHORT="+repr(sha((LEAF/'cohort-result.json').read_bytes()))),
 ("NEW='34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b'","NEW="+repr(c['target_manifest_sha256'])),
 ("PAYLOAD='f1162d2b5614327f0ce78c918cec62fd681d42cca99d8c03819cfa41086230bc'","PAYLOAD="+repr(c['forward']['sha256'])),
 ("len(raw)==27163","len(raw)=="+str(c['forward']['bytes'])),
 ("r'usb-irq-protection-activate-[a-z0-9-]{8,48}'","r'irq-native-usb-pm-activate-[a-z0-9-]{8,48}'"),
 ("expected['adapter_revision']='usb-irq-native-pm-budget504-01'","expected['adapter_revision']='usb-irq-native-pm-notify-02'"),
 ("first.get('attempted') == first.get('terminal') == '1' and sha(raw) == MAC_CACHE_SHA","(first.get('attempted'), first.get('terminal')) in [('0','0'), ('1','1')] and sha(raw) == MAC_CACHE_SHA")]:source=replace(source,old,new)
 create(OUT/'stage-worker.py',source.encode());worker=load(OUT/'stage-worker.py','notify_stage_local')
 payload=(BASE/'usb-input-pm-notify-cohort-private-02/forward-two-files.tar.gz').read_bytes()
 need(sha(payload)==c['forward']['sha256'],'actual package')
 req=dict(schema='samurai-irq-native-usb-pm-stage-request-v1',transaction_id=TX,cohort_delivery_sha256=worker.COHORT,
  payload_sha256=c['forward']['sha256'],payload_base64=base64.b64encode(payload).decode(),worker_sha256=sha(source.encode()),lease_token=secrets.token_hex(24),
  identity=dict(boot_id=a['boot'],version=a['version'],serial_sha256=a['serial_sha256'],compatible_sha256=a['compatible_sha256'],rootfs_sha256=a['rootfs']),
  adoption=dict(transaction_id=a['transaction_id'],guard_path=a['guard'],guard_sha256=sha((a['boot']+'\n').encode())))
 worker.unpack(req);worker.manifest_delta(json.loads((BASE/'usb-input-pm-notify-cohort-private-02/manifest-old.json').read_bytes()),json.loads((BASE/'usb-input-pm-notify-cohort-private-02/manifest-new.json').read_bytes()))
 save(OUT/'request-private.json',req);save(OUT/'derivation.json',dict(original_sha256=original,derived_sha256=sha(source.encode()),changes='504/d046 source identity, exact r2 package, new current adoption and read-only actual cache; original safety and atomic bodies retained'))
 return dict(bound=True,module=c['target_usb_sha256'])
def request():
 r=json.loads((OUT/'request-private.json').read_bytes());need(sha((OUT/'stage-worker.py').read_bytes())==r['worker_sha256'],'worker changed');return r
def preflight():
 r=request();raw=(json.dumps(r,indent=2)+'\n').encode()
 code=("import io,sys\nsys.stdin=io.TextIOWrapper(io.BytesIO("+repr(raw)+"))\nsys.argv=['stage','--preflight']\n__file__='preflight.py'\n").encode()+(OUT/'stage-worker.py').read_bytes()
 reply=call('preflight',code);need(reply['passed'] and reply['eligible'],str(reply.get('reason')));return dict(passed=True,mode=reply['healthy_state'])
def launch():
 r=request();p=json.loads((OUT/'preflight/reply.json').read_bytes());need(p['passed'] and p['eligible'],'preflight')
 worker=("import io,sys,runpy\nsys.stdin=io.TextIOWrapper(io.BytesIO("+repr((OUT/'request-private.json').read_bytes())+"))\nsys.argv=['stage','--execute-stage']\nrunpy.run_path("+repr(REMOTE+'/stage-worker.py')+",run_name='__main__')\n").encode()
 supervisor=(POST/'pm-smoke-supervisor.py').read_bytes()
 files={'stage-worker.py':(OUT/'stage-worker.py').read_bytes(),'worker.py':worker,'supervisor.py':supervisor,'request-private.json':(OUT/'request-private.json').read_bytes(),
  'rollback-two-files.tar.gz':(BASE/'usb-input-pm-notify-cohort-private-02/rollback-two-files.tar.gz').read_bytes()}
 packet=dict(root=REMOTE,boot_id=r['identity']['boot_id'],request=r,files={n:base64.b64encode(b).decode() for n,b in files.items()},hashes={n:sha(b) for n,b in files.items()})
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
lease=dict(transaction_id=r['transaction_id'],boot_id=r['identity']['boot_id'],token=r['lease_token'],owner='charging',exclusive=True,camera_released=True,bluetooth_released=True,issued_boottime_s=now,expires_boottime_s=now+120)
save(Path('/run')/(r['transaction_id']+'-window-private.json'),(json.dumps(lease)+'\n').encode())
save(root/'launch-private.json',(json.dumps(dict(worker_sha256=PACKET['hashes']['worker.py'],boot_id=PACKET['boot_id']))+'\n').encode())
with (root/'supervisor-stdout-private.txt').open('xb') as out,(root/'supervisor-stderr-private.txt').open('xb') as err:
 child=subprocess.Popen([sys.executable,'-B',str(root/'supervisor.py'),'--supervise',str(root)],stdin=subprocess.DEVNULL,stdout=out,stderr=err,close_fds=True,start_new_session=True)
 stat=Path('/proc',str(child.pid),'stat').read_text().rsplit(')',1)[1].split();receipt=dict(pid=child.pid,startticks=int(stat[19]),argv=[p.decode() for p in Path('/proc',str(child.pid),'cmdline').read_bytes().split(bytes([0])) if p])
 save(root/'supervisor-launch-private.json',(json.dumps(receipt)+'\n').encode())
print(json.dumps(dict(launched=True,supervisor=receipt)))
'''
 return call('launch',code,False)
def fetch():
 code=('REMOTE='+repr(REMOTE)+'\n').encode()+br'''
from pathlib import Path
import base64,hashlib,json
root=Path(REMOTE);files={}
for p in root.rglob('*'):
 if p.is_file() and p.suffix not in ('.before','.gz'):
  raw=p.read_bytes();assert len(raw)<2000000;files[str(p.relative_to(root))]=dict(sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
print(json.dumps(dict(files=files)))
'''
 reply=call('fetch-'+secrets.token_hex(4),code);out=OUT/('raw-'+secrets.token_hex(4));out.mkdir(mode=0o700)
 for name,row in reply['files'].items():
  p=out/name;need(p.is_relative_to(out),'path');p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(row['base64'],validate=True);need(sha(raw)==row['sha256'],'fetch');create(p,raw)
 save(OUT/('fetch-selection-'+out.name+'.json'),dict(raw_directory=str(out)))
 term=out/'worker-terminal-private.json';result=out/'device-stage/result.json'
 return dict(raw_directory=str(out),terminal=json.loads(term.read_bytes()) if term.exists() else None,result=json.loads(result.read_bytes()) if result.exists() else None)
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['bind','preflight','launch','fetch']);a=p.parse_args();reply=globals()[a.action]();print(json.dumps(reply,indent=2))
if __name__=='__main__':main()
