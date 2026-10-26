from pathlib import Path
import host,json

here=Path(__file__).resolve().parent
assert json.loads((here/'flash-validation.json').read_text())['boot_flash_success']
assert (host.PRIVATE/'fastboot-reboot-request-private.json').exists()
p=host.ssh('python3 -',input=(here/'collect-newboot.py').read_bytes(),timeout=110)
(host.PRIVATE/'newboot-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
assert report['new_boot_identity_verified'] and report['patched_sensor_module_loaded_note_matches_installed']
assert report['taint']==0 and not any(report['fault_counts'].values())
assert report['remoteprocs']==dict(adsp='running',slpi='running',modem='running')
(here/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for name in ['reboot-request-private.json','boot-flash-request-private.json','fastboot-reboot-request-private.json']:
    path=host.PRIVATE/name;record=json.loads(path.read_text());record.update(state='closed',new_boot_verified=True,new_boot_guard='/var/lib/samurai/k219-runtime/boot-id-private.txt');path.write_text(json.dumps(record,indent=2)+'\n')
state=json.loads((host.PRIVATE/'current-work-private.json').read_text());state.update(state='boot219 and driver219 verified on a new normal boot; full mode still opt-in',guard='/var/lib/samurai/k219-runtime/boot-id-private.txt',transition_pending=False,next='Verify factory bin mode, then guarded full raw experiment and native CPU decoding; full peripheral goal remains active')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(report))
