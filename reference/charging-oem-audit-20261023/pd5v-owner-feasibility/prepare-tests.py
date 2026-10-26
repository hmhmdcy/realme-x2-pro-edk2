"""Extract actual candidate functions; fake only kernel/IO boundaries."""
from pathlib import Path
import hashlib,json,re
HERE=Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
s=(HERE/'qcom_pmic_typec_5v.c').read_text()
prefix=s[s.index('#define PD5V_STABLE_MS'):s.index('static unsigned long long pd5v_now_ms')]
records=[];parts=[prefix]
for m in re.finditer(r'(?m)^(?:static )?(?:unsigned long long|int|void|struct samurai_pd5v \*)\s*(\w+)\([^;]*?\n\{',s):
 first=s.index('{',m.start());depth=1;end=first+1
 while depth:
  if s[end]=='{':depth+=1
  elif s[end]=='}':depth-=1
  end+=1
 body=s[m.start():end];parts.append(body+'\n')
 records.append(dict(name=m.group(1),line=s[:m.start()].count('\n')+1,sha256=sha(body.encode())))
assert len(records)==17,(len(records),[r['name'] for r in records])
(HERE/'actual-functions.inc').write_bytes('\n'.join(parts).encode())
probe=(HERE/'qcom_pmic_typec.c').read_text();probe_parts=[]
for name in ['qcom_pmic_typec_init','qcom_pmic_typec_probe','qcom_pmic_typec_remove','qcom_pmic_typec_prepare','qcom_pmic_typec_complete']:
 m=re.search(r'(?m)^static (?:int|void) '+name+r'\([^;]*?\n\{',probe);assert m,name
 first=probe.index('{',m.start());depth=1;end=first+1
 while depth:
  if probe[end]=='{':depth+=1
  elif probe[end]=='}':depth-=1
  end+=1
 body=probe[m.start():end];probe_parts.append(body+'\n')
 records.append(dict(name=name,source='qcom_pmic_typec.c',line=probe[:m.start()].count('\n')+1,sha256=sha(body.encode())))
(HERE/'actual-probe.inc').write_bytes('\n'.join(probe_parts).encode())
(HERE/'function-manifest.json').write_text(json.dumps(dict(source_sha256=sha(s.encode()),probe_source_sha256=sha(probe.encode()),functions=records),indent=2)+'\n')
print(json.dumps(dict(extracted=len(records))))
