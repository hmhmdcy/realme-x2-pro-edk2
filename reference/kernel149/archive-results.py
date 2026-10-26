"""Keep raw evidence and tools in persistent private storage before cleanup."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai')
archives=root/'k149-private-archives';archives.mkdir(mode=0o700,exist_ok=True)
entries=[]
for out in sorted(root.glob('k149-*')):
    if not (out/'result.json').is_file():continue
    archive=archives/(out.name+'-private.tar.gz')
    if not archive.exists():
        subprocess.run(['tar','-C',str(out),'-czf',str(archive),'.'],check=True,timeout=90)
    entries.append(dict(label=out.name.removeprefix('k149-'),name=archive.name,
        bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
deployment=root/'k149-deployment'
archive=archives/'k149-deployment-private.tar.gz'
if not archive.exists():subprocess.run(['tar','-C',str(deployment),'-czf',str(archive),'.'],check=True,timeout=90)
entries.append(dict(label='deployment',name=archive.name,bytes=archive.stat().st_size,
    sha256=hashlib.sha256(archive.read_bytes()).hexdigest()))
tools=root/'k149-tools/scripts';tools.mkdir(mode=0o700,exist_ok=True)
saved=[]
for p in sorted(Path('/tmp').glob('k149-*.py')):
    target=tools/p.name;shutil.copy2(p,target)
    assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
    saved.append(p.name)
report=dict(archives=entries,archive_count=len(entries),uploaded_tools_persisted=saved)
(archives/'archive-index.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
