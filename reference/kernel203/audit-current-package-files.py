from pathlib import Path
import hashlib,json,os,stat

root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k203-baseline/boot-id-private.txt').read_bytes()
out=root/'k203-package-file-audit-r2';assert not out.exists();out.mkdir(mode=0o700)
manifest=json.loads((root/'k203-package-records/upstream-payload-manifest.json').read_text())
diffs=[]
for relative,expected in manifest.items():
 assert relative.startswith(('etc/','usr/','lib/','bin/','sbin/')) and '..' not in Path(relative).parts
 path=Path('/')/relative
 if expected['kind']=='symlink':
  actual=dict(kind='symlink',target=str(path.readlink())) if path.is_symlink() else dict(kind='missing-or-other')
 else:
  actual=dict(kind='file',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),mode=stat.S_IMODE(path.stat().st_mode)) if path.is_file() else dict(kind='missing-or-other')
 wanted={key:value for key,value in expected.items() if key!='package'}
 if actual!=wanted:diffs.append(dict(path=relative,package=expected['package'],expected=wanted,actual=actual))
(out/'differences-private.json').write_text(json.dumps(diffs,indent=2)+'\n')
r=dict(stage=203,files_checked=len(manifest),differences=diffs,no_files_changed=True)
(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(stage=203,files_checked=len(manifest),different_paths=[item['path'] for item in diffs],no_files_changed=True)))
