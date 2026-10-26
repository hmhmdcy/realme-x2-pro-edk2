"""Check only stock RFS work-state metadata; no substitute rules or payloads."""
from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,os,stat,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai');out=root/'k231-rfs-work-layout'
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k230-runtime/boot-id-private.txt').read_bytes()
assert not out.exists() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
prior=json.loads((root/'k231-stock-rfs-layout/partitions-private.json').read_text())['persist'];dev=prior['device']
assert subprocess.check_output(['lsblk','-ndo','PARTLABEL',dev],text=True).strip()=='persist'
def check():assert subprocess.check_output(['sha256sum',dev],text=True,timeout=35).split()[0]==prior['sha256']
check();out.mkdir(mode=0o700);mp=Path('/run/k231-rfs-work-persist-ro');assert not mp.exists();mp.mkdir(mode=0o700)
subprocess.run(['mount','-t','ext4','-o','ro,noload,nosuid,nodev,noexec',dev,str(mp)],capture_output=True,check=True,timeout=20)
rows=[]
try:
 mount=next(l for l in Path('/proc/mounts').read_text().splitlines() if l.split()[1]==str(mp));options=mount.split()[3].split(',');assert 'ro' in options and 'norecovery' in options
 for relative in ['rfs/msm/mpss','rfs/msm/mpss/ota_firewall','rfs/msm/mpss/ota_firewall/ruleset','rfs/msm/mpss/mcfg.tmp']:
  path=mp/relative;row=dict(relative=relative,exists=path.exists() or path.is_symlink())
  if row['exists']:
   s=path.lstat();row.update(type=stat.S_IFMT(s.st_mode),mode=stat.S_IMODE(s.st_mode),bytes=s.st_size)
  rows.append(row)
 (out/'stock-stat-only-private.json').write_text(json.dumps(rows,indent=2)+'\n');(out/'mount-private.txt').write_text(mount+'\n')
finally:subprocess.run(['umount',str(mp)],capture_output=True,check=True,timeout=20)
check();assert boot==Path('/proc/sys/kernel/random/boot_id').read_bytes() and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
report=dict(stage=231,current230_guard_verified=True,stock_persist_ro_noload=True,partition_hash_preserved=True,temporary_mount_closed=True,
 payloads_not_read=True,no_generated_rules_or_nv_service_change=True,metadata=rows)
(out/'summary-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=90);(host.PRIVATE/'stock-work-layout-host-private.json').write_bytes(r.stdout)
report=json.loads(r.stdout);(Path(__file__).resolve().parent/'stock-work-layout-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
