"""Read published USB-IF specifications mirrored in TI's public attachment store.
USB-IF ZIP download returned403; no retry/bypass of that endpoint is attempted.
"""
from pathlib import Path
import hashlib
import json
import urllib.request
from pypdf import PdfReader

root = Path(__file__).resolve().parent / 'primary'
root.mkdir(exist_ok=True)
documents = {
    'usb20-original': 'https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/196/Universal-Serial-Bus-Specification.pdf',
    'bc12-original': 'https://e2echina.ti.com/cfs-file/__key/telligent-evolution-components-attachments/00-24-01-00-00-14-32-53/USB_2D00_IF_5F003575606C45513575C4893C682800_Battery_5F00_Charging_5F00_Specification_2D00_1.2_2900_.pdf',
}
report = []
for label, url in documents.items():
    path = root / (label + '.pdf')
    if not path.exists():
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read(20000000)
        assert len(data) < 20000000 and data.startswith(b'%PDF-')
        path.write_bytes(data)
    data = path.read_bytes()
    reader = PdfReader(path)
    text = '\n'.join('\n[PDF PAGE ' + str(i + 1) + ']\n' + (page.extract_text() or '')
                     for i, page in enumerate(reader.pages))
    (root / (label + '.txt')).write_text(text, encoding='utf-8')
    report.append({'label': label, 'url': url, 'bytes': len(data),
                   'sha256': hashlib.sha256(data).hexdigest(), 'pages': len(reader.pages)})
(root / 'documents.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
