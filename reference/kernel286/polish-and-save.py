"""Explain the barriers, retest and save the final combined candidate patch."""
from pathlib import Path
import hashlib,json,os,subprocess,sys

ROOT=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel286')
TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
PREFIX='drivers/media/platform/qcom/camss/'
FIRST='f2626cc3c7a94439e9db504478e59bcdab5fe7b5'
BASE='d1a5f84405cfa774765e9b8ffabd6d1533dec2b6'
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')==FIRST and not git('status','--porcelain')
old=json.loads((ROOT/'depth-gamma-commit-validation.json').read_text())
(PRIVATE/'initial-commit-validation-private.json').write_text(json.dumps(old,indent=2)+'\n')
(PRIVATE/'initial-checkpatch-private.txt').write_bytes((PRIVATE/'depth-gamma-checkpatch-private.txt').read_bytes())
(PRIVATE/'initial-host-tests-validation-private.json').write_bytes((ROOT/'depth-gamma-host-tests-validation.json').read_bytes())
changes={
    'camss-vfe-175-gamma.c':[
        ('\t\twmb();\n\t\twritel_relaxed(lut_cfg', '\t\t/* Complete all LUT writes before changing the bank selection. */\n\t\twmb();\n\t\twritel_relaxed(lut_cfg'),
        ('\twmb();\n\tvalue = readl_relaxed', '\t/* Publish the bank/configuration before enabling Gamma; no PIX RUP. */\n\twmb();\n\tvalue = readl_relaxed')],
    'camss-vfe-175-round.c':[
        ('\twmb();\n\tenabled =', '\t/* Make both output configurations visible before setting their enables. */\n\twmb();\n\tenabled =')]
}
for name,items in changes.items():
    for path in [TREE/PREFIX/name,ROOT/'source'/name]:
        s=path.read_text()
        for before,after in items:assert s.count(before)==1;s=s.replace(before,after)
        path.write_text(s)
subprocess.run([sys.executable,str(ROOT/'test-depth-gamma.py')],check=True)
files=[PREFIX+n for n in changes]
subprocess.run(['git','-C',str(TREE),'add','--',*files],check=True)
assert sorted(git('diff','--cached','--name-only').splitlines())==sorted(files)
subprocess.run(['git','-C',str(TREE),'-c','user.name=Samurai Builder','-c','user.email=samurai@localhost','commit','-m',
                'media: qcom: camss: explain VFE175 bank and output barriers'],check=True,capture_output=True)
commit=git('rev-parse','HEAD');assert git('rev-parse','HEAD^')==FIRST and not git('status','--porcelain')
patch=subprocess.check_output(['git','-C',str(TREE),'diff','--binary','--full-index',BASE,commit])
(ROOT/'vfe175-depth-gamma-candidate.patch').write_bytes(patch)
check=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(ROOT/'vfe175-depth-gamma-candidate.patch')],text=True,capture_output=True)
(PRIVATE/'depth-gamma-checkpatch-private.txt').write_text(check.stdout+check.stderr)
assert '0 errors, 1 warnings' in check.stdout,check.stdout
index=PRIVATE/'patch-check-index-final-private';assert not index.exists()
env=dict(os.environ,GIT_INDEX_FILE=str(index))
subprocess.run(['git','-C',str(TREE),'read-tree',BASE],env=env,check=True)
subprocess.run(['git','-C',str(TREE),'apply','--cached',str(ROOT/'vfe175-depth-gamma-candidate.patch')],env=env,check=True)
assert subprocess.check_output(['git','-C',str(TREE),'write-tree'],env=env,text=True).strip()==git('rev-parse','HEAD^{tree}')
for name in ['camss-vfe-175-cst.c','camss-vfe-175-demosaic.c']:
    assert subprocess.check_output(['git','-C',str(TREE),'show',BASE+':'+PREFIX+name])==(TREE/PREFIX/name).read_bytes()
old.update(commit=commit,parent=FIRST,patch_base=BASE,implementation_commit=FIRST,barrier_comments_followup=True,
           patch_sha256=hashlib.sha256(patch).hexdigest(),checkpatch_exit=check.returncode,
           checkpatch_summary=[l for l in check.stdout.splitlines() if l.startswith('total:')],
           source_sha256={n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in old['source_sha256']})
(ROOT/'depth-gamma-commit-validation.json').write_text(json.dumps(old,indent=2)+'\n')
print(json.dumps(old,indent=2))
