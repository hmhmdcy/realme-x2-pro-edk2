from pathlib import Path
import json
import host
code=b'''from pathlib import Path
import json
p=Path('/var/lib/samurai/k192-pmic-a-release/summary.json');raw=json.loads(p.read_text())
result={}
for key in ['before_second','during_first','after_second']:
 data=raw[key];ldos=[]
 for r in data.get('ldos',[]):
  voltage=r['voltage_mv'];enable=r['enable'];status=r['status']
  ldos.append(dict(index=r['index'],programmed_mv=int.from_bytes(bytes(voltage['data']),'little') if voltage.get('success') else None,
   enable=enable.get('data'),status=status.get('data')))
 result[key]=dict(identity=data['identity'],sid_config=data['sid_config'],chip_enable=data['chip_enable'],ldos=ldos)
print(json.dumps(result))
'''
p=host.ssh('python3 -',input=code);print(p.stdout.decode())
(host.PRIVATE/'pmic-register-summary-private.json').write_bytes(p.stdout)
host.download('/var/lib/samurai/k192-pmic-a-release/summary.json',host.PRIVATE/'pmic-release-summary-private.json')
