from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel214');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
old=json.loads((private/'config-package-build-result-private.json').read_text());assert old['abuild_exit']==1 and len(old['packages'])==2
source=root/'private/samurai-linux-203.rsa.pub';target=root/'etc/apk/keys'/source.name;assert not target.exists();shutil.copyfile(source,target);target.chmod(0o644)
packages=sorted((root/'packages-config').rglob('*.apk'));assert len(packages)==2
for index,path in enumerate(packages):
    p=subprocess.run(['chroot',str(root),'/sbin/apk','verify','/'+str(path.relative_to(root))],capture_output=True,timeout=30)
    (private/('config-signature-verify-'+str(index)+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
with (private/'config-index-repair-private.log').open('xb') as log:
    p=subprocess.run(['chroot',str(root),'/usr/bin/env','SOURCE_DATE_EPOCH=1792022400','/bin/ash','-c','cd /work/samurai-camera-config && exec /usr/bin/abuild -F -d -K -P /packages-config index'],stdout=log,stderr=subprocess.STDOUT,timeout=60)
assert p.returncode==0
record=dict(stage=214,config_and_stack_packages_built=True,package_count=2,all_project_signatures_verified=True,first_index_failure_due_to_missing_project_public_key_in_build_root=True,public_project_key_added_only_to_isolated_host_root=True,private_key_not_published_or_copied_to_phone=True,repository_index_created=True,phone_not_modified=True)
(here/'config-package-build-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
