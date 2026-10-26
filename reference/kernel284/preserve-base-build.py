"""Preserve the completed 282 kernel and modules before changing candidate source."""
from pathlib import Path
import collections
import hashlib
import json
import shutil
import subprocess
import tarfile
import sys
from storage import mounted_build

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel284')
BUILD=mounted_build()
PREVIOUS=Path('/mnt/e/edk2-samurai-out/kernel282')
result=json.loads((PREVIOUS/'full-kernel-r3-build-result-private.json').read_text())
assert result['terminal'] and result['exit']==0 and result['source_still_clean']
for pid in [592,794]:
    cmd=Path('/proc',str(pid),'cmdline')
    assert not cmd.exists() or b'camera279-isp-kernel' not in cmd.read_bytes() and b'build-full-kernel.py' not in cmd.read_bytes()
mount=subprocess.check_output(['findmnt','-n','-o','SOURCE,TARGET','/mnt/samurai-full282'],text=True).split()
assert len(mount)==2 and mount[1]=='/mnt/samurai-full282'
backing=Path('/sys/class/block',Path(mount[0]).name,'loop/backing_file').read_text().strip()
assert Path(backing).resolve()==(PREVIOUS/'full-kernel-build282.ext4').resolve()
DEST=PRIVATE/'completed-base282'
resume=sys.argv[1:]==['resume-o-order']
assert not sys.argv[1:] or resume
assert DEST.is_dir() if resume else not DEST.exists()
DEST.mkdir(exist_ok=resume)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
artifacts={}
for name in list(result['artifacts'])+['.config','System.map']:
    source=BUILD/name;target=DEST/name;target.parent.mkdir(parents=True,exist_ok=True)
    if name in result['artifacts']:assert sha(source)==result['artifacts'][name]['sha256']
    if target.exists():assert resume and sha(source)==sha(target)
    else:shutil.copyfile(source,target)
    assert sha(source)==sha(target)
    artifacts[name]=dict(bytes=target.stat().st_size,sha256=sha(target))
ordered=(BUILD/'modules.order').read_text().splitlines();assert len(ordered)==778
assert all(name.endswith('.o') for name in ordered)
modules=[str(Path(name).with_suffix('.ko')) for name in ordered]
module_hashes={}
archive=DEST/'modules-verified.tar.gz'
assert not archive.exists()
with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
    for name in modules:
        path=BUILD/name;assert name.endswith('.ko') and path.resolve().is_relative_to(BUILD.resolve())
        assert path.is_file() and not path.is_symlink()
        module_hashes[name]=sha(path);tar.add(path,arcname=name,recursive=False)
with tarfile.open(archive,'r:gz') as tar:
    assert tar.getnames()==modules
    for item in tar:
        assert hashlib.sha256(tar.extractfile(item).read()).hexdigest()==module_hashes[item.name]
(DEST/'module-hashes-private.json').write_text(json.dumps(module_hashes,indent=2)+'\n')
lines=[line for line in (PREVIOUS/'full282-r3-w1-private.log').read_text().splitlines()
       if 'warning:' in line.lower() or 'error:' in line.lower()]
assert len(lines)==1140 and not any('error:' in line.lower() for line in lines)
categories=collections.Counter(line.rsplit('[-W',1)[-1].rstrip(']') if '[-W' in line else 'other' for line in lines)
examples={name:next(line for line in lines if ('[-W'+name+']') in line) for name in categories if name!='other'}
report=dict(stage=284,base_commit=result['commit'],full_build_exit=0,artifacts=artifacts,
            module_count=778,module_archive_bytes=archive.stat().st_size,module_archive_sha256=sha(archive),
            all_archived_module_hashes_verified=True,warnings=len(lines),errors=0,
            module_order_uses_o_suffix=True,actual_ko_payloads_verified=True,
            warning_categories=dict(categories),warning_examples=examples,camss_diagnostics=[],
            dtb_unchanged=True,not_deployed=True,no_hardware_isp_claim=True)
(ROOT/'base-full-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
