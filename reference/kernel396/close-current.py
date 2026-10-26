"""Verify the offline candidate and the still-installed395 runtime separately."""
from pathlib import Path
import importlib.util,json,shlex,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
for n in ['colour-validation.json','colour-arm64-validation.json','enable-abi-validation.json','routing-validation.json','intree-build-validation.json']:assert json.loads((HERE/n).read_text())['passed']
spec=importlib.util.spec_from_file_location('storage284',HERE.parent/'kernel284/storage.py');storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage)
source=storage.mounted_build().parent/'source354';expected=json.loads((HERE/'source-state.json').read_text());git=lambda *a:subprocess.check_output(['git','-C',str(source),*a],text=True).strip()
assert git('rev-parse','HEAD')==expected['commit'] and not git('status','--porcelain')
assert set(git('diff-tree','--no-commit-id','--name-only','-r','HEAD').splitlines())==set(expected['changed'])
build=json.loads((HERE/'intree-build-validation.json').read_text());candidate=build['modules'][0]['private_path']
symbols=subprocess.check_output(['aarch64-linux-gnu-nm',candidate],text=True)
assert any(l.endswith(' camss_a5_ipe_cc_encode') for l in symbols.splitlines())
assert not subprocess.check_output(['modinfo','-F','parm',candidate],text=True).strip()
meta=json.loads((P.parent/'kernel395/manifest-private.json').read_text())
code=r'''from pathlib import Path
import hashlib,json
meta=META;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k394-recovered/boot-id-private.txt').read_bytes()
assert sha(meta['core_target'])==meta['new_core_sha256'] and sha('/sys/module/qcom_camss_icp_a5_core/notes/.note.gnu.build-id')==meta['new_core_note_sha256']
assert all(sha(n)==h for n,h in meta['other_files'].items())
for n,h in meta['unchanged_notes'].items():assert sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h
assert not Path('/sys/module/qcom_camss_icp_a5_core/parameters/test_drop_frame_ack').exists()
dev=Path('/sys/bus/platform/devices/ac10000.icp');s=json.loads((dev/'m2m_status').read_text());c=json.loads((dev/'state').read_text())
assert not any(s[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
assert not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','watchdogs','protocol_errors'])
pm={n:Path('/sys/bus/platform/devices',n,'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']};assert all(v=='suspended' for v in pm.values())
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
print(json.dumps(dict(same_guard394=True,normal395_disk_and_loaded_note_match=True,adapter393_camss389_notes_match=True,test_knobs_absent=True,m2m=s,core=c,camera_pm=pm,taint=0)))
'''.replace('META',repr(meta))
q=host.ssh('python3 -c '+shlex.quote(code),timeout=25);d=json.loads(q.stdout);(P/'current-device-private.json').write_bytes(q.stdout)
assert d['m2m']['jobs']==d['m2m']['completed']==d['m2m']['direct_completed']==48
report=dict(stage=396,source_commit=expected['commit'],source_clean=True,codec_present_in_built_core=True,only_three_candidate_source_files_changed=True,existing_runtime_abi_and_callers_unchanged=True,candidate_core_installed=False,installed_core_stage=395,installed_adapter_stage=393,userspace_deployment_stage=391,no_phone_state_transition_or_capture_this_stage=True,remaining_full_iq_and_optical_scope=True,**d,passed=True)
(HERE/'current-state-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ['m2m','core','camera_pm']},indent=2))
