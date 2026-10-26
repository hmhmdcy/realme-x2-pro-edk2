from pathlib import Path
import hashlib,json
import host

p=host.ssh('sh /var/lib/samurai/k189-reboot-tools/quiesce-current183.sh',timeout=110)
(host.PRIVATE/'quiesce-host-private.log').write_bytes(p.stdout+p.stderr)
p=host.ssh('tar -C /var/lib/samurai -czf /tmp/k189-before-reboot-private.tar.gz k189-baseline k189-preflash k189-quiesce && sha256sum /tmp/k189-before-reboot-private.tar.gz',timeout=55)
digest=p.stdout.decode().split()[0];path=host.PRIVATE/'before-reboot-private.tar.gz'
host.download('/tmp/k189-before-reboot-private.tar.gz',path);assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
p=host.ssh('cat /var/lib/samurai/k189-quiesce/quiesce-validation.json');proof=json.loads(p.stdout)
assert proof['quiesce_audit_pass'] and proof['current_kernel']==183
(host.PRIVATE/'quiesce-validation-private.json').write_bytes(p.stdout)
(Path(__file__).resolve().parent/'pre-reboot-archive-validation.json').write_text(json.dumps(dict(sha256=digest,verified=True,all_remoteprocs_offline=True,no_transition_sent=True),indent=2)+'\n')
print('Current boot quiesced and private archive verified; no reboot sent yet.')
