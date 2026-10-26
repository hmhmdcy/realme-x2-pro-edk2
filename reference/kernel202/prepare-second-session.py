from pathlib import Path
import ast,host

here=Path(__file__).resolve().parent
source=(here/'test-geoclue-after-reboot.py').read_text()
source=source.replace("k202-geoclue-reboot-test", "k202-geoclue-second-session")
source=source.replace("watch_before['worker_starts']==watch_before['worker_completions']==0", "watch_before['worker_starts']==watch_before['worker_completions']==1")
source=source.replace(" 180\\n", " 90\\n").replace("str(script),'180'", "str(script),'90'")
source=source.replace('time.monotonic()+235', 'time.monotonic()+145')
ast.parse(source);(here/'test-geoclue-second-session.py').write_text(source)
host.ssh('test ! -e /usr/libexec/samurai-gnss-validation')
host.upload(here.parent/'kernel201/geoclue-validation-client.py','/usr/libexec/samurai-gnss-validation')
host.ssh('chmod 755 /usr/libexec/samurai-gnss-validation')
print('Second ordinary GNSS session prepared; no manual time or RF power operation.')
