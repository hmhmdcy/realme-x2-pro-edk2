"""Commit only the CST backend and its kernel-internal integration."""
from pathlib import Path
import hashlib,json,os,re,subprocess

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel285')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
BASE='af9e2a02365a2ec1a19d3cc42da5c65e84c244c4'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==BASE and git('branch','--show-current')=='samurai-vfe175-cst285'
assert subprocess.run(['git','-C',str(TREE),'diff','--cached','--quiet']).returncode==0
test=json.loads((ROOT/'cst-host-tests-validation.json').read_text());assert test['exit']==0
prefix='drivers/media/platform/qcom/camss/'
files=[prefix+n for n in ['Makefile','camss-vfe-175-cst.c','camss-vfe-175-cst.h','camss-vfe-175-pixel.c']]
for n,h in test['source_sha256'].items():assert hashlib.sha256((TREE/prefix/n).read_bytes()).hexdigest()==h
subprocess.run(['git','-C',str(TREE),'add','--',*files],check=True)
assert sorted(git('diff','--cached','--name-only').splitlines())==sorted(files)
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--cached','--binary','--full-index'])
(ROOT/'vfe175-cst-candidate.patch').write_bytes(patch)
check=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(ROOT/'vfe175-cst-candidate.patch')],text=True,capture_output=True)
(PRIVATE/'cst-checkpatch-private.txt').write_text(check.stdout+check.stderr)
assert '0 errors' in check.stdout,check.stdout
message='''media: qcom: camss: add the VFE175 CST12 color encoding backend

Build BT.601 and BT.709 full/limited matrices from the capture format's
encoding and quantization. Keep neutral chroma exact, preserve reserved
bits and validate every signed Q10 coefficient, offset and clamp before
MMIO. Program the output transform before enabling frame bit zero, with
PIX RUP left to output start, and clear it on stop or enable failure.

This is an internal backend, not a new userspace color tuning ABI. Keep
the three RDI resources unchanged while the remaining processing and
statistics stages are developed. Hardware color and slot ordering still
need TPG/RAW validation once the full pipeline is available.

Signed-off-by: Samurai Builder <samurai@localhost>
'''
body=PRIVATE/'cst-commit-message-private.txt';body.write_text(message)
subprocess.run(['git','-C',str(TREE),'-c','user.name=Samurai Builder','-c','user.email=samurai@localhost','commit','-F',str(body)],check=True,capture_output=True)
commit=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==BASE and not git('status','--porcelain')
# Reproduce the entire tree through an independent index without touching this checkout.
index=PRIVATE/'patch-check-index-private';assert not index.exists()
env=dict(os.environ,GIT_INDEX_FILE=str(index))
subprocess.run(['git','-C',str(TREE),'read-tree',BASE],env=env,check=True)
subprocess.run(['git','-C',str(TREE),'apply','--cached',str(ROOT/'vfe175-cst-candidate.patch')],env=env,check=True)
rebuilt=subprocess.check_output(['git','-C',str(TREE),'write-tree'],env=env,text=True).strip()
assert rebuilt==git('rev-parse','HEAD^{tree}')
old=subprocess.check_output(['git','-C',str(TREE),'show',BASE+':'+prefix+'camss-vfe-175-pixel.c'],text=True)
new=(TREE/prefix/'camss-vfe-175-pixel.c').read_text()
preserved={}
for name in ['vfe_175_wb_q7','vfe_175_wb_write','vfe_175_wb_validate','vfe_175_params_unsupported','vfe_175_params_apply']:
    def extract(text):
        m=re.search(r'(?:static )?(?:void|int|u32) '+name+r'\(',text);assert m
        return text[m.start():text.index('\n}',m.start())+2]
    assert extract(old)==extract(new)
    preserved[name]=hashlib.sha256(extract(new).encode()).hexdigest()
dem=prefix+'camss-vfe-175-demosaic.c'
assert subprocess.check_output(['git','-C',str(TREE),'show',BASE+':'+dem])==(TREE/dem).read_bytes()
report=dict(stage=285,commit=commit,parent=BASE,branch='samurai-vfe175-cst285',
            source_sha256={n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in files},
            patch_sha256=hashlib.sha256(patch).hexdigest(),independent_index_tree_matches=True,
            wb_functions_identical=preserved,demosaic_source_identical=True,
            checkpatch_exit=check.returncode,checkpatch_summary=[l for l in check.stdout.splitlines() if l.startswith('total:')],
            not_pushed=True,not_deployed=True)
(ROOT/'cst-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
