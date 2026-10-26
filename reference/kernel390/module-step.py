from pathlib import Path
import json,shlex,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;action=sys.argv[1];root='/var/lib/samurai/k390-deployment'
if action=='launch':
 assert json.loads((HERE/'staging-validation.json').read_text())['passed']
 code="""from pathlib import Path
import json,subprocess,os
root=Path(ROOT);assert not (root/'state.json').exists() and not (root/'launch.json').exists()
log=(root/'worker.log').open('xb');child=subprocess.Popen(['python3',str(root/'worker.py'),str(root)],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
data=dict(pid=child.pid);f=(root/'launch.json').open('x');json.dump(data,f);f.flush();os.fsync(f.fileno());print(json.dumps(data))
"""
elif action=='observe':
 code="""from pathlib import Path
import json
root=Path(ROOT);s=json.loads((root/'state.json').read_text());p=Path('/proc',str(s['pid']))
live=p.exists() and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z' and str(root/'worker.py').encode() in (p/'cmdline').read_bytes()
print(json.dumps(dict(state=s,worker_live=live)))
"""
else:raise ValueError(action)
q=host.ssh('python3 -c '+shlex.quote(code.replace('ROOT',repr(root))),timeout=25);(P/('module-'+action+'-private.json')).write_bytes(q.stdout);d=json.loads(q.stdout)
if action=='observe':
 s=d['state'];report=dict(stage=390,worker_live=d['worker_live'],**{k:s[k] for k in ['phase','terminal','passed','candidate_files_installed','old_loaded_code_preserved','failure','files_rolled_back','rollback_error','service_restore_error'] if k in s})
 if s.get('terminal'):(HERE/'module-install-validation.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
else:print(q.stdout.decode())
