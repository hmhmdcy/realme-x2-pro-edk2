from pathlib import Path
import json,tarfile
ref=Path(__file__).resolve().parent;archive=Path('/mnt/e/edk2-samurai-out/kernel201/native-evidence-private.tar.gz');records=[]
with tarfile.open(archive) as tar:
 for folder in ['k201-geoclue-test-r2','k201-geoclue-utc-off','k201-geoclue-utc-online','k201-geoclue-auto','k201-geoclue-auto-final']:
  stamps=set()
  for line in tar.extractfile(folder+'/locations-private.jsonl').read().decode().splitlines():
   values=json.loads(line)['locations']
   for key,value in values.items():
    if int(key)!=4:continue
    for sentence in str(value).replace('\r','').split('\n'):
     fields=sentence.split('*')[0].split(',')
     if fields[0]=='$GPGGA' and len(fields)>1:stamps.add(fields[1])
  r=dict(trial=folder,distinct_gga_time_fields=len(stamps),all_gga_time_fields_zero=bool(stamps) and all(not value or float(value)==0 for value in stamps),gga_time_advances=len(stamps)>1)
  if folder=='k201-geoclue-test-r2':assert r['all_gga_time_fields_zero'] and not r['gga_time_advances']
  else:assert not r['all_gga_time_fields_zero'] and r['gga_time_advances']
  records.append(r)
report=dict(stage=201,trials=records,actual_time_fields_and_nmea_kept_private=True)
(ref/'nmea-clock-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
