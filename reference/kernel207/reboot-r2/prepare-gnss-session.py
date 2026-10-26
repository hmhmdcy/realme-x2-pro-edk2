from pathlib import Path
import ast, host, json
here = Path(__file__).resolve().parent
context = 'k207r2-gnss-context'
native = "from pathlib import Path; import os; os.umask(0o077); root=Path('/var/lib/samurai'); boot=Path('/proc/sys/kernel/random/boot_id').read_bytes(); assert boot==(root/'k207r2-runtime/boot-id-private.txt').read_bytes(); p=root/'k207r2-gnss-context'; p.mkdir(mode=0o700); (p/'boot-id-private.txt').write_bytes(boot)"
host.ssh('python3 -', input=native.encode())
inspect = (here.parent.parent / 'kernel203/inspect-desktop-session.py').read_text().replace('k203-baseline', context).replace('stage=203', 'stage=207')
ast.parse(inspect)
(here / 'inspect-desktop-session.py').write_text(inspect)
p = host.ssh('python3 -', input=inspect.encode())
(host.PRIVATE / 'actual-desktop-session-private.json').write_bytes(p.stdout)
source = (here.parent.parent / 'kernel204/reboot-r2/test-geoclue-first-session.py').read_text().replace('k204r2-runtime', context).replace('k204r2-geoclue-first-session', 'k207r2-geoclue-first-session').replace('stage=204', 'stage=207')
source = source.replace('first_session_after_automatic_idle_utc=True,', 'first_session_after_automatic_idle_utc=True,tftp_runtime_replaced_before_session=True,new_tftp_startup_not_yet_tested=False,stock_mcfg_auto_staging_verified_before_session=True,')
ast.parse(source)
(here / 'test-geoclue-first-session.py').write_text(source)
host.ssh('test ! -e /usr/libexec/samurai-gnss-validation')
host.upload(here.parent.parent / 'kernel201/geoclue-validation-client.py', '/usr/libexec/samurai-gnss-validation')
host.ssh('chmod 755 /usr/libexec/samurai-gnss-validation')
host.upload(here / 'test-geoclue-first-session.py', '/var/lib/samurai/k207r2-gnss-context/test-geoclue-first-session.py')
p = host.ssh('nohup python3 /var/lib/samurai/k207r2-gnss-context/test-geoclue-first-session.py > /var/lib/samurai/k207r2-geoclue-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE / 'geoclue-worker-pid-private.txt').write_bytes(p.stdout)
poll = (here.parent.parent / 'kernel204/reboot-r2/poll-gnss-first-session.py').read_text().replace('k204r2-runtime', context).replace('k204r2-geoclue-first-session', 'k207r2-geoclue-first-session')
(here / 'poll-gnss-session.py').write_text(poll)
print('Started one finite 180-second GNSS-only session on the existing boot; poll the recorded worker, do not relaunch.')
