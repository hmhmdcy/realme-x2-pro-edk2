from pathlib import Path
import hashlib,io,json,shlex,sys,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;run=sys.argv[1]
d=json.loads((P/('read-'+run+'-observation.json')).read_text());assert d['state']['terminal'] and not d['worker_live'] and d['state']['summary']['passed']
code='''
from pathlib import Path
import sys,tarfile
root=Path(ROOT)
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
 for p in [root/'reads-private.json',*root.glob('*-read*-private.bin')]:tar.add(p,arcname=p.name)
'''.replace('ROOT',repr('/var/lib/samurai/k326-eeprom-'+run))
q=host.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);dest=P/('reads-'+run)
with tarfile.open(fileobj=io.BytesIO(q.stdout),mode='r:') as tar:tar.extractall(dest,filter='data')
proof=json.loads((dest/'reads-private.json').read_text());rows=[]
for model,item in proof.items():
 samples=[]
 for index,entry in enumerate(item['reads'],1):
  raw=(dest/(model+f'-read{index}-private.bin')).read_bytes();assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256'];samples.append(raw)
 assert len(samples)==2 and samples[0]==samples[1]
 rows.append(dict(model=model,bytes_per_read=len(samples[0]),independent_reads=2,duplicate_reads_equal=True,host_transfer_verified=True))
report=dict(stage=326,run=run,cameras=rows,individual_data_and_fingerprints_private=True,no_eeprom_data_writes=True,no_values_applied=True,passed=True)
(HERE/('transfer-'+run+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')
if run=='r2':(HERE/'transfer-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
