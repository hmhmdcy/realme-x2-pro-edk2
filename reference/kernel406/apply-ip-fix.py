"""Commit the explicit full-frame IP bit before the second physical test."""
from pathlib import Path
import importlib.util,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
assert json.loads((HERE/'ip-enable-validation.json').read_text())['passed']
assert json.loads((HERE/'runtime-validation-r1.json').read_text())['state']['terminal']
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';relative=Path('drivers/media/platform/qcom/camss/camss-icp-a5-ipe.c');parent='3b65d2989ca8d71b658f8a859e8784be3e6bb965'
git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip();assert git('rev-parse','HEAD')==parent and not git('status','--porcelain')
assert (source/relative).read_bytes()==(P/'camss-icp-a5-ipe.c.before').read_bytes()
(HERE/'source-state-r1.json').write_bytes((HERE/'source-state.json').read_bytes());(HERE/'intree-build-validation-r1.json').write_bytes((HERE/'intree-build-validation.json').read_bytes())
for name in ['manifest-private.json','preflight-private.json','worker.py']:
 (P/(name.replace('-private.json','-r1-private.json') if '-private.json' in name else 'worker-r1.py')).write_bytes((P/name).read_bytes())
git('switch','-c','samurai-ipe-full-pass-ip406');(source/relative).write_bytes((P/'camss-icp-a5-ipe.c.proposed').read_bytes());git('diff','--check');git('add','--',str(relative));git('commit','-m','media: camss: honour explicit full-pass LTM image-processing enable','--',str(relative))
state=dict(stage=406,parent=parent,source=str(source),branch=git('branch','--show-current'),commit=git('rev-parse','HEAD'),changed=[str(relative)],clean=not git('status','--porcelain'),installed=False,source_unchanged_from405=False,temporary_adapter_source_restored=True,explicit_full_pass_ip_enable=True,original_hal_dc_coarse_policy_not_reused_for_explicit_ip=True,r1_failed_mask_pixels_retained=True,r2_pixels_pending=True,phone_changed_by_source_commit=False)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n');print(json.dumps(state,indent=2))
