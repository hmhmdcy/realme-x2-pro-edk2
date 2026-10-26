"""Execute recovery read-only guards and local adoption with modeled transport."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,re,struct,sys,tempfile,types
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
r=load('inverse_restart_contract',HERE/'restart.py');p=load('inverse_postboot_contract',HERE/'postboot.py')
u=r.u;m=r.h.worker();base=u.BASE;sources=r.sources();collector=p.collector()
scope={};exec(compile(collector,'<actual-restored-collector>','exec'),scope)
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def note(raw):
    off=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    s=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
    return raw[s[4]:s[4]+s[5]]
oldko=(base/'charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko').read_bytes()
newko=(base/'charge-timer-hold-module-private-02/samurai-mp2650-reattach-observation-private.ko').read_bytes()
usb=(base/'usb-input-irq-wake-module-private-01/samurai-usb-input-irq-wake-private.ko').read_bytes()
protection=(base/'protection-observed-2719-profile-module-private-01/samurai-gauge-protection-observed-2719-private.ko').read_bytes()
old_manifest=(base/'charge-timer-hold-cohort-private-02/manifest-old.json').read_bytes()
cases=[]
for profile in m.PROFILES:
    identity=copy.deepcopy(m.SOURCE_IDENTITY)
    if profile==m.PROFILES[1]:identity['boot_id']='77777777-8888-4999-aaaa-bbbbbbbbbbbb'
    stage=dict(schema='samurai-charger-timer-cold-rollback-result-v1',transaction_id=u.TX,
        restored=True,terminal=True,stop_verified=True,disk_state='all_original_fsynced',primary_error=None,
        unknown_write_state=False,module_or_carrier_action=False,automatic_replay_or_rollback=False,
        actual_resident_notes=copy.deepcopy(m.OLD_NOTES if profile==m.PROFILES[0] else m.NEW_NOTES),
        final_files={path:dict(sha256=digest,mode='0600',classification='original') for path,digest in m.OLD_FILES.items()})
    stage_raw=(json.dumps(stage,indent=2)+'\n').encode()
    with tempfile.TemporaryDirectory(prefix='samurai-inverse-recovery-') as name:
        root=Path(name);out=root/'out';out.mkdir();rawdir=out/'raw-modeled/device-rollback';rawdir.mkdir(parents=True)
        (rawdir/'result.json').write_bytes(stage_raw)
        (rawdir.parent/'worker-terminal-private.json').write_text(json.dumps(dict(terminal=True,returncode=0,receipt_error=None)))
        saved_out=r.u.OUT;saved_request=r.h.request
        r.u.OUT=out;r.h.request=lambda:dict(identity=identity,profile=profile,lease_token='a'*48)
        try:built,meta=r.build()
        finally:r.u.OUT=saved_out;r.h.request=saved_request
        assert built==sources and meta['changed_files']==m.OLD_FILES
        assert meta['source_charger_note']==stage['actual_resident_notes']['samurai-mp2650']
        for owner in ['quiesce','restart']:
            source=sources[owner].decode().split("r=Path('/var/lib/samurai')",1)[0]
            tree=ast.parse(source);tree.body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
            prefix=compile(tree,'<actual-inverse-readonly-'+owner+'>','exec')
            for failure in [None,'wrong-resident','new-disk','changed-result']:
                serial=b'explicit-modeled-serial\n';compat=b'realme,samurai\0qcom,sm8150\0';rootfs=b'ROOTFS_ID=samurai-f2fs-rootfs01\n'
                current=copy.deepcopy(meta);current.update(serial_sha256=sha(serial),compatible_sha256=sha(compat),rootfs_release_sha256=sha(rootfs))
                usb_path='/lib/modules/'+m.RELEASE+'/extra/samurai-charging/samurai-usb-input.ko'
                live=newko if profile==m.PROFILES[1] else oldko
                if failure=='wrong-resident':live=oldko if profile==m.PROFILES[1] else newko
                blobs={'/proc/sys/kernel/random/boot_id':(identity['boot_id']+'\n').encode(),'/proc/sys/kernel/tainted':b'0\n',
                    '/etc/samurai-rootfs-release':rootfs,'/sys/devices/soc0/serial_number':serial,'/sys/firmware/devicetree/base/compatible':compat,
                    current['adoption_guard']:(identity['boot_id']+'\n').encode(),current['stage_result']:stage_raw+(b' ' if failure=='changed-result' else b''),
                    '/sys/class/power_supply/samurai-gauge-protection/health':b'Good\n','/sys/module/samurai_usb_input/parameters/native_retained':b'Y\n',
                    '/sys/module/samurai_usb_input/notes/.note.gnu.build-id':note(usb),'/sys/module/samurai_mp2650/notes/.note.gnu.build-id':note(live),
                    '/sys/module/samurai_gauge_protection/notes/.note.gnu.build-id':note(protection),m.MANIFEST:old_manifest,usb_path:usb,
                    m.TARGET:newko if failure=='new-disk' else oldko}
                paths={}
                for index,(target,raw) in enumerate(blobs.items()):
                    path=root/('blob'+str(index));path.write_bytes(raw);path.chmod(0o600);paths[target]=path
                guard=root/'guard.json';guard.write_text(json.dumps(current));guard.chmod(0o600)
                def mapped(value,*parts):
                    path=Path(value,*parts);return paths.get(path.as_posix(),path)
                local=dict(Path=mapped,json=json,hashlib=hashlib,re=re,sys=types.SimpleNamespace(argv=['guard','--guard',str(guard),'--inspect']),
                    os=types.SimpleNamespace(uname=lambda:types.SimpleNamespace(machine='aarch64',release=m.RELEASE,version=m.VERSION504)))
                rejected=False
                try:exec(prefix,local)
                except AssertionError:rejected=True
                assert rejected==(failure is not None),(profile,owner,failure)
                cases.append(dict(profile=profile,owner=owner,failure=failure,passed=True))
    request=dict(schema='samurai-charger-timer-restored-postboot-v1',profile='forward_504',carrier_writes=0,original_key_transport_verified=True,
        source_identity=identity,new_boot_id='11111111-2222-4333-8444-555555555555',stage=stage,stage_result_sha256=sha(stage_raw),
        guard=dict(boot_id=identity['boot_id'],new_boot_id='11111111-2222-4333-8444-555555555555',transaction_id=u.TX,
                   source_kernel_version=m.VERSION504,target_kernel_version=m.VERSION504))
    assert scope['validate_request'](request)['manifest_sha256']==m.OLD_FILES[m.MANIFEST]
    for failure in ['same-boot','not-restored','new-manifest','changed-result']:
        changed=copy.deepcopy(request)
        if failure=='same-boot':changed['new_boot_id']=changed['guard']['new_boot_id']=identity['boot_id']
        elif failure=='not-restored':changed['stage']['restored']=False
        elif failure=='new-manifest':changed['stage']['final_files'][m.MANIFEST]['sha256']=m.NEW_FILES[m.MANIFEST]
        else:changed['stage_result_sha256']='0'*64
        try:scope['validate_request'](changed)
        except AssertionError:pass
        else:raise AssertionError('invalid restored request accepted: '+failure)
    # Execute actual host-side adoption/CAS only. Intercept transport before any
    # remote execution; the device twelve checks and guard remain unexecuted.
    with tempfile.TemporaryDirectory(prefix='samurai-inverse-adopt-') as name:
        root=Path(name);out=root/'out';(out/'postboot').mkdir(parents=True)
        previous=dict(boot_id=identity['boot_id'],charging_manifest_sha256=m.NEW_FILES[m.MANIFEST],PM_suspend_resume_verified=True,
            PM_result_sha256='historical-only',PM_current_USB_irq_wake_cohort_verified=True,protection_capture_source_authenticated=True,
            protection_capture_result_sha256='historical-only',charger_timer_hold_candidate_loaded=True,charger_timer_hold_transition_verified=True)
        pointer_raw=(json.dumps(previous,indent=2)+'\n').encode();(root/'boot-adoption-private.json').write_bytes(pointer_raw);(out/'previous-pointer.json').write_bytes(pointer_raw)
        (out/'postboot-request.json').write_text(json.dumps(request));(out/'postboot-reviewed.json').write_text(json.dumps(dict(passed=True,checks=list(range(12)),errors=[])))
        (out/'postboot-collector.py').write_bytes(collector);(out/'postboot/stdout-private.json').write_text('{}')
        (out/'postboot/reply.json').write_text(json.dumps(dict(raw=dict(protection_cache_after=dict(sha256='modeled-current-cache')))))
        def no_transport(label,code,readonly=True):
            assert label=='adopt' and not readonly and b'collect(REQUEST,raw);result=audit(raw,REQUEST)' in code
            ast.parse(code)
            return dict(twelve_passed=True,boot_id=request['new_boot_id'],fresh_validation_sha256='modeled-fresh-proof')
        saved=(p.u.BASE,p.u.OUT,p.u.call,p.prior.collector);p.u.BASE=root;p.u.OUT=out;p.u.call=no_transport;p.prior.collector=lambda:collector
        try:assert p.adopt()==dict(adopted=True,diagnostic_query_started=False)
        finally:p.u.BASE,p.u.OUT,p.u.call,p.prior.collector=saved
        current=json.loads((root/'boot-adoption-private.json').read_bytes())
        assert current['charging_manifest_sha256']==m.OLD_FILES[m.MANIFEST] and current['boot_id']==request['new_boot_id']
        for key in ['PM_suspend_resume_verified','PM_current_USB_irq_wake_cohort_verified','PM_current_charger_timer_cohort_verified',
                    'protection_capture_source_authenticated','USB_physical_wakeup_verified','charger_timer_hold_candidate_loaded','charger_timer_hold_transition_verified']:
            assert current[key] is False,key
        assert 'PM_result_sha256' not in current and 'protection_capture_result_sha256' not in current
        assert current['previous_runtime_evidence']['PM_result_sha256']=='historical-only'
    cases.append(dict(profile=profile,postboot_request_five_cases=True,actual_local_adoption_CAS=True,passed=True))
record=dict(passed=True,cases=cases,actual_readonly_guard_and_host_adoption_bodies=True,identity_files_and_transport_modeled=True,
            phone_accessed=False,quiesce_started=False,restart_requested=False,actual_newboot_checked=False,real_pointer_modified=False)
with (HERE/'recovery-contract-result.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,restart_guard_cases=16,postboot_request_cases=10,local_adoption_cases=2,phone_accessed=False)))
