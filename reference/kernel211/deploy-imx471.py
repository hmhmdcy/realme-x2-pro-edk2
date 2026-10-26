from pathlib import Path
import hashlib,json,host
here=Path(__file__).resolve().parent
p=host.ssh('python3 -',input=(here/'backup-installed-module.py').read_bytes(),timeout=90);(host.PRIVATE/'module-backup-host-private.log').write_bytes(p.stdout+p.stderr)
dest='/var/lib/samurai/k211-module-stage';host.ssh('test ! -e '+dest+' && mkdir -m700 '+dest)
for local,name in [(host.PRIVATE/'modules/imx471.ko','imx471.ko'),(here/'imx471-module-build-validation.json','imx471-module-build-validation.json')]:host.upload(local,dest+'/'+name)
archive='/tmp/k211-module-before-private.tar.gz';p=host.ssh('tar -C /var/lib/samurai -czf '+archive+' k211-module-before && sha256sum '+archive)
digest=p.stdout.decode().split()[0];target=host.PRIVATE/'module-before-private.tar.gz';assert not target.exists();host.download(archive,target);assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
p=host.ssh('python3 -',input=(here/'install-imx471.py').read_bytes(),timeout=100);(host.PRIVATE/'module-install-host-private.log').write_bytes(p.stdout+p.stderr)
report=json.loads(p.stdout);report['private_rollback_archive_verified_before_install']=True
(here/'module-install-validation.json').write_text(json.dumps(report,indent=2)+'\n')
plan=json.loads((host.PRIVATE/'current-work-private.json').read_text());plan.update(state='211 updated IMX471 installed on disk with old module/metadata privately exported first. Only sensor module changed;771 others preserved. Running old module remains bound/crop errno22 until planned warm boot. Heap config/scoped access deployed and user-tested.',next='Prepare fresh211 quiesce moving camera unload after GUI/monitor closure; fresh current checks/archive, guarded warm reboot of boot210 without flashing. Verify new crop TRY/ACTIVE, automatic heaps/access and native/libcamera capture.')
(host.PRIVATE/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps(report))
