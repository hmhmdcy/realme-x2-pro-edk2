"""Capture actual boot, package database and old signed repository before any mutation."""
from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,os,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k273-work/boot-id-private.txt').read_bytes()
boot=Path(subprocess.check_output(['findfs','PARTLABEL=boot'],text=True).strip())
line=Path('/etc/apk/repositories.d/60-samurai-camera.list').read_text().strip();assert line.startswith('ndx file://') and line.endswith('/forward/packages.adb')
old_repo=line[len('ndx file://'):-len('/forward/packages.adb')];old=json.loads((Path(old_repo)/'forward-manifest.json').read_text())
assert len(old['packages'])==7 and all(p['version']==('0.1.0-r16' if p['name'].startswith('samurai-camera-') else '99990.7.2-r21') for p in old['packages'])
print(json.dumps(dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),boot_partition_sha256=hashlib.sha256(boot.read_bytes()).hexdigest(),package_db_sha256=hashlib.sha256(Path('/lib/apk/db/installed').read_bytes()).hexdigest(),old_repo=old_repo,release=os.uname().release)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);d=json.loads(q.stdout)
assert d['boot_partition_sha256']==json.loads((R.parent/'kernel273/build-package-validation.json').read_text())['boot_sha256']
(host.PRIVATE/'deployment-baseline-private.json').write_bytes(q.stdout)
print(json.dumps(dict(stage=275,actual_boot273_verified=True,old_seven_r21_r16_repository_identified=True,package_database_recorded=True,no_device_mutation=True)))
