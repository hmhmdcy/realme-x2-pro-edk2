"""Upload checked tools and stage the next-boot module after the fresh baseline."""
from pathlib import Path
import json
import host

ref = Path(__file__).resolve().parent
result = host.ssh("python3 -", input=b"from pathlib import Path; p=Path('/var/lib/samurai/k228-tools'); assert not p.exists(); p.mkdir(mode=0o700); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k228-baseline/boot-id-private.txt').read_bytes(); print('Fresh228 tools directory created')", timeout=20)
(host.PRIVATE / 'tools-create-private.log').write_bytes(result.stdout + result.stderr)
for name in ['install-module.py', 'quiesce-current183.sh', 'stop-gnss-idle.py', 'quiesce-camera.py',
             'disable-crtc.py', 'check-quiesce.py', 'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py']:
    destination = '/var/lib/samurai/k228-tools/' + name if name in ['install-module.py', 'linux-restart2-bootloader.py'] else '/tmp/k228-' + name
    host.upload(ref / name, destination)
host.upload(host.PRIVATE.parent / 'kernel227/fastrpc227-candidate-private.ko', '/var/lib/samurai/k228-tools/fastrpc-candidate-private.ko')
host.upload(ref.parent / 'kernel227/fastrpc-build-validation.json', '/var/lib/samurai/k228-tools/fastrpc-build-validation.json')
result = host.ssh('python3 /var/lib/samurai/k228-tools/install-module.py', timeout=50)
(host.PRIVATE / 'module-install-host-private.log').write_bytes(result.stdout + result.stderr)
report = json.loads(result.stdout)
(ref / 'module-install-validation.json').write_text(json.dumps(report, indent=2) + '\n')
state = json.loads((host.PRIVATE / 'current-work-private.json').read_text())
state.update(state='candidate file installed for next boot; old driver still live; quiesce not started',
             next='Run guarded quiesce once, verify terminal/audit, single bootloader request then freshly identified fastboot reboot without flashing')
(host.PRIVATE / 'current-work-private.json').write_text(json.dumps(state, indent=2) + '\n')
print(json.dumps(report))
