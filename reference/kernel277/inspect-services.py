from pathlib import Path
import json
import host
R=Path(__file__).resolve().parent
source=(R.parent/'kernel273/inspect-services.py').read_text().replace('stage=273','stage=277')
exec(compile(source,'services276-derived.py','exec'),dict(__file__=str(R/'inspect-services.py')))
d=json.loads((R/'services-validation.json').read_text());items=[p for p in d['processes'] if p['comm'] in ['phoc','phosh','pipewire','wireplumber']]
assert len(items)==4 and all(p['state']!='Z' for p in items) and all(d['services'][n]['exit']==0 for n in ['greetd','samurai-ssc','iio-sensor-proxy'])
code="from pathlib import Path;import json;p=Path('/var/lib/samurai/k277-services-verified-private.json');assert not p.exists();p.write_text(json.dumps(dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),processes=%r)))"%items
host.ssh('python3 -',input=code.encode(),timeout=15)
