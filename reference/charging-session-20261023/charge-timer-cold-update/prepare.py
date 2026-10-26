"""Current504 charger-only cold stage, derived from the actual successful owner."""
from pathlib import Path
import ast,base64,hashlib,importlib.util,io,json,secrets,tokenize
HERE=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
PREVIOUS=BASE/'usb-irq-wake-update-live-20261024-01'
OUT=BASE/'charge-timer-cold-update-live-20261024-01'
TX='irq-native-usb-pm-stage-timer-20261024-01'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
helpers=load('timer_cold_source_helpers',HERE.parent/'protection-profile-update/host.py')
def main():
    assert not OUT.exists()
    current=(BASE/'boot-adoption-private.json').read_bytes()
    assert current==(PREVIOUS/'adoption-pointer-after-pm.json').read_bytes()
    pointer=json.loads(current)
    cpath=HERE.parent/'charge-timer-hold-r2-candidate/cohort-result.json'
    cohort=json.loads(cpath.read_bytes());assert cohort['passed'] and not cohort['deployed']
    assert pointer['charging_manifest_sha256']==cohort['source_manifest_sha256']
    assert pointer['PM_current_USB_irq_wake_cohort_verified']
    post=json.loads((PREVIOUS/'postboot/reply.json').read_bytes())
    assert post['result']['passed'] and len(post['result']['checks'])==12
    idraw=post['raw']['identity_after']
    identity=dict(boot_id=idraw['boot_id'],version=idraw['uname']['version'],serial_sha256=idraw['serial_sha256'],
                  compatible_sha256=sha(base64.b64decode(idraw['compatible_b64'])),rootfs_sha256=idraw['rootfs']['sha256'])
    assert identity['boot_id']==pointer['boot_id'] and identity['version']=='#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
    original=(PREVIOUS/'stage-worker.py').read_bytes()
    bound=json.loads((PREVIOUS/'request-private.json').read_bytes());assert sha(original)==bound['worker_sha256']
    # Rename identifiers, not provider names/paths/strings. Preserve the proven
    # algorithm; TARGET now designates only the charger module on disk.
    names={'USB':'TARGET','USB_OLD':'TARGET_OLD','USB_NEW':'TARGET_NEW'}
    source=tokenize.untokenize([t._replace(string=names.get(t.string,t.string)) if t.type==tokenize.NAME else t
                               for t in tokenize.generate_tokens(io.StringIO(original.decode()).readline)])
    source=source.replace('One current-IRQ disk-only USB stage.','One current504 disk-only charger timer stage.')
    before=source
    values=dict(TARGET="PLACEHOLDER",OLD=cohort['source_manifest_sha256'],NEW=cohort['target_manifest_sha256'],
        TARGET_OLD=cohort['source_charger_sha256'],TARGET_NEW=cohort['target_charger_sha256'],
        COHORT=sha(cpath.read_bytes()),PAYLOAD=cohort['forward']['sha256'],
        MAC_CACHE_SHA=pointer['protection_capture_cache_sha256'],
        NOTES={'samurai-usb-input':'028ea63c24b0b46ec6edb03b9c3cbfc999c4b7a119034dc18ac70d1bcbf064e6',
               'samurai-gauge-protection':'bf148be50cb3a4c30bf3ab194f90163fbd47ce5dcbcaf1adb7d84392d242ecdd',
               'samurai-mp2650':'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'})
    for key,value in values.items():
        if key!='TARGET':source=helpers.assigned(source,key,value)
    source=helpers.assigned(source,'TARGET','/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko')
    assert source.count('len(raw)==28922')==1
    source=source.replace('len(raw)==28922','len(raw)=='+str(cohort['forward']['bytes']))
    delta='''def manifest_delta(old,new):
    expected=copy.deepcopy(old)
    need(old['release']==RELEASE and old['modules']['samurai-mp2650']=={'target':TARGET,'sha256':TARGET_OLD},'current exact charger97c')
    expected['adapter_revision']='confirmed-stop-timer-02'
    expected['modules']['samurai-mp2650']['sha256']=TARGET_NEW;expected['installed_files'][TARGET]=TARGET_NEW
    need(new==expected and old['installed_files'][SERVICE]==SERVICE_SHA,'only charger and cohort revision change')
    need(old['modules']['samurai-usb-input']['sha256']=='13f41e7cdbd1825982e2155bfb97e0105227179d1afa8da8a2795ba39f4299a4' and old['modules']['samurai-gauge-protection']['sha256']=='f6bef8a239d5101dbb710f1dd5da9642bdc7ac5e4e568e2e1193de6233a31d7e','retain current USB wake and protection')
    need(old['default_input_cap_ua']==900000 and old['default_charge_cap_ua']==250000 and old['source_budget_enforced'] is True,'unchanged caps and budget')'''
    source=helpers.function(source,'manifest_delta',delta)
    # Cosmetic phase label only; consumers must use the explicit target map.
    source=source.replace("phase='replace-usb'", "phase='replace-charger'")
    def bodies(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    left,right=bodies(before),bodies(source)
    assert set(left)==set(right)
    changed={name for name in left if left[name]!=right[name]}
    assert changed=={'manifest_delta','unpack','stage'}
    assert left['stage'].replace("phase='replace-usb'","phase='replace-charger'")==right['stage']
    assert left['unpack'].replace('len(raw)==28922','len(raw)=='+str(cohort['forward']['bytes']))==right['unpack']
    assert b'rmmod' not in source.encode() and b'insmod' not in source.encode()
    with (HERE/'stage-worker.py').open('x') as f:f.write(source)
    worker=load('timer_charger_cold_stage',HERE/'stage-worker.py')
    assert worker.ORDER==[worker.KO,worker.MANIFEST] and worker.TARGET==worker.KO
    payload=(BASE/'charge-timer-hold-cohort-private-02/forward-two-files.tar.gz').read_bytes()
    assert sha(payload)==cohort['forward']['sha256']
    tx=Path(pointer['guard_path']).parent.name.removesuffix('-adopted')
    request=dict(schema='samurai-irq-native-usb-pm-stage-request-v1',transaction_id=TX,cohort_delivery_sha256=worker.COHORT,
                 payload_sha256=worker.PAYLOAD,payload_base64=base64.b64encode(payload).decode(),worker_sha256=sha(source.encode()),
                 lease_token=secrets.token_hex(24),identity=identity,
                 adoption=dict(transaction_id=tx,guard_path=pointer['guard_path'],guard_sha256=sha((identity['boot_id']+'\n').encode())))
    files,new=worker.unpack(request)
    worker.manifest_delta(json.loads((BASE/'charge-timer-hold-cohort-private-02/manifest-old.json').read_bytes()),new)
    OUT.mkdir(mode=0o700)
    with (OUT/'previous-pointer.json').open('xb') as f:f.write(current)
    with (OUT/'stage-worker.py').open('xb') as f:f.write(source.encode())
    save(OUT/'request-private.json',request)
    result=dict(passed=True,prepared_offline_only=True,device_accessed=False,lease_created=False,stage_started=False,
                actual_base_worker_sha256=sha(original),worker_sha256=sha(source.encode()),
                identifier_renames=names,changed_functions={'manifest_delta':'exact charger/revision/retained providers',
                'unpack':'payload length only','stage':'phase label only'},
                all_original_atomic_safety_stop_snapshot_and_Device_bodies_retained=True,
                runtime_cycle_and_Full_not_erased_by_hot_unload=True,
                target_files=list(files),source_cohort_sha256=sha(cpath.read_bytes()))
    save(HERE/'derivation.json',result);save(OUT/'derivation.json',result)
    print(json.dumps(dict(prepared=True,device_accessed=False,lease_created=False,stage_started=False)))
if __name__=='__main__':main()
