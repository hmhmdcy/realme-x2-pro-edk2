"""Locate one existing handset modem backup; keep its identifying path private."""
from pathlib import Path
import hashlib,json
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel242')
files=list(Path('/mnt/e/BACKUPS').glob('*/*/modem.emmc.win'));assert len(files)==1
backup=files[0];expected=Path(str(backup)+'.sha2').read_text().split()[0]
h=hashlib.sha256()
with backup.open('rb') as f:
 while x:=f.read(4*1024*1024):h.update(x)
assert h.hexdigest()==expected
(P/'android-backup-source-private.json').write_text(json.dumps(dict(modem_image=str(backup),bytes=backup.stat().st_size,sha256=h.hexdigest()),indent=2)+'\n')
report=dict(stage=242,unique_existing_backup=True,modem_image_bytes=backup.stat().st_size,backup_sha256_sidecar_verified=True,backup_not_modified=True,identifying_path_private=True)
(R/'android-backup-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
