from pathlib import Path
import importlib.util,json,shlex
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('usb360',HERE.parent/'kernel360/host.py');usb=importlib.util.module_from_spec(spec);spec.loader.exec_module(usb)
code='''from pathlib import Path
import json
assert b'realme,samurai' in Path('/sys/firmware/devicetree/base/compatible').read_bytes()
print(json.dumps(dict(model_verified=True,kernel=Path('/proc/sys/kernel/osrelease').read_text().strip(),
 same369_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k369-recovered/boot-id-private.txt').read_bytes(),
 uptime=float(Path('/proc/uptime').read_text().split()[0]))))
'''
q=usb.raw_ssh('python3 -c '+shlex.quote(code),timeout=20);facts=json.loads(q.stdout);assert facts['model_verified']
(P/'current-transport-private.json').write_text(json.dumps(dict(kind='usb',original_key_verified=True))+'\n')
print(json.dumps(facts))
