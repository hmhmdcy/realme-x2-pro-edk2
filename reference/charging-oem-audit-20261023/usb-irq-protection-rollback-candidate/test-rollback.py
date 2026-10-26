"""Only actual newly affected rollback functions; IO/process boundaries are fake."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast,base64,copy,hashlib,importlib.util,json,os,subprocess,sys,tarfile
HERE=Path(__file__).resolve().parent
REF=HERE.parent.parent
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01')
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def check(ok,message='condition'):
    if not ok:raise AssertionError(message)


def main():
    m=load(HERE/'restore-worker.py','actual_rollback_worker')
    def contents(name):
        with tarfile.open(PRIVATE/name,'r:gz') as tar:
            return {'/'+x.name:tar.extractfile(x).read() for x in tar.getmembers()}
    original=contents('rollback-r8-payload.tar.gz');forward=contents('usb-irq-protection-payload.tar.gz')
    # Only the old fake-filesystem boundary class is reused. No old test body,
    # fake transaction algorithm or old test module is executed.
    oldtest=REF/'charging-ui-audit-20261023/usb-irq-protection-stage-candidate/test-stage.py'
    text=oldtest.read_text();node=next(n for n in ast.parse(text).body if isinstance(n,ast.ClassDef) and n.name=='FakeFS')
    fake_source=ast.get_source_segment(text,node)
    namespace=dict(Path=Path,os=os,m=m,old_bytes=forward,check=check)
    exec(compile(fake_source,str(oldtest),'exec'),namespace)
    FakeFS=namespace['FakeFS'];m.os=SimpleNamespace(**{**vars(os),'O_NOFOLLOW':getattr(os,'O_NOFOLLOW',0)})
    source=dict(boot_id='00000000-0000-4000-8000-000000000502',version=m.VERSION,
        serial_sha256='1'*64,compatible_sha256=sha(b'realme,samurai\0'),rootfs_sha256='2'*64)
    base=dict(schema='samurai-usb-irq-protection-rollback-request-v1',transaction_id='usb-irq-protection-rollback-synthetic001',
        profile=m.PROFILES[0],identity=copy.deepcopy(source),source_identity=copy.deepcopy(source),
        source_stage={'transaction_id':'usb-irq-protection-stage-synthetic001'},activation=None,
        payload_sha256=m.ROLLBACK_PAYLOAD,payload_base64=base64.b64encode((PRIVATE/'rollback-r8-payload.tar.gz').read_bytes()).decode(),
        worker_sha256=sha((HERE/'restore-worker.py').read_bytes()),lease_token='3'*48)
    cases=[]
    def reject(name,operation):
        try:operation()
        except (RuntimeError,ValueError,AssertionError,KeyError):cases.append(name)
        else:raise AssertionError(name)
    def request_for(profile):
        req=copy.deepcopy(base);req['profile']=profile
        if profile!=m.PROFILES[0]:
            req['identity']['boot_id']='00000000-0000-4000-8000-000000000503'
            boot=m.IRQ_BOOT if profile==m.PROFILES[1] else m.BOOT
            req['activation']=dict(schema='samurai-irq-rollback-saved-activation-binding-v1',activation_transaction_id='usb-irq-protection-activate-synthetic001',
                **{key:'4'*64 for key in ('context_sha256','guard_sha256','flash_request_sha256','flash_result_sha256','reboot_request_sha256','reboot_result_sha256')},
                flash_claimed_ns=1,reboot_claimed_ns=2,boot_sha256=boot,retained_logdump_sha256=m.LOGDUMP,
                action_pair=['flash-candidate','reboot-candidate'] if profile==m.PROFILES[1] else ['rollback-original','reboot-original'])
        return req
    class FakeDevice(m.Device):
        def __init__(self,request,stopped=True):
            super().__init__();self.request=request;self.fs=FakeFS();self.logs={};self.closed=False;self.stops=0
            self.out=Path('/synthetic/device-rollback');self.fail_source=self.fail_stop=self.fail_fresh=self.fail_close=False;self.expire=False
            boot,notes=m.expected_profile(request)
            self.actual=dict(identity=copy.deepcopy(request['identity']),release=m.RELEASE,machine='aarch64',taint='0',
                boot=dict(bytes=100663296,sha256=boot),logdump=dict(bytes=67108864,sha256=m.LOGDUMP),
                notes=copy.deepcopy(notes),module_states={n:'live' for n in notes})
            sample=dict(valid=1,protection_ok=1,shadow=0,age_ms=5,cell1_uv=4300000,cell2_uv=4300000,pack_uv=8600000,
                temp_decic=265,error=0,stop_error=0,latched=0,fault=0,cycle_timeout=0,thermal_inhibit=0,gauge_charge_stop=0)
            registers={'00':10,'01':0,'02':5,'03':0,'04':0x68,'05':0,'07':0,'08':8 if stopped else 0x10,'09':0,'0f':10,'13':2}
            self.observation=dict(read_start=99.5,read_end=99.8,sample=sample,notes=copy.deepcopy(notes),
                state=dict(boot_id=request['identity']['boot_id'],registers=registers,driver='samurai-mp2650',taint='0',
                    camera_pm={str(x):'suspended' for x in range(4)},m2m=json.dumps(dict(users=0,running=False,fatal=False,pinned=False,orphans=0,first_error=0))),
                limits=dict(input_ua=500000,charge_ua=250000,cv_pack_uv=8725000),source=dict(current_max='500000'),
                charge_behaviour='inhibit-charge' if stopped else 'auto',protection_health='Good',
                protection=dict(id=0x2719,error=0,safety=0,pf=0,operation=0x300,manufacturing=0x18))
        def begin(self,request):pass
        def source_proof(self,request):
            if self.fail_source:raise RuntimeError('synthetic source worker not terminal')
            return dict(source_stage_terminal_verified=True)
        def current(self,request,carriers=True):return copy.deepcopy(self.actual)
        def manager(self):return {}
        def verify_retained(self,manager):check(self.fs.files[m.MANIFEST]==forward[m.MANIFEST])
        def read_owned(self,path):return self.fs.reader(path)
        def now(self):return 100
        def observe(self,manager):
            value=copy.deepcopy(self.observation)
            if self.fail_fresh:value['sample']['age_ms']=-1
            return value
        def backup(self,files,before):
            for path,(raw,mode) in files.items():self.logs[Path(path).name+'.before']=raw
            self.log('before-private.json',before)
        def stop(self,manager,meta):
            self.stops+=1
            if self.fail_stop:raise RuntimeError('synthetic normal stop failed')
            self.observation['state']['registers']['08']=8;self.observation['charge_behaviour']='inhibit-charge'
        def replace(self,path,raw):return m.atomic_replace(path,raw,self.request['transaction_id'],m.NEW_FILES[path],self.event,ops=self.fs,reader=self.read_owned)
        def check_window(self,request):
            if self.expire and self.fs.renames:raise RuntimeError('synthetic expired between files')
        def verify_restored(self,files,manager):check(all(self.fs.files[p]==r for p,r in files.items()))
        def event(self,value):self.events.append(value)
        def log(self,name,value):self.logs[name]=copy.deepcopy(value)
        def finish(self,result):
            with patch.object(m,'read_owned',self.read_owned):super().finish(result)
        def close(self):
            self.closed=True
            if self.fail_close:raise RuntimeError('synthetic close failed')
        def publish(self,result):self.logs['result.json']=copy.deepcopy(result)
    for profile in m.PROFILES:
        req=request_for(profile);device=FakeDevice(req);result=m.restore(req,device,execute=True)
        check(result['restored'] and result['status']=='staged_original/runtime_pending',json.dumps(result))
        check(device.fs.renames==m.ORDER and device.stops==0 and device.closed and device.actual['notes']==m.expected_profile(req)[1])
        cases.append('actual restore all three exact files, INHIBIT retained: '+profile)
    req=request_for(m.PROFILES[1]);device=FakeDevice(req,stopped=False);result=m.restore(req,device,execute=True)
    check(result['restored'] and device.stops==1);cases.append('enabled input uses one normal stop, no module lifecycle')
    for budget in ('0',{'errno':61},None):
        device=FakeDevice(req);device.observation['source']['current_max']=budget
        device.observation['sample'].update(latched=1,cycle_timeout=1,error=-110)
        result=m.restore(req,device,execute=True);check(result['restored'] and result['existing_fault_history']['latched']==1 and device.stops==0)
    cases.append('unknown zero ENODATA source budget is evidence only while fresh stopped hard-cap state holds')
    for name,change in [('missing fresh sample',lambda d:d.observation['sample'].update(valid=0,age_ms=-1,cell1_uv=0,cell2_uv=0)),
                        ('protection unavailable',lambda d:d.observation['protection'].update(error=-5)),
                        ('hardware exceeds input hard cap',lambda d:d.observation['limits'].update(input_ua=950000)),
                        ('wrong current live notes',lambda d:d.actual['notes'].update({'samurai-usb-input':m.OLD_NOTES['samurai-usb-input']})),
                        ('postboot still source UUID',lambda d:d.actual['identity'].update(boot_id=d.request['source_identity']['boot_id']))]:
        device=FakeDevice(copy.deepcopy(req));change(device);result=m.restore(device.request,device,execute=True)
        check(not result['restored'] and not device.fs.renames and device.stops==0);cases.append(name+' gives zero replacement')
    for attr in ('fail_source','fail_stop'):
        device=FakeDevice(copy.deepcopy(req),stopped=False);setattr(device,attr,True);result=m.restore(device.request,device,execute=True)
        check(not result['restored'] and not device.fs.renames);cases.append(attr+' gives zero replacement')
    device=FakeDevice(req);device.expire=True;result=m.restore(req,device,execute=True)
    check(not result['restored'] and device.fs.renames==[m.USB] and result['disk_state']=='partial_known');cases.append('lease expires after first ko, partial kept and no replay')
    for phase in ('rename','directory-fsync','readback'):
        device=FakeDevice(req);device.fs.failure=(m.PROTECTION,phase);result=m.restore(req,device,execute=True)
        check(not result['restored'] and result['primary_error']['atomic_stage']==phase and device.closed)
        check(device.fs.files[m.MANIFEST]==forward[m.MANIFEST]);cases.append('original atomic '+phase+' failure keeps exact partial state and manifest new')
    device=FakeDevice(req);device.fail_close=True;result=m.restore(req,device,execute=True)
    check(not result['restored'] and device.fs.renames==m.ORDER and result['disk_state']=='all_original_fsynced' and result['close_error'])
    cases.append('close error after exact old fsync cannot claim successful transaction')
    for profile in m.PROFILES:
        r=request_for(profile);actual=FakeDevice(r).actual
        if profile==m.PROFILES[0]:actual['notes']=m.NEW_NOTES
        else:actual['boot']['sha256']=m.BOOT if profile==m.PROFILES[1] else m.IRQ_BOOT
        reject('profile tuple cannot be guessed or mixed: '+profile,lambda r=r,actual=actual:m.validate_profile(r,actual))
    # Real manager stop/inhibit functions, fake only their existing file IO.
    manager_path=REF/'charging-session-20261023/r8-source-integration/rootfs-sources/usr/sbin/samurai-charging'
    source_text=manager_path.read_text();functions={n.name:ast.get_source_segment(source_text,n) for n in ast.parse(source_text).body if isinstance(n,ast.FunctionDef)}
    writes=[];registers={'08':0x10}
    class FakePath:
        def __init__(self,path=''):self.path=path
        def __truediv__(self,name):return FakePath(self.path+'/'+name)
        def mkdir(self,**kw):pass
        def read_text(self):return 'synthetic boot'
        def resolve(self):return SimpleNamespace(name='samurai-mp2650')
        def write_text(self,value):writes.append((self.path,value));registers['08']=8
    scope=dict(Path=FakePath,STATE=FakePath('/state'),live=SimpleNamespace(PSY=FakePath('/psy'),CLIENT=FakePath('/client'),registers=lambda:dict(registers)))
    exec(compile(functions['inhibit']+'\n\n'+functions['command'],str(manager_path),'exec'),scope)
    check(scope['command']({},'stop')=={'managed':True,'requested':'inhibit-charge'} and len(writes)==1 and registers['08']==8)
    cases.append('actual manager614 stop branch only normal inhibit and hardware readback')
    result=dict(passed=True,count=len(cases),cases=cases,
        tested_files={n:sha((HERE/n).read_bytes()) for n in ('restore-worker.py','worker-body.py.inc','test-rollback.py')},
        actual_transaction_profile_safe_stopped_and_atomic_functions=True,old_fake_filesystem_class_only_sha256=sha(fake_source.encode()),
        actual_manager_stop_functions=True,old_suites_rerun=False,synthetic_request_only=True,
        device_SSH_USB_PM_build_SDK_Git=False,host_supervisor_or_dispatcher_implemented=False)
    with (HERE/'test-result.json').open('w') as file:file.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,count=len(cases))))


if __name__=='__main__':main()
