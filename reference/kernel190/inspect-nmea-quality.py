from pathlib import Path
import json
import host

code='''from pathlib import Path
import json,collections,math
path=Path('/var/lib/samurai/k190-mm-stream/locations-private.jsonl')
seen=set();view=[];used=[];snr=[];gsa=[]
for row in path.read_text().splitlines():
 values=json.loads(row)['locations']
 for key,value in values.items():
  if int(key)!=4:continue
  for line in str(value).replace('\\r','').split('\\n'):
   if not line.startswith('$') or line in seen:continue
   seen.add(line);f=line.split('*')[0].split(',');kind=f[0][-3:]
   if kind=='GSV':
    if len(f)>3 and f[3].isdigit():view.append(int(f[3]))
    for i in range(7,len(f),4):
     if f[i].isdigit():snr.append(int(f[i]))
   if kind=='GGA' and len(f)>7 and f[7].isdigit():used.append(int(f[7]))
   if kind=='GSA' and len(f)>2 and f[2].isdigit():gsa.append(int(f[2]))
report=dict(maximum_satellites_in_view=max(view,default=None),maximum_satellites_used=max(used,default=None),
 cnr_numeric_fields=len(snr),maximum_cnr=max(snr,default=None),nonzero_cnr_fields=sum(v>0 for v in snr),
 gsa_fix_types=sorted(set(gsa)),distinct_sentences=len(seen))
Path('/var/lib/samurai/k190-mm-stream/signal-quality-summary.json').write_text(json.dumps(report,indent=2)+'\\n')
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'nmea-quality-host-private.log').write_bytes(p.stdout)
report=json.loads(p.stdout);(Path(__file__).resolve().parent/'nmea-quality-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
