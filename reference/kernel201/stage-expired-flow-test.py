from pathlib import Path
import ast,host
ref=Path(__file__).resolve().parent
s=(ref/'test-geoclue-auto-final.py').read_text().replace('k201-geoclue-auto-final','k201-geoclue-expired-auto').replace("'30'","'90'").replace('samurai-gnss-validation 30','samurai-gnss-validation 90').replace('time.monotonic()+85','time.monotonic()+145');ast.parse(s);(ref/'test-geoclue-expired-auto.py').write_text(s)
host.ssh('test ! -e /usr/libexec/samurai-gnss-validation && mkdir -m700 /var/lib/samurai/k201-expired-flow-tools')
host.upload(ref/'geoclue-validation-client.py','/usr/libexec/samurai-gnss-validation');host.ssh('chmod 755 /usr/libexec/samurai-gnss-validation')
host.upload(ref/'test-geoclue-expired-auto.py','/var/lib/samurai/k201-expired-flow-tools/test-geoclue-expired-auto.py')
print('K201_REAL_STALE_CACHE_RECOVERY_TEST_TOOLS_PREPARED_WITH_CURRENT_FILE_FALLBACK')
