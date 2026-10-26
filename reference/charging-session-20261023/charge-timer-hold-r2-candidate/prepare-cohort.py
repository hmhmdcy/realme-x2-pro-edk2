"""Prepare exact charger/manifest forward and inverse pairs; no device access."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os
HERE=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=BASE/'charge-timer-hold-cohort-private-02'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
spec=importlib.util.spec_from_file_location('timer_pair_original_packet',HERE.parent/'protection-profile-update/prepare.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def write(path,raw):
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
def main():
    assert not OUT.exists()
    build=json.loads((HERE/'ko-result.json').read_bytes())
    assert build['passed'] and not build['diagnostics'] and build['tracked_inputs_unchanged']
    assert all(row['terminal'] and row['returncode']==0 for row in build['commands'])
    assert build['module_sha256']=='bef4dba73e1244fec4c89f2d5b47ac6b1483384c1f64aa1d589de792d2e97d6f'
    assert build['strong_import_count']==54 and build['all_imports_from_Image502_builtin']
    delivery=json.loads((HERE/'delivery.json').read_bytes());assert delivery['passed']
    assert all(sha((HERE/name).read_bytes())==row['sha256'] for name,row in delivery['files'].items())
    old_raw=(BASE/'usb-irq-wake-cohort-private-01/manifest-new.json').read_bytes()
    assert sha(old_raw)=='5ef4eaef76896f1fda932d95d6c3e4e1117bcc451075ad7265dbe22204880c70'
    pointer=json.loads((BASE/'boot-adoption-private.json').read_bytes())
    assert pointer['charging_manifest_sha256']==sha(old_raw) and pointer['PM_current_USB_irq_wake_cohort_verified']
    old=json.loads(old_raw);target=old['modules']['samurai-mp2650']['target'];manifest='/usr/share/samurai-charging/manifest.json'
    original=(BASE/'charger-reattach-observation-module-private-01/samurai-mp2650-reattach-observation-private.ko').read_bytes()
    module=Path(build['private_module_path']).read_bytes()
    assert sha(original)==old['modules']['samurai-mp2650']['sha256']=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'
    assert sha(module)==build['module_sha256']
    new=copy.deepcopy(old);new['modules']['samurai-mp2650']['sha256']=sha(module)
    new['installed_files'][target]=sha(module);new['adapter_revision']='confirmed-stop-timer-02'
    new_raw=(json.dumps(new,indent=2)+'\n').encode()
    forward=m.packet([(target,module),(manifest,new_raw)])
    inverse=m.packet([(target,original),(manifest,old_raw)])
    assert m.packet([(target,module),(manifest,new_raw)])==forward
    os.umask(0o077);OUT.mkdir(mode=0o700)
    for name,raw in [('forward-two-files.tar.gz',forward),('rollback-two-files.tar.gz',inverse),('manifest-old.json',old_raw),('manifest-new.json',new_raw)]:write(OUT/name,raw)
    result=dict(passed=True,prepared_only=True,deployed=False,phone_accessed=False,
        source_charger_sha256=sha(original),target_charger_sha256=sha(module),target_charger_note_sha256=build['module_note_sha256'],
        source_manifest_sha256=sha(old_raw),target_manifest_sha256=sha(new_raw),
        forward=dict(sha256=sha(forward),bytes=len(forward)),rollback=dict(sha256=sha(inverse),bytes=len(inverse)),
        only_changed_files=[target,manifest],retained_USB_sha256=old['modules']['samurai-usb-input']['sha256'],
        retained_protection_sha256=old['modules']['samurai-gauge-protection']['sha256'],
        retained_service_sha256=old['installed_files']['/usr/sbin/samurai-charging'],
        USB_and_protection_not_reloaded=True,query_or_rearm_issued=False,
        activation_requires_fresh_current_state_and_safe_cycle=True,hot_unload_during_Full_allowed=False,
        current_runtime_PM_not_reassigned_to_candidate=True,module_build_result_sha256=sha((HERE/'ko-result.json').read_bytes()))
    for path in [HERE/'cohort-result.json',OUT/'cohort.json']:write(path,(json.dumps(result,indent=2)+'\n').encode())
    print(json.dumps({key:result[key] for key in ['passed','target_manifest_sha256','forward','rollback','deployed']}))
if __name__=='__main__':main()
