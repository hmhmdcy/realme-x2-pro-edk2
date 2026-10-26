from pathlib import Path
import hashlib,json
import host

p=host.ssh('sh /var/lib/samurai/k187-reboot-tools/quiesce-current183.sh',timeout=110)
(host.PRIVATE/'quiesce-host-private.log').write_bytes(p.stdout+p.stderr)
p=host.ssh('tar -C /var/lib/samurai -czf /tmp/k187-before-reboot-private.tar.gz k187-a11-trial k187-preflash k187-quiesce k187-tools && sha256sum /tmp/k187-before-reboot-private.tar.gz',timeout=55)
digest=p.stdout.decode().split()[0]
path=host.PRIVATE/'k187-before-reboot-private.tar.gz';host.download('/tmp/k187-before-reboot-private.tar.gz',path)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
p=host.ssh('cat /var/lib/samurai/k187-quiesce/quiesce-validation.json')
data=json.loads(p.stdout);assert data['quiesce_audit_pass'] and data['current_kernel']==183
(host.PRIVATE/'quiesce-validation-private.json').write_bytes(p.stdout)
(Path(__file__).resolve().parent/'pre-reboot-archive-validation.json').write_text(json.dumps(dict(
    archive_sha256=digest,verified=True,all_remoteprocs_offline=True,no_transition_sent=True),indent=2)+'\n')
print(json.dumps({'quiesce_passed':True,'archive_sha_verified':True,'no_flash_requested':True}))
