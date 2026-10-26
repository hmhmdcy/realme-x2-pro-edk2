from pathlib import Path
import hashlib,json,subprocess
repo='https://github.com/realme-kernel-opensource/realmeX2Pro-kernel-source.git'
commit='9668fcdc6ec15be7a10d66f7b93c347829e0fdb6'
dest=Path('/home/cy122/x2pro-linux/refs/realme-amp-git-k102')
out=Path('/mnt/e/edk2-samurai-out/kernel102')
assert not dest.exists()
subprocess.run(['git','init','-q',str(dest)],check=True)
subprocess.run(['git','remote','add','origin',repo],cwd=dest,check=True)
subprocess.run(['git','fetch','--depth=1','--filter=blob:none','origin',commit],cwd=dest,check=True)
assert subprocess.check_output(['git','rev-parse','FETCH_HEAD'],cwd=dest,text=True).strip()==commit
tree=subprocess.check_output(['git','ls-tree','-r','--name-only',commit],cwd=dest,text=True).splitlines()
paths=[p for p in tree if p.startswith('audio-kernel/') and 'max989' in p.lower()]
assert paths
files=[]
for path in paths:
    data=subprocess.check_output(['git','show',commit+':'+path],cwd=dest)
    assert b'GNU General Public License' in data[:2500] or b'SPDX-License-Identifier: GPL' in data[:1000]
    p=dest/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    files.append(dict(path=path,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
report=dict(primary_repository=repo,pinned_commit=commit,checkout_created=False,downloaded_files=files)
(out/'oem-amp-git-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(commit=commit,files=[f['path'] for f in files])))
