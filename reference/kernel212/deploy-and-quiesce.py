from pathlib import Path
import host,json
here=Path(__file__).resolve().parent;dest='/var/lib/samurai/k212-reboot-tools'
assert not (host.PRIVATE/'reboot-request-private.json').exists()
host.ssh('test ! -e /var/lib/samurai/k212-before-reboot && test ! -e /var/lib/samurai/k212-quiesce && mkdir -p -m700 '+dest)
for name in ['warning-guard.py','quiesce-current183.sh','stop-gnss-idle.py','quiesce-camera.py','disable-crtc.py','check-quiesce.py','freeze-for-bootloader.sh','linux-restart2-bootloader.py']:
    host.upload(here/name,dest+'/'+name);host.ssh('cp '+dest+'/'+name+' /tmp/k212-'+name)
p=host.ssh('python3 -',input=(here/'collect-pre-reboot.py').read_bytes(),timeout=100);(host.PRIVATE/'pre-reboot-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);(here/'pre-reboot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
p=host.ssh('sh '+dest+'/quiesce-current183.sh',timeout=200);(host.PRIVATE/'quiesce-host-private.log').write_bytes(p.stdout+p.stderr)
p=host.ssh('cat /var/lib/samurai/k212-quiesce/quiesce-validation.json');proof=json.loads(p.stdout);assert proof['quiesce_audit_pass'] and proof['known_gpu_unmap_warnings']==349
(host.PRIVATE/'quiesce-validation-private.json').write_bytes(p.stdout)
public={k:v for k,v in proof.items() if k!='boot_id'};(here/'quiesce-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(public))
