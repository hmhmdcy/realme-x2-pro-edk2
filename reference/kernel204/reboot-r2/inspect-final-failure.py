from pathlib import Path
import json
import host

native=r'''
from pathlib import Path
import json,runpy,time
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204r2-runtime/boot-id-private.txt').read_bytes()
out=root/'k204r2-final-health-r2';ns=runpy.run_path('/usr/sbin/samurai-gnss-assist',run_name='inspect_readonly');v=ns['loc_exchange']('validity')
watch=json.loads((root/'gnss-assist/watch-state.json').read_text())
r=dict(files=[p.name for p in out.iterdir()],validity=v,is_current=ns['validity_current'](v['start'],v['hours'],time.time()),helper_running=watch['running'],helper_active=watch['active'],helper_preparations=watch['time_preparation_starts'],helper_workers=watch['worker_starts'])
(root/'k204r2-runtime/final-failure-inspection-private.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=35);(host.PRIVATE/'final-failure-inspection-private.json').write_bytes(p.stdout);print(p.stdout.decode())
