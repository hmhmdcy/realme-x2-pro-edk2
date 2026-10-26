import host

code='''from pathlib import Path
import re,json
root=Path('/var/lib/samurai/k190-orbits')
report={}
for name in ['loc-get-predicted-orbits-data-source','loc-get-predicted-orbits-data-validity','loc-get-engine-lock']:
 raw=(root/(name+'-private.txt')).read_text()
 # URLs and any server tokens remain private; only numeric sizes/status are exported.
 lines=[line for line in raw.splitlines() if not re.search(r'https?://|server|qrtr://',line,re.I)]
 report[name]=lines
print(json.dumps(report))
'''
p=host.ssh('python3 -',input=code.encode());(host.PRIVATE/'orbits-detail-inspection-private.json').write_bytes(p.stdout);print(p.stdout.decode())
