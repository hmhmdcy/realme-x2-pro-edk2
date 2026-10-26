from pathlib import Path
import json
from pqwm1 import selftest

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel208')
for label in ['baseline','query-nmea-mask','observe-mm-debug','analyze-mm-debug','analyze-aiding-debug','analyze-mm-nmea','final-health']:
    value=json.loads((private/(label+'-host-private.log')).read_text())
    (here/(label+'-validation.json')).write_text(json.dumps(value,indent=2)+'\n')
(here/'parser-validation.json').write_text(json.dumps(dict(stage=208,**selftest()),indent=2)+'\n')
health=json.loads((here/'final-health-validation.json').read_text())
assert health['nmea_mask_independently_verified']==63 and health['gnss_enabled']==0 and health['worker_starts']==health['worker_completions']==2
plan=json.loads((private/'current-work-private.json').read_text())
plan.update(state='Both208 debugworkers terminal. Firstfailed beforeGPSstart (unsupported signalname), second120.29s completed and restoredmask63/GPS0. Separate20.35s MM observer captured147NMEA including20PQWM1 and20eachPQWP2-6. RF/clock/aiding diagnostics analyzed, nofix/CNR. Health2177.49s:3DSP/fault0/NVunchanged; no lateflags normalization needed.',
    debug_worker_terminal=True,transition_pending=False,current_health=health,
    next='Export208 private evidence; finalize source/checkpoint/mirror. Next investigate UTC uncertainty against chrony bound and realreceiver conditions, without declaringRFhealthy fromADC. Continue camera/cellular/sensor/BT/PM/fullrootfs work.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('Diagnostic results and terminal state recorded. No active worker or reboot pending.')
