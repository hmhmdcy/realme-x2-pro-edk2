"""Actual inverse/core/source checks; OS, processes and hardware are models."""
from pathlib import Path
import ast,base64,copy,hashlib,importlib.util,json,os,struct,tempfile,time,types
HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('actual_timer_cold_rollback',HERE/'restore-worker.py')
fixture_module=load('same_forward_fixture',HERE/'test-source-fixture.py')
fixture=fixture_module.make_fixture(m);raws=fixture['raws']
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
inverse=(BASE/'charge-timer-hold-cohort-private-02/rollback-two-files.tar.gz').read_bytes()
new_manifest=(BASE/'charge-timer-hold-cohort-private-02/manifest-new.json').read_bytes()
new_charger=fixture['forward_files'][m.TARGET]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def request_for(profile):
    identity=copy.deepcopy(m.SOURCE_IDENTITY)
    if profile==m.PROFILES[1]:identity['boot_id']='77777777-8888-4999-aaaa-bbbbbbbbbbbb'
    paths=m.source_paths(m.SOURCE_TX)
    return dict(schema='samurai-charger-timer-cold-rollback-request-v1',transaction_id='charger-timer-cold-rollback-offline-fixture',
        profile=profile,identity=identity,source_identity=copy.deepcopy(m.SOURCE_IDENTITY),
        source_stage=dict(transaction_id=m.SOURCE_TX,evidence={name:dict(path=paths[name],sha256=sha(raw)) for name,raw in raws.items()}),
        current_cache=copy.deepcopy(fixture['post']['raw']['protection_cache_after']),payload_sha256=m.ROLLBACK_PAYLOAD,
        payload_base64=base64.b64encode(inverse).decode(),worker_sha256=sha((HERE/'restore-worker.py').read_bytes()),lease_token='a'*48)
def observations(request):
    if request['profile']==m.PROFILES[1]:
        value=dict(state='source_boot_ended',source_boot_id=m.SOURCE_IDENTITY['boot_id'],current_boot_id=request['identity']['boot_id'])
        return {'worker':copy.deepcopy(value),'supervisor':copy.deepcopy(value)}
    return {role:dict(state='absent',pid=json.loads(raws[role+'_process'])['pid']) for role in ['worker','supervisor']}
cases=[]
for profile in m.PROFILES:
    request=request_for(profile);files=m.unpack(request)
    assert set(files)==set(m.ORDER) and len(json.dumps(request).encode())<100000
    proof=m.verify_source_records(request,raws,observations(request));assert proof['source_stage_terminal_verified']
cases.append(dict(name='both_actual_inverse_profiles_and_seventeen_source_records',passed=True))

for failure in ['worker-terminal','wrong-source-boot','fault-after-stage','old-backup']:
    request=request_for(m.PROFILES[1]);changed=copy.deepcopy(raws)
    key={'worker-terminal':'worker_terminal','wrong-source-boot':'before','fault-after-stage':'after','old-backup':'old_charger'}[failure]
    if key=='old_charger':changed[key]=new_charger
    else:
        row=json.loads(changed[key])
        if key=='worker_terminal':row['returncode']=1
        elif key=='before':row['state']['boot_id']='00000000-1111-4222-8333-444444444444'
        else:row['sample']['latched']=1
        changed[key]=(json.dumps(row,indent=2)+'\n').encode()
    request['source_stage']['evidence'][key]['sha256']=sha(changed[key])
    try:m.verify_source_records(request,changed,observations(request))
    except (AssertionError,RuntimeError):pass
    else:raise AssertionError('forged source accepted: '+failure)
    cases.append(dict(name='source_rejects_'+failure,passed=True))

def electrical_profile(request):
    profile=m.expected_profile(request)
    return dict(identity=copy.deepcopy(request['identity']),release=m.RELEASE,machine='aarch64',taint='0',
                boot=dict(bytes=100663296,sha256=m.BOOT),logdump=dict(bytes=67108864,sha256=m.LOGDUMP504),
                notes=copy.deepcopy(profile['notes']),module_states={name:'live' for name in profile['notes']},current_cache=copy.deepcopy(request['current_cache']))

service=fixture['artifacts'][m.SERVICE].decode()
function_names=['verify','inhibit','command']
service_functions=[n for n in ast.parse(service).body if isinstance(n,ast.FunctionDef) and n.name in function_names]
assert len(service_functions)==3
for profile,full,fault,already_stopped,failure in [
    (m.PROFILES[0],True,False,False,None),
    (m.PROFILES[1],False,True,True,None),
    (m.PROFILES[1],True,False,False,'lost-Full'),
    (m.PROFILES[1],True,False,False,'rename-manifest')]:
    request=request_for(profile)
    with tempfile.TemporaryDirectory(prefix='samurai-timer-inverse-') as directory:
        root=Path(directory);paths={}
        artifacts={**fixture['artifacts'],m.TARGET:new_charger,m.MANIFEST:new_manifest}
        for target,raw in artifacts.items():
            p=root/target.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o755 if target==m.SERVICE else 0o600);paths[target]=p
        paths['/sys/firmware/devicetree/base/compatible']=root/'compatible';paths['/sys/firmware/devicetree/base/compatible'].write_bytes(b'realme,samurai\0qcom,sm8150\0')
        paths['/proc/sys/kernel/random/boot_id']=root/'boot-id';paths['/proc/sys/kernel/random/boot_id'].write_text(request['identity']['boot_id']+'\n')
        def mapped(value,*parts):
            p=Path(value,*parts);return paths.get(p.as_posix(),p)
        old_path=m.Path;old_reader=m.read_owned;m.Path=mapped
        m.read_owned=lambda value,*args,**kwargs:old_reader(mapped(value),*args,**kwargs)
        psy=root/'psy';supply=psy/'mp2650-input';supply.mkdir(parents=True)
        behaviour=supply/'charge_behaviour';behaviour.write_text('inhibit-charge' if already_stopped else 'auto')
        client=root/'client';client.mkdir();driver=root/'samurai-mp2650';driver.mkdir();(client/'driver').symlink_to(driver)
        class Device(m.Device):
            def __init__(self):
                super().__init__();self.request=request;self.out=root/'evidence';self.out.mkdir();self.control=[];self.injected=False
                self.journal=(self.out/'journal-private.jsonl').open('xb')
            def begin(self,r):self.request=r
            def source_proof(self,r):return m.verify_source_records(r,raws,observations(r))
            def current(self,r,carriers=True):return electrical_profile(r)
            def check_window(self,r):pass
            def manager(self):return manager
            def now(self):return time.clock_gettime(time.CLOCK_BOOTTIME)
            def cache_evidence(self):return copy.deepcopy(request['current_cache'])
            def observe(self,manager):
                stopped=behaviour.read_text().strip()=='inhibit-charge';value=copy.deepcopy(json.loads(raws['before']))
                registers=value['state']['registers'];registers['08']=(registers['08']&~0x18)|(8 if stopped else 0 if full else 0x10)
                s=value['sample'];logical=full and not (failure=='lost-Full' and stopped)
                s.update(logical_full=int(logical),full_cause=3 if logical else 0,full_holding=int(logical and not stopped),hold_requested=int(logical and not stopped),
                         desired_enable=int(not stopped and not full),session_seconds=36000 if fault else 0,latched=int(fault),cycle_timeout=int(fault),fault=2 if fault else 0,error=-62 if fault else 0,stop_error=0)
                value.update(notes=copy.deepcopy(m.expected_profile(request)['notes']),current_cache=self.cache_evidence(),charge_behaviour=behaviour.read_text().strip(),
                             read_start=self.now(),read_end=self.now(),limits=dict(input_ua=500000,charge_ua=250000,cv_pack_uv=8725000),
                             source=dict(online={'errno':61},current_max={'errno':61}) if fault else value['source'])
                value['state']['boot_id']=request['identity']['boot_id'];return value
            def stop(self,manager,meta):
                self.control.append('stop');return super().stop(manager,meta)
        device=Device()
        def registers():return device.observe(None)['state']['registers']
        live=types.SimpleNamespace(PSY=psy,CLIENT=client,registers=registers)
        scope=dict(Path=mapped,json=json,hashlib=hashlib,MANIFEST=paths[m.MANIFEST],STATE=root/'service-state',live=live,
                   os=types.SimpleNamespace(geteuid=lambda:0,uname=lambda:types.SimpleNamespace(release=m.RELEASE)))
        exec(compile(ast.Module(body=service_functions,type_ignores=[]),'<actual-service-verify-inhibit-command>','exec'),scope)
        manager={**{name:scope[name] for name in function_names},'live':live}
        real_atomic=m.atomic_replace
        class Ops:
            def __getattr__(self,key):return getattr(os,key)
            def replace(self,src,dst):
                if failure=='rename-manifest' and Path(dst)==paths[m.MANIFEST]:raise OSError(5,'injected inverse second rename error')
                return os.replace(src,dst)
        if failure=='rename-manifest':
            m.atomic_replace=lambda *args,**kw:real_atomic(*args,**kw,ops=Ops())
        try:result=m.restore(request,device,True)
        finally:m.Path=old_path;m.read_owned=old_reader;m.atomic_replace=real_atomic
        assert not result['module_or_carrier_action'] and not result['automatic_replay_or_rollback']
        assert device.control==([] if already_stopped else ['stop']),(profile,result.get('primary_error'))
        assert behaviour.read_text().strip()=='inhibit-charge'
        if failure is None:
            assert result['restored'] and result['disk_state']=='all_original_fsynced',(profile,result.get('primary_error'),result.get('receipt_error'),result.get('close_error'))
            assert paths[m.TARGET].read_bytes()==fixture['artifacts'][m.TARGET] and paths[m.MANIFEST].read_bytes()==raws['old_manifest']
            assert result['existing_fault_history']['latched']==int(fault) and result['existing_fault_history']['cycle_timeout']==int(fault)
        elif failure=='lost-Full':
            assert not result['restored'] and paths[m.TARGET].read_bytes()==new_charger and paths[m.MANIFEST].read_bytes()==new_manifest
        else:
            assert not result['restored'] and result['disk_state']=='partial_known' and paths[m.TARGET].read_bytes()==fixture['artifacts'][m.TARGET] and paths[m.MANIFEST].read_bytes()==new_manifest
        assert all(paths[target].read_bytes()==raw for target,raw in fixture['artifacts'].items() if target!=m.TARGET)
        cases.append(dict(name='actual_inverse_'+profile,full=full,existing_fault_timeout=fault,already_stopped=already_stopped,failure=failure,passed=True))

request=request_for(m.PROFILES[1]);cache=copy.deepcopy(request['current_cache']);raw=base64.b64decode(cache['raw_base64']).replace(b'attempted=0 terminal=0',b'attempted=1 terminal=0')
cache.update(raw_base64=base64.b64encode(raw).decode(),sha256=sha(raw))
try:m.validate_cache(cache)
except RuntimeError:pass
else:raise AssertionError('in-progress cache accepted')
cases.append(dict(name='schema2_profile1_in_progress_cache_rejected',passed=True))
record=dict(passed=True,cases=cases,worker_sha256=sha((HERE/'restore-worker.py').read_bytes()),
            real_forward_stage_and_inverse_atomic_filesystem=True,actual_service_verify_inhibit_command=True,
            processes_identity_hardware_and_time_edges_modeled=True,phone_accessed=False,lease_created=False,rollback_started=False,newboot_restore_accepted=False)
with (HERE/'test-result.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,cases=len(cases),phone_accessed=False)))
