from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert (host.PRIVATE/'fastboot-reboot-private.json').exists()
p=host.ssh('python3 -',input=(here/'collect-newboot.py').read_bytes(),timeout=100);(host.PRIVATE/'newboot-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout)
assert report['new_boot_identity_verified'] and report['patched_sensor_module_loaded_note_matches_installed'] and report['same_boot211_image_second_warm_boot']
assert report['taint']==0 and not any(report['fault_counts'].values()) and report['remoteprocs']==dict(adsp='running',slpi='running',modem='running')
(here/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
host.download('/var/lib/samurai/k212-runtime/boot-id-private.txt',host.PRIVATE/'new-boot-id-private.txt')
for name in ['reboot-request-private.json','fastboot-reboot-private.json']:
    path=host.PRIVATE/name;record=json.loads(path.read_text());record.update(state='closed',new_boot_verified=True,new_boot_guard='/var/lib/samurai/k212-runtime/boot-id-private.txt');path.write_text(json.dumps(record,indent=2)+'\n')
plan=json.loads((host.PRIVATE/'current-work-private.json').read_text());plan.update(state='212 no-flash warm boot completed. Same boot211 image, new identity, exact partitions/products/module tree, loaded sensor note, crop selections, heap config and three DSPs verified. Clean taint/fault0 before capture.',guard='/var/lib/samurai/k212-runtime/boot-id-private.txt',transition_pending=False,next='Verify actual UID10000 libcamera capture with system CPU configuration and no environment override; warm-up frames, resources and clean final health. Sensor helper/quality and all five cameras/full peripherals remain open.')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))
