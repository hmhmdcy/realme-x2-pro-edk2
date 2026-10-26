from pathlib import Path
import json
import struct

root = Path('/sys/firmware/devicetree/base')
report = []
for path in root.rglob('qcom,vmids'):
    data = path.read_bytes()
    assert len(data) % 4 == 0
    ids = list(struct.unpack('>'+'I'*(len(data)//4), data))
    report.append({'node': str(path.parent.relative_to(root)), 'vmids': ids})
out = Path('/var/lib/samurai/k186-load-fastrpc-r2/vmids-private.json')
out.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
