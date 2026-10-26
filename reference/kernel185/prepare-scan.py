from pathlib import Path
import hashlib
import json
import subprocess
import host

ref = Path(__file__).resolve().parent
base = ref.parent / 'kernel130'
text = (base / 'test-bluez-service-discovery.py').read_text()
text = text.replace('sys.path.insert(0,\'/tmp\')', "sys.path.insert(0,'/var/lib/samurai/k185-tools')")
text = text.replace('from k130_bt_mgmt import', 'from bt_mgmt import')
text = text.replace("root=Path('/var/lib/samurai/k130-bluez-service-discovery')", "root=Path(sys.argv[1])")
text = text.replace('k129-first-runtime/boot-id-private.txt', 'k185-baseline/boot-id-private.txt')
text = text.replace("startswith('#129 ')", "startswith('#183 ')")
text = text.replace('dict(kernel=129,', 'dict(kernel=183,')
path = ref / 'test-bluez-scan.py'
path.write_text(text)
subprocess.run(['python3', '-m', 'py_compile', str(path)], check=True)
host.ssh('test ! -e /var/lib/samurai/k185-tools && mkdir -m700 /var/lib/samurai/k185-tools')
for p in [path, base / 'bt_mgmt.py']:
    host.upload(p, '/var/lib/samurai/k185-tools/' + p.name)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(p.read_bytes()).hexdigest() + '  /var/lib/samurai/k185-tools/' + p.name + '\n').encode())
result = host.ssh('nohup python3 /var/lib/samurai/k185-tools/test-bluez-scan.py /var/lib/samurai/k185-scan-before > /var/lib/samurai/k185-scan-before-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'scan-before-worker-pid-private.txt').write_bytes(result.stdout)
print(json.dumps({'baseline_le_bredr_auto_scans_started': True, 'no_pairing_or_connection_requested': True}))
