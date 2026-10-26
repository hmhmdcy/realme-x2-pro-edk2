"""Exercise actual cancellation checks during slow reads on the host."""
from pathlib import Path
import ast,json,signal,time
import host
HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE/'conditions-observer.py').read_text())
nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in ['stop','read','read_fields']]
namespace={'running':True};exec(compile(ast.Module(body=nodes,type_ignores=[]),'actual-observer-functions','exec'),namespace)
calls=[]
class SlowValue:
 def read_text(self):calls.append(time.monotonic());time.sleep(.2);return '123\n'
paths=[('a',SlowValue()),('b',SlowValue())]
assert namespace['read_fields'](paths)=={'a':'123','b':'123'} and len(calls)==2
calls.clear();signal.signal(signal.SIGALRM,namespace['stop']);signal.setitimer(signal.ITIMER_REAL,.05)
start=time.monotonic();assert namespace['read_fields'](paths) is None;elapsed=time.monotonic()-start
signal.setitimer(signal.ITIMER_REAL,0);assert len(calls)==1 and elapsed<.8
calls.clear();assert namespace['read_fields'](paths) is None and not calls
stage=HERE/'stage-runtime.py';prefix=stage.read_text().split("source=(HERE.parent/'kernel441/stage-runtime.py')",1)[0]
exec(compile(prefix,str(stage),'exec'),{'__file__':str(stage)})
body=(HERE/'capture-body.py').read_text()
assert body.index('shutil.rmtree(userroot)')<body.index('if observer is not None:assert observer.returncode==0')
assert 'try:observer.wait(timeout=8)' in body and 'k449-user-' not in body
assert "dict(exit_code=observer.returncode,timed_out=observer_timeout)" in body
assert "[('user-sustained-1080',True,True)]" in body
assert "startswith('k450-user-')" in (HERE/'user-launcher.py').read_text()
r=dict(stage=450,actual_observer_read_fields_tested=True,normal_cancel_during_read_and_pre_cancel_cases=3,slow_read_cancel_stops_before_next_field=True,measured_cancel_seconds=round(elapsed,3),user_payload_cleanup_precedes_observer_exit_assertion=True,new_transaction_long_only_retains_r2_camera_cancellation=True,phone_accessed=False,passed=True)
(HERE/'observer-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
