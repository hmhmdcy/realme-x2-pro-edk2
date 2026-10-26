"""One bounded read-only preflight; it never loads or arms the helper."""
from pathlib import Path
import importlib.util
import json
import time

REF=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
CODE=r'''from pathlib import Path
import hashlib,json,os,re,time
expected='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
notes={'samurai_usb_input':'f0edb792d30ee1168ee1793e89707aa48b2085c845acde8f472f2c13a03804b0','samurai_gauge_protection':'930e0e1f34e89e4e06a7632ca14a26181975f9f35e55a51209af71480b56fe76','samurai_mp2650':'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k363+'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert sha('/usr/share/samurai-charging/manifest.json')==expected
assert all(sha('/sys/module/'+n+'/notes/.note.gnu.build-id')==h for n,h in notes.items())
assert not Path('/sys/module/samurai_usbin_init').exists()
assert Path('/run/openrc/started/samurai-charging').exists()
samples=[]
for _ in range(2):
 text=Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text()
 s={k:int(v) for k,v in (x.split('=') for x in text.split())}
 assert s['valid']==s['online']==s['protection_ok']==1 and 0<=s['age_ms']<=3000
 assert all(s[k]==0 for k in ['shadow','fault','error','stop_error','latched','source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop'])
 assert not s['flags']&0xc000
 samples.append(s)
 time.sleep(.2)
ps=Path('/sys/class/power_supply')
def value(supply,key):return int((ps/supply/key).read_text())
limits={'source_budget_ua':value('samurai-usb-input','current_max'),'native_ua':value('samurai-usb-input','input_current_limit'),'input_ua':value('mp2650-input','input_current_limit'),'charge_ua':value('mp2650-input','constant_charge_current'),'cv_pack_uv':value('mp2650-input','constant_charge_voltage')}
assert value('samurai-usb-input','online')==value('mp2650-input','online')==1
assert 0<limits['input_ua']<=min(900000,limits['source_budget_ua']) and 0<limits['charge_ua']<=250000 and 0<limits['cv_pack_uv']<=8725000
pm={n:(Path('/sys/bus/platform/devices')/n/'power/runtime_status').read_text().strip() for n in ['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']}
assert all(x=='suspended' for x in pm.values())
m2m=json.loads(Path('/sys/bus/platform/devices/ac10000.icp/m2m_status').read_text())
assert all(m2m.get(k)==0 for k in ['users','orphans','jobs','first_error']) and all(m2m.get(k) is False for k in ['running','fatal','pinned'])
services=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  comm=(p/'comm').read_text().strip()
  if comm not in ['phoc','phosh','pipewire','wireplumber']:continue
  uid=int(re.search(r'^Uid:\s+(\d+)',(p/'status').read_text(),re.M)[1])
  if uid==10000:services.append({'pid':int(p.name),'comm':comm,'uid':uid})
 except (FileNotFoundError,ProcessLookupError):continue
assert len(services)==4 and len({s['comm'] for s in services})==4
p=Path('/sys/kernel/debug/regmap/0-02')
assert (p/'name').read_text().strip()=='pmic-spmi' and (p/'range').read_text()=='0-ffff\n'
fd=os.open(p/'registers',os.O_RDONLY|os.O_CLOEXEC)
try:
 raw=os.pread(fd,9,0x1358*9);assert re.fullmatch(rb'1358: [0-9a-f]{2}\n',raw)
 cfg=int(raw[6:8],16)
finally:os.close(fd)
print(json.dumps({'passed':True,'manifest_sha256':expected,'notes':notes,'limits':limits,'samples':samples,'camera_pm':pm,'m2m':m2m,'services':services,'usbin_cfg_1358':cfg,'helper_absent':True,'hardware_writes':0,'taint':0}))
'''

def main():
    compile(CODE,'<read-only-usbin-preflight>','exec')
    spec=importlib.util.spec_from_file_location('usbin_window',REF/'device-window.py')
    window=importlib.util.module_from_spec(spec);spec.loader.exec_module(window)
    out=PRIVATE/('usbin-init-preflight-'+str(time.time_ns()))
    out.mkdir(mode=0o700)
    (out/'executed-device-source.py').write_text(CODE)
    response=window.host.ssh('python3 -',input=CODE.encode(),timeout=35,check=False)
    (out/'stdout-private.json').write_bytes(response.stdout)
    (out/'stderr-private.txt').write_bytes(response.stderr)
    if response.returncode:
        print(response.stderr.decode(errors='replace')[-1800:]);return response.returncode
    result=json.loads(response.stdout)
    (REF/'usbin-init-preflight-result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['passed','limits','services','usbin_cfg_1358','helper_absent','hardware_writes','taint']},indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
