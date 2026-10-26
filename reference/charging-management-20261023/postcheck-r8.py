"""Verify the completed R8 update and release only its owned window lease."""
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
    before = json.loads((PRIVATE / 'r8-preflight/stdout-private.json').read_bytes())['observation']
    marker = json.loads((PRIVATE / 'r8-update/launch-request-private.json').read_bytes())
    assert marker['worker_sha256'] == EXPECTED
    spec = importlib.util.spec_from_file_location('window', REF / 'device-window.py')
    window = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(window)
    incoming = dict(worker=base64.b64encode(worker).decode(), before=before, token=marker['token'])
    code = '''import base64,hashlib,json
from pathlib import Path
data=json.loads(%r)
worker=base64.b64decode(data['worker'],validate=True)
assert hashlib.sha256(worker).hexdigest()==%r
ns={'__name__':'r8_postcheck'};exec(compile(worker,'<frozen-r8-updater>','exec'),ns)
base=Path('/root/charging-management-20261023/charging-update-r8-runner')
receipt=json.loads(base.with_suffix('.pid-private.json').read_bytes())
assert receipt['worker_sha256']==%r
proc=Path('/proc')/str(receipt['pid'])
state='absent'
if proc.exists():
 try:
  fields=(proc/'stat').read_text().rsplit(')',1)[1].split()
  assert fields[19]!=receipt['startticks'] or fields[0]=='Z', 'original update worker is still live'
  state='pid_reused' if fields[19]!=receipt['startticks'] else 'exited_zombie'
 except FileNotFoundError: pass
result=json.loads((Path(ns['OUT'])/'result.json').read_bytes())
assert result['passed'] and result['terminal'] and not result['mutating_process_unknown'] and result['pending_child_pid'] is None
io=ns['Device']();request=json.loads(base.with_suffix('.request-private.json').read_bytes())
assert request['window_token']==data['token'];io.check_window(request)
m=io.manager(ns['SERVICE_SHA']);meta=io.verify(m)
assert hashlib.sha256(Path(ns['MANIFEST']).read_bytes()).hexdigest()==ns['NEW']
io.notes_match(m,meta)
after=io.observe(m);accepted=ns['healthy'](after,True);ns['unchanged'](data['before'],after)
assert after['limits']==data['before']['limits'] and after['source']==data['before']['source']
assert after['sample']['thermal_band']==4 and 'band_pre_shake' in after['sample']
assert '[auto]' in (m['live'].PSY/'mp2650-input/charge_behaviour').read_text()
lease=Path(ns['WINDOW']);lease_data=json.loads(lease.read_bytes())
assert lease_data['token']==data['token'] and lease_data['transaction']=='charging-update-r8'
lease.unlink()
print(json.dumps({'passed':True,'worker_state':state,'accepted_state':accepted,
 'lease_released':True,'manifest_sha256':ns['NEW'],'observation':after}))
''' % (json.dumps(incoming), EXPECTED, EXPECTED)
    response = window.host.ssh('python3 -', input=code.encode(), timeout=30, check=False)
    out = PRIVATE / 'r8-update'
    (out / 'postcheck-stdout-private.json').write_bytes(response.stdout)
    (out / 'postcheck-stderr-private.txt').write_bytes(response.stderr)
    if response.returncode:
        print(response.stderr.decode(errors='replace')[-2200:])
        return response.returncode
    data = json.loads(response.stdout)
    observation = data['observation']
    print(json.dumps(dict(passed=data['passed'], lease_released=data['lease_released'],
                          worker_state=data['worker_state'], manifest_sha256=data['manifest_sha256'],
                          notes=observation['notes'], sample=observation['sample'],
                          limits=observation['limits'], services=observation['state']['services'],
                          taint=observation['state']['taint']), indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
