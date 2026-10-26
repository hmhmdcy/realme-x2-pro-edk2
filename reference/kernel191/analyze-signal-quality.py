from pathlib import Path
import json,math,tarfile,sys
ref=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel191')
radio=len(sys.argv)>1 and sys.argv[1]=='radio';assert len(sys.argv)==1 or radio
archive='radio-supplement-private.tar.gz' if radio else 'evidence-private.tar.gz'
entry='k191-online-gps/locations-private.jsonl' if radio else 'k191-mm-stream/locations-private.jsonl'
with tarfile.open(private/archive) as tar:lines=tar.extractfile(entry).read().decode().splitlines()
seen=set();view=[];used=[];snr=[];fix=[]
for line in lines:
 for key,value in json.loads(line)['locations'].items():
  if int(key)!=4:continue
  for sentence in str(value).replace('\r','').split('\n'):
   if not sentence.startswith('$') or sentence in seen:continue
   seen.add(sentence);f=sentence.split('*')[0].split(',');kind=f[0][-3:]
   if kind=='GSV':
    if len(f)>3 and f[3].isdigit():view.append(int(f[3]))
    for i in range(7,len(f),4):
     try:v=float(f[i])
     except ValueError:continue
     if math.isfinite(v):snr.append(v)
   if kind=='GGA' and len(f)>7 and f[7].isdigit():used.append(int(f[7]))
   if kind=='GSA' and len(f)>2 and f[2].isdigit():fix.append(int(f[2]))
report=dict(stage=191,distinct_sentences=len(seen),maximum_satellites_in_view=max(view,default=None),maximum_satellites_used=max(used,default=None),
 cnr_numeric_fields=len(snr),positive_cnr_fields=sum(v>0 for v in snr),maximum_cnr=max(snr,default=None),gsa_fix_types=sorted(set(fix)))
(ref/('online-signal-quality-validation.json' if radio else 'nmea-quality-validation.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
