from pathlib import Path
import json,math,sys
sys.path.insert(0,'/var/lib/samurai/k208-loc-tools')
from pqwm1 import sentence
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
out=root/'k208-mm-nmea-analysis';out.mkdir(mode=0o700)
seen=set();report=dict(stage=208,saved_existing_session_only=True,unique_nmea=0,nmea_types={},checksum_errors=0,valid_gga=0,active_rmc=0,positive_cnr_fields=0,raw_coordinate_dicts=0)
for line in (root/'k208-mm-debug-observer/mm-nmea-private.jsonl').read_text().splitlines():
    values=json.loads(line)
    raw=values.get('2',{})
    if isinstance(raw,dict) and all(name in raw and math.isfinite(float(raw[name])) for name in ['latitude','longitude']):report['raw_coordinate_dicts']+=1
    for text in str(values.get('4','')).replace('\r','').split('\n'):
        if not text.startswith('$') or text in seen:continue
        seen.add(text);report['unique_nmea']+=1
        try:fields=sentence(text)
        except ValueError:report['checksum_errors']+=1;continue
        name=fields[0];report['nmea_types'][name]=report['nmea_types'].get(name,0)+1
        if name.endswith('GGA') and len(fields)>6 and fields[6].isdigit():report['valid_gga']+=int(int(fields[6])>0)
        if name.endswith('RMC') and len(fields)>2:report['active_rmc']+=int(fields[2]=='A')
        if name.endswith('GSV'):
            for i in range(7,len(fields),4):
                try:value=float(fields[i])
                except ValueError:continue
                report['positive_cnr_fields']+=int(math.isfinite(value) and value>0)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
