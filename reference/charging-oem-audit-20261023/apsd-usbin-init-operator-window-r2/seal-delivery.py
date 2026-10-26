from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-usbin-init-candidate'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((HERE/'test-result.json').read_text());b=json.loads((HERE/'build-result.json').read_text())
assert t['passed'] and t['group_count']==5 and not t['old_12_rerun']
assert b['passed'] and not b['diagnostic_lines'] and b['shared_config_unchanged'] and b['shared_makefile_unchanged']
for n,h in t['files'].items():assert sha(HERE/n)==h,n
for n,h in b['files'].items():assert sha(HERE/n)==h,n
assert (HERE/'samurai-usbin-init.c').read_bytes()==(OLD/'samurai-usbin-init.c').read_bytes()
assert (HERE/'usbin-init-core.h').read_bytes()==(OLD/'usbin-init-core.h').read_bytes().replace(b'#define UI_WAIT_MS 60000ULL',b'#define UI_WAIT_MS 300000ULL')
protocol=json.loads((HERE/'protocol.json').read_text());oldp=json.loads((OLD/'protocol.json').read_text());oldp['times']['window_ms']=300000;assert protocol==oldp
module=Path(b['module']);assert sha(module)==b['module_sha256']
export=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/apsd-usbin-init-operator-window-r2/samurai-usbin-init.ko')
export.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(module,export);assert sha(export)==sha(module)
names=['README.md','samurai-usbin-init.c','usbin-init-core.h','operator-window.patch','protocol.json','prepare.py','source-result.json',
 'prepare-tests.py','tested-functions.inc','tested-struct.inc','function-manifest.json','test-boundary-prefix.inc','test-boundary.c','run-tests.py',
 'actual-state-fixtures.json','actual-state-fixtures.jsonl','test-result.json','build-private.py','build-result.json','seal-delivery.py']
r=dict(passed=True,status='frozen operator-window R2 offline candidate',window_ms=300000,
 only_production_change='UI_WAIT_MS 60000ULL -> 300000ULL',files={n:sha(HERE/n) for n in names},
 module_path=str(module),module_export_path=str(export),module_sha256=sha(module),
 old_delivery_sha256=sha(OLD/'delivery.json'),old_test_receipt_sha256=sha(OLD/'test-result.json'),old_12_groups_rerun=False,
 new_boundary_groups=5,actual_module_functions=12,actual_core_functions=7,actual_state_fixtures=True,
 kernel='7.3.0-rc6-rmx1931-samurai-k363+',warnings=[],controller_included=False,
 phone_accessed=False,ssh_executed=False,usb_accessed=False,sdk_invoked=False,Git_invoked=False,
 shared_source_modified=False,shared_build_modified=False,Image_built=False,installed=False,physical_validation=False)
(HERE/'delivery.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),module_sha256=sha(module),
 protocol_sha256=sha(HERE/'protocol.json'),core_sha256=sha(HERE/'usbin-init-core.h'),
 fixtures_sha256=sha(HERE/'actual-state-fixtures.json'),test_sha256=sha(HERE/'test-result.json'),build_sha256=sha(HERE/'build-result.json'),
 module_export_path=str(export)),indent=2))
