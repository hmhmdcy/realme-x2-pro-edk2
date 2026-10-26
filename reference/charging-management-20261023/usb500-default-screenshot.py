"""Capture the existing session and compare current supply state."""
from pathlib import Path
import base64,hashlib,importlib.util,json,re,shlex,sys

REF=Path(__file__).resolve().parent
BASE=Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
CODE=r'''from pathlib import Path
import base64,json,subprocess,sys,time
d=json.loads(sys.stdin.buffer.read())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==d['observed_new_boot']==Path(d['guard_path']).read_text().strip()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
w=subprocess.run(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 wlr-randr --output DSI-1 --on'],capture_output=True,timeout=8)
time.sleep(.6)
q=subprocess.run(['su','-s','/bin/sh','cy122','-c','XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 grim -'],capture_output=True,timeout=10)
u=subprocess.run(['upower','-d'],capture_output=True,timeout=4)
ps=Path('/sys/class/power_supply');batteries={}
for p in ps.iterdir():
 if (p/'type').read_text().strip()!='Battery':continue
 batteries[p.name]={}
 for n in ['status','current_now','current_avg','capacity']:
  try:batteries[p.name][n]=(p/n).read_text().strip()
  except OSError as e:batteries[p.name][n]={'errno':e.errno}
r={'display_on_rc':w.returncode,'screenshot_rc':q.returncode,'screenshot_stderr':q.stderr.decode(errors='replace'),'image_b64':base64.b64encode(q.stdout).decode(),'upower_rc':u.returncode,'upower_text':u.stdout.decode(errors='replace'),'battery':batteries,'telemetry':Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text(),'UDC':Path('/sys/class/udc/a600000.usb/state').read_text().strip(),'MaxPower_ma':int(Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text()),'boottime_ns':time.clock_gettime_ns(time.CLOCK_BOOTTIME)}
print(json.dumps(r))
'''

def main():
 tag=sys.argv[1] if len(sys.argv)==2 else 'screenshot-01-private'
 assert len(sys.argv)<=2 and re.fullmatch(r'screenshot-[0-9]{2}(?:-post-replug)?-private',tag)
 out=BASE/'usb500-default-r1-private'/tag;out.mkdir(mode=0o700)
 endpoint=json.loads((BASE/'eud-boot-activation/eud-boot-r2-live-001/new-endpoint-private.json').read_bytes())
 spec=importlib.util.spec_from_file_location('transport',REF/'eud-postboot-transport.py');host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
 q=host.raw_ssh('python3 -c '+shlex.quote(CODE),input=json.dumps(endpoint).encode(),timeout=28,check=False)
 (out/'stdout-private.json').write_bytes(q.stdout);(out/'stderr-private.txt').write_bytes(q.stderr);q.check_returncode()
 d=json.loads(q.stdout);assert d['screenshot_rc']==0
 raw=base64.b64decode(d['image_b64'],validate=True);assert raw.startswith(b'\x89PNG\r\n\x1a\n')
 (out/'screen.png').write_bytes(raw)
 print(json.dumps({k:d[k] for k in ['battery','telemetry','UDC','MaxPower_ma']}))
 print(json.dumps({'image_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}))

if __name__=='__main__':main()
