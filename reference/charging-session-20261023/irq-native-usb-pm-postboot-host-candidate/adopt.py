"""Adopt a fully audited current PM boot; no charge or partition writes."""
from pathlib import Path
import base64, hashlib, inspect, json, os, re, sys
sys.dont_write_bytecode = True
if sys.flags.optimize: raise RuntimeError('nonoptimized Python required')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import host
BASE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
sha = host.sha; need = host.need
OLD = host.load(host.REF / 'charging-oem-audit-20261023/irq-cohort-adoption-candidate/adopt.py', 'pm_adoption_original')
# Preserve exclusive creation, fsync, process identity, EOF and same-child wait.
import subprocess
for function in (OLD.create, OLD.save, OLD.process_identity, OLD.transfer):
    exec(compile(inspect.getsource(function), '<original-' + function.__name__ + '>', 'exec'), globals())

def descriptor(context, camera, probe, capture):
    result = host.evaluate_response(context, camera, probe, capture)
    need(result['passed'] is True and result['transport_returncode'] == 0 and len(result['checks']) == 12 and not result['errors'], 'all twelve actual postboot checks required')
    request = host.make_request(context, camera, probe); tx = request['activation_transaction_id']
    need(Path(context).resolve().parent.name == tx and Path(capture).resolve().is_relative_to(Path(context).resolve().parent), 'capture activation ownership')
    raw = (Path(capture) / 'stdout-private.json').read_bytes(); report = json.loads(raw); identity = report['raw']['identity_before']
    return dict(schema='samurai-irq-native-usb-pm-adoption-v1', transaction_id=tx, profile=request['profile'],
                stage_transaction_id=request['guard']['transaction_id'], boot=identity['boot_id'], old_boot=request['activation_guard']['boot_id'],
                release=identity['uname']['release'], version=identity['uname']['version'], rootfs=identity['rootfs']['sha256'], serial_sha256=identity['serial_sha256'],
                compatible_sha256=sha(base64.b64decode(identity['compatible_b64'], validate=True)), guard='/var/lib/samurai/' + tx + '-adopted/boot-id-private.txt',
                manifest=report['raw']['manifest']['sha256'], candidate_boot_sha256=report['raw']['boot_partition']['sha256'], candidate_logdump_sha256=report['raw']['logdump_partition']['sha256'],
                context_sha256=request['context_sha256'], activation_guard_sha256=request['guard_sha256'], postboot_raw_sha256=sha(raw),
                postboot_request_sha256=sha((json.dumps(request, sort_keys=True) + '\n').encode()), postboot_request=request, endpoint=request['new_endpoint'])

def payload(value):
    host.source_check()
    source = (host.DEVICE / 'device.py').read_bytes().split(b"\nif __name__=='__main__':", 1)
    need(len(source) == 2, 'collector main delimiter')
    tail = (host.REF / 'charging-oem-audit-20261023/irq-cohort-adoption-candidate/adopt-device-tail.inc').read_text()
    tail = tail.replace("adoption['schema']=='samurai-usb-irq-protection-adoption-v1'", "adoption['schema']=='samurai-irq-native-usb-pm-adoption-v1'")
    tail = tail.replace("r'usb-irq-protection-activate-[a-z0-9-]{8,48}'", "r'irq-native-usb-pm-(?:rollback-)?activate-[a-z0-9-]{8,48}'")
    tail = tail.replace("adoption['version']=='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'", "adoption['version']==PROFILES[adoption['profile']]['version']")
    tail = tail.replace("verified['passed'] is True and not verified['errors']", "verified['passed'] is True and len(verified['checks'])==12 and not verified['errors']")
    return ('ADOPTION=' + repr(value) + '\n').encode() + source[0] + b'\n' + tail.encode()

def adopt(context, camera, probe, capture):
    value = descriptor(context, camera, probe, capture)
    out = Path(context).resolve().parent / 'pm-adoption-01-private'
    need(not out.exists(), 'once adoption already exists; inspect original')
    pointer = BASE / 'boot-adoption-private.json'; before = pointer.read_bytes()
    os.umask(0o077); out.mkdir(mode=0o700)
    create(out / 'boot-adoption-before-private.json', before); save(out / 'adopt-request-private.json', value)
    code = payload(value); create(out / 'executed-adoption-source.py', code)
    reply = transfer(out, code, host, value['endpoint'])
    expected = dict(guard_created=True, old_guards_preserved=True, transaction_id=value['transaction_id'], boot_id=value['boot'], guard=value['guard'],
                    postboot_raw_sha256=value['postboot_raw_sha256'], fresh_validation_passed=True, cohort_verified=True, charging_controls_written=False, hardware_writes=0)
    need(all(reply.get(key) == item for key, item in expected.items()), 'fresh device adoption reply differs')
    need(reply['guard_sha256'] == sha((value['boot'] + '\n').encode()) and re.fullmatch('[0-9a-f]{64}', reply['fresh_validation_sha256']), 'fresh guard/proof readback')
    current = dict(guard_path=value['guard'], original_key_verified=True, baseline481_verified=True, USB_IRQ_protection_verified=True,
                   USB_native_PM_cohort_verified=True, PM_suspend_resume_verified=False, charging_manifest_sha256=value['manifest'],
                   candidate_boot_sha256=value['candidate_boot_sha256'], candidate_logdump_sha256=value['candidate_logdump_sha256'],
                   postboot_raw_sha256=value['postboot_raw_sha256'], fresh_validation_sha256=reply['fresh_validation_sha256'],
                   stage_transaction_id=value['stage_transaction_id'], profile=value['profile'], boot_id=value['boot'],
                   Image502_verified=value['profile']=='restored_502', Image504_verified=value['profile']=='forward_504')
    save(out / 'adoption-pointer-private.json', current)
    endpoint = dict(kind='usb-ipv6', peer=value['endpoint'], interface_index=29, host_key_alias='169.254.42.1', original_key_verified=True,
                    observed_new_boot=value['boot'], guard_path=value['guard'], postboot_USB_native_PM_cohort_passed=True)
    save(out / 'new-endpoint-private.json', endpoint)
    need(pointer.read_bytes() == before, 'global pointer changed; preserve completed evidence')
    temporary = BASE / (value['transaction_id'] + '-adoption-next-private.json'); create(temporary, (json.dumps(current, indent=2) + '\n').encode())
    need(pointer.read_bytes() == before, 'global pointer changed before publish')
    temporary.replace(pointer)
    fd = os.open(BASE, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)
    save(out / 'adoption-result-private.json', dict(passed=True, pointer=current, old_pointer_and_guards_preserved=True))
    return dict(adopted=True, PM_suspend_resume_accepted=False)

def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('context','camera','probe-directory','capture-directory'): p.add_argument('--'+name)
    p.add_argument('--execute-adopt', action='store_true'); a=p.parse_args()
    if a.execute_adopt: result=adopt(a.context,a.camera,a.probe_directory,a.capture_directory)
    else: host.source_check(); result=dict(source_checked=True, device_accessed=False)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
