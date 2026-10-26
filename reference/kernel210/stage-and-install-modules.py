from pathlib import Path
import hashlib,json,host
here=Path(__file__).resolve().parent;private=host.PRIVATE
assert json.loads((here/'install-baseline-validation.json').read_text())['original_mfd_and_module_metadata_backed_up']
dest='/var/lib/samurai/k210-module-stage'
host.ssh('test ! -e '+dest+' && mkdir -m700 '+dest)
for name in ['imx471.ko','v4l2-cci.ko','qcom-pm8008.ko']:host.upload(private/'modules'/name,dest+'/'+name)
host.upload(here/'camera-module-build-validation.json',dest+'/camera-module-build-validation.json')
host.upload(here/'install-camera-modules.py',dest+'/install-camera-modules.py')
archive='/tmp/k210-modules-before-private.tar.gz'
p=host.ssh('tar -C /var/lib/samurai -czf '+archive+' k210-install-before-r2 && sha256sum '+archive)
digest=p.stdout.decode().split()[0];target=private/'modules-before-private.tar.gz';assert not target.exists();host.download(archive,target)
assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
p=host.ssh('python3 '+dest+'/install-camera-modules.py',timeout=120)
(private/'module-install-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);report['private_rollback_archive_verified_before_install']=True
(here/'module-install-validation.json').write_text(json.dumps(report,indent=2)+'\n')
plan=json.loads((private/'current-work-private.json').read_text());plan.update(state='210 three compatible camera modules installed after off-device rollback backup; all unrelated modules preserved; native load/unload check passed. Static DTB boot package built and verified but not flashed.',next='Fresh device/partitions/NV checks, quiesce with installed module manifest, archive and single guarded bootloader transition. Flash boot210 only after current fastboot identity.',transition_pending=False)
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))
