from pathlib import Path
import ast
ref=Path(__file__).resolve().parent;s=(ref/'test-geoclue-utc-off.py').read_text().replace('k201-geoclue-utc-off','k201-geoclue-utc-online');ast.parse(s);(ref/'test-geoclue-utc-online.py').write_text(s)
print('K201_SAME_90_SECOND_GEOCUE_GNSS_PIPELINE_FOR_CURRENT_ONLINE_POWER_STATE_PREPARED')
