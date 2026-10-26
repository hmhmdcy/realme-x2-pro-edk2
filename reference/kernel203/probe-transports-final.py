from pathlib import Path
import hashlib,importlib.util,json,subprocess,time

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel203')
native=b"from pathlib import Path\nimport json,os\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k203-baseline/boot-id-private.txt').read_bytes()\nassert os.uname().version.startswith('#183 ')\nprint(json.dumps(dict(current203_boot_verified=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()))))\n"
candidate=private/'ModemManager191-candidate'
local=dict(bytes=candidate.stat().st_size,sha256=hashlib.sha256(candidate.read_bytes()).hexdigest()) if candidate.exists() else None
results={}
for name,path in [('usb',here.parent/'kernel202/reboot-r2/host.py'),('wifi',here.parent/'kernel200/host-before-newboot.py')]:
 spec=importlib.util.spec_from_file_location('probe_'+name,path);transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
 try:
  p=transport.ssh('python3 -',input=native,timeout=18);record=json.loads(p.stdout);record['responsive']=True
 except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
  (private/(name+'-probe-final-failed-private.log')).write_bytes((error.stdout or b'')+(error.stderr or b''));record=dict(responsive=False)
 results[name]=record
(private/'transport-probes-final-private.json').write_text(json.dumps(dict(local_candidate=local,transports=results),indent=2)+'\n')
print(json.dumps(dict(local_candidate=local,transports=results)))
