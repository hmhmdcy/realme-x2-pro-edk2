"""Summarize retained first-shadow failure without exposing raw device IDs."""
from pathlib import Path
import json

ref=Path(__file__).resolve().parent
private=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/window3')
data=json.loads((private/'diagnostic-stdout-private.json').read_text())
before=json.loads(data['before']);after=json.loads(data['restored'])
assert before['boot_id']==after['boot_id']
assert before['registers']==after['registers']
assert before['services']==after['services']
assert before['camera_pm']==after['camera_pm'] and before['m2m']==after['m2m']
assert after['driver']=='mp2650' and int(after['taint'])==512
assert not any(line.startswith(('samurai_mp2650 ','samurai_gauge_protection ','samurai_usb_input '))
    for line in data['modules'].splitlines())
report={'first_shadow_passed':False,'configuration_writes':0,
    'same_boot':True,'all_captured_charger_registers_unchanged':True,
    'original_observer_restored':True,'candidate_modules_all_unloaded':True,
    'camera_pm_and_complete_m2m_unchanged':True,'captured_desktop_processes_unchanged':True,
    'taint_before':int(before['taint']),'taint_after':int(after['taint']),
    'failure':'runtime USB platform device and same-named power_supply shared software fwnode; duplicate sysfs link then software_node_notify_remove refcount WARN',
    'fix':'share firmware fwnode only for DT devices; runtime supply has no firmware node',
    'shadow_telemetry_retained':False,'recovery_required':True,
    'evidence_private_directory':str(private)}
(ref/'shadow-incident-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
