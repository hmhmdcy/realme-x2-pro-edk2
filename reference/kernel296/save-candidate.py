"""Save the tested SoC SRAM initialization change without deploying it."""
from pathlib import Path
import json,subprocess
ROOT=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel296');TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
assert json.loads((ROOT/'parent-init-validation.json').read_text())['expected_failure_observed']
assert json.loads((ROOT/'stats-host-validation.json').read_text())['bhist_all_1024_sram_words_cleared']
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('branch','--show-current')=='samurai-stats296' and git('rev-parse','HEAD')=='d249946aefa1a01d99fd5484825a4458423b7348'
patch=subprocess.check_output(['git','-C',str(TREE),'diff']);assert patch
q=subprocess.run([str(TREE/'scripts/checkpatch.pl'),'--no-tree','--strict','-'],input=patch,capture_output=True)
(P/'candidate-checkpatch-private.log').write_bytes(q.stdout+q.stderr);assert q.returncode==0,q.stdout.decode()
subprocess.run(['git','-C',str(TREE),'add','drivers/media/platform/qcom/camss/camss-vfe-175-stats.c'],check=True)
subprocess.run(['git','-C',str(TREE),'commit','-m','media: qcom: camss: initialize VFE175 Bayer histogram SRAM'],check=True)
assert not git('status','--porcelain');commit=git('rev-parse','HEAD')
(ROOT/'source-validation.json').write_text(json.dumps(dict(stage=296,branch='samurai-stats296',commit=commit,parent='d249946aefa1a01d99fd5484825a4458423b7348',source_clean=True,checkpatch_errors=0,checkpatch_warnings=0,pushed=False,not_deployed=True,scope='Pre-stream SoC BHIST SRAM initialization; shared DMI and CGC state restored; no board, UAPI, firmware or product user-space change',host_evidence='stats-host-validation.json',parent_negative_control='parent-init-validation.json',protocol_sources='dmi-protocol-sources.json'),indent=2)+'\n')
(ROOT/'camss-vfe-175-stats.c').write_bytes((TREE/'drivers/media/platform/qcom/camss/camss-vfe-175-stats.c').read_bytes())
(ROOT/'bhist-init-candidate.patch').write_bytes(patch)
s=(ROOT.parent/'kernel295/test-metadata-restart.py').read_text().replace('stage=295','stage=296');(ROOT/'test-metadata-restart.py').write_text(s)
print(json.dumps(dict(commit=commit,clean=True,not_deployed=True)))
