"""Only the new host/payload optimize guards and original source delta."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
original=(HERE/'before-optimize-gate/adopt.py').read_bytes();actual=(HERE/'adopt.py').read_bytes()
assert sha(original)=='cce2f18ac0aaa1fb8d4e51bf6ddbb431448886a1358218fc78fcb305681a897d'
host=b"if sys.flags.optimize:raise RuntimeError('optimized Python disables adoption checks')\n"
remote=b'''b'import sys\\nif sys.flags.optimize:raise RuntimeError("optimized Python disables adoption checks")\\n'+'''
assert actual.count(host)==1 and actual.count(remote)==1
assert actual.replace(host,b'').replace(remote,b'')==original
spec=importlib.util.spec_from_file_location('adopt_opt_gate',HERE/'adopt.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
_,src=m.sources();payload=m.payload({},src);compile(payload,'actual-remote-adoption-payload','exec')
assert payload.startswith(b'import sys\nif sys.flags.optimize:raise RuntimeError(')
rows=[]
for label,argv,stdin in [('normal-default',[sys.executable,'-B',str(HERE/'adopt.py')],None),
                         ('optimized-host',[sys.executable,'-B','-O',str(HERE/'adopt.py')],None),
                         ('optimized-remote',[sys.executable,'-B','-O','-'],payload)]:
 r=subprocess.run(argv,input=stdin,capture_output=True,timeout=15)
 if label=='normal-default':assert r.returncode==0 and json.loads(r.stdout)['device_accessed'] is False
 else:assert r.returncode!=0 and b'RuntimeError: optimized Python disables adoption checks' in r.stderr
 rows.append({'label':label,'returncode':r.returncode,'refused_explicitly':label!='normal-default'})
result={'passed':True,'cases':rows,'only_two_explicit_guards_added':True,'old_three_groups_reused_not_rerun':True,
 'files':{n:sha((HERE/n).read_bytes()) for n in ['adopt.py','test-optimize.py','source-pins.json']},
 'no_network_device_native_worker_or_remote_guard':True}
(HERE/'test-optimize-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':True,'new_cases':len(rows),'old_groups_not_rerun':True}))
