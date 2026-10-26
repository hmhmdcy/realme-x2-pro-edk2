"""Save the tested driver revision and precise module identity."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;TREE=Path('/home/cy122/x2pro-linux/camera318-lsc-kernel')
BASE='afad7bde625bbf7bf58c145bde1f977b806da986'
def git(*args):return subprocess.check_output(['git','-C',str(TREE),*args],text=True).strip()
subprocess.run(['git','-C',str(TREE),'diff','--check'],check=True)
names=git('diff','--name-only',BASE).splitlines()
assert set(names)=={('include/uapi/linux/' if p.name=='qcom-camss-config.h' else 'drivers/media/platform/qcom/camss/')+p.name for p in (HERE/'kernel').iterdir() if p.is_file()}
if git('rev-parse','HEAD')==BASE:
 subprocess.run(['git','-C',str(TREE),'add','--',*names],check=True)
 subprocess.run(['git','-C',str(TREE),'commit','-m','media: camss: add optional VFE175 lens shading mesh parameters'],check=True)
(HERE/'lsc-driver.patch').write_text(git('diff',BASE,'HEAD')+'\n')
assert not git('status','--short')
module=Path(json.loads((HERE/'kernel-build-validation.json').read_text())['module'])
proof=json.loads((host.PRIVATE/'install-proof.json').read_text())
report=dict(stage=318,tree=str(TREE),branch=git('branch','--show-current'),base_commit=BASE,head=git('rev-parse','HEAD'),
 changed_sources={n:hashlib.sha256((TREE/n).read_bytes()).hexdigest() for n in names},
 source_patch='lsc-driver.patch',module=str(module),module_sha256=proof['module_sha256'],module_note_sha256=proof['module_note_sha256'],
 system_module_installed=json.loads((HERE/'install-r1-validation.json').read_text())['passed'],
 dt_sensor_sources_changed=False,v4l2_core_changed=False,userspace_packages_changed=False,
 scope='Optional VFE175 regular mesh LSC on the existing metadata queue. Calibration policy and resampling remain in userspace. LSC starts disabled.')
(HERE/'source-state.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['head','module_sha256','system_module_installed']},indent=2))
