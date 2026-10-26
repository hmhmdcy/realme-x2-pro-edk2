import host, json, shutil
target = host.PRIVATE / 'publish-mcfg-first-failure-private.log'
host.download('/var/lib/samurai/k207-mcfg-deploy/publish-stock-mcfg-private.log', target)
print('\n'.join(target.read_text().splitlines()[-5:]))
code = r'''
from pathlib import Path
import json
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k207-runtime/boot-id-private.txt').read_bytes()
paths=['/run/samurai-wifi','/run/samurai-wifi/firmware/qcom/sm8150/realme/samurai']
print(json.dumps({p:dict(mode=oct(Path(p).stat().st_mode&0o777),uid=Path(p).stat().st_uid) for p in paths}))
'''
p = host.ssh('python3 -', input=code.encode()); (host.PRIVATE / 'mcfg-failure-directory-modes-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
shutil.copyfile(host.PRIVATE / 'transport-last-failure-private.log', host.PRIVATE / 'mcfg-first-deploy-failure-private.log')
