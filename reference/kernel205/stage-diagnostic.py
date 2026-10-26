from pathlib import Path
import ast,hashlib,json
import host

here=Path(__file__).resolve().parent;out=host.PRIVATE
policy=(here.parent/'kernel204/setup-scan-policy.py').read_text().replace('k204-runtime/boot-id-private.txt','k205-baseline/boot-id-private.txt').replace('k204-bt-policy','k205-bt-policy').replace('main.conf.k204-new','main.conf.k205-new');ast.parse(policy);(here/'setup-scan-policy.py').write_text(policy)
p=host.ssh('python3 -',input=policy.encode(),timeout=80);(out/'scan-policy-host-private.log').write_bytes(p.stdout+p.stderr)
dest='/var/lib/samurai/k205-tools';host.ssh('test ! -e '+dest+' && mkdir -m700 '+dest)
for p in [out/'hci_uart-k205-diagnostic-r2-private.ko',here/'diagnostic-build-validation.json',here/'load-diagnostic.py']:
 host.upload(p,dest+'/'+p.name);host.ssh('sha256sum -c -',input=(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+dest+'/'+p.name+'\n').encode())
p=host.ssh('python3 '+dest+'/load-diagnostic.py',timeout=120);(out/'load-diagnostic-host-private.log').write_bytes(p.stdout+p.stderr);r=json.loads(p.stdout);(here/'diagnostic-load-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
