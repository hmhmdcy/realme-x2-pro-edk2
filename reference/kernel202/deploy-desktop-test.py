from pathlib import Path
import host

here=Path(__file__).resolve().parent
host.ssh('test ! -e /usr/libexec/samurai-gnss-validation')
host.upload(here.parent/'kernel201/geoclue-validation-client.py','/usr/libexec/samurai-gnss-validation')
host.ssh('chmod 755 /usr/libexec/samurai-gnss-validation')
p=host.ssh('python3 -',input=(here/'inspect-desktop-session.py').read_bytes(),timeout=30)
(host.PRIVATE/'actual-desktop-switch-private.json').write_bytes(p.stdout)
print(p.stdout.decode())
