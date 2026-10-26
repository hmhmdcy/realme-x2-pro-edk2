"""Actual cold-stage/atomic/manager verification; phone I/O is modeled."""
from pathlib import Path
import ast,base64,copy,hashlib,importlib.util,json,os,struct,tarfile,tempfile,time,types
HERE=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=BASE/'charge-timer-cold-update-live-20261024-01'
source=(HERE/'stage-worker.py').read_bytes();request=json.loads((OUT/'request-private.json').read_bytes())
oldraw=(BASE/'charge-timer-hold-cohort-private-02/manifest-old.json').read_bytes()
newraw=(BASE/'charge-timer-hold-cohort-private-02/manifest-new.json').read_bytes()
oldmeta=json.loads(oldraw);newmeta=json.loads(newraw)
cache=BASE/'usb-irq-wake-update-live-20261024-01/raw-bd62c031/device-stage'
before=json.loads((cache/'before-private.json').read_bytes())
paused=json.loads((cache/'stopped-private.json').read_bytes())
post=json.loads((BASE/'usb-irq-wake-update-live-20261024-01/postboot/reply.json').read_bytes())
artifacts={}
with tarfile.open(BASE/'r6-candidate/r5-to-r6-payload.tar.gz') as archive:
    for entry in archive.getmembers():
        if entry.isfile():artifacts['/'+entry.name]=archive.extractfile(entry).read()
artifacts['/usr/sbin/samurai-charging']=(HERE.parent/'protection-profile-update/samurai-charging.py').read_bytes()
for target,source_name in {'/etc/init.d/samurai-charging':'samurai-charging.openrc',
 '/usr/lib/samurai-charging/control-trial.py':'control-trial.py',
 '/usr/lib/samurai-charging/live-session.py':'live-session.py'}.items():
    artifacts[target]=(HERE.parents[1]/'charging-management-20261023'/source_name).read_bytes()
for name,relative in {
 'samurai-mp2650':'charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko',
 'samurai-usb-input':'usb-input-irq-wake-module-private-01/samurai-usb-input-irq-wake-private.ko',
 'samurai-gauge-protection':'protection-observed-2719-profile-module-private-01/samurai-gauge-protection-observed-2719-private.ko'}.items():
    artifacts[oldmeta['modules'][name]['target']]=(BASE/relative).read_bytes()
sha=lambda raw:hashlib.sha256(raw).hexdigest()
assert all(sha(artifacts[name])==digest for name,digest in oldmeta['installed_files'].items())
artifacts={name:artifacts[name] for name in oldmeta['installed_files']}
service=artifacts['/usr/sbin/samurai-charging'].decode()
functions=[n for n in ast.parse(service).body if isinstance(n,ast.FunctionDef) and n.name in ['verify','loaded_matches']]
assert len(functions)==2
cases=[]
for failure in [None,'verify-new','rename-charger','rename-manifest','cache-after-charger']:
    spec=importlib.util.spec_from_file_location('timer_stage_'+str(failure),HERE/'stage-worker.py')
    w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
    files,_=w.unpack(request);w.manifest_delta(oldmeta,newmeta)
    with tempfile.TemporaryDirectory(prefix='samurai-timer-cold-stage-') as name:
        root=Path(name);paths={target:root/target.lstrip('/') for target in artifacts}
        paths[w.MANIFEST]=root/'manifest.json'
        paths['/sys/firmware/devicetree/base/compatible']=root/'compatible'
        for target,raw in artifacts.items():
            p=paths[target];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(0o755 if target==w.SERVICE else 0o600)
        paths[w.MANIFEST].write_bytes(oldraw);paths[w.MANIFEST].chmod(0o600)
        paths['/sys/firmware/devicetree/base/compatible'].write_bytes(base64.b64decode(post['raw']['identity_before']['compatible_b64']))
        def mapped(value,*parts):
            p=Path(value,*parts);return paths.get(p.as_posix(),p)
        # Simulated live notes are extracted from the actual installed old ELF
        # bytes. Execute the actual service's loaded_matches, including backups.
        for module,entry in oldmeta['modules'].items():
            raw=artifacts[entry['target']];offset=struct.unpack_from('<Q',raw,40)[0]
            stride,count,strings=struct.unpack_from('<HHH',raw,58)
            sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*stride) for i in range(count)]
            names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
            note=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
            value=raw[note[4]:note[4]+note[5]];assert sha(value)==w.NOTES[module]
            p=root/(module+'.note');p.write_bytes(value)
            paths['/sys/module/'+module.replace('-','_')+'/notes/.note.gnu.build-id']=p
        scope=dict(Path=mapped,struct=struct,json=json,hashlib=hashlib,MANIFEST=paths[w.MANIFEST],
                   os=types.SimpleNamespace(geteuid=lambda:0,uname=lambda:types.SimpleNamespace(release=w.RELEASE)))
        exec(compile(ast.Module(body=functions,type_ignores=[]),'<actual-service-verify-and-loaded-matches>','exec'),scope)
        w.Path=mapped
        class Device(w.Device):
            def __init__(self):
                super().__init__((json.dumps(request,indent=2)+'\n').encode());self.running=True;self.control=[];self.injected=False;self.changed_cache=False
            def identity(self,r):return dict(r['identity'],guard_sha256=r['adoption']['guard_sha256'])
            def begin(self,r):self.request=r;self.out=root/'evidence';self.out.mkdir(mode=0o700)
            def check_window(self,r):pass
            def module_state(self,module='samurai-mp2650'):return 'live'
            def mac_evidence(self):
                value=copy.deepcopy(post['raw']['protection_cache_after'])
                if self.changed_cache:value['sha256']='changed'
                return value
            def manager(self,digest):
                assert sha(paths[w.SERVICE].read_bytes())==digest==w.SERVICE_SHA
                def command(meta,action):
                    assert action=='stop';self.control.append(action);self.running=False
                def registers():return copy.deepcopy((before if self.running else paused)['registers'])
                return dict(_r8_code_sha256=digest,verify=scope['verify'],loaded_matches=scope['loaded_matches'],
                            command=command,live=types.SimpleNamespace(registers=registers))
            def verify(self,manager):
                result=super().verify(manager)
                if failure=='verify-new' and not self.injected and sha(paths[w.MANIFEST].read_bytes())==w.NEW:
                    self.injected=True;raise RuntimeError('injected after actual new manager verification')
                return result
            def observe(self,manager):
                value=copy.deepcopy(before if self.running else paused);now=time.clock_gettime(time.CLOCK_BOOTTIME)
                value.update(notes=copy.deepcopy(w.NOTES),identity=self.identity(request),mac_evidence=self.mac_evidence(),read_start=now-.001,read_end=now)
                return value
        real_atomic=w.atomic_replace
        class Ops:
            def __getattr__(self,key):return getattr(os,key)
            def replace(self,src,dst):
                target=paths[w.TARGET] if failure=='rename-charger' else paths[w.MANIFEST]
                if failure in ['rename-charger','rename-manifest'] and Path(dst)==target and not device.injected:
                    device.injected=True;raise OSError(5,'injected target rename failure')
                result=os.replace(src,dst)
                if failure=='cache-after-charger' and Path(dst)==paths[w.TARGET] and not device.injected:
                    device.injected=True;device.changed_cache=True;raise OSError(5,'injected cache change after charger rename')
                return result
        def atomic(*args,**kwargs):return real_atomic(*args,**kwargs,ops=Ops())
        w.atomic_replace=atomic;device=Device()
        result=w.stage(request,device,True)
        assert device.control==['stop'] and not device.running
        assert not result['new_module_loaded'] and not result['activation_attempted'] and not result['capture_issued']
        if failure is None:
            assert result['staged'] and result['disk_state']=='all_new_fsynced' and result['logical_full_retained']==1 and result['full_cause_retained']==3
            expected={w.TARGET:files[w.TARGET],w.MANIFEST:newraw}
        elif failure=='cache-after-charger':
            assert not result['staged'] and result['disk_state']=='partial_known' and result['recovery_error'] and not result.get('restored_original_disk')
            expected={w.TARGET:files[w.TARGET],w.MANIFEST:oldraw}
        else:
            assert not result['staged'] and result['restored_original_disk'] and result['disk_state']=='all_old' and result['recovery_error'] is None
            expected={w.TARGET:artifacts[w.TARGET],w.MANIFEST:oldraw}
        assert all(paths[target].read_bytes()==raw for target,raw in expected.items())
        assert all(paths[target].read_bytes()==raw for target,raw in artifacts.items() if target!=w.TARGET)
        cases.append(dict(failure=failure,passed=True,status=result['status'],disk_state=result['disk_state'],original_stop_only=True,
                          actual_service_verify_all_seven_files=True,actual_loaded_matches_retained_notes_and_backup=True))
assert (HERE/'stage-worker.py').read_bytes()==source
record=dict(passed=True,cases=cases,worker_sha256=sha(source),phone_accessed=False,lease_created=False,
            actual_stage_atomic_Device_replace_verify_and_note_functions=True,
            old_Full_snapshot_with_current_identity_notes_cache_modeled=True,real_cold_boot_or_timer_acceptance=False)
with (HERE/'test-result.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,cases=len(cases),phone_accessed=False)))
