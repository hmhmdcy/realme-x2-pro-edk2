from pathlib import Path
import ast,json
import host

here=Path(__file__).resolve().parent;repo=here.parents[2]
source=(here.parents[1]/'kernel203/inspect-desktop-session.py').read_text().replace('k203-baseline','k204r2-runtime').replace('stage=203','stage=204');ast.parse(source);(here/'inspect-desktop-session.py').write_text(source)
source=(here.parents[1]/'kernel202/reboot-r2/test-geoclue-first-session.py').read_text().replace('k202r2-runtime','k204r2-runtime').replace('k202r2-geoclue-first-session','k204r2-geoclue-first-session').replace('stage=202','stage=204');ast.parse(source);(here/'test-geoclue-first-session.py').write_text(source)
host.ssh('test ! -e /usr/libexec/samurai-gnss-validation');host.upload(here.parents[1]/'kernel201/geoclue-validation-client.py','/usr/libexec/samurai-gnss-validation');host.ssh('chmod 755 /usr/libexec/samurai-gnss-validation')
p=host.ssh('python3 -',input=(here/'inspect-desktop-session.py').read_bytes(),timeout=30);(host.PRIVATE/'actual-desktop-session-private.json').write_bytes(p.stdout)
native=r'''
from pathlib import Path
import json,runpy
root=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k204r2-runtime/boot-id-private.txt').read_bytes()
ns=runpy.run_path('/usr/sbin/samurai-gnss-assist',run_name='before_readonly');value=ns['loc_exchange']('validity');(root/'k204r2-runtime/before-first-gnss-validity-private.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(stage=204,before_first_gnss_validity=value)))
'''
p=host.ssh('python3 -',input=native.encode(),timeout=35);(host.PRIVATE/'before-first-gnss-validity-private.json').write_bytes(p.stdout);print(p.stdout.decode())
host.upload(here/'test-geoclue-first-session.py','/var/lib/samurai/k204r2-reboot-tools/test-geoclue-first-session.py')
p=host.ssh('nohup python3 /var/lib/samurai/k204r2-reboot-tools/test-geoclue-first-session.py > /var/lib/samurai/k204r2-geoclue-worker-private.log 2>&1 < /dev/null & echo $!');(host.PRIVATE/'geoclue-worker-pid-private.txt').write_bytes(p.stdout)
print('Started one finite 180-second packaged GNSS-only desktop first session; poll this PID, do not resubmit.')
