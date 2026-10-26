from pathlib import Path
import json
import host
ROOT=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import hashlib,json,subprocess
state=json.loads(Path('/run/samurai-ssc/state.json').read_text())
logs={str(p):p.read_text(errors='replace')[-50000:] for p in Path('/run/samurai-ssc').glob('*') if p.is_file() and p.name.endswith(('.log','.txt'))}
kernel=subprocess.check_output(['dmesg'],text=True)
files={str(p):dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),text=p.read_text(errors='replace')) for p in [Path('/etc/init.d/samurai-ssc'),Path('/usr/sbin/samurai-ssc'),Path('/etc/conf.d/greetd')] if p.is_file()}
print(json.dumps(dict(state=state,logs=logs,files=files,kernel=kernel)))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'ssc-failure-context-private.json').write_bytes(q.stdout);d=json.loads(q.stdout)
errors={p:[l for l in t.splitlines() if any(w in l.lower() for w in ['error','fail','timeout','fatal','not permitted'])][-10:] for p,t in d['logs'].items()}
report=dict(stage=293,kernel_build=293,started=d['state']['started'],attempted=d['state']['attempted'],stopped=d['state'].get('stopped'),readiness_failure=d['state'].get('readiness_failure'),log_errors=errors,
 dependency_config_sha256=d['files']['/etc/conf.d/greetd']['sha256'],prior_similar_failure_stage=273,root_cause_unresolved=True)
(ROOT/'ssc-failure-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
