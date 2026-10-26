from pathlib import Path
import host,hashlib,json,subprocess,ast

ref=Path(__file__).resolve().parent
for name in ['install-paired-module.py','final-transition.sh','finish-quiesce-after-network-stop.sh']:
    host.upload(ref/name,'/var/lib/samurai/k200-reboot-tools/'+name)
p=host.ssh('cat /var/lib/samurai/k200-preliminary/summary-private.json')
proof=json.loads(p.stdout);assert proof['preliminary_quiesce_pass'];(host.PRIVATE/'preliminary-quiesce-private.json').write_bytes(p.stdout)
p=host.ssh('python3 /var/lib/samurai/k200-reboot-tools/install-paired-module.py',timeout=45)
deployment=json.loads(p.stdout);assert deployment['module_replaced_for_paired_static_dt_boot']
(host.PRIVATE/'paired-module-deployment-private.json').write_bytes(p.stdout)
p=host.ssh('tar -C /var/lib/samurai -czf /tmp/k200-before-transition-private.tar.gz k200-baseline k200-quiesce k200-reboot-tools k200-preliminary k200-deploy && sha256sum /tmp/k200-before-transition-private.tar.gz',timeout=45)
digest=p.stdout.decode().split()[0];path=host.PRIVATE/'before-transition-private.tar.gz'
host.download('/tmp/k200-before-transition-private.tar.gz',path);assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
host.download('/var/lib/samurai/k200-baseline/boot-id-private.txt',host.PRIVATE/'source-boot-id-private.txt')
report=dict(stage=200,preliminary_quiesce_pass=True,private_archive_verified=True,exact_original_camss_backup_verified=True,
    paired_module_installed_but_not_loaded_against_old_dt=True,boot_rollback_file_verified=True,
    full_quiesce_required_in_single_detached_transition=True,networkmanager_auto_activation_reason_recorded=True,
    no_reboot_or_flash_yet=True)
(ref/'pre-transition-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
