from pathlib import Path
import hashlib,json,subprocess
dest=Path('/home/cy122/x2pro-linux/refs/realme-amp-git-k102')
out=Path('/mnt/e/edk2-samurai-out/kernel102')
commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
assert subprocess.check_output(['git','rev-parse','FETCH_HEAD'],cwd=dest,text=True).strip()==commit
files=[]
for name in ('max98937.c','max98937.h'):
    path='audio-kernel/asoc/codecs/max989xx/'+name
    data=subprocess.check_output(['git','show',commit+':'+path],cwd=dest)
    if name.endswith('.c'):assert b'GNU General Public License version 2' in data[:1000] and b'MODULE_LICENSE("GPL")' in data
    else:assert b'MAX98937_REV_ID' in data and b'#include "max98937.h"' in subprocess.check_output(['git','show',commit+':audio-kernel/asoc/codecs/max989xx/max98937.c'],cwd=dest)
    p=dest/path;assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    files.append(dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'oem-amp-git-provenance.json').write_text(json.dumps(dict(primary_repository='https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source',pinned_commit=commit,
 files=files,implementation_license='GPL-2.0',header_used_by_GPL_implementation=True,build_recipes_not_copied=True),indent=2)+'\n')
print('PINNED_OFFICIAL_DUAL_AMP_SOURCE_VERIFIED')
