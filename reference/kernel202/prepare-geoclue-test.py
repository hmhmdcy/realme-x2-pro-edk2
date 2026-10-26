"""Keep the native201 desktop test, adding new-boot and automatic-worker evidence."""
from pathlib import Path
import ast

here = Path(__file__).resolve().parent
prior = here.parent/'kernel201'
source = (prior/'inspect-desktop-session.py').read_text()
source = source.replace('k201-baseline', 'k202-runtime').replace('k201-geoclue-install', 'k202-runtime').replace('stage=201', 'stage=202')
ast.parse(source); (here/'inspect-desktop-session.py').write_text(source)

source = (prior/'test-geoclue-gnss.py').read_text()
source = source.replace('k201-geoclue-test-r2', 'k202-geoclue-reboot-test').replace('k201-baseline', 'k202-runtime').replace('stage=201', 'stage=202')
source = source.replace("validity=json.loads((root/'k201-validity-after/summary.json').read_text());assert validity['start_utc_timestamp']<=time.time()<validity['start_utc_timestamp']+validity['duration_hours']*3600", "watch_before=json.loads((root/'gnss-assist/watch-state.json').read_text());assert watch_before['running'] and not watch_before['active'] and watch_before['worker_starts']==watch_before['worker_completions']==0\n(out/'watch-before-private.json').write_text(json.dumps(watch_before))")
source = source.replace("assert original==(root/'k201-geoclue-install/geoclue.conf-private').read_bytes()", "(out/'geoclue.conf-original-private').write_bytes(original)")
source = source.replace("report=dict(stage=202,", "report=dict(stage=202,new_boot_verified=True,manual_utc_or_data_injection=False,ggatime_nonzero=0,ggatime_distinct=0,automatic_worker_observed=False,initial_modem_power_state=int(mp.Get('org.freedesktop.ModemManager1.Modem','PowerState')),")
source = source.replace('child=None;geopid=None;seen=set();started=time.monotonic()', 'child=None;geopid=None;seen=set();ggatimes=set();started=time.monotonic()')
source = source.replace("if kind=='GGA' and len(fields)>6", "if kind=='GGA' and len(fields)>1 and fields[1] not in ['', '0', '000000', '000000.0', '000000.00']:\n    ggatimes.add(fields[1]);report['ggatime_nonzero']+=1;report['ggatime_distinct']=len(ggatimes)\n   if kind=='GGA' and len(fields)>6")
source = source.replace("(out/'progress.json').write_text", "watch_now=json.loads((root/'gnss-assist/watch-state.json').read_text());report['automatic_worker_observed']|=watch_now['worker_starts']>0\n   (out/'watch-latest-private.json').write_text(json.dumps(watch_now))\n   (out/'progress.json').write_text")
source = source.replace("if desktop.exists():desktop.unlink()", "if desktop.exists():desktop.unlink()\n if script.exists():script.unlink()")
source = source.replace("report['elapsed_seconds']=time.monotonic()-started", "report['elapsed_seconds']=time.monotonic()-started\n watch_after=json.loads((root/'gnss-assist/watch-state.json').read_text());(out/'watch-after-private.json').write_text(json.dumps(watch_after,indent=2)+'\\n')\n report['automatic_worker_starts']=watch_after['worker_starts'];report['automatic_worker_completions']=watch_after['worker_completions'];report['automatic_worker_result']=watch_after['last_result']")
ast.parse(source)
(here/'test-geoclue-after-reboot.py').write_text(source)
print('Prepared standard UID10000 desktop test; no location or RF operation issued.')
