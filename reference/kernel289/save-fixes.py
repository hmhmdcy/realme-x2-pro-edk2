"""Check and save the independent transport and Gamma clock fixes as local commits."""
from pathlib import Path
import hashlib,json,subprocess
import host

ROOT=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git=lambda *a:subprocess.check_output(['git','-C',str(TREE),*a],text=True).strip()
assert git('rev-parse','HEAD')=='8c79b7e1912790d3e18a84c9c6621a6d92baa768'
assert set(git('diff','--name-only').splitlines())=={'drivers/media/platform/qcom/camss/camss-csid-gen2.c','drivers/media/platform/qcom/camss/camss-vfe-175-gamma.c'}
p=TREE/'drivers/media/platform/qcom/camss/camss-csid-gen2.c';s=p.read_text();s=s.replace('\tu32 val;\n\n\n\t/* configure one DT','\tu32 val;\n\n\t/* configure one DT');p.write_text(s)
subprocess.run(['python3',str(ROOT/'test-tpg-isolation.py')],check=True,capture_output=True)
rows=[]
for filename,stem,subject,body in [
 ('camss-csid-gen2.c','csid-gen2-tpg-isolation','media: qcom: camss: isolate gen2 internal TPG from PHY history',
  'The internal test generator emits four D-PHY lanes. Do not retain the lane encoding or C-PHY mode from the last physical sensor link when configuring the internal source. Keep the stored external PHY configuration intact.'),
 ('camss-vfe-175-gamma.c','vfe175-gamma-clock','media: qcom: camss: clock VFE175 Gamma RAM during DMI uploads',
  'Gamma SRAM access requires its module clock even before pixel traffic starts. Hold the Gamma clock override while uploading the inactive tables and publishing their banks, then restore the original clock policy. Preserve unrelated clock bits and the shared DMI state.')]:
 path='drivers/media/platform/qcom/camss/'+filename
 patch=ROOT/(stem+'-candidate.patch');patch.write_bytes(subprocess.check_output(['git','-C',str(TREE),'diff','--',path]))
 q=subprocess.run(['perl',str(TREE/'scripts/checkpatch.pl'),'--no-tree',str(patch)],capture_output=True,text=True)
 (host.PRIVATE/(stem+'-checkpatch-private.txt')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stdout+q.stderr
 message=host.PRIVATE/(stem+'-commit-message-private.txt');message.write_text(subject+'\n\n'+body+'\n')
 subprocess.run(['git','-C',str(TREE),'add','--',path],check=True)
 subprocess.run(['git','-C',str(TREE),'commit','-F',str(message)],check=True,capture_output=True)
 rows.append(dict(subject=subject,commit=git('rev-parse','HEAD'),patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),checkpatch_exit=0))
assert not git('status','--porcelain')
combined=subprocess.check_output(['git','-C',str(TREE),'diff','8c79b7e1912790d3e18a84c9c6621a6d92baa768','HEAD'])
(ROOT/'tpg-gamma-fixes-candidate.patch').write_bytes(combined)
report=dict(stage=289,branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),commits=rows,
 source_clean=True,pushed=False,not_deployed=True,upstream_acceptance_not_claimed=True)
(ROOT/'fixes-commit-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
