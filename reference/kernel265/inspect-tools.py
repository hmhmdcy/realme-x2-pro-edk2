from pathlib import Path
import json
import host
code=r'''
import json,shutil,subprocess
names=['pw-cli','pw-metadata','pw-dump','wpctl','dbus-send'];paths={n:shutil.which(n) for n in names};d=dict(paths=paths)
if paths['wpctl']:
 for args in [['wpctl','--help'],['wpctl','set-log-level','--help']]:
  q=subprocess.run(args,capture_output=True,timeout=5);d[' '.join(args)]=dict(exit=q.returncode,output=(q.stdout+q.stderr).decode())
print(json.dumps(d,indent=2))
'''
q=host.ssh('python3 -',input=code.encode(),timeout=20);(host.PRIVATE/'tool-inventory-private.json').write_bytes(q.stdout);print(q.stdout.decode())
