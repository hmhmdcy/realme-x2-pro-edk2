from pathlib import Path
import ast,json

here=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/kernel208')
first=json.loads((here/'debug-nmea-validation.json').read_text())
assert first['gps_enabled_final']==0 and first['nmea_mask_restored'] and first['client_released'] and first['device_closed']
assert first['errors']==['TypeError'] and 'temporary_nmea_mask' not in first
source=(here/'capture-debug-nmea.py').read_text().replace("out=root/'k208-debug-nmea'", "out=root/'k208-debug-nmea-r2'")
source=source.replace(";session.connect('fix-session-state',fix_session)", '')
source=source.replace('|Qmi.LocEventRegistrationFlag.FIX_SESSION_STATE','')
ast.parse(source);(here/'capture-debug-nmea-r2.py').write_text(source)
start=(here/'start-debug-capture.py').read_text().replace('debug-worker-submitted-private','debug-worker-r2-submitted-private').replace('capture-debug-nmea.py','capture-debug-nmea-r2.py').replace('debug-worker-pid-private','debug-worker-r2-pid-private').replace('k208-debug-worker-private','k208-debug-worker-r2-private')
ast.parse(start);(here/'start-debug-capture-r2.py').write_text(start)
poll=(here/'poll-debug-capture.py').read_text().replace('debug-worker-pid-private','debug-worker-r2-pid-private').replace("out=root/'k208-debug-nmea'", "out=root/'k208-debug-nmea-r2'").replace('capture-debug-nmea.py','capture-debug-nmea-r2.py').replace('debug-last-observation-private','debug-r2-last-observation-private').replace('debug-nmea-validation','debug-nmea-r2-validation')
ast.parse(poll);(here/'poll-debug-capture-r2.py').write_text(poll)
plan=json.loads((private/'current-work-private.json').read_text())
plan.update(state='Firstdebug worker terminal beforeGPSstart: unsupportedfix-session-state signalname. Originalmask63 restored, GPS0, CIDclosed. Correctedr2 sources use verifiedsignals only; r2 notyet submitted.',next='Run one correctedr2 diagnostic via newmarker, then inspect its recordedPID. Preserve firstfailure; no reboot.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('First failure and clean terminal state verified. Newr2 script/marker names prepared; no session started.')
