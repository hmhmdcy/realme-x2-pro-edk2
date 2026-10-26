"""Check allocation metadata for the exact firmware DDR range, without reading RAM."""
from pathlib import Path
import json,shlex
import host
HERE=Path(__file__).resolve().parent
code=r'''
from pathlib import Path
import collections,json,re,struct
start=0x9ab00000;size=0x500000;end=start+size;rows=[]
for line in Path('/proc/iomem').read_text().splitlines():
 m=re.match(r'\s*([0-9a-f]+)-([0-9a-f]+) : (.*)',line)
 if m and int(m[1],16)<end and int(m[2],16)>=start:rows.append(line)
result=dict(physical=start,bytes=size,iomem_overlaps=rows)
flags=Path('/proc/kpageflags');counts=Path('/proc/kpagecount')
if flags.exists():
 with flags.open('rb',buffering=0) as stream:stream.seek((start//4096)*8);raw=stream.read((size//4096)*8)
 assert len(raw)==(size//4096)*8;values=struct.unpack('<'+str(size//4096)+'Q',raw)
 result['flag_counts']={hex(value):n for value,n in collections.Counter(values).items()}
 result['page_categories']={name:sum(bool(value&(1<<bit)) for value in values) for name,bit in [('slab',7),('buddy',10),('mapped',11),('anon',12),('no_page',20),('page_table',26),('internal_reserved_bit32',32)]}
if counts.exists():
 with counts.open('rb',buffering=0) as stream:stream.seek((start//4096)*8);raw=stream.read((size//4096)*8)
 assert len(raw)==(size//4096)*8;values=struct.unpack('<'+str(size//4096)+'Q',raw)
 result['mapping_counts']={str(value):n for value,n in collections.Counter(values).items()}
print(json.dumps(result))
'''
q=host.ssh('python3 -c '+shlex.quote(code),timeout=20);d=json.loads(q.stdout);(host.PRIVATE/'firmware-reservation-metadata-private.json').write_bytes(q.stdout)
d.update(stage=369,read_only_allocation_metadata=True,raw_ddr_not_read=True,firmware_cpu_not_started=True)
(HERE/'firmware-reservation-validation.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
