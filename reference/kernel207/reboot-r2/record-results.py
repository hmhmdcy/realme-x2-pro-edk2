from pathlib import Path
import json
import host

here=Path(__file__).resolve().parent
health=json.loads((host.PRIVATE/'final-health-r2-host-private.log').read_text())
assert health['same_second207_boot_verified'] and health['gnss_session_terminal_and_test_files_removed']
(here/'final-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')
late=json.loads((host.PRIVATE/'late-location-inspection-private.json').read_text())
(here/'late-location-validation.json').write_text(json.dumps(late,indent=2)+'\n')
test=json.loads((here/'geoclue-first-session-validation.json').read_text())
assert test['client_exit']==0 and test['automatic_worker_starts']==test['automatic_worker_completions']==1
for folder in [host.PRIVATE,host.PRIVATE.parent]:
    path=folder/'current-work-private.json';plan=json.loads(path.read_text())
    plan.update(state='Second207 boot verified.173 own-stockMCFG files auto-staged; actualmdtime reads no longerENOENT.181.37s GNSS-only test187NMEA/174advancingUTC, automatic1download+1inject168h, nofix/CNR/location. Testfinished; lateflags saved and normalized. ThreeDSP running/fault0. No pendingreboot.',
        current_boot_guard='/var/lib/samurai/k207r2-runtime/boot-id-private.txt',current_host='reference/kernel207/reboot-r2/host.py',
        transition_pending=False,gnss_worker_terminal=True,current_health=health,
        next='Export207 evidence and finish source/docs mirror. Then investigate actual GNSS receiver/stock initialization differences using verified public sources; do not repeat identical NMEA tests or foreignNV edits. Continue complete peripheralgoal.')
    path.write_text(json.dumps(plan,indent=2)+'\n')
print('GNSS result and independent final health recorded; no worker or reboot pending.')
