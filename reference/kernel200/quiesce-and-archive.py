from pathlib import Path
import host,hashlib,json

p=host.ssh('sh /var/lib/samurai/k200-reboot-tools/quiesce-current183.sh',timeout=120)
(host.PRIVATE/'quiesce-host-private.log').write_bytes(p.stdout+p.stderr)
p=host.ssh('cat /var/lib/samurai/k200-quiesce/quiesce-validation.json')
r=json.loads(p.stdout);assert r['current_kernel']==183 and r['taint']==512 and r['quiesce_audit_pass']
(host.PRIVATE/'quiesce-validation-private.json').write_bytes(p.stdout)
p=host.ssh('tar -C /var/lib/samurai -czf /tmp/k200-before-transition-private.tar.gz k200-baseline k200-quiesce k200-reboot-tools && sha256sum /tmp/k200-before-transition-private.tar.gz',timeout=45)
digest=p.stdout.decode().split()[0];path=host.PRIVATE/'before-transition-private.tar.gz'
host.download('/tmp/k200-before-transition-private.tar.gz',path)
assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
host.download('/var/lib/samurai/k200-baseline/boot-id-private.txt',host.PRIVATE/'source-boot-id-private.txt')
report=dict(stage=200,quiesce_audit_pass=True,taint=512,current_kernel=183,private_archive_verified=True,
    old_camss_module_backup_in_archive=True,wifi_management_kept_until_detached_final_transition=True,
    no_reboot_or_flash_yet=True)
(Path(__file__).resolve().parent/'pre-transition-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
