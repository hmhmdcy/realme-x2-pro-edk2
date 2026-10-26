"""Read/hash receipts and unchanged bodies; no build/test/device actions."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent;REF=HERE.parents[1]
OLD=REF/'charging-session-20261023/apsd-session-owner-candidate'
PD=REF/'charging-oem-audit-20261023/pd5v-owner-context-r2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=json.loads((HERE/'source-inputs.json').read_bytes())
for n,h in inputs.items():assert sha(REF/n)==h,n
def function(s,n):
 m=re.search(r'(?m)^.*\b'+re.escape(n)+r'\([^;]*?\)\n\{',s);assert m,n
 end=m.end();depth=1
 while depth:depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[m.start():end]+'\n'
old=(PD/'qcom_pmic_typec_5v.c').read_text();new=(HERE/'qcom_pmic_typec_5v.c').read_text()
names=['pd5v_now_ms','pd5v_read','pd5v_policy','pd5v_off','pd5v_same_status','pd5v_disabled','pd5v_disable_off','pd5v_verify','samurai_pd5v_acquire','samurai_pd5v_validate','pd5v_free','pd5v_unpublish_if_retired','samurai_pd5v_release','qcom_pmic_typec_5v_acquire','samurai_pd5v_quiesce','samurai_pd5v_complete','samurai_pd5v_destroy']
bodies={}
for n in names:
 a,b=function(old,n),function(new,n);assert a==b,n
 bodies[n]=hashlib.sha256(a.encode()).hexdigest()
unchanged=dict(PD_R2_function_bodies=bodies,DWC_files={n:sha(HERE/n) for n in ['core.c','core.h','gadget.c']})
for n,h in unchanged['DWC_files'].items():assert sha(OLD/n)==h
(HERE/'unchanged-functions.json').write_text(json.dumps(unchanged,indent=2)+'\n')
t=json.loads((HERE/'test-result.json').read_bytes());b=json.loads((HERE/'build-result.json').read_bytes())
assert t['passed'] and t['affected_groups']==14 and b['passed'] and b['shared_unchanged']
for n,h in t['tested_files'].items():assert sha(HERE/n)==h,n
for n,h in b['sources'].items():assert sha(HERE/n)==h,n
gate=function((HERE/'samurai-apsd-owner.c').read_text(),'owner_entry_gate')
assert 'return -EOPNOTSUPP;' in gate and 'return 0;' not in gate
r=dict(schema='samurai-apsd-pd5v-client-bridge-v1',frozen=True,implemented='real PD5V client bridge only',
 default_enabled=False,APSD_transfer_enabled=False,full_PD_supported=False,full_charging_adaptation_complete=False,
 actual_TYPEC_QCOM_PMIC='m; refused',future_builtin_objects='command-only compile view; not a deployed/link configuration',
 tests=dict(passed=True,new_affected_groups=14,receipt_sha256=sha(HERE/'test-result.json'),old_suites_rerun=False),
 build=dict(passed=True,receipt_sha256=sha(HERE/'build-result.json'),shared_unchanged=True,Image_or_module_linked=False),
 sources={n:sha(HERE/n) for n in ['samurai-apsd-owner.c','samurai-apsd-owner.h','qcom_pmic_typec_5v.c','qcom_pmic_typec_5v.h','bridge.patch','Kconfig.fragment']},
 device_accessed=False,SDK_invoked=False,Git_invoked=False,installed=False)
(HERE/'result.json').write_text(json.dumps(r,indent=2)+'\n')
files=[p for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='delivery.json' and 'test-private' not in p.parts]
d=dict(schema='samurai-apsd-pd5v-client-bridge-delivery-v1',frozen=True,files={p.relative_to(HERE).as_posix():sha(p) for p in sorted(files)})
(HERE/'delivery.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(dict(source=sha(HERE/'samurai-apsd-owner.c'),PD_api=sha(HERE/'qcom_pmic_typec_5v.c'),patch=sha(HERE/'bridge.patch'),test=sha(HERE/'test-result.json'),build=sha(HERE/'build-result.json'),result=sha(HERE/'result.json'),delivery=sha(HERE/'delivery.json'))))
