"""One bounded read of PM8150B control bytes in an explicitly returned window."""
from pathlib import Path
import base64
import hashlib
import importlib.util
import json

REF = Path(__file__).resolve().parent
OUT = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/pd-controls-r8-r3')
WORKER = REF.parent / 'charging-oem-audit-20261023/r8-update/update-r8.py'
EXPECTED = '479916c260c7ee9c654ba6471ec22f3ece67d5d797d2de03d5d5e199ee80814b'


def main():
    raw = WORKER.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED
    code = r'''from pathlib import Path
import base64,hashlib,json,os,re,time
worker=base64.b64decode(%r,validate=True);assert hashlib.sha256(worker).hexdigest()==%r
ns={'__name__':'pd_controls_r8_read_only'};exec(compile(worker,'<frozen-r8>','exec'),ns)
io=ns['Device']();m=io.manager(ns['SERVICE_SHA']);meta=io.verify(m)
assert hashlib.sha256(Path(ns['MANIFEST']).read_bytes()).hexdigest()==ns['NEW'];io.notes_match(m,meta)
before=io.observe(m);ns['healthy'](before,True);ns['unchanged'](before,before)
p=Path('/sys/kernel/debug/regmap/0-02')
assert (p/'name').read_text().strip()=='pmic-spmi' and (p/'range').read_text()=='0-ffff\n'
registers=[0x1307,0x1308,0x1310,0x1358,0x1362,0x1506,0x1509,0x150a,0x150b,0x150d,0x1544,0x1740,0x1744,0x1746,0x174c,0x174e]
fd=os.open(p/'registers',os.O_RDONLY|os.O_CLOEXEC)
snapshots=[]
try:
 for index in range(2):
  start=time.clock_gettime_ns(time.CLOCK_BOOTTIME);values={}
  for reg in registers:
   line=os.pread(fd,9,reg*9);match=re.fullmatch(rb'([0-9a-f]{4}): ([0-9a-f]{2})\n',line)
   assert match and int(match[1],16)==reg
   values[hex(reg)]=int(match[2],16)
  snapshots.append({'start_boottime_ns':start,'end_boottime_ns':time.clock_gettime_ns(time.CLOCK_BOOTTIME),'registers':values})
  if index==0:time.sleep(.1)
finally:os.close(fd)
after=io.observe(m);ns['healthy'](after,True);ns['unchanged'](before,after)
assert before['limits']==after['limits'] and before['source']==after['source']
try:voltage=int((m['live'].PSY/'mp2650-input/voltage_now').read_text())
except OSError as error:voltage={'errno':error.errno}
print(json.dumps({'passed':True,'scope':'two selected control-byte observations, no hardware writes',
 'before':before,'snapshots':snapshots,'after':after,
 'charger_voltage_now_uv':voltage,
 'pdphy_engine_enable_bits':[s['registers']['0x1746']&1 for s in snapshots],
 'bc1p2_source_detection_enable_bits':[(s['registers']['0x1362']>>3)&1 for s in snapshots]}))
''' % (base64.b64encode(raw).decode(), EXPECTED)
    compile(code, '<generated-pd-controls-read>', 'exec')
    spec = importlib.util.spec_from_file_location('window', REF / 'device-window.py')
    window = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(window)
    response = window.host.ssh('python3 -', input=code.encode(), timeout=30, check=False)
    OUT.mkdir(mode=0o700, exist_ok=False)
    (OUT / 'stdout-private.json').write_bytes(response.stdout)
    (OUT / 'stderr-private.txt').write_bytes(response.stderr)
    if response.returncode:
        print(response.stderr.decode(errors='replace')[-2200:])
        return response.returncode
    data = json.loads(response.stdout)
    public = dict(passed=data['passed'], scope=data['scope'], snapshots=data['snapshots'],
                  pdphy_engine_enable_bits=data['pdphy_engine_enable_bits'],
                  bc1p2_source_detection_enable_bits=data['bc1p2_source_detection_enable_bits'],
                  charger_voltage_now_uv=data['charger_voltage_now_uv'],
                  manifest_sha256=ns_manifest(), limits=data['after']['limits'],
                  sample=data['after']['sample'], loaded_notes_sha256=data['after']['notes'],
                  camera_and_four_services_unchanged=True,
                  services=data['after']['state']['services'],
                  taint=int(data['after']['state']['taint']),
                  pd_contract_inactive_proven=False, hardware_writes=0)
    (REF / 'pd-controls-r8-result.json').write_text(json.dumps(public, indent=2) + '\n')
    print(json.dumps(public, indent=2))
    return 0


def ns_manifest():
    return '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'


if __name__ == '__main__':
    raise SystemExit(main())
