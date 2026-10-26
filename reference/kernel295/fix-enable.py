"""Correct the SoC BHIST enable bit, preserving the first failing implementation."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel295');TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='456e46ca43142e7123a3bd353e559a5cb6bf768d' and not git('status','--porcelain')
negative=json.loads((ROOT/'parent-enable-validation.json').read_text());assert negative['expected_failure_observed']
for name in ['stats-tests-private.c','stats-tests-private.log']:
 shutil.copyfile(P/name,P/('parent-'+name))
subprocess.run(['git','-C',str(TREE),'switch','-c','samurai-stats295'],check=True)
p=TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-stats.c';s=p.read_text()
old='#define VFE_175_BHIST_ENABLE             BIT(5)';assert s.count(old)==1
p.write_text(s.replace(old,'#define VFE_175_BHIST_ENABLE             BIT(4)'))
patch=subprocess.check_output(['git','-C',str(TREE),'diff']);(ROOT/'bhist-enable-candidate.patch').write_bytes(patch)
q=subprocess.run([str(TREE/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True)
(P/'enable-checkpatch-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stdout.decode()
subprocess.run(['git','-C',str(TREE),'add','drivers/media/platform/qcom/camss/camss-vfe-175-stats.c'],check=True)
subprocess.run(['git','-C',str(TREE),'commit','-m','media: qcom: camss: select the BHIST statistics enable bit'],check=True)
assert not git('status','--porcelain');commit=git('rev-parse','HEAD')
(ROOT/'source-validation.json').write_text(json.dumps(dict(stage=295,branch='samurai-stats295',commit=commit,parent='456e46ca43142e7123a3bd353e559a5cb6bf768d',source_clean=True,checkpatch_errors=0,checkpatch_warnings=0,not_deployed=True,pushed=False,scope='SoC VFE175 BHIST bit4; bit5 is RS; no board/DT/UAPI/firmware/user package changes',independent_protocol_proof='../kernel294/enable-correction-validation.json',parent_negative_control='parent-enable-validation.json'),indent=2)+'\n')
(ROOT/'test-metadata-restart.py').write_text((ROOT.parent/'kernel294/test-metadata-restart.py').read_text().replace('stage=294','stage=295'))
print(json.dumps(dict(commit=commit,clean=True,not_deployed=True)))
