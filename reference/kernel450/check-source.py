from pathlib import Path
import hashlib,json,re,subprocess,tempfile
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
volume=storage.mount.mounted_build().parent;tree=storage.candidate()/'src/libcamera-v0.7.2'
baseline=json.loads((HERE.parent/'kernel448/source-state.json').read_text())
state=json.loads((HERE/'source-state.json').read_text());changed=state['changed_this_stage'];assert changed==['src/libcamera/pipeline/camss-vfe/camss_vfe.cpp']
for row in baseline['source_hashes']:
 if row['path'] not in changed:assert hashlib.sha256((tree/row['path']).read_bytes()).hexdigest()==row['sha256']
with tempfile.TemporaryDirectory(prefix='patch-replay-',dir=P) as work:
 root=Path(work);p=root/changed[0];p.parent.mkdir(parents=True);p.write_bytes((volume/'libcamera448-capacity-lease/src/libcamera-v0.7.2'/changed[0]).read_bytes())
 q=subprocess.run(['patch','-p1','--batch','--fuzz=0','-i',str(HERE/'0061-camss-retire-statistics-before-proxy-call.patch')],cwd=root,capture_output=True)
 (P/'patch-replay.log').write_bytes(q.stdout+q.stderr);assert not q.returncode and not re.search(rb'offset|fuzz',q.stdout+q.stderr,re.I)
 assert p.read_bytes()==(tree/changed[0]).read_bytes()
assert json.loads((HERE/'retirement-validation.json').read_text())['passed']
r=dict(stage=450,only_pipeline_statistics_retirement_changed=True,ipa6_factory_algorithms_focus_and_capacity_helper_unchanged=True,patch_zero_fuzz_offset_and_source_equal=True,baseline_bug_reproduced_and_fixed_reentry_cases_passed=True,phone_accessed=False,passed=True)
(HERE/'source-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
