"""Commit the validated shared bypass/LTM geometry encoder in maintained C."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['serializer','layouts','iq-geometry','model-source']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert json.loads((HERE/'serializer-validation.json').read_text())['native_source_sha256']==hashlib.sha256((P/'camss-icp-a5-ipe.c.proposed').read_bytes()).hexdigest()
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
parent='37040a4a11e5e3197268bdbc0c64f17e5337b592';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
names=['camss-icp-a5-ipe.c','camss-icp-a5-ipe.h']
for name in names:assert (source/relative/name).read_bytes()==(P/(name+'.before')).read_bytes()
git('switch','-c','samurai-ipe-ltm-geometry404')
for name in names:(source/relative/name).write_bytes((P/(name+'.proposed')).read_bytes())
git('diff','--check');git('add','--',*[str(relative/name) for name in names]);git('commit','-m','media: camss: encode checked full-frame LTM striping geometry','--',*[str(relative/name) for name in names])
state=dict(stage=404,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=[str(relative/name) for name in names],clean=not git('status','--porcelain'),installed=False,source_unchanged_from403=False,ltm_full_frame_geometry_encoder_added=True,shared_bypass_geometry_encoder=True,ltm_runtime_submission_enabled=False,gamma_opcode1_retained=True,phone_accessed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
(HERE/'ltm-geometry.patch').write_text(subprocess.check_output(['git','-C',str(source),'diff',parent,'HEAD','--',*[str(relative/name) for name in names]],text=True))
print(json.dumps(state,indent=2))
