"""Read new boot through the original pinned key; adopt only after proofs."""
from pathlib import Path
import importlib.util
import json
import shlex
import sys

ref=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('window',ref/'device-window.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-transition')
action=sys.argv[1]

def query(code):
    q=w.host.raw_ssh('python3 -c '+shlex.quote(code),timeout=35,check=False)
    (private/(action+'-stdout-private.json')).write_bytes(q.stdout)
    (private/(action+'-stderr-private.txt')).write_bytes(q.stderr)
    if q.returncode:print(q.stderr.decode(errors='replace')[-2000:]);raise SystemExit(q.returncode)
    return json.loads(q.stdout)

if action=='charging':
    build=json.loads((ref/'usb-boot-result.json').read_text())
    data=query('BOOT_SHA='+repr(build['boot_sha256'])+'\n'+(ref/'inspect-managed-boot.py').read_text())
    report={k:v for k,v in data.items() if k!='boot_id'}
    report.update(passed=True,boot_readback_exact=True,physical_sdp_source_not_tested=True)
    (ref/'managed-boot-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
elif action=='camera':
    expected=json.loads((ref.parent/'kernel440/current-state-validation.json').read_text())
    code=(ref/'recovery-baseline.py').read_text()
    old="assert not any(Path('/sys/module',n).exists() for n in\n        ['samurai_mp2650','samurai_gauge_protection','samurai_usb_input'])"
    assert code.count(old)==1
    code=code.replace(old,old.replace('not any','all'))
    code=code.replace("data['charger_driver'] == 'mp2650'","data['charger_driver'] == 'samurai-mp2650'")
    data=query('EXPECTED='+repr(expected)+'\n'+code)
    assert data['taint']==0
    charging=json.loads((private/'charging-stdout-private.json').read_text())
    assert data['boot_id']==charging['boot_id']
    previous=json.loads((private.parent/'boot-adoption-private.json').read_text())
    (private/'previous-boot-adoption-private.json').write_text(json.dumps(previous))
    guard='/var/lib/samurai/charging-usb-dt/boot-id-private.txt'
    code='from pathlib import Path\nimport os\np=Path('+repr(guard)+');p.parent.mkdir(mode=0o700,exist_ok=True)\nassert not p.exists()\nwith p.open("x") as f:f.write('+repr(data['boot_id']+'\n')+');f.flush();os.fsync(f.fileno())'
    w.host.raw_ssh('python3 -c '+shlex.quote(code),timeout=15).check_returncode()
    (private.parent/'boot-adoption-private.json').write_text(json.dumps({'guard_path':guard,'original_key_verified':True,'baseline440_verified':True}))
    report={k:v for k,v in data.items() if k not in ['boot_id','core']}
    report.update(passed=True,charging_service_allowed=True,formal_camera_payload_preserved=True)
    (ref/'postboot-camera-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
elif action=='readiness':
    code="""from pathlib import Path
import json,subprocess
d={n:[] for n in ['phoc','phosh','pipewire','wireplumber']}
for p in Path('/proc').glob('[0-9]*'):
 try:
  n=(p/'comm').read_text().strip()
  if n in d and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':d[n].append(p.stat().st_uid)
 except OSError:pass
s=Path('/var/lib/samurai/charging-managed/state-private.json')
try:
 q=subprocess.run(['rc-service','samurai-charging','status'],capture_output=True,text=True,timeout=2)
 status={'exit':q.returncode,'text':(q.stdout+q.stderr).strip()}
except subprocess.TimeoutExpired:status={'status_query_timed_out':True}
modules={n:Path('/sys/module',n).exists() for n in ['samurai_mp2650','samurai_usb_input','samurai_gauge_protection']}
logs=Path('/var/log/messages');tail=logs.read_text(errors='replace').splitlines()[-200:] if logs.exists() else []
print(json.dumps({'uptime':Path('/proc/uptime').read_text().split()[0],'taint':int(Path('/proc/sys/kernel/tainted').read_text()),'processes':d,'modules':modules,'service_status':status,'charger_driver':Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name,'service_state':json.loads(s.read_text()) if s.exists() else None,'charging_logs':[x for x in tail if 'charg' in x.lower() or 'samurai' in x.lower()]}))
"""
    print(json.dumps(query(code),indent=2))
else:raise ValueError(action)
