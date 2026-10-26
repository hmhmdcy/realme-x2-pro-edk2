from pathlib import Path
import hashlib, json, subprocess
import host

here = Path(__file__).resolve().parent
dest = '/var/lib/samurai/k210-reboot-tools'
host.ssh('test ! -e '+dest+' && mkdir -m700 '+dest)
for name in ['quiesce-current183.sh', 'stop-gnss-idle.py', 'disable-crtc.py', 'check-quiesce.py', 'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py']:
    host.upload(here/name, dest+'/'+name)
    host.ssh('cp '+dest+'/'+name+' /tmp/k210-'+name)
try:
    p = host.ssh('sh '+dest+'/quiesce-current183.sh', timeout=140)
except subprocess.CalledProcessError as error:
    (host.PRIVATE/'quiesce-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''))
    raise SystemExit('Quiesce failed; inspect private evidence, no transition sent')
(host.PRIVATE/'quiesce-host-private.log').write_bytes(p.stdout+p.stderr)
p = host.ssh('cat /var/lib/samurai/k210-quiesce/quiesce-validation.json')
report = json.loads(p.stdout)
assert report['quiesce_audit_pass'] and report['taint'] == 0 and report['stage'] == 210
(host.PRIVATE/'quiesce-validation-private.json').write_bytes(p.stdout)
p = host.ssh('tar -C /var/lib/samurai -czf /tmp/k210-before-reboot-private.tar.gz k210-before-reboot k210-quiesce k210-reboot-tools gnss-assist k210-baseline k210-camera-before-r2 k210-install-before-r2 k210-module-install k210-module-stage && sha256sum /tmp/k210-before-reboot-private.tar.gz', timeout=60)
digest = p.stdout.decode().split()[0]
target = host.PRIVATE/'before-reboot-private.tar.gz'
host.download('/tmp/k210-before-reboot-private.tar.gz', target)
assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
(here/'pre-reboot-validation.json').write_text(json.dumps(dict(stage=210, full_quiesce=True, taint=0, private_archive_verified=True, no_transition_yet_sent=True), indent=2)+'\n')
print('K202_GNSS_IDLE_STOP_FULL_QUIESCE_AND_PRIVATE_ARCHIVE_VERIFIED')
