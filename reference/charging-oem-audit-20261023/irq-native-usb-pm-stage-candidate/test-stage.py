"""Small actual-stage/atomic compositions; only device/manager boundaries are faked."""
from pathlib import Path
import base64,copy,hashlib,importlib.util,json,os,tarfile,tempfile,time
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
spec=importlib.util.spec_from_file_location('stage_worker',HERE/'stage-worker.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
package=PRIVATE/'irq-native-usb-pm-budget504-cohort-private-01'
payload=(package/'irq-native-pm-payload.tar.gz').read_bytes()
oldraw=(PRIVATE/'charger-reattach-observation-payload-private-01/manifest-new.json').read_bytes()
oldusb=(PRIVATE/'usb-input-irq-board-private-01/samurai-usb-input-irq-private.ko').read_bytes()
with tarfile.open(PRIVATE/'r6-candidate/r5-to-r6-payload.tar.gz') as a:service=a.extractfile(u.SERVICE.lstrip('/')).read()
sample={k:int(v,0) for k,v in (x.split('=') for x in json.loads((PRIVATE/'charger-readonly-before-update-01-private/stdout-private.json').read_bytes())['telemetry'].split())}
request=dict(schema='samurai-irq-native-usb-pm-stage-request-v1',transaction_id='irq-native-usb-pm-stage-offline-fixture',cohort_delivery_sha256=u.COHORT,payload_sha256=u.PAYLOAD,
payload_base64=base64.b64encode(payload).decode(),worker_sha256=u.sha((HERE/'stage-worker.py').read_bytes()),lease_token='5'*48,
identity=dict(boot_id='11111111-2222-3333-4444-555555555555',version=u.VERSION,serial_sha256='1'*64,compatible_sha256='2'*64,rootfs_sha256='3'*64),
adoption=dict(transaction_id='usb-irq-protection-activate-fixture0001',guard_path='/var/lib/samurai/usb-irq-protection-activate-fixture0001-adopted/boot-id-private.txt',guard_sha256='4'*64))
files,newmeta=u.unpack(request);u.manifest_delta(json.loads(oldraw),newmeta)

class Fake(u.Device):
    def __init__(self,root,full=False,fail=None):
        super().__init__(json.dumps(request).encode());self.root=Path(root);self.request=copy.deepcopy(request)
        self.current={u.USB:self.root/'usb',u.MANIFEST:self.root/'manifest'}
        for k,raw in [(u.USB,oldusb),(u.MANIFEST,oldraw)]:self.current[k].write_bytes(raw);self.current[k].chmod(0o600)
        self.running=True;self.full=full;self.full_cause=3 if full else 0;self.fail=fail;self.calls=[];self.badcache=False
    def read_owned(self,path):
        if str(path)==u.SERVICE:return service,0o755
        return u.read_owned(self.current[str(path)])
    def identity(self,request):return dict(request['identity'],guard_sha256=request['adoption']['guard_sha256'])
    def begin(self,request):
        self.calls.append('begin');self.out=self.root/'device-stage';self.out.mkdir(mode=0o700,exist_ok=False)
    def open_readonly(self,request):self.calls.append('readonly-shared-lock')
    def check_window(self,request):self.calls.append('window')
    def manager(self,expected):
        assert expected==u.SERVICE_SHA==u.sha(service)
        def command(meta,action):
            assert action=='stop';self.calls.append('stop');self.running=False
            if self.fail=='stop':raise RuntimeError('stop failed')
            if self.fail=='full-lost':self.full=False;self.full_cause=0
        return {'_r8_code_sha256':expected,'command':command}
    def verify(self,manager):
        meta=json.loads(self.read_owned(u.MANIFEST)[0]);assert u.sha(self.read_owned(u.USB)[0])==meta['installed_files'][u.USB];return meta
    def notes_match(self,manager,old,backups=False):
        assert old['modules']['samurai-usb-input']['sha256']==u.USB_OLD
        if backups:assert u.sha((self.out/'samurai-usb-input.ko.before').read_bytes())==u.USB_OLD
    def module_state(self,name='samurai-mp2650'):return 'live'
    def mac_evidence(self):return {'sha256':'changed' if self.badcache else u.MAC_CACHE_SHA,'attribute_dev':3,'attribute_inode':4,'instance_inode':5,'raw_base64':'fixture-only'}
    def observe(self,manager):
        now=time.clock_gettime(time.CLOCK_BOOTTIME);s=copy.deepcopy(sample)
        s.update(logical_full=int(self.full),full_cause=self.full_cause,hold_requested=int(self.full and self.running),full_holding=int(self.full and self.running),desired_enable=int(self.running and not self.full),session_seconds=0)
        r={'00':10,'0f':10,'02':5,'04':104,'08':8 if not self.running else 0 if self.full else 0x10,'13':2 if not self.running else 0xe if self.full else 6}
        state=dict(boot_id=request['identity']['boot_id'],release=u.RELEASE,driver='samurai-mp2650',taint='0',registers=r,
                   camera_pm={str(k):'suspended' for k in range(4)},m2m=json.dumps(dict(users=0,orphans=0,jobs=0,first_error=0,running=False,fatal=False,pinned=False)),
                   services=[dict(comm=k,pid=i+20,uid=10000) for i,k in enumerate(['phoc','phosh','pipewire','wireplumber'])])
        return dict(state=state,registers=r,sample=s,limits=dict(native_ua=500000,source_budget_ua=500000,input_ua=500000,charge_ua=250000,cv_uv=4362500),
                    source=dict(online='1',usb_type='Unknown [SDP] DCP CDP C',current_max='500000',input_current_limit='500000'),
                    notes=copy.deepcopy(u.NOTES),openrc_started=True,identity=self.identity(request),mac_evidence=self.mac_evidence(),read_start=now,read_end=now,
                    protection=dict(id=0x2719,error=0,safety=0,pf=0,operation=0x300,manufacturing=0x18),protection_health='Good')
    def registers(self):return self.observe(None)['registers']
    def replace(self,name,raw,restore=False):
        self.calls.append(('restore:' if restore else 'forward:')+Path(name).name)
        if self.fail=='unknown' and not restore:
            self.uncertain=True;raise RuntimeError('unknown original owner boundary')
        path=self.current[name];current,mode=u.read_owned(path)
        assert mode==0o600 and u.sha(current) in (u.OLD_FILES[name],u.NEW_FILES[name]) and not self.running
        def record(row):
            self.event(row)
            if self.fail in ('usb-renamed','manifest-renamed','cache-renamed') and row['step']=='renamed' and not restore and (name==u.MANIFEST)==(self.fail=='manifest-renamed'):
                which=self.fail;self.fail=None
                if which=='cache-renamed':self.badcache=True
                raise RuntimeError('injected after actual rename')
        if restore and current==raw:return
        u.atomic_replace(path,raw,request['transaction_id']+('-restore' if restore else ''),u.sha(current),record)
    def close(self):self.calls.append('close')

cases=[]
def case(name,fn):fn();cases.append(dict(name=name,passed=True))
def one(fn,**kwargs):
    with tempfile.TemporaryDirectory() as root:
        f=Fake(root,**kwargs);return fn(f)
def success(f):
    r=u.stage(request,f,True);assert r['staged'] and r['status']=='staged/runtime_pending' and r['disk_state']=='all_new_fsynced'
    assert f.calls.count('stop')==1 and not f.running and r['new_module_loaded'] is False and r['activation_attempted'] is False
    assert all(r['final_files'][n]['sha256']==u.NEW_FILES[n] for n in u.ORDER)
    before=json.loads((f.out/'before-private.json').read_bytes());after=json.loads((f.out/'after-private.json').read_bytes())
    assert before['notes']==after['notes']==u.NOTES and before['mac_evidence']==after['mac_evidence']
    return f,r,before,after
case('managed-cold-stage-only-two-disk-files-no-module-operation',lambda:one(success))
def full(f):
    _,r,b,a=success(f)
    assert b['sample']['logical_full']==b['sample']['full_holding']==b['sample']['hold_requested']==1
    assert a['sample']['logical_full']==1 and a['sample']['full_cause']==3 and a['sample']['session_seconds']==0
    assert a['sample']['full_holding']==a['sample']['hold_requested']==a['sample']['desired_enable']==0 and a['registers']['08']&0x18==8
case('healthy-Full-stop-retains-logical-cause-session-zero-while-holding-clears',lambda:one(full,full=True))
def refusal(f):
    r=u.stage(request,f,True);assert not r['staged'] and not any(x.startswith('forward:') for x in f.calls if isinstance(x,str))
    assert all(r['final_files'][n]['sha256']==u.OLD_FILES[n] for n in u.ORDER)
case('lost-Full-fact-before-replacement-rejected-with-old-disk',lambda:one(refusal,full=True,fail='full-lost'))
case('stop-failure-before-replacement-zero-file-writes',lambda:one(refusal,fail='stop'))
def restored(f):
    r=u.stage(request,f,True);assert not r['staged'] and r['restored_original_disk'] and r['disk_state']=='all_old'
    assert not f.running and f.calls.count('stop')==1 and r['status']=='failed_old_disk_restored_inhibited'
case('actual-first-file-rename-error-restores-original-two-files-inhibited',lambda:one(restored,fail='usb-renamed'))
case('actual-manifest-rename-error-restores-original-two-files-inhibited',lambda:one(restored,fail='manifest-renamed'))
def unknown(f):
    r=u.stage(request,f,True);assert not r['staged'] and not r['terminal'] and not any(x.startswith('restore:') for x in f.calls if isinstance(x,str))
case('unknown-original-owner-no-replay-or-fallback',lambda:one(unknown,fail='unknown'))
def cache_change(f):
    r=u.stage(request,f,True);assert not r['staged'] and r['recovery_error'] and not any(x.startswith('restore:') for x in f.calls if isinstance(x,str))
    assert r['disk_state']=='partial_known' and not f.running
case('changed-protection-instance-cache-no-further-disk-action',lambda:one(cache_change,fail='cache-renamed'))
def replay(f):
    success(f);before={k:f.read_owned(k) for k in u.ORDER};count=f.calls.count('stop')
    r=u.stage(request,f,True);assert not r['staged'] and f.calls.count('stop')==count and {k:f.read_owned(k) for k in u.ORDER}==before
case('exclusive-directory-prevents-same-transaction-replay',lambda:one(replay))
def readonly(f):
    r=u.preflight(request,f,f.request_raw)
    assert r['passed'] and r['identity_match'] and r['eligible'] and r['healthy_state']=='full_holding'
    assert r['directory_or_lease_created'] is False and f.calls==['readonly-shared-lock','close']
    assert f.out is None and not (f.root/'device-stage').exists() and f.full and f.running
case('readonly-Full-preflight-is-cold-stage-eligible-no-stop-directory-or-lease',lambda:one(readonly,full=True))
def readonly_bad(f):
    r=copy.deepcopy(request);r['identity']['version']='#501 wrong'
    out=u.preflight(r,f,json.dumps(r).encode())
    assert not out['passed'] and not out['eligible'] and f.calls==['close'] and f.out is None
case('readonly-preflight-rejects-old-kernel-request-before-device-access',lambda:one(readonly_bad))
result=dict(passed=True,groups=len(cases),cases=cases,tested_files={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['stage-worker.py','test-stage.py']},
            actual_frozen_forward_payload_used=True,identity_and_hardware_models_only=True,actual_atomic_replace_used_on_private_temp_files=True,device_accessed=False,old_matrices_rerun=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
