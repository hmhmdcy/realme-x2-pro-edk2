from pathlib import Path
import ast
ref=Path(__file__).resolve().parent;s=(ref/'test-geoclue-gnss.py').read_text().replace('k201-geoclue-test-r2','k201-geoclue-auto');ast.parse(s);(ref/'test-geoclue-auto.py').write_text(s)
print('K201_STANDARD_DESKTOP_GPS_TEST_WITH_NEW_AUTOMATIC_ASSIST_SERVICE_PREPARED')
