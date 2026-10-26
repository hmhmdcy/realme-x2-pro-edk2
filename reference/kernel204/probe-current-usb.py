from pathlib import Path
import importlib.util,json,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel204')
spec=importlib.util.spec_from_file_location('usb_current',here.parent/'kernel203/host-usb-before-recovery.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
code=b"from pathlib import Path\nimport json\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k204-baseline-r2/boot-id-private.txt').read_bytes()\nprint(json.dumps(dict(current204_boot_verified=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()))))\n"
try:
 p=transport.ssh('python3 -',input=code,timeout=18);r=json.loads(p.stdout);assert r['taint']==0
except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
 (private/'usb-probe-failed-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));raise SystemExit('Current USB probe failed; no transport change performed')
(private/'usb-probe-private.json').write_text(json.dumps(r)+'\n')
source=(here/'host.py').read_text();backup=here/'host-wifi-before-transition.py';assert not backup.exists();backup.write_text(source)
source=source.replace("parent.parent/'kernel203/host.py'","parent.parent/'kernel203/host-usb-before-recovery.py'")
(here/'host.py').write_text(source);print(json.dumps(r))
