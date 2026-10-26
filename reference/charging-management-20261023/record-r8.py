"""Summarize retained completed R8 originals; no device or network access."""
from pathlib import Path
import hashlib
import json

REF = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
FETCH = PRIVATE / 'r8-update/fetch-1792749921278700617'
read = lambda path: json.loads(path.read_bytes())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
worker_hash = '479916c260c7ee9c654ba6471ec22f3ece67d5d797d2de03d5d5e199ee80814b'
marker = read(PRIVATE / 'r8-update/launch-request-private.json')
result = read(FETCH / 'result.json')
process = read(FETCH / 'runner-pid-private')
post = read(PRIVATE / 'r8-update/postcheck-stdout-private.json')
before = read(PRIVATE / 'r8-preflight/stdout-private.json')['observation']
after = post['observation']
assert sha(FETCH / 'runner-worker-private') == marker['worker_sha256'] == process['worker_sha256'] == worker_hash
assert result['passed'] and result['terminal'] and result['installed_new']
assert result['pending_child_pid'] is None and not result['mutating_process_unknown']
assert post['passed'] and post['lease_released'] and post['worker_state'] in ['absent', 'pid_reused', 'exited_zombie']
assert result['new_manifest_sha256'] == post['manifest_sha256'] == '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
assert before['limits'] == after['limits'] and before['source'] == after['source']
for name in ['boot_id', 'release', 'camera_pm', 'm2m', 'services']:
    assert before['state'][name] == after['state'][name]
assert after['state']['taint'] == '0'
for name in ['samurai-usb-input', 'samurai-gauge-protection']:
    assert before['notes'][name] == after['notes'][name]
assert after['notes']['samurai-mp2650'] == 'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'
assert after['sample']['valid'] == after['sample']['protection_ok'] == 1
assert all(after['sample'][name] == 0 for name in ['error', 'stop_error', 'fault', 'latched', 'source_inhibit', 'thermal_inhibit', 'cycle_timeout'])
summary = dict(result, worker_sha256=worker_hash, worker_exited=True,
               terminal_verified=True, single_dispatch=True,
               runtime_scope='R8 installation, INHIBIT and NORMAL SDP100 restoration only',
               physical_thermal_boundaries_accepted=False,
               physical_full_recharge_accepted=False,
               icon_latency_accepted=False, sdp500_accepted=False)
(REF / 'r8-update-result.json').write_text(json.dumps(summary, indent=2) + '\n')
handoff = dict(passed=True, manifest_sha256=post['manifest_sha256'],
               worker_sha256=worker_hash, worker_exited=True,
               owned_window_lease_released=True,
               release=after['state']['release'], taint=0,
               sample=after['sample'], limits=after['limits'], source=after['source'],
               loaded_notes_sha256=after['notes'],
               camera_pm=after['state']['camera_pm'],
               m2m=json.loads(after['state']['m2m']),
               services=after['state']['services'],
               hardware_charge_control_bits=after['registers']['08'] & 0x18,
               usb_pm_boot_unchanged=True,
               note='Last instantaneous +4mA is a single sample, not sustained net charging or icon acceptance.')
(REF / 'r8-handoff-result.json').write_text(json.dumps(handoff, indent=2) + '\n')
adoption = read(PRIVATE / 'boot-adoption-private.json')
adoption.update(schema='charging-r8-same-boot-adoption-v1',
                charging_manifest_sha256=post['manifest_sha256'],
                previous_charging_manifest_sha256=result['old_manifest_sha256'],
                loaded_notes_sha256=after['notes'],
                boot_id=after['state']['boot_id'],
                guard_unchanged=True, worker_exited=True,
                window_lease_released=True,
                baseline440_evidence='R7 postboot formal files retained; R8 writes only charger and manifest',
                transport_endpoint=str(PRIVATE / 'r7-postboot/usb-ipv6-transport-private.json'))
with (PRIVATE / 'r8-adoption-private.json').open('x') as stream:
    json.dump(adoption, stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(passed=True, worker_exited=True,
                     manifest_sha256=post['manifest_sha256'],
                     loaded_notes_sha256=after['notes'],
                     adoption_pointer=str(PRIVATE / 'r8-adoption-private.json'))))
