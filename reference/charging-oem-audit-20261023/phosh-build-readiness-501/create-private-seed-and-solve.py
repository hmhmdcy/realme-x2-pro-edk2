"""One new private copy + native-host APK simulation. Never writes the original seed."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import stat
import subprocess
import time

HERE = Path(__file__).resolve().parent
SEED = Path('/home/cy122/x2pro-linux/libcamera214-root')
BASE = Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT = BASE/'root'
APK = Path('/home/cy122/pmos-samurai-rootfs01/work/apk.static')
KEYS = Path('/home/cy122/pmos-samurai-rootfs01/work/config_apk_keys')
sha = lambda b: hashlib.sha256(b).hexdigest()
os.umask(0o077)
inventory = json.loads((HERE/'inventory-result.json').read_bytes())
readiness = json.loads((HERE/'result.json').read_bytes())
db = (SEED/'lib/apk/db/installed').read_bytes()
world = (SEED/'etc/apk/world').read_bytes()
assert sha(db) == inventory['seed']['installed_db_sha256']
assert sha(world) == inventory['seed']['world_sha256']
assert BASE.is_absolute() and BASE.parent == Path('/home/cy122/charging-management-20261023') and not BASE.exists()
assert not any(str(SEED) in line.split()[4] for line in Path('/proc/self/mountinfo').read_text().splitlines())
assert KEYS.is_dir() and APK.is_file()

tops = ['bin','sbin','lib','usr','etc','var']
excluded = {'var/cache','var/log','var/tmp'}
count = total = 0
for top in tops:
    for base, dirs, files in os.walk(SEED/top, followlinks=False):
        relative = Path(base).relative_to(SEED)
        dirs[:] = [d for d in dirs if str(relative/d) not in excluded]
        for name in files:
            p = Path(base)/name
            if p.is_symlink():
                continue
            st = p.stat()
            assert stat.S_ISREG(st.st_mode), str(p)
            count += 1
            total += st.st_size
free = shutil.disk_usage(BASE.parent).free
assert free > total*2+4*1024**3, (free,total)
BASE.mkdir(mode=0o700)
ROOT.mkdir(mode=0o700)
state = {'phase':'copying-private-seed','source':str(SEED),'private_root':str(ROOT),
         'source_regular_files':count,'source_regular_bytes':total,'free_before':free,
         'no_hardlinks':True,'excluded':['original work/private/candidate/packages/home/root directories',*sorted(excluded)],
         'original_db_sha256':sha(db),'original_world_sha256':sha(world),'terminal':False}
def save():
    (BASE/'state-private.json').write_text(json.dumps(state,indent=2)+'\n')
save()
def ignore(directory,names):
    rel = Path(directory).relative_to(SEED)
    return [n for n in names if str(rel/n) in excluded]
copied = 0
def independent_copy(source,destination):
    global copied
    shutil.copy2(source,destination)
    a,b = os.stat(source),os.stat(destination)
    assert (a.st_dev,a.st_ino) != (b.st_dev,b.st_ino)
    copied += 1
    return destination
for top in tops:
    shutil.copytree(SEED/top,ROOT/top,symlinks=True,copy_function=independent_copy,ignore=ignore)
for name in ['dev','proc','sys','run','tmp','root','home','work','private','packages','var/cache','var/log','var/tmp']:
    (ROOT/name).mkdir(parents=True,exist_ok=True)
os.chmod(ROOT/'tmp',0o1777)
os.chmod(ROOT/'root',0o700)
assert copied == count
assert (ROOT/'lib/apk/db/installed').read_bytes() == db
assert (ROOT/'etc/apk/world').read_bytes() == world
assert (SEED/'lib/apk/db/installed').read_bytes() == db and (SEED/'etc/apk/world').read_bytes() == world
state.update(phase='private-copy-complete',copied_regular_files=copied)
save()

repo = BASE/'frozen-repositories'
index_sources = {
    'main':(Path('/home/cy122/pmos-samurai-rootfs01/work/cache_apk_aarch64/APKINDEX.53194aba.tar.gz'),'8408c99f518586b74c6740f1afc7ed4c4c4e038c7364d8fa73235dd72ac3b119'),
    'community':(Path('/home/cy122/pmos-samurai-rootfs01/work/cache_apk_aarch64/APKINDEX.d022dfc8.tar.gz'),'86a0b6cc580f430eebd071784067e0140457d49c33ad56334340228fd8dc60cd'),
}
index_pins = {}
for name,(source,digest) in index_sources.items():
    raw = source.read_bytes()
    assert sha(raw) == digest
    output = repo/name/'aarch64/APKINDEX.tar.gz'
    output.parent.mkdir(parents=True)
    output.write_bytes(raw)
    index_pins[name] = {'source':str(source),'sha256':digest,'private':str(output)}
repositories = BASE/'repositories-private.list'
repositories.write_text(''.join('file://'+str(repo/name)+'\n' for name in index_sources))
requested = [name+'='+row['version'] for name,row in readiness['pinned_direct_download_candidates_and_checkdepends'].items()]
command = [str(APK),'--root',str(ROOT),'--arch','aarch64','--no-network','--keys-dir',str(KEYS),
           '--repositories-file',str(repositories),'--no-cache','add','--simulate',*requested]
state.update(phase='private-native-host-solver',requested=requested,index_pins=index_pins,
             apk_static_sha256=sha(APK.read_bytes()),solver_command=command)
save()
start = time.monotonic()
result = subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
(BASE/'solver-private.log').write_bytes(result.stdout)
assert (SEED/'lib/apk/db/installed').read_bytes() == db and (SEED/'etc/apk/world').read_bytes() == world
assert (ROOT/'lib/apk/db/installed').read_bytes() == db and (ROOT/'etc/apk/world').read_bytes() == world
state.update(phase='solver-complete' if result.returncode==0 else 'solver-failed',terminal=True,
             solver_returncode=result.returncode,solver_seconds=round(time.monotonic()-start,3),
             original_and_private_db_world_unchanged_by_simulation=True,
             solver_log_sha256=sha(result.stdout))
save()
(HERE/'private-copy-and-solver-result.json').write_text(json.dumps(state,indent=2)+'\n')
print(result.stdout.decode(errors='replace'))
print(json.dumps({'returncode':result.returncode,'private_root':str(ROOT),'copied_files':copied,'copied_bytes':total,
                  'result_sha256':sha((HERE/'private-copy-and-solver-result.json').read_bytes())}))
raise SystemExit(result.returncode)
