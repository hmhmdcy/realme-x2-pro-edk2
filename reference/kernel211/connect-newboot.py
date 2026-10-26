from pathlib import Path
import host,json
here=Path(__file__).resolve().parent;assert (host.PRIVATE/'fastboot-reboot-request-private.json').exists()
p=host.ssh('python3 -',input=(here/'collect-newboot.py').read_bytes(),timeout=100);(host.PRIVATE/'newboot-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);assert report['new_boot_identity_verified'] and report['patched_sensor_module_loaded_note_matches_installed']
(here/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');host.download('/var/lib/samurai/k211-runtime/boot-id-private.txt',host.PRIVATE/'new-boot-id-private.txt')
plan=json.loads((host.PRIVATE/'current-work-private.json').read_text());plan.update(state='211 guarded boot-only sensor-domain update and new boot completed. New boot/readback verified; loaded patched module note matches, TRY/ACTIVE crop succeed with real ROI, heap autoload and scoped permissions verified.',guard='/var/lib/samurai/k211-runtime/boot-id-private.txt',transition_pending=False,next='Observe normal service readiness and actual UID10000 libcamera software ISP capture. Keep sensor/graph/rails restored and retain all other peripheral/five-camera work.')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))
