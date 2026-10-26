"""Match tested C bodies to current source, without repeating unrelated tests."""
from pathlib import Path
import importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(s);s.loader.exec_module(storage);source=storage.mounted_build().parent/'source354';base=source/'drivers/media/platform/qcom/camss';state=json.loads((HERE/'source-state.json').read_text())
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==state['commit'] and not subprocess.check_output(['git','-C',str(source),'status','--porcelain'])
for relative in state['changed']:
 name=Path(relative).name;assert (source/relative).read_bytes()==(P/(name+'.proposed')).read_bytes()
assert (base/'camss-icp-a5-colour.c').read_bytes()==(P/'colour.c').read_bytes()
assert (base/'camss-icp-a5-colour.h').read_bytes()==(P/'include/camss-icp-a5-colour.h').read_bytes()
model=(P/'transfer-model.c').read_text();pattern=r'(?:static )?(?:bool|void|int|u32)\s+(\w+)\([^;]+?\n\{.*?^\}\n'
normalize=lambda text:re.sub(r'\s+','',text)
tested={m[1]:normalize(m[0]) for m in re.finditer(pattern,model,re.S|re.M)};counts={}
for name in ['camss-icp-a5-colour.c','camss-icp-a5-dma.c']:
 matches=list(re.finditer(pattern,(base/name).read_text(),re.S|re.M));assert matches
 for m in matches:assert tested.get(m[1])==normalize(m[0]),(name,m[1])
 counts[name]=len(matches)
boot=(base/'camss-icp-a5-boot.c').read_text();names=['nv12_layout_valid','camss_a5_backing_owned','free_imported_images','free_memory','free_transfer_memory','transfer_region_locked','transfer_alloc','transfer_released','run_colour_status','camss_a5_ipe_run_status','camss_a5_ipe_run_colour_status','camss_a5_ipe_run_colour_chain_status','camss_a5_ipe_run_gamma_status','camss_a5_ipe_run_ltm_status','camss_a5_ipe_run']
for name in names:
 m=next(m for m in re.finditer(pattern,boot,re.S|re.M) if m[1]==name);assert tested[name]==normalize(m[0]),name
counts['boot_request_and_cleanup_functions']=len(names)
old=(P/'camss-icp-a5-colour.c.before').read_text();new=(P/'camss-icp-a5-colour.c.proposed').read_text().split('static int ltm_unsigned_check(')[0].replace('#include <linux/kernel.h>\n','');assert old.strip()==new.strip()
report=dict(stage=405,source_clean=True,source_matches_proposal=True,codec_matches_host_arm_and_shared_models=True,transfer_model_native_functions_match_current_source=counts,old_colour_cc_gamma_function_bodies_unchanged=True,geometry_unchanged_from404=True,only_model_transport_and_allocation_providers_not_hardware=True,passed=True)
(HERE/'source-model-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
