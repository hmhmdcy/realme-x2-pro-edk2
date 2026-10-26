"""Narrow read-only source and receipt binding. No runtime entry is imported."""
from pathlib import Path
import ast,hashlib,json
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
ADOPT=REF/'charging-session-20261023/gauge-image501-adoption-candidate'
ICON=REF/'charging-session-20261023/icon-capture-image501-candidate'
OLD=REF/'charging-oem-audit-20261023/icon-capture-r8-eud-off-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def fn(path):
    text=path.read_text()
    return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
def delivery(directory):
    record=json.loads((directory/'delivery.json').read_bytes())
    for name,pin in record['files'].items():assert sha(directory/name)==pin['sha256'],name
    return sha(directory/'delivery.json')
adopt_delivery=delivery(ADOPT);icon_delivery=delivery(ICON)
for name in ['worker.py','audit.py','baseline-test-result.json']:assert (ICON/name).read_bytes()==(OLD/name).read_bytes()
newguard=b'/var/lib/samurai/image501-gauge-live-001-adopted/boot-id-private.txt'
oldguard=b'/var/lib/samurai/eud-boot-r2-live-001-adopted/boot-id-private.txt'
assert (ICON/'capture-entry.py').read_bytes().replace(newguard,oldguard)==(OLD/'capture-entry.py').read_bytes()
a,b=fn(ICON/'launcher.py'),fn(OLD/'launcher.py')
unchanged=['ready_check','retain_fetch','cleanup_check','save_new']
assert all(a[n]==b[n] for n in unchanged)
def remote(path):
    tree=ast.parse(path.read_text())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='REMOTE' for t in n.targets))
assert remote(ICON/'launcher.py').replace('/icon-capture-image501','/icon-capture-r8-eud-off')==remote(OLD/'launcher.py')
tested=json.loads((ICON/'template-test-result.json').read_bytes())
assert tested['passed'] and tested['launcher_sha256']==sha(ICON/'launcher.py')
for name,digest in tested['files'].items():assert sha(ICON/name)==digest
adopt_test=json.loads((ADOPT/'test-result.json').read_bytes());assert adopt_test['passed']
for name,digest in adopt_test['files'].items():assert sha(ADOPT/name)==digest
source_pins=json.loads((ADOPT/'source-pins.json').read_bytes())
for name,pin in source_pins.items():
    path=Path('E:/'+pin['path'][len('/mnt/e/'):])
    assert sha(path)==pin['sha256']
adopt_text=(ADOPT/'adopt.py').read_text()
host=b"if sys.flags.optimize:raise RuntimeError('optimized Python disables adoption checks')\n"
remote=b'''b'import sys\\nif sys.flags.optimize:raise RuntimeError("optimized Python disables adoption checks")\\n'+'''
actual=(ADOPT/'adopt.py').read_bytes();original=(ADOPT/'before-optimize-gate/adopt.py').read_bytes()
assert hashlib.sha256(original).hexdigest()=='cce2f18ac0aaa1fb8d4e51bf6ddbb431448886a1358218fc78fcb305681a897d'
assert actual.count(host)==actual.count(remote)==1 and actual.replace(host,b'').replace(remote,b'')==original
optimize=json.loads((ADOPT/'test-optimize-result.json').read_bytes())
assert optimize['passed'] and [r['returncode'] for r in optimize['cases']]==[0,1,1]
for name,digest in optimize['files'].items():assert sha(ADOPT/name)==digest
optimization_gate=True
r={'scope':'static new adoption and collector identity/profile changes only; source hashes and existing actual-function receipts',
   'adoption_delivery_sha256':adopt_delivery,'adopt_sha256':sha(ADOPT/'adopt.py'),'adoption_original_three_groups_byte_exact_reused_not_rerun':True,
   'adoption_host_and_remote_nonassert_optimization_rejection_present':optimization_gate,'new_optimization_cases_bound':3,'adoption_review_issue':None,
   'icon_delivery_sha256':icon_delivery,'icon_launcher_sha256':sha(ICON/'launcher.py'),'icon_template_two_groups_bound':True,
   'generic_worker_audit_and_old_receipt_byte_equal':True,'capture_entry_only_guard_literal_changed':True,
   'ready_and_fetch_functions_byte_equal':unchanged,'remote_lifecycle_only_output_base_changed':True,
   'old_readiness_130_seconds_3second_freshness_exact_PID_and_advancing_ticks_preserved':True,
   '300second_deadline_90second_stable_settle_preserved':True,
   'collector_Runtime_pins_require_real_adopted501_full_pair_flagY_AVG_500_evidence':True,
   'source_or_hardware_IO_added':False,'tests_rerun':False,'device_network_SDK_Git_used':False,
   'new_blocker_remaining':False,'runtime_adoption_or_capture_accepted':False}
(HERE/'review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'review_sha256':sha(HERE/'review.json'),'adopt_sha256':r['adopt_sha256'],'icon_launcher_sha256':r['icon_launcher_sha256'],'optimization_gate_present':optimization_gate}))
