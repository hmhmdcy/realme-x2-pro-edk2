"""Run only new private-copy tools; statically inspect actual required ELF dependencies."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'phosh-build-readiness-501'
BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
sha=lambda b:hashlib.sha256(b).hexdigest()
commands=[['gcc','--version'],['python3','--version'],['g-ir-scanner','--version'],['g-ir-compiler','--version'],
          ['pkg-config','--modversion','gtk+-3.0','upower-glib'],['pkg-config','--modversion','gnome-desktop-3.0']]
tools=[]
for command in commands:
    p=subprocess.run(['chroot',str(ROOT),*command],capture_output=True,timeout=60,
                     env={'PATH':'/usr/sbin:/usr/bin:/sbin:/bin','HOME':'/root','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'})
    tools.append({'command':command,'returncode':p.returncode,'stdout':p.stdout.decode(errors='replace'),'stderr':p.stderr.decode(errors='replace')})
def resolve(path):
    current=path
    for _ in range(40):
        assert current.is_relative_to(ROOT),current
        parts=current.relative_to(ROOT).parts;cursor=ROOT;changed=False
        for i,part in enumerate(parts):
            cursor=cursor/part
            if cursor.is_symlink():
                target=Path(os.readlink(cursor))
                candidate=(ROOT/target.relative_to('/')) if target.is_absolute() else cursor.parent/target
                current=Path(os.path.normpath(candidate.joinpath(*parts[i+1:])))
                changed=True;break
        if not changed:return current
    raise ValueError('too many symlinks')
def library(name,search):
    for directory in search+['usr/lib','lib']:
        p=resolve(ROOT/directory/name)
        if p.is_file():return p
    return None
abi=json.loads((OLD/'closure-abi-result.json').read_bytes())
queue=[{'name':p['requirement'][3:],'chain':[p['requirement'][3:]]} for p in abi['direct_soname_provider_comparison']]
seen=set();checked=[];missing=[]
while queue:
    row=queue.pop(0);name=row['name']
    if name in seen:continue
    seen.add(name);p=library(name,row.get('search',[]))
    if p is None:missing.append(row);continue
    r=subprocess.run(['readelf','--dynamic',str(p)],capture_output=True,timeout=20)
    assert r.returncode==0,(name,r.stderr.decode())
    dynamic=r.stdout.decode()
    needed=re.findall(r'\(NEEDED\).*?\[(.*?)\]',dynamic)
    paths=re.findall(r'\((?:RUNPATH|RPATH)\).*?\[(.*?)\]',dynamic)
    search=[]
    for value in paths:
        for directory in value.split(':'):
            directory=directory.replace('$ORIGIN',str(p.parent.relative_to(ROOT)))
            search.append(directory.lstrip('/'))
    checked.append({'soname':name,'path':str(p.relative_to(ROOT)),'sha256':sha(p.read_bytes()),'needed':needed,'rpath':paths})
    for dep in needed:queue.append({'name':dep,'chain':row['chain']+[dep],'search':search})
result={'only_private_copy_commands_executed':tools,'actual_42_provider_transitive_elf_count':len(checked),
        'missing_actual_DT_NEEDED':missing,'checked_ELF':checked,'no_package_complete_claim':True,
        'source_sha256':sha(Path(__file__).read_bytes())}
(HERE/'private-tools-links-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'tools':tools,'ELF_count':len(checked),'missing':missing,
                  'result_sha256':sha((HERE/'private-tools-links-result.json').read_bytes())},indent=2))
