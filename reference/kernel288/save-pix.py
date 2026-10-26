"""Commit the tested PIX integration and independently reproduce its complete tree."""
from pathlib import Path
import hashlib, json, os, subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel288')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE='6ddf1ba4cfafe221a38cc12667a1aac06f3f9ec5'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==BASE and git('branch','--show-current')=='samurai-vfe175-pix288'
assert subprocess.run(['git','-C',str(TREE),'diff','--cached','--quiet']).returncode==0
prefix='drivers/media/platform/qcom/camss/'
files=[prefix+n for n in ['camss-vfe-175-output.c','camss-vfe-17x.c','camss-vfe.c','camss-vfe.h','camss-video.c','camss-video.h','camss.c']]
assert sorted(git('diff','--name-only').splitlines())==sorted(files)
for report_name in ['pix-negotiation-host-validation.json','demux-mnds-host-tests-validation.json']:
    test=json.loads((ROOT/report_name).read_text());assert test['exit']==0 and test['stage']==288
    for name,sha in test['source_sha256'].items():
        assert hashlib.sha256((TREE/prefix/name).read_bytes()).hexdigest()==sha
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--binary','--full-index'])
path=ROOT/'vfe175-pix-candidate.patch';path.write_bytes(patch)
check=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(path)],text=True,capture_output=True)
log=PRIVATE/'pix-checkpatch-private.txt'
if log.exists():
    n=1
    while (PRIVATE/f'pix-checkpatch-private.txt.attempt{n}').exists():n+=1
    log.rename(PRIVATE/f'pix-checkpatch-private.txt.attempt{n}')
log.write_text(check.stdout+check.stderr)
assert check.returncode==0,check.stdout
subprocess.run(['git','-C',str(TREE),'add','--',*files],check=True)
body=PRIVATE/'pix-commit-message-private.txt'
body.write_text('''media: qcom: camss: expose the VFE175 FULL NV12 pixel path

Describe Bayer input separately from processed capture formats. Allow
per-output frame bounds and steps without changing legacy video nodes,
and keep compose/crop negotiation consistent with a full-input scaler.

Add the fourth PIX line to both SM8150 full IFEs, with only the two
implemented pads and one FULL output using clients 3/4 and group zero.
Preserve all three RDI lines, and do not advertise unsupported DS or
metadata outputs. Keep clocks, supplies and routing in existing generic
frameworks; no board DT, private control or userspace workaround is added.

This enables the candidate for standard media-controller hardware tests.
It does not claim verified silicon pixels, completed statistics/IPA,
calibration or full camera application support.

Signed-off-by: Samurai Builder <samurai@localhost>
''')
subprocess.run(['git','-C',str(TREE),'-c','user.name=Samurai Builder','-c','user.email=samurai@localhost','commit','-F',str(body)],check=True,capture_output=True)
commit=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==BASE and not git('status','--porcelain')
index=PRIVATE/'patch-check-index-private';assert not index.exists()
env=dict(os.environ,GIT_INDEX_FILE=str(index))
subprocess.run(['git','-C',str(TREE),'read-tree',BASE],env=env,check=True)
subprocess.run(['git','-C',str(TREE),'apply','--cached',str(path)],env=env,check=True)
rebuilt=subprocess.check_output(['git','-C',str(TREE),'write-tree'],env=env,text=True).strip()
assert rebuilt==git('rev-parse','HEAD^{tree}')
report=dict(stage=288,commit=commit,parent=BASE,branch=git('branch','--show-current'),
            source_sha256={n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in files},
            independent_index_tree_matches=True,patch_sha256=hashlib.sha256(patch).hexdigest(),
            checkpatch_exit=check.returncode,checkpatch_summary=[l for l in check.stdout.splitlines() if l.startswith('total:')],
            not_pushed=True,not_deployed=True)
(ROOT/'pix-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
