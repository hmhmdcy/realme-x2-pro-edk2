from pathlib import Path
import json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel113')
with tarfile.open(out/'sensor-ram-v7.tar') as t:
    data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
rpc=data['rpcd.txt'].decode(errors='replace')
errors=[r for r in rpc.splitlines() if r.startswith(('Could not','Unsupported','Unexpected','Invalid','Expected','RAM registry'))]
result=dict(error_count=len(errors),error_classes=sorted(set(re.sub(r'/[^ :]+','<path>',x) for x in errors)),
            slpi_after=data['slpi-state-after.txt'].decode().strip(),
            ssc400_endpoints=[r for r in data['qrtr-after.txt'].decode().splitlines() if re.search(r'\b400\b',r)],
            oem_reads=len(re.findall('oppoVersion/modemType',rpc)),
            first_query_no_accel=b"No 'accel' sensor available" in data['accelerometer.txt'],
            late_query_no_accel=b"No 'accel' sensor available" in data['accelerometer-late.txt'],
            ram_write_count=rpc.count('ram-write('),ram_rename_count=rpc.count('ram-rename('))
(out/'rpc-v7-summary-private.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
