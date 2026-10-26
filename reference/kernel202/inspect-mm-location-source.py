from pathlib import Path
import json,re

base=Path('/mnt/e/edk2-samurai-out/kernel190/mm-build/ModemManager-7f0bf17ab518cd78925cf7e53cc0d5c42f88b41a/src')
out=Path('/mnt/e/edk2-samurai-out/kernel202')
results=[]
for name in ['mm-shared-qmi.c','mm-broadband-modem-qmi.c','mm-iface-modem.c','mm-iface-modem-location.c']:
    path=base/name
    lines=path.read_text().splitlines()
    for index,line in enumerate(lines):
        if re.search(r'INJECT_UTC|inject_time|inject_utc|EVENT.*UTC|power_down|POWER_STATE_OFF|OPERATING_MODE_OFFLINE|OPERATING_MODE_SHUTTING_DOWN',line):
            results.append(dict(file=name,line=index+1,context='\n'.join(lines[max(0,index-4):index+7])))
(out/'mm-location-power-source-hits.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(dict(contexts=len(results))))
for result in results[:10]:print(json.dumps(result))
