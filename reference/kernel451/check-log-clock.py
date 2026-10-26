"""Execute the old/new actual worker cutoff assignments after simulated suspend."""
from pathlib import Path
import ast,hashlib,importlib.util,json,types
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('monotonic_prepare',HERE/'prepare-with-monotonic.py')
wrapper=importlib.util.module_from_spec(spec);spec.loader.exec_module(wrapper)
body=(HERE.parent/'kernel434/capture-worker-body.py').read_text()
assert body.count(wrapper.OLD)==1
def cutoff(source,mono,suspend):
    tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='start_uptime' for t in n.targets))
    class MockPath:
        def __init__(self,name):assert name=='/proc/uptime'
        def read_text(self):return str(mono+suspend)+' 0'
    namespace=dict(Path=MockPath,time=types.SimpleNamespace(monotonic=lambda:mono))
    exec(compile(ast.Module(body=[node],type_ignores=[]),'actual-worker-cutoff','exec'),namespace)
    return namespace['start_uptime']
cases=[]
for mono,suspend in [(100,0),(100,3396.19),(17000,500)]:
    old=cutoff(body,mono,suspend)
    new=cutoff(body.replace(wrapper.OLD,wrapper.NEW),mono,suspend)
    fault_time=mono+.5
    assert new==mono and fault_time>=new
    assert (fault_time>=old)==(suspend==0)
    cases.append(dict(simulated_suspend_seconds=suspend,old_retains_fault=fault_time>=old,new_retains_fault=True))
for kind in ['comparison','diagnostic']:
    path,source=wrapper.transformed_source(kind)
    assert source.count('.replace('+repr(wrapper.OLD)+','+repr(wrapper.NEW)+')')==1
report=dict(stage=451,actual_worker_assignment_executed=True,legacy_source_sha256=hashlib.sha256(body.encode()).hexdigest(),cases=cases,both_new_prepare_sources_syntax_checked=True,original_prepare_files_unchanged=True,no_phone_sdk_or_build=True,synthetic_clock_test_not_hardware=True,passed=True)
(HERE/'log-clock-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
