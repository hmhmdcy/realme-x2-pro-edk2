from pathlib import Path
import host,json
code=r'''
from pathlib import Path
import json,shutil,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k221-baseline/boot-id-private.txt').read_bytes()
r={n:shutil.which(n) is not None for n in ['cc','gcc','pkg-config']}
p=subprocess.run(['pkg-config','--modversion','qmi-glib','qrtr-glib','gio-2.0'],capture_output=True,text=True);r['pkg_exit']=p.returncode;r['versions']=p.stdout.splitlines();r['header']=Path('/usr/include/libqmi-glib/libqmi-glib.h').is_file()
print(json.dumps(r))
'''
p=host.ssh('python3 -',input=code.encode(),timeout=25);(host.PRIVATE/'native-build-inspect-private.log').write_bytes(p.stdout+p.stderr);print(p.stdout.decode())
