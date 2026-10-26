from pathlib import Path
import importlib.util,json,subprocess,time
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
spec=importlib.util.spec_from_file_location('strict184',HERE.parent/'kernel184/host.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
selected=json.loads((P.parent/'kernel303/fresh-working-endpoint-private.json').read_text());assert selected['kind']=='wifi'
command="python3 -c \"from pathlib import Path;import json;assert b'realme,samurai' in Path('/sys/firmware/devicetree/base/compatible').read_bytes();print(json.dumps(dict(model_verified=True,uptime=Path('/proc/uptime').read_text().split()[0],same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k367-work/boot-id-private.txt').read_bytes())))\""
start=time.monotonic()
try:
 q=subprocess.run([base.SSH,'-T',*base.OPTIONS,'-4','-o','HostKeyAlias=169.254.42.1','root@'+selected['IPAddress'],command],capture_output=True,timeout=15)
 (P/'wifi-probe-private.log').write_bytes(q.stdout+q.stderr)
 if not q.returncode:
  facts=json.loads(q.stdout);assert facts['model_verified'];(P/'current-transport-private.json').write_text(json.dumps(dict(kind='wifi',IPAddress=selected['IPAddress'],original_key_verified=True)))
  print(json.dumps(dict(authenticated=True,seconds=round(time.monotonic()-start,2),**facts)))
 else:print(json.dumps(dict(authenticated=False,exit_code=q.returncode)))
except subprocess.TimeoutExpired as error:
 (P/'wifi-probe-private.log').write_bytes((error.stdout or b'')+(error.stderr or b''));print(json.dumps(dict(authenticated=False,timeout=True)))
