"""Exercise prepared read-only restart guards; never execute quiesce/restart tail."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,re,struct,sys,tempfile,types
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('timer_restart_contract',HERE/'restart.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
sources,template=r.build();base=r.u.BASE
newmeta=json.loads((base/'charge-timer-hold-cohort-private-02/manifest-new.json').read_bytes())
newko=(base/'charge-timer-hold-module-private-02/samurai-mp2650-reattach-observation-private.ko').read_bytes()
oldko=(base/'charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko').read_bytes()
usb=(base/'usb-input-irq-wake-module-private-01/samurai-usb-input-irq-wake-private.ko').read_bytes()
protection=(base/'protection-observed-2719-profile-module-private-01/samurai-gauge-protection-observed-2719-private.ko').read_bytes()
def note(raw):
    offset=struct.unpack_from('<Q',raw,40)[0];stride,count,strings=struct.unpack_from('<HHH',raw,58)
    sections=[struct.unpack_from('<IIQQQQIIQQ',raw,offset+i*stride) for i in range(count)]
    names=raw[sections[strings][4]:sections[strings][4]+sections[strings][5]]
    item=next(s for s in sections if names[s[0]:].split(b'\0')[0]==b'.note.gnu.build-id')
    return raw[item[4]:item[4]+item[5]]
sha=lambda raw:hashlib.sha256(raw).hexdigest()
cases=[]
for key in ['quiesce','restart']:
    source=sources[key].decode().split("r=Path('/var/lib/samurai')",1)[0]
    tree=ast.parse(source);tree.body=[n for n in tree.body if not isinstance(n,(ast.Import,ast.ImportFrom))]
    prefix=compile(tree,'<actual-readonly-'+key+'-guards>','exec')
    for failure in [None,'candidate-already-live','old-disk-charger','changed-stage-result']:
        with tempfile.TemporaryDirectory(prefix='samurai-timer-restart-gates-') as name:
            root=Path(name);meta=copy.deepcopy(template)
            serial=b'explicit-modeled-SoC-serial\n';compat=b'realme,samurai\0qcom,sm8150\0';rootfs=b'ROOTFS_ID=samurai-f2fs-rootfs01\n'
            meta.update(serial_sha256=sha(serial),compatible_sha256=sha(compat),rootfs_release_sha256=sha(rootfs))
            stage=dict(staged=True,terminal=True,stop_verified=True,disk_state='all_new_fsynced',primary_error=None,recovery_error=None)
            stage_raw=(json.dumps(stage,indent=2)+'\n').encode();meta['stage_result_sha256']=sha(stage_raw)
            manifest_raw=(base/'charge-timer-hold-cohort-private-02/manifest-new.json').read_bytes()
            blobs={
                '/proc/sys/kernel/random/boot_id':(meta['boot_id']+'\n').encode(),'/proc/sys/kernel/tainted':b'0\n',
                '/etc/samurai-rootfs-release':rootfs,'/sys/devices/soc0/serial_number':serial,
                '/sys/firmware/devicetree/base/compatible':compat,meta['adoption_guard']:(meta['boot_id']+'\n').encode(),
                meta['stage_result']:stage_raw+(b' ' if failure=='changed-stage-result' else b''),
                '/sys/class/power_supply/samurai-gauge-protection/health':b'Good\n',
                '/sys/module/samurai_usb_input/parameters/native_retained':b'Y\n',
                '/sys/module/samurai_usb_input/notes/.note.gnu.build-id':note(usb),
                '/sys/module/samurai_mp2650/notes/.note.gnu.build-id':note(newko if failure=='candidate-already-live' else oldko),
                '/sys/module/samurai_gauge_protection/notes/.note.gnu.build-id':note(protection),
                '/usr/share/samurai-charging/manifest.json':manifest_raw,
                newmeta['modules']['samurai-usb-input']['target']:usb,
                newmeta['modules']['samurai-mp2650']['target']:oldko if failure=='old-disk-charger' else newko}
            paths={}
            for index,(target,raw) in enumerate(blobs.items()):
                p=root/str(index);p.write_bytes(raw);p.chmod(0o600);paths[target]=p
            guard=root/'guard.json';guard.write_text(json.dumps(meta));guard.chmod(0o600)
            def mapped(value,*parts):
                p=Path(value,*parts);return paths.get(p.as_posix(),p)
            fake_os=types.SimpleNamespace(uname=lambda:types.SimpleNamespace(machine='aarch64',release=r.u.VERSION and '7.3.0-rc6-rmx1931-samurai-k363+',version=r.u.VERSION))
            scope=dict(Path=mapped,json=json,hashlib=hashlib,re=re,sys=types.SimpleNamespace(argv=['guard','--guard',str(guard),'--inspect']),os=fake_os)
            rejected=False
            try:exec(prefix,scope)
            except AssertionError:rejected=True
            assert rejected==(failure is not None),(key,failure)
            cases.append(dict(owner=key,failure=failure,passed=True,rejected_before_quiesce_or_restart=rejected))
record=dict(passed=True,cases=cases,actual_prepared_readonly_guard_bodies=True,modeled_identity_and_OS_boundaries=True,
            phone_accessed=False,quiesce_started=False,restart_requested=False,carrier_writes=0)
with (HERE/'restart-contract-result.json').open('x') as f:json.dump(record,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,cases=len(cases),phone_accessed=False,restart_requested=False)))
