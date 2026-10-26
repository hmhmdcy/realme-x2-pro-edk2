from pathlib import Path
import ast,host

here=Path(__file__).resolve().parent
source=(here.parent/'kernel202/reboot-r2/inspect-desktop-session.py').read_text().replace('k202r2-runtime','k203-baseline').replace('stage=202','stage=203');ast.parse(source);(here/'inspect-desktop-session.py').write_text(source)
source=(here.parent/'kernel202/reboot-r2/test-geoclue-first-session.py').read_text().replace('k202r2-runtime','k203-baseline').replace('k202r2-geoclue-first-session','k203-geoclue-package-test').replace('stage=202','stage=203')
source=source.replace('new_boot_verified=True','same_boot202r2_verified=True').replace('first_session_after_automatic_idle_utc=True','packaged_helper_activation=True')
source=source.replace("str(script),'180'","str(script),'60'").replace(' 180\\n',' 60\\n').replace('time.monotonic()+235','time.monotonic()+115')
ast.parse(source);(here/'test-geoclue-from-package.py').write_text(source)
host.ssh('test ! -e /usr/libexec/samurai-gnss-validation')
host.upload(here.parent/'kernel201/geoclue-validation-client.py','/usr/libexec/samurai-gnss-validation');host.ssh('chmod 755 /usr/libexec/samurai-gnss-validation')
p=host.ssh('python3 -',input=(here/'inspect-desktop-session.py').read_bytes(),timeout=30);(host.PRIVATE/'actual-desktop-session-private.json').write_bytes(p.stdout);print(p.stdout.decode())
