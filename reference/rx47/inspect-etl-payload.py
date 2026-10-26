from pathlib import Path
from hashlib import sha256
import xml.etree.ElementTree as ET
from collections import Counter
import re

b=Path('/mnt/e/edk2-samurai-out/rx46')
raw=(b/'etw-r46g-capture.etl').read_bytes()
for name, needle in [('frame',bytes.fromhex('90 0a 65 63 68 6f 20 52 34 36 47 0a')),
                     ('payload',b'echo R46G\n'),('ascii-hex',b'900a6563686f20523436470a')]:
    print(name, 'raw ETL occurrences=', raw.count(needle), 'first_offset=', raw.find(needle))
ns={'e':'http://schemas.microsoft.com/win/2004/08/events/event'}
root=ET.parse(b/'etw-r46g-capture.all-local-lr.xml').getroot()
events=root.findall('e:Event',ns)
ucx=[ev for ev in events if ev.find('e:System/e:Provider',ns).get('Name')=='Microsoft-Windows-USB-UCX']
print('UCX event ID/version counts:', Counter((e.findtext('e:System/e:EventID',namespaces=ns),e.findtext('e:System/e:Version',namespaces=ns)) for e in ucx))
print('Target completion templates:')
for ev in ucx:
    fields={e.get('Name'):(e.text or '').strip() for e in ev.findall('.//e:Data',ns)}
    if fields.get('fid_UsbDevice')=='0x3FF44207E648' and fields.get('fid_PipeHandle')=='0xFFFFC00BB08ABC80' and ev.findtext('e:System/e:EventID',namespaces=ns)=='27':
        print('Version',ev.findtext('e:System/e:Version',namespaces=ns),'field_names',sorted(fields))
text=(b/'ucx-provider-local.xml').read_text(encoding='utf-8-sig')
for match in re.finditer(r'<event value="(?:26|27|28|29)"[^>]*>',text): print(match.group())
print('ETL sha256=',sha256(raw).hexdigest())
