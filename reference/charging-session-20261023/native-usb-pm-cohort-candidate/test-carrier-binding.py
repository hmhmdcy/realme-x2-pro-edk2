"""Only new carrier-binding cases; reuse ten unchanged package cases."""
from pathlib import Path
import ast,copy,difflib,importlib.util,json,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cohort',HERE/'cohort.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
before=Path('E:/edk2-samurai-out/charging-management-20261023/before-carrier-binding-cohort-private.py').read_text()
assert c.sha(before.encode())=='1938cb4bb3bdea285188b3220305426912cf0057cd914615c0df294c0810d41a'
after=(HERE/'cohort.py').read_text()
def functions(source):return {node.name:ast.get_source_segment(source,node) for node in ast.parse(source).body if isinstance(node,ast.FunctionDef)}
old,new=functions(before),functions(after)
reused=['need','encode','make_manifest','check_manifest_delta','archive','check_archive']
assert all(old[n]==new[n] for n in reused)
prior=json.loads((HERE/'test-result.json').read_bytes());assert prior['passed'] and prior['actual_package_boundary_cases']==10 and prior['cohort_source_sha256']==c.sha(before.encode())
carrier=json.loads((HERE/'carrier-input.json').read_bytes());receipt=json.loads(c.pinned(carrier['receipt']).read_bytes())
image={'sha256':carrier['Image504_sha256'],'bytes':59243008};cases=[]
def reject(record,desc):
    try:c.validate_carrier(record,carrier,image)
    except ValueError:cases.append(desc);return
    raise AssertionError('expected binding rejection: '+desc)
c.validate_carrier(receipt,carrier,image);cases.append('actual new504 completed carrier accepted')
old_receipt=json.loads((HERE.parent/'gauge-image502-logdump-candidate/logdump-result.json').read_bytes())
old_receipt['candidate']={k:carrier['logdump'][k] for k in ['sha256','bytes']}
reject(old_receipt,'passing old502 receipt cannot be relabelled Image504')
bad=copy.deepcopy(receipt);bad['rollback_logdump_sha256']='0'*64
reject(bad,'wrong actual saved base rejected')
bad=copy.deepcopy(receipt);bad['Image_readback_exact']=False
reject(bad,'incomplete actual readback rejected')
report=dict(passed=True,cohort_source_sha256=c.file_sha(HERE/'cohort.py'),
    original_package_test_result_sha256=c.file_sha(HERE/'test-result.json'),reused_package_cases=10,
    original_tested_source_sha256=c.sha(before.encode()),reused_functions_exact=reused,
    new_actual_binding_cases=len(cases),binding_cases=cases,binding_source_sha256=c.sha(new['validate_carrier'].encode()),
    actual_carrier_receipt_sha256=carrier['receipt']['sha256'],old_tests_or_builds_repeated=False,
    device_accessed=False,hardware_or_boot_accepted=False)
with (HERE/'package-verification.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
with (HERE/'carrier-binding-delta.patch').open('x') as f:f.write(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='tested1938/cohort.py',tofile='bound504/cohort.py')))
print(json.dumps(report,indent=2))
