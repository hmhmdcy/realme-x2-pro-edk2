"""Save only this stage's verified Demosaic36 source changes."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel284')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE='97a4c563803fd943e5a4c3f0359548a3d758bcc5'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==BASE and git('branch','--show-current')=='samurai-vfe175-demosaic284'
assert subprocess.run(['git','-C',str(TREE),'diff','--cached','--quiet']).returncode==0
assert json.loads((ROOT/'demosaic-host-tests-validation.json').read_text())['exit']==0
names=['Makefile','camss-vfe-175-demosaic.c','camss-vfe-175-demosaic.h',
       'camss-vfe-175-pixel.c','camss-vfe-175-pixel.h','camss-vfe-17x.c']
files=['drivers/media/platform/qcom/camss/'+n for n in names]
subprocess.run(['git','-C',str(TREE),'add','--',*files],check=True)
assert sorted(git('diff','--cached','--name-only').splitlines())==sorted(files)
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--cached','--binary','--full-index'])
(ROOT/'vfe175-demosaic-candidate.patch').write_bytes(patch)
check=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(ROOT/'vfe175-demosaic-candidate.patch')],text=True,capture_output=True)
(PRIVATE/'demosaic-checkpatch-private.txt').write_text(check.stdout+check.stderr)
assert '0 errors' in check.stdout,check.stdout
message='''media: qcom: camss: configure Demosaic36 on full VFE175

Use the matched SM8150 Demosaic36 backend, preserving reserved fields and
validating interpolation/classifier values before MMIO. Configure the
bring-up profile before enabling the module and leave PIX RUP to output
start. Disable only its lens bit on full-output stop or enable failure.

The complete pixel processing chain and hardware validation remain
pending; keep the current three RDI resources unchanged.

Signed-off-by: Samurai Builder <samurai@localhost>
'''
body=PRIVATE/'demosaic-commit-message-private.txt';body.write_text(message)
subprocess.run(['git','-C',str(TREE),'-c','user.name=Samurai Builder','-c','user.email=samurai@localhost',
                'commit','-F',str(body)],check=True,capture_output=True)
commit=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==BASE and not git('status','--porcelain')
report=dict(stage=284,commit=commit,parent=BASE,branch='samurai-vfe175-demosaic284',
            source_sha256={n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in files},
            patch_sha256=hashlib.sha256(patch).hexdigest(),checkpatch_exit=check.returncode,
            checkpatch_summary=[l for l in check.stdout.splitlines() if l.startswith('total:')],
            not_pushed=True,not_deployed=True)
(ROOT/'demosaic-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
