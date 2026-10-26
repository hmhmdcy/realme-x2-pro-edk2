from pathlib import Path
import ast
ref=Path(__file__).resolve().parent;s=(ref/'test-geoclue-auto.py').read_text().replace('k201-geoclue-auto','k201-geoclue-auto-final').replace("'180'","'30'").replace('samurai-gnss-validation 180','samurai-gnss-validation 30').replace('time.monotonic()+235','time.monotonic()+85');ast.parse(s);(ref/'test-geoclue-auto-final.py').write_text(s)
print('K201_FINAL_WORKER_THROUGH_DISTINCT_UID10000_GEOCLUE_APPLICATION_TEST_PREPARED')
