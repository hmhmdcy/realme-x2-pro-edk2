"""Verify the small maintained patch, ABI, build cohort and restored outputs."""
from pathlib import Path
import hashlib,importlib.util,json,re,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
s=importlib.util.spec_from_file_location('storage430source',HERE.parent/'kernel284/storage.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b=m.mounted_build();k=b.parent/'source354';d=k/'drivers/media/platform/qcom/camss';state=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(k),*a])
assert git('rev-parse','HEAD').decode().strip()==state['commit'] and not git('status','--porcelain')
patch=(HERE/'dc-topology.patch').read_bytes();assert git('diff',state['parent_commit'],state['commit'])==patch
replay=P/'patch-replay';replay.mkdir(exist_ok=True)
for row in state['source_hashes']:
 assert hashlib.sha256((k/row['path']).read_bytes()).hexdigest()==row['sha256']
 p=replay/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(git('show',state['parent_commit']+':'+row['path']))
q=subprocess.run(['patch','--batch','--fuzz=0','-p1','-i',str(HERE/'dc-topology.patch')],cwd=replay,capture_output=True)
assert not q.returncode and b'offset' not in q.stdout and b'fuzz' not in q.stdout
for row in state['source_hashes']:assert (replay/row['path']).read_bytes()==(k/row['path']).read_bytes()
build=json.loads((HERE/'intree-build-validation.json').read_text());assert build['passed'] and build['attempt']==1 and not build['diagnostics'] and len(build['modules'])==10
assert json.loads((P/'intree-build-state.json').read_text())['terminal']
for row in build['modules']:assert hashlib.sha256(Path(row['private_path']).read_bytes()).hexdigest()==row['sha256']
for name in ['qcom-camss.ko','qcom-camss-icp-a5-core.ko','camss-icp-a5-m2m.ko','camss-icp-a5-ipe.o','camss-icp-a5-boot.o']:
 rel=Path('drivers/media/platform/qcom/camss')/name;before=P/'intree-build-r1-before'/rel;after=b/rel
 assert before.exists()==after.exists()
 if before.exists():assert before.read_bytes()==after.read_bytes()
for rel in ['include/uapi/linux/qcom-ipe-a5.h','include/uapi/linux/qcom-camss-config.h','drivers/media/platform/qcom/camss/camss-icp-a5-ipe.h','drivers/media/platform/qcom/camss/camss-icp-a5-m2m.c']:
 assert git('show',state['parent_commit']+':'+rel)==(k/rel).read_bytes()
assert 'readl(a5->resources.ipe[' not in (d/'camss-icp-a5-boot.c').read_text()
r=dict(stage=430,commit=state['commit'],source_clean=True,source_hashes_match=True,patch_sha256=hashlib.sha256(patch).hexdigest(),patch_replays_without_fuzz_or_offset=True,
 matched_candidate_cohort_hashes=True,build_terminal=True,shared_selected_build_outputs_restored=True,
 user_abi_job_layout_m2m_ownership_and_capture_driver_unchanged=True,unsafe_mmio_diagnostic_absent=True,installed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
