from pathlib import Path
import host
source=host.PRIVATE/'source/mm-shared-qmi.c'
p=host.ssh('python3 -',input=b"from pathlib import Path\np=Path('/var/lib/samurai/k191-mm-build');p.mkdir(mode=0o700)\nprint('New build evidence directory created')\n")
print(p.stdout.decode());host.upload(source,'/var/lib/samurai/k191-mm-build/mm-shared-qmi-patched.c');print('Patched source uploaded')
