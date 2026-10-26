from pathlib import Path
import ast
ref=Path(__file__).resolve().parent
s=(ref.parent/'kernel191/probe-utc-injection.py').read_text().replace('k191','k201').replace('stage=191','stage=201').replace('k189r2-reboot-runtime','k201-baseline');ast.parse(s);(ref/'probe-utc-injection.py').write_text(s)
s=(ref/'test-geoclue-gnss.py').read_text().replace('k201-geoclue-test-r2','k201-geoclue-utc-off').replace("'180'","'90'").replace('samurai-gnss-validation 180','samurai-gnss-validation 90')
s=s.replace('time.monotonic()+235','time.monotonic()+145');ast.parse(s);(ref/'test-geoclue-utc-off.py').write_text(s)
print('K201_ONE_SYNC_UTC_AND_SAME_DESKTOP_PIPELINE_COMPARISON_PREPARED')
