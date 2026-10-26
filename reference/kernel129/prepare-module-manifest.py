from pathlib import Path
import hashlib,json,tarfile
r=Path('/mnt/e/RealmeX2Pro edk2');ref=r/'reference/kernel129';out=Path('/mnt/e/edk2-samurai-out/kernel129')
build=json.loads((ref/'kernel-build-validation.json').read_text());pack=out/'modules-k129-private.tar.gz'
assert hashlib.sha256(pack.read_bytes()).hexdigest()==build['archive_sha256']
release=build['release'];prefix='lib/modules/'+release+'/';lines=[];modules=0
with tarfile.open(pack) as tf:
 for m in tf:
  assert (m.isfile() or m.isdir()) and '..' not in Path(m.name).parts and not Path(m.name).is_absolute()
  if not m.isfile():continue
  assert m.name.startswith(prefix)
  name=m.name[len(prefix):];assert '\n' not in name and not name.startswith('/')
  payload=tf.extractfile(m).read();lines.append(hashlib.sha256(payload).hexdigest()+'  ./'+name)
  modules+=name.endswith('.ko')
assert modules==770
(out/'module-tree.sha256').write_text('\n'.join(sorted(lines))+'\n')
print('K129_HOST_ARCHIVE_SAFE_770_MODULE_ALL_FILE_HASH_MANIFEST_READY',flush=True)
