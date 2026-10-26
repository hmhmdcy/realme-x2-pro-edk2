from pathlib import Path
import hashlib,json
import host

p=host.ssh('sh /var/lib/samurai/k189r2-reboot-tools/quiesce-current183.sh',timeout=110)
(host.PRIVATE/'quiesce-host-private.log').write_bytes(p.stdout+p.stderr)
p=host.ssh('tar -C /var/lib/samurai -czf /tmp/k189r2-before-reboot-private.tar.gz k189-freezer-original k189-tools k189-module-deploy k189-deploy k189r2-preflash k189r2-quiesce && sha256sum /tmp/k189r2-before-reboot-private.tar.gz',timeout=55)
digest=p.stdout.decode().split()[0];path=host.PRIVATE/'before-reboot-private.tar.gz'
host.download('/tmp/k189r2-before-reboot-private.tar.gz',path);assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
p=host.ssh('cat /var/lib/samurai/k189r2-quiesce/quiesce-validation.json');report=json.loads(p.stdout);assert report['quiesce_audit_pass']
(host.PRIVATE/'quiesce-validation-private.json').write_bytes(p.stdout)
(Path(__file__).resolve().parent.parent/'r2-pre-reboot-archive-validation.json').write_text(json.dumps(dict(sha256=digest,verified=True,no_transition_yet_sent=True),indent=2)+'\n')
print('Second current-boot quiesce and full private archive passed.')
