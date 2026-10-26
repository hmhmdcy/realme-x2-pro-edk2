from pathlib import Path
import hashlib,host,json,shutil
here=Path(__file__).resolve().parent;private=host.PRIVATE;target=private/'phone-apk-installed-original-private.txt';assert not target.exists()
code=r'''
from pathlib import Path
import hashlib,json
root=Path('/var/lib/samurai');base=root/'k214-baseline';assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(base/'boot-id-private.txt').read_bytes()
data=(base/'apk-installed-before-private.txt').read_bytes();assert data==Path('/lib/apk/db/installed').read_bytes();print(json.dumps(dict(size=len(data),sha256=hashlib.sha256(data).hexdigest())))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=30);record=json.loads(p.stdout)
with target.open('xb') as output:
    for offset in range(0,record['size'],65536):
        p=host.ssh('dd if=/var/lib/samurai/k214-baseline/apk-installed-before-private.txt bs=65536 skip='+str(offset//65536)+' count=1',timeout=30);assert len(p.stdout)==min(65536,record['size']-offset);output.write(p.stdout)
assert hashlib.sha256(target.read_bytes()).hexdigest()==record['sha256']
root=Path('/home/cy122/x2pro-linux/libcamera214-solver-before');assert not root.exists();(root/'lib/apk/db').mkdir(mode=0o700,parents=True);(root/'etc/apk/keys').mkdir(mode=0o700,parents=True)
shutil.copyfile(target,root/'lib/apk/db/installed');shutil.copyfile(private/'phone-world-private.txt',root/'etc/apk/world')
for p in (private/'phone-trusted-public-keys').glob('*.pub'):shutil.copyfile(p,root/'etc/apk/keys'/p.name)
count=sum(line.startswith('P:') for line in target.read_text().splitlines())
report=dict(stage=214,actual_phone_installed_package_database_and_world_copied=True,source_database_unchanged_since214_baseline=True,sha256_transfer_verified=True,host_solver_root_isolated=True,already_trusted_public_keys_only=True,installed_package_count=count,no_device_package_transaction_sent=True)
(here/'solver-snapshot-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
