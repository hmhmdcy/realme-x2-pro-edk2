from pathlib import Path
import ast
here=Path(__file__).resolve().parent
source=(here.parent/'kernel208/final-health.py').read_text().replace('k208-baseline','k209-baseline').replace('k208-final-health','k209-final-health').replace('k208-loc-tools','k209-tools').replace('stage=208','stage=209')
start=source.index("for name in ['k208-debug-nmea'")
end=source.index('bus=dbus.SystemBus',start)
source=source[:start]+"value=json.loads((root/'k209-clock-compare/summary.json').read_text())\nassert not value['errors'] and value['nmea_mask_restored'] and value['gps_enabled_final']==0 and value['client_released'] and value['device_closed']\n"+source[end:]
source=source.replace("watch['worker_starts']==watch['worker_completions']==2","watch['worker_starts']==watch['worker_completions']==3")
ast.parse(source);(here/'final-health.py').write_text(source)
print('209 final health source prepared, with the current comparison receipt and worker count.')
