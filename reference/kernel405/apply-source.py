"""Apply verified LTM IQ/LUT and ownership in the maintained core."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for name in ['parcel','transfer','firmware-parcel']:assert json.loads((HERE/(name+'-validation.json')).read_text())['passed']
assert len(json.loads((HERE/'firmware-parcel-validation.json').read_text())['cases'])==59
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';relative=Path('drivers/media/platform/qcom/camss')
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip();parent='5bd98599e9d920c46be03c416b13287336a05bc5'
assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
names=['camss-icp-a5-colour.c','camss-icp-a5-colour.h','camss-icp-a5-boot.c','camss-icp-a5-ipe.h']
for name in names:assert (source/relative/name).read_bytes()==(P/(name+'.before')).read_bytes()
git('switch','-c','samurai-ipe-ltm-ownership405')
for name in names:(source/relative/name).write_bytes((P/(name+'.proposed')).read_bytes())
git('diff','--check');git('add','--',*[str(relative/name) for name in names]);git('commit','-m','media: camss: retain typed LTM IQ and LUTs with the IPE request','--',*[str(relative/name) for name in names])
state=dict(stage=405,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=[str(relative/name) for name in names],clean=not git('status','--porcelain'),installed=False,ltm_typed_quantized_interface_added=True,ltm_same_request_iq_lut_ownership=True,ltm_internal_submission_api_added=True,ltm_hardware_verified=False,ltm_product_default_enabled=False,gamma_legacy_opcode1_and_layout_retained=True,source_unchanged_from404=False,phone_accessed=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
