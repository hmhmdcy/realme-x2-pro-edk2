"""Check generated handoff/prefix/load order before the distinct r2 window."""
from pathlib import Path
import ast,hashlib,importlib.util,json,runpy,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;PRIVATE=Path('/mnt/e/edk2-samurai-out/kernel468')
spec=importlib.util.spec_from_file_location('storage468',HERE.parent/'kernel461/storage.py')
storage=importlib.util.module_from_spec(spec);spec.loader.exec_module(storage);storage.mount.mounted_build()
work=PRIVATE/'prepared-r2';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=json.loads((work/'payload-files-private.json').read_bytes());manifest=json.loads((work/'manifest.json').read_bytes())
assert all(sha(Path(files[name]))==digest for name,digest in manifest.items())
plan=json.loads((work/'tele-plan-private.json').read_bytes());handoff=json.loads(Path(files['handoff-private.json']).read_bytes())
common=runpy.run_path(str(work/'capture-common-private.py'))
assert plan['window_id']==handoff['window_id']=='k468-tele-mode2-r2'
assert plan['window_id'].startswith(common['PREFIX']) and common['PREFIX']=='k468-tele-mode2-'
assert not plan['window_id'].startswith('k467-tele-')
worker=(work/'worker.py').read_text();tree=ast.parse(worker)
assert len([n for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Store) and n.id=='tele'])==1
assert "tele_formal=baseline['tele_sensor']" in worker
assert worker.index("for n in names:run(['rmmod',n]")<worker.index("run(['rmmod','s5k3m5']")<worker.index("run(['insmod',str(root/proof['sensor']['file'])]")
assert worker.index("run(['modprobe','s5k3m5']")<worker.index("run(['modprobe','qcom_camss']")
assert "state['sensor_module_restored']=True" in worker and "assert state.get('sensor_module_restored')" in worker
assert 'os.killpg' not in worker and 'start_uptime=time.monotonic()' in worker
assert plan['sensor_mode']==2 and plan['actual_sensor']==[4208,2368] and plan['candidate_sensor_module']
failed=json.loads((PRIVATE/'runtime-collected-r1/state.json').read_bytes())
assert failed['terminal'] and not failed['passed'] and 'root.name.startswith(PREFIX)' in failed['failure']
assert 'before_notes' not in failed and not failed.get('captures')
assert failed['taint_after']==0 and not failed['new_faults']
for path in files.values():
    if Path(path).suffix=='.py':ast.parse(Path(path).read_text())
report=dict(stage=468,passed=True,generated_r2_prefix_matches_handoff_and_plan=True,original_prefix_rejected=True,
    module_replacement_after_notifier_removal=True,sensor_restoration_before_camss=True,no_module_dictionary_shadowing=True,
    r1_failure_before_module_or_client_actions=True,r1_terminal_preserved=True,r2_distinct_transaction=True,
    worker_sha256=sha(work/'worker.py'),payload_files=len(files),ast_checked=True,phone_accessed=False)
(HERE/'runtime-tool-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
