from pathlib import Path
import json
import host
code=r'''
from pathlib import Path
import json,subprocess
b=subprocess.check_output(['dmesg'],text=True)
cci={}
for n in ['ac4a000.cci','ac4b000.cci']:
 p=Path('/sys/bus/platform/devices')/n;node=p/'of_node'
 cci[n]=dict(runtime=(p/'power/runtime_status').read_text().strip(),power_domains=(node/'power-domains').read_bytes().hex() if (node/'power-domains').exists() else None)
ssc=json.loads(Path('/run/samurai-ssc/state.json').read_text())
print(json.dumps(dict(cci=cci,dmesg_camera_errors=[l for l in b.splitlines() if any(s in l.lower() for s in ['cci','lc898','lens','timeout','failed to open'])][-100:],ssc=ssc,
 genpd=Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_text(),rails=[dict(name=(p/'name').read_text().strip(),state=(p/'state').read_text().strip(),users=(p/'num_users').read_text().strip()) for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'name').read_text().strip()=='cam-main-vaf'])))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);d=json.loads(q.stdout);(host.PRIVATE/'lens-timeout-inspection-private.json').write_bytes(q.stdout)
print(json.dumps({k:v for k,v in d.items() if k not in ['genpd','ssc']},indent=2));print('\n'.join(l for l in d['genpd'].splitlines() if any(t in l for t in ['titan','cci','s5kgw1','6-0072'])))
