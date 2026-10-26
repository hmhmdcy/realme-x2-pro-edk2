from pathlib import Path
import json
import host

here=Path(__file__).resolve().parent
runtime=json.loads((here/'runtime-validation.json').read_text())
assert runtime['new_boot_identity_verified'] and runtime['chrony_normal']
for label,target in [('inspect-bootstrap','bootstrap'),('query-pdc-readonly','query-pdc-readonly'),('query-pdc-details','query-pdc-details')]:
    value=json.loads((host.PRIVATE/(label+'-host-private.log')).read_text())
    (here/(target+'-validation.json')).write_text(json.dumps(value,indent=2)+'\n')
clock=dict(stage=207,reboot_cycle=2,initial_observation_timed_out=True,
    initial_reason='clock-not-synchronized',wifi_connected_and_global_connectivity_verified=True,
    existing_ntp_sources_refresh_online_and_burst_requested=True,ntp_configuration_unchanged=True,
    manual_wall_clock_set=False,manual_gnss_utc_or_assistance_injection=False,
    chrony_subsequently_normal=True,gnss_service_utc_preparation_automatic=True,
    utc_preparation_attempts=runtime['idle_utc_preparation_attempts'],fully_unattended_clock_bootstrap_proven=False)
(here/'clock-readiness-validation.json').write_text(json.dumps(clock,indent=2)+'\n')
for folder in [host.PRIVATE,host.PRIVATE.parent]:
    path=folder/'current-work-private.json'
    plan=json.loads(path.read_text())
    plan.update(state='Second207 boot identity, full readbacks and automatic173-file stockMCFG staging verified. ExistingNTP sources were refreshed after clock-not-synchronized; chrony thenNormal and serviceUTC preparation19/19. First finite180s GNSS-only worker running; inspect recorded worker, do not relaunch.',
        current_boot_guard='/var/lib/samurai/k207r2-runtime/boot-id-private.txt',
        current_host='reference/kernel207/reboot-r2/host.py',transition_pending=False,reboot_cycle=2,
        next='Poll the singleGNSS worker; collect cleanup/health and private evidence. Both207 rebootcycles are complete; do not replay transition scripts.')
    path.write_text(json.dumps(plan,indent=2)+'\n')
print('Second207 boot and clock exception recorded. Current GNSS worker remains the only active test.')
