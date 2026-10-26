"""Only affected Full/normal cases; actual new/R1/checker and fixed OEM host gate."""
from pathlib import Path
import ast,copy,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'eud-postboot-readonly-candidate'
COMMON=HERE.parent/'apsd-usbin-init-host-operator-r2/common.py'
PRIVATE=Path('/mnt/e/edk2-samurai-out')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(path):
 env={'__name__':'only_offline_function_definitions'}
 exec(compile(path.read_text(),str(path),'exec'),env)
 return env
new=load(HERE/'device.py');old=load(OLD/'device.py')
common_source=COMMON.read_text();tree=ast.parse(common_source)
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='healthy')
oracle={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'actual-common-healthy','exec'),oracle)
# Reuse only the original actual fixture builder, not its test-suite main.
test_source=(OLD/'test-boundaries.py').read_text()
fixture_fn=next(n for n in ast.parse(test_source).body if isinstance(n,ast.FunctionDef) and n.name=='charging')
health_path=PRIVATE/'kernel481/final-health-r2-private.json'
fixture={'sample':json.loads(health_path.read_bytes())['health']['samples'][0]['telemetry']}
exec(compile(ast.Module(body=[fixture_fn],type_ignores=[]),'original-actual-charging-fixture','exec'),fixture)
make=fixture['charging']
def changed(r,**kv):
 r=copy.deepcopy(r)
 for key in ['telemetry_before','telemetry_after']:
  t=new['parse_kv'](r[key]);t.update(kv)
  r[key]=' '.join(k+'='+str(v) for k,v in t.items())
 return r
def accepts(env,r):
 try:return env['check_charging'](r)['ready']
 except (AssertionError,KeyError,ValueError):return False
def common_accepts(r):
 s=new['parse_kv'](r['telemetry_before'])
 usb={k:int(v) for k,v in r['source'].items() if k!='usb_type'}
 chg={k:int(v) if k in ['input_current_limit','constant_charge_current','constant_charge_voltage'] else v for k,v in r['charger'].items()}
 return oracle['healthy']({'telemetry':s,'source':{'usb':usb,'charger':chg},'source_online':1,'acok_online':1})
full=changed(make(full=True),session_seconds=0)
cases=[('normal exact state',make(),True),('Full exact session0',full,True),
 ('Full cause1',changed(full,full_cause=1),True),('Full cause3',changed(full,full_cause=3),True),
 ('R1 actual Full969 regression',make(full=True),False),
 ('normal stale cause',changed(make(),full_cause=2),False),
 ('normal stale hold',changed(make(),hold_requested=1),False),
 ('Full desired remains enabled',changed(full,desired_enable=1),False),
 ('Full holding absent',changed(full,full_holding=0),False),
 ('Full logical flag absent',changed(full,logical_full=0),False),
 ('Full cause absent',changed(full,full_cause=0),False)]
rows=[]
for label,r,want in cases:
 actual=accepts(new,r);reference=common_accepts(r)
 assert actual==reference==want,(label,actual,reference,want)
 rows.append(dict(label=label,accepted=actual,common_healthy_accepted=reference))
assert accepts(old,make(full=True)) is True
assert accepts(old,changed(make(),full_cause=2)) is True
result=dict(passed=True,scope='affected Full/normal mode only; real functions with finite metadata fixtures',
 cases=rows,case_count=len(rows),actual_R1_inconsistent_Full969_accepted=True,
 actual_R1_normal_stale_cause_accepted=True,
 actual_fixed_common_healthy_differential=True,common_sha256=sha(COMMON),
 reused_R1_other_groups=9,old_10_group_suite_rerun=False,device_accessed=False,
 tested_files={n:sha(HERE/n) for n in ['device.py','device-body.py','healthy-mode-source.inc','test-full-revision.py']},
 R1_test_receipt_sha256=sha(OLD/'test-result.json'),R1_device_sha256=sha(OLD/'device.py'),
 private_cached_fixture_sha256=sha(health_path))
(HERE/'test-full-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=True,cases=len(rows),old_10_suite_rerun=False,device_accessed=False)))
