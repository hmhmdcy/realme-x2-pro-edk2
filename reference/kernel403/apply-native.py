"""Commit only the validated common/LTM partition primitive in maintained C."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'native-partitions-validation.json').read_text())['passed']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip();parent='195f81dd30ca8865d440bafa32c7397006a436ef';assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
names=['camss-icp-a5-ipe.c','camss-icp-a5-ipe.h']
for name in names:assert (source/relative/name).read_bytes()==(P/(name+'.before')).read_bytes()
git('switch','-c','samurai-ipe-ltm-partitions403')
for name in names:(source/relative/name).write_bytes((P/(name+'.proposed')).read_bytes())
git('diff','--check');git('add','--',*[str(relative/name) for name in names]);git('commit','-m','media: camss: add checked LTM partition ranges with shared bypass checks','--',*[str(relative/name) for name in names])
state=dict(stage=403,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=[str(relative/name) for name in names],clean=not git('status','--porcelain'),installed=False,source_unchanged_from402=False,ltm_partition_primitive_added=True,ltm_runtime_submission_enabled=False,gamma_opcode1_retained=True,phone_accessed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
