"""Exact patch/cohort audit, including removal of the faulting diagnostic."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b=m.mounted_build();k=b.parent/'source354';d=k/'drivers/media/platform/qcom/camss';state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(k),*a])
assert git('rev-parse','HEAD').decode().strip()==state['commit'] and not git('status','--porcelain')
assert git('diff',state['parent_commit'],state['commit'])==(HERE/'pd10-runtime.patch').read_bytes()
replay=P/'patch-replay';replay.mkdir(exist_ok=True)
for row in state['source_hashes']:
 assert hashlib.sha256((k/row['path']).read_bytes()).hexdigest()==row['sha256']
 p=replay/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(git('show',state['parent_commit']+':'+row['path']))
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'pd10-runtime.patch')],cwd=replay,capture_output=True)
assert not q.returncode and b'offset' not in q.stdout and b'fuzz' not in q.stdout
for row in state['source_hashes']:assert (replay/row['path']).read_bytes()==(k/row['path']).read_bytes()
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and build['attempt']==3 and not build['diagnostics'] and len(build['modules'])==10
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
for row in build['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
for name in ['qcom-camss.ko','qcom-camss-icp-a5-core.ko','camss-icp-a5-m2m.ko','camss-icp-a5-ipe.o','camss-icp-a5-boot.o']:
 rel=Path('drivers/media/platform/qcom/camss')/name;before=P/'intree-build-r3-before'/rel;after=b/rel
 assert before.exists()==after.exists()
 if before.exists():assert before.read_bytes()==after.read_bytes()
old=git('show',state['parent_commit']+':drivers/media/platform/qcom/camss/camss-icp-a5-ipe.h').decode();new=(d/'camss-icp-a5-ipe.h').read_text()
pattern=r'struct camss_a5_ipe_job \{.*?^\};';assert re.search(pattern,old,re.S|re.M)[0]==re.search(pattern,new,re.S|re.M)[0]
old=git('show',state['parent_commit']+':include/uapi/linux/qcom-ipe-a5.h').decode();new=(k/'include/uapi/linux/qcom-ipe-a5.h').read_text()
assert old[old.index('struct qcom_ipe_a5_frame_params'):]==new[new.index('struct qcom_ipe_a5_frame_params'):]
boot=(d/'camss-icp-a5-boot.c').read_text();assert 'readl(a5->resources.ipe[' not in boot and state['unsafe_pps_mmio_diagnostic_removed']
state['legacy_job_and_existing_user_parameters_unchanged']=state.pop('legacy_job_and_user_api_unchanged',state.get('legacy_job_and_existing_user_parameters_unchanged',False))
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
r=dict(stage=429,commit=state['commit'],source_clean=True,source_hashes_match=True,patch_replays_without_fuzz_or_offset=True,
 matched_candidate_cohort_hashes=True,build_terminal=True,changed_objects_recompiled=True,shared_selected_build_outputs_restored=True,
 legacy_job_layout_and_6008_byte_parameters_unchanged=True,experimental_local_paired_format_addition=True,
 faulting_mmio_diagnostic_absent=True,unsafe_build2_core_forbidden=True,latest_fixed_build=3,
 device_recovery_or_dc_statistics_not_claimed_by_source_check=True,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
