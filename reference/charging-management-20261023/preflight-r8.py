"""Read current R7 prerequisites after camera handback; no phone mutation."""
from pathlib import Path
import base64
import hashlib
import importlib.util
import json

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
EXPECTED = '479916c260c7ee9c654ba6471ec22f3ece67d5d797d2de03d5d5e199ee80814b'


def main():
    worker = (REF.parent / 'charging-oem-audit-20261023/r8-update/update-r8.py').read_bytes()
    assert hashlib.sha256(worker).hexdigest() == EXPECTED
    spec = importlib.util.spec_from_file_location('window', REF / 'device-window.py')
    window = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(window)
    code = '''import base64,hashlib,json
from pathlib import Path
worker=base64.b64decode(%r,validate=True)
assert hashlib.sha256(worker).hexdigest()==%r
ns={'__name__':'r8_readonly_preflight'};exec(compile(worker,'<frozen-r8-updater>','exec'),ns)
io=ns['Device']();m=io.manager(ns['SERVICE_SHA']);meta=io.verify(m)
assert hashlib.sha256(Path(ns['MANIFEST']).read_bytes()).hexdigest()==ns['OLD']
io.notes_match(m,meta)
before=io.observe(m);ns['healthy'](before,False);ns['unchanged'](before,before)
assert before['limits']['native_ua']==before['limits']['source_budget_ua']==before['limits']['input_ua']==100000
assert before['limits']['charge_ua']==250000 and '[SDP]' in before['source']['usb_type']
assert '[auto]' in (m['live'].PSY/'mp2650-input/charge_behaviour').read_text()
print(json.dumps({'preflight_passed':True,'observation':before,'manifest_sha256':ns['OLD']}))
''' % (base64.b64encode(worker).decode(), EXPECTED)
    response = window.host.ssh('python3 -', input=code.encode(), timeout=30, check=False)
    output = PRIVATE / 'r8-preflight'
    output.mkdir(mode=0o700, exist_ok=True)
    (output / 'stdout-private.json').write_bytes(response.stdout)
    (output / 'stderr-private.txt').write_bytes(response.stderr)
    if response.returncode:
        print(response.stderr.decode(errors='replace')[-2200:])
        return response.returncode
    data = json.loads(response.stdout)
    print(json.dumps(dict(preflight_passed=data['preflight_passed'],
                          limits=data['observation']['limits'],
                          temperature_decic=data['observation']['sample']['temp_decic'],
                          taint=data['observation']['state']['taint'])))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
