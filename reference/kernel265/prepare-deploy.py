"""Reuse audited transaction/restart workers with current stage265 identities."""
from pathlib import Path
import ast
R=Path(__file__).parent;B=R.parent/'kernel264'
def worker(name):
 tree=ast.parse((B/name).read_text())
 return next(node.value.value for node in tree.body if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='code' for t in node.targets))
code=worker('install-packages.py').replace('stage=264','stage=265').replace('k264-package','k265-package').replace("'-1.6.9-r2.apk'","'-1.6.9-r3.apk'").replace("versions={name:'1.6.9-r2'","versions={name:'1.6.9-r3'")
old="old=[str(inputs/(name+'-1.6.9-r0.apk')) for name in names]";assert code.count(old)==1;code=code.replace(old,"old=[str(inputs/(i['package']+'-'+i['original_version']+'.apk')) for i in proof]")
code=code.replace('len(actions)==2','len(actions)==3').replace('len(lines)==2','len(lines)==3')
outer='''from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent;proof=json.loads((R/'package-build-validation.json').read_text())
for mode in [6000141,6000142,6000143]:
 d=json.loads((R/('compat-'+str(mode)+'-validation.json')).read_text());assert d['diagnostic_completed']
 for c in d['probe_result']['clients']:assert c['held_content_changed']==0 and c['not_recycled_errors']==0
for run in [12,13,14]:
 d=json.loads((R/('ownership-'+str(run)+'-validation.json')).read_text());assert d['completed'] and d['held_changes']==0 and d['missing_busy']==0 and d['held_without_extra_loan']==0
sim=json.loads((R/'package-simulation-validation.json').read_text());assert sim['all_six_apk_signatures_trusted'] and sim['database_and_world_unchanged']
CODE
q=host.ssh('python3 - '+shlex.quote(json.dumps(proof)),input=code.encode(),timeout=115,check=False);(host.PRIVATE/'package-install-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Inspect saved transaction state before any retry'
d=json.loads(q.stdout);(R/'package-install-validation.json').write_text(json.dumps(d,indent=2)+'\\n');print(json.dumps(d,indent=2))
'''
p=R/'install-packages.py';assert not p.exists();p.write_text(outer.replace('CODE','code='+repr(code)))
code=worker('restart-services.py').replace('stage=264','stage=265').replace("out=root/'k264-services'","out=root/'k265-services'")
needle=" assert not any(k in env for k in ['PIPEWIRE_CONFIG_DIR','PIPEWIRE_CONFIG_NAME','PIPEWIRE_RUNTIME_DIR','PIPEWIRE_REMOTE','SPA_PLUGIN_DIR'])";assert code.count(needle)==1
code=code.replace(needle," if 'SPA_PLUGIN_DIR' in env:\n  assert env['SPA_PLUGIN_DIR']=='/var/lib/samurai/k265-spa-fresh';env.pop('SPA_PLUGIN_DIR')\n"+needle)
code=code.replace("assert not any('/var/lib/samurai/k264-' in l and '.so' in l for l in maps)","assert not any(('/var/lib/samurai/k264-' in l or '/var/lib/samurai/k265-' in l) and '.so' in l for l in maps)")
needle="(out/'summary.json').write_text(json.dumps(report,indent=2)+'\\n');state['terminal']=True;"
assert code.count(needle)==1
code=code.replace(needle,"(root/'k265-services-current-private.json').write_text(json.dumps(dict(stage=265,new_processes=new,spa_candidate_active=False,spa_path='/usr/lib/spa-0.2/libcamera/libspa-libcamera.so'),indent=2)+'\\n')\n"+needle)
outer='''from pathlib import Path
import json,shlex
import host
R=Path(__file__).parent;proof=json.loads((R/'package-install-validation.json').read_text());assert proof['installed']
query="from pathlib import Path;import json;r=Path('/var/lib/samurai');m=json.loads((r/'k265-services-current-private.json').read_text());print(json.dumps(m))"
current=json.loads(host.ssh('python3 -c '+shlex.quote(query),timeout=12).stdout)
phosh=json.loads((R/'baseline-validation.json').read_text())['phosh']
baseline=dict(processes=[*current['new_processes'],dict(name='phosh',**phosh)],runtime=['/sys/bus/i2c/devices/7-0010','/sys/bus/i2c/devices/9-0010','/sys/bus/platform/devices/ac4a000.cci','/sys/bus/platform/devices/ac4b000.cci','/sys/bus/platform/devices/acb3000.camss'])
CODE
q=host.ssh('python3 - '+shlex.quote(json.dumps([proof,baseline])),input=code.encode(),timeout=65,check=False);(host.PRIVATE/'services-restart-private.log').write_bytes(q.stdout+q.stderr)
assert q.returncode==0,'Inspect saved service state; do not replay this restart'
d=json.loads(q.stdout);(R/'services-restart-validation.json').write_text(json.dumps(d,indent=2)+'\\n');print(json.dumps(d,indent=2))
'''
p=R/'restart-services.py';assert not p.exists();p.write_text(outer.replace('CODE','code='+repr(code)))
print('Prepared verified triple-package transaction and standard-environment restart')

