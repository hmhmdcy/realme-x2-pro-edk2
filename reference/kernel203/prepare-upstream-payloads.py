from pathlib import Path
import hashlib,json,stat,subprocess,tarfile

root=Path('/mnt/e/edk2-samurai-out/kernel203');dest=Path('/home/cy122/x2pro-linux/samurai-packages203/upstream-payloads');assert not dest.exists();dest.mkdir(mode=0o700,parents=True)
old_manifest=root/'upstream-payload-manifest.json'
if old_manifest.exists():
 backup=root/'upstream-payload-manifest-drvfs-private.json';assert not backup.exists();backup.write_bytes(old_manifest.read_bytes())
apk='/home/cy122/pmos-samurai-rootfs01/work/apk.static';keys='/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys'
records=json.loads((Path(__file__).resolve().parent/'upstream-package-validation.json').read_text())
manifest={}
for record in records:
 source=root/'upstream-apks'/(record['name']+'-'+record['version']+'.apk');assert hashlib.sha256(source.read_bytes()).hexdigest()==record['sha256']
 payload=dest/record['name'];payload.mkdir()
 p=subprocess.run([apk,'--keys-dir',keys,'extract','--destination',str(payload),str(source)],capture_output=True,check=True)
 (root/(record['name']+'-extract-private.log')).write_bytes(p.stdout+p.stderr)
 with tarfile.open(source,'r:gz',ignore_zeros=True) as archive:modes={member.name:member.mode for member in archive.getmembers() if member.isfile() and not member.name.startswith('.')}
 for path in payload.rglob('*'):
  relative=str(path.relative_to(payload))
  if path.is_symlink():item=dict(kind='symlink',target=str(path.readlink()))
  elif path.is_file():
   assert stat.S_IMODE(path.stat().st_mode)==modes[relative]
   assert path.stat().st_uid==path.stat().st_gid==0
   item=dict(kind='file',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),mode=modes[relative])
  else:continue
  assert not relative.startswith('.') and relative.startswith(('etc/','usr/','lib/','sbin/','bin/'))
  assert relative not in manifest;manifest[relative]=dict(package=record['name'],**item)
(root/'upstream-payload-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(dict(stage=203,payload_files=len(manifest),official_signed_package_payloads_extracted=True)))
