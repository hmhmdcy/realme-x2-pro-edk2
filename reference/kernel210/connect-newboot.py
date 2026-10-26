from pathlib import Path
import host,json
here=Path(__file__).resolve().parent
assert (host.PRIVATE/'boot-flash-request-private.json').exists()
p=host.ssh('python3 -',input=(here/'collect-newboot.py').read_bytes(),timeout=100)
(host.PRIVATE/'newboot-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);assert report['new_boot_identity_verified']
(here/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
host.download('/var/lib/samurai/k210-runtime/boot-id-private.txt',host.PRIVATE/'new-boot-id-private.txt')
plan=json.loads((host.PRIVATE/'current-work-private.json').read_text());plan.update(state='Boot210 flashed once; new boot identity and boot/logdump/persist/NV/module readback verified. See runtime report for actual sensor binding; no stream yet.',guard='/var/lib/samurai/k210-runtime/boot-id-private.txt',next='Check static sensor/media graph, power state and fault baseline. Capture finite real front frames only if normal drivers are bound; no legacy overlay/helper.',transition_pending=False)
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))
