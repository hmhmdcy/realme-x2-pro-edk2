"""One current-state query for latency work: no control or service changes."""
from pathlib import Path
import importlib.util,json,shlex

REF=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
OUT=BASE/'latency-baseline-20261024-01-private'
CODE=r'''from pathlib import Path
import hashlib,json,os,sys,time
d=json.loads(sys.stdin.buffer.read());sha=lambda b:hashlib.sha256(b).hexdigest()
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot==d['observed_new_boot']==Path(d['guard_path']).read_text().strip()
assert sha(Path('/usr/share/samurai-charging/manifest.json').read_bytes())=='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
def read(p):
 try:return Path(p).read_text().strip()
 except OSError as e:return {'errno':e.errno}
packages={}
for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
 fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
 if fields.get('P') in ['phosh','upower']:packages[fields['P']]={'fields':fields,'raw_block':block}
assert set(packages)=={'phosh','upower'}
processes={}
for p in Path('/proc').glob('[0-9]*'):
 try:
  name=(p/'comm').read_text().strip()
  if name not in ['phosh','upowerd']:continue
  exe=Path(os.readlink(p/'exe'));assert exe.is_file()
  processes[name]={'path':str(exe),'sha256':sha(exe.read_bytes())}
 except FileNotFoundError:continue
ps=Path('/sys/class/power_supply')
r={'packages':packages,'processes':processes,'kernel_release':os.uname().release,
 'kernel_version':os.uname().version,'taint':0,
 'source':{n:read(ps/'samurai-usb-input'/n) for n in ['online','usb_type','current_max','input_current_limit']},
 'telemetry':read('/sys/bus/i2c/devices/0-005c/telemetry'),
 'battery':{p.name:{n:read(p/n) for n in ['status','current_now','current_avg']} for p in ps.iterdir() if read(p/'type')=='Battery'},
 'udc':read('/sys/class/udc/a600000.usb/state'),
 'MaxPower':read('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower'),
 'samurai_instant_current':read('/sys/module/bq27xxx_battery/parameters/samurai_instant_current'),
 'boottime_ns':time.clock_gettime_ns(time.CLOCK_BOOTTIME)}
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==boot
print(json.dumps(r))
'''

def main():
 OUT.mkdir(mode=0o700)
 endpoint=json.loads((BASE/'eud-boot-activation/eud-boot-r2-live-001/new-endpoint-private.json').read_bytes())
 spec=importlib.util.spec_from_file_location('transport',REF/'eud-postboot-transport.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
 q=host.raw_ssh('python3 -c '+shlex.quote(CODE),input=json.dumps(endpoint).encode(),timeout=20,check=False)
 (OUT/'stdout-private.json').write_bytes(q.stdout);(OUT/'stderr-private.txt').write_bytes(q.stderr)
 (OUT/'terminal-private.json').write_text(json.dumps({'returncode':q.returncode}));q.check_returncode()
 r=json.loads(q.stdout)
 print(json.dumps({'packages':{n:{k:v['fields'].get(k) for k in ['V','o','c','U']} for n,v in r['packages'].items()},
  'kernel_version':r['kernel_version'],'source':r['source'],'battery':r['battery'],
  'udc':r['udc'],'MaxPower':r['MaxPower'],'taint':r['taint']}))

if __name__=='__main__':main()
