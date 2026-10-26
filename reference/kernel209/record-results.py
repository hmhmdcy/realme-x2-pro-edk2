from pathlib import Path
import json
from clock_uncertainty import selftest
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel209')
for label in ['baseline','inspect-clock-bound','inspect-utc-enum','inspect-camera-normal','inspect-camera-installed-modules','final-health']:
    value=json.loads((private/(label+'-host-private.log')).read_text())
    (here/(label+'-validation.json')).write_text(json.dumps(value,indent=2)+'\n')
(here/'clock-bound-validation.json').write_text(json.dumps(dict(stage=209,**selftest()),indent=2)+'\n')
automatic=json.loads((private/'automatic-worker-after-comparison-private.json').read_text())
assert automatic['last_result']['download_count']==automatic['last_result']['injection_count']==0
(here/'assistance-control-validation.json').write_text(json.dumps(dict(stage=209,automatic_helper_result=automatic['last_result'],worker_starts=automatic['worker_starts'],worker_completions=automatic['worker_completions']),indent=2)+'\n')
value=json.loads((here/'utc-comparison-validation.json').read_text())
assert not value['errors'] and value['nmea_mask_restored'] and value['gps_enabled_final']==0
health=json.loads((here/'final-health-validation.json').read_text())
plan=json.loads((private/'current-work-private.json').read_text())
plan.update(state='209 comparison terminal. In oneGPS session,25PQWM1 with1000ms vs60PQWM1 after418ms injection bothreport~6s; ACK+completion23ms, nofix/CNR. Original1000ms freshUTC resent; mask63/GPS0 restored, health3301s fault0/NVunchanged. Candidate notdeployed. Read-only camera inventory confirmsCCI0/1 disabled, noPM8008/IMX471 nodes, media22entities nofrontsensor.',
    current_health=health,comparison_worker_terminal=True,transition_pending=False,
    next='Archive209 and close source/docs. Continue normalboot camera graph/modules integration using200 provenfront topology andfresh209 inventory; fullperipheral goal remainsactive. Physicalsky condition question optional/pending; do not repeat unchangedGNSS clock experiment.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print('209 negative control, original policy restoration, final health and camera inventory recorded.')
