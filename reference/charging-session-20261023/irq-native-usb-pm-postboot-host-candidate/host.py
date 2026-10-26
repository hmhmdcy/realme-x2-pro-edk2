"""Current forward/recovery postboot audit; reuse the original owned transport."""
from pathlib import Path
from contextlib import contextmanager
import argparse, base64, hashlib, importlib.util, inspect, json, os, sys
if sys.flags.optimize: raise RuntimeError('nonoptimized Python required')
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
DEVICE = HERE.parent / 'irq-native-usb-pm-postboot-device-candidate'
PEER = 'fe80::62:bcff:fe28:a101%29'
CAMERA = '1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
BOOT = 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
sha = lambda raw: hashlib.sha256(raw).hexdigest()

def need(value, message):
    if not value: raise ValueError(message)

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def read_json(path): return json.loads(Path(path).read_bytes())
def local(value):
    text = str(value).replace('\\', '/')
    return Path('/mnt/e/' + text[3:] if os.name != 'nt' and text.startswith('E:/') else text)

PROFILE = load(REF / 'charging-oem-audit-20261023/irq-postboot-compressed-profile/profile.py', 'pm_postboot_owned_transport')
ORIGINAL = load(REF / 'charging-oem-audit-20261023/irq-cohort-postboot-host-candidate/host.py', 'pm_postboot_original_host')

def source_check():
    PROFILE.check_sources()
    need(sha((DEVICE / 'delivery.json').read_bytes()) == '0e8aa940cec2bdcd20570bd43bbf32aa3b8ce109a0bb3a43a1b4db0818d050d4', 'current device delivery changed')
    for name, row in read_json(DEVICE / 'delivery.json')['files'].items():
        need(sha((DEVICE / name).read_bytes()) == (row['sha256'] if isinstance(row, dict) else row), 'device source changed: ' + name)
    return True

def transport_argv(endpoint, *, collection=False):
    return PROFILE.host_module().transport_argv(endpoint, collection=collection)

# Exact original same-child/stdin/output/terminal authentication, no spawning.
exec(compile(inspect.getsource(ORIGINAL.saved_transport), '<original-saved-transport>', 'exec'), globals())

@contextmanager
def recovery_modules():
    directory = HERE.parent / 'irq-native-usb-pm-rollback-restart-host-candidate'
    before = {key: sys.modules.get(key) for key in ('sources', 'proof')}
    try:
        sources = load(directory / 'sources.py', 'pm_postboot_recovery_sources'); sys.modules['sources'] = sources
        load(HERE / 'rollback-profile.py', 'pm_path_recovery_profile').recovery_sources(sources)
        proof = load(directory / 'proof.py', 'pm_postboot_recovery_proof'); sys.modules['proof'] = proof
        operator = load(directory / 'fastboot-operator.py', 'pm_postboot_recovery_operator')
        yield operator, proof
    finally:
        for key, value in before.items():
            if value is None: sys.modules.pop(key, None)
            else: sys.modules[key] = value

def completed(context_path):
    source_check(); path = local(context_path).resolve(); context = read_json(path)
    saved = load(HERE.parent / 'irq-native-usb-pm-rollback-host-candidate/saved-proof.py', 'pm_postboot_saved_commands')
    if context['schema'] == 'samurai-irq-native-usb-pm-fastboot-context-v1':
        profile = 'forward_504'
        saved.OPERATOR_PATH = HERE / 'fastboot-operator.py'
        source = saved.review_profile_sources('booted_504_new_resident', context['stage_directory'], context['stage_fetch_directory'], path)
        result_raw = (local(context['stage_fetch_directory']) / 'raw/result.json').read_bytes()
        projection = source['source_stage']
        need(sha(result_raw) == projection['result_sha256'] == projection['evidence']['result']['sha256'], 'original stage result changed')
        # Use the original reference parser, including regular-path/hash checks.
        operator = saved.operator_for_past_context({'stage': projection}, context['stage_directory'], context['stage_fetch_directory'])
        guard_path = operator.reference_file(path.parent, context['files']['guard'])
    elif context['schema'] == 'samurai-irq-native-usb-pm-rollback-fastboot-context-v1':
        profile = 'restored_502'
        with recovery_modules() as (wrapper, proof):
            checked = wrapper.validate_context(path); need(checked == context, 'saved recovery context changed')
            operator = wrapper.owner(); base = path.parent / 'fastboot-operator'
            operator.prior_terminal(base, 'inspect')
            saved.OPERATOR_PATH = Path(wrapper.__file__)
            flash = saved.review_action(operator, path, context, 'rollback-original')
            reboot = saved.review_action(operator, path, context, 'reboot-original')
            need(flash['claimed_ns'] < reboot['claimed_ns'], 'restore must precede reboot')
            need(not any((base / name).exists() for name in ('flash-candidate', 'reboot-candidate')), 'recovery has opposing action')
            review = proof.review_completed(context['rollback_directory'], context['rollback_fetch_directory'], context['post_restore_probe_directory'])
            result_raw = (local(context['rollback_fetch_directory']) / 'raw/result.json').read_bytes()
            need(sha(result_raw) == review['result_sha256'] and json.loads(result_raw) == review['result'], 'original rollback result changed')
            guard_path = operator.reference_file(path.parent, context['files']['guard'])
    else: raise ValueError('unsupported actual activation context')
    guard_raw = guard_path.read_bytes(); guard = json.loads(guard_raw); result = json.loads(result_raw)
    need(sha(guard_raw) == context['guard_sha256'] and guard['boot_id'] == context['old_boot_id'], 'actual guard binding changed')
    actual = dict(profile=profile, context=context, guard=guard, context_sha256=sha(path.read_bytes()), guard_sha256=sha(guard_raw),
                  source_boot_id=guard['boot_id'], activation_transaction_id=context['transaction_id'],
                  saved_activation_commands_verified=True, partitions_written=['logdump'])
    return actual, dict(transaction_id=result['transaction_id'], stage_result=result, result_sha256=sha(result_raw))

def device_module(): return load(DEVICE / 'device.py', 'pm_postboot_current_audit')

def collection_guard(actual, stage):
    g = actual['guard']; row = device_module().PROFILES[actual['profile']]
    return dict(transaction_id=stage['transaction_id'], boot_id=g['boot_id'], kernel_release=g['kernel_release'],
                source_kernel_version=g.get('source_kernel_version', g['kernel_version']), target_kernel_version=row['version'],
                rootfs_release_sha256=g['rootfs_release_sha256'], soc_serial_sha256=g['soc_serial_sha256'],
                compatible_sha256=g['compatible_sha256'], candidate_boot_sha256=BOOT, partitions=['logdump'],
                candidate_logdump_sha256=row['logdump'], image_sha256=row['image'])

def envelope(name, request, source): return (name + '=' + repr(request) + '\n').encode() + source

def probe_request(actual, stage, endpoint):
    need(endpoint == PEER, 'original-key endpoint required')
    return dict(schema='samurai-irq-native-usb-pm-postboot-identity-probe-v1', profile=actual['profile'], new_endpoint=endpoint,
                activation_transaction_id=actual['activation_transaction_id'], context_sha256=actual['context_sha256'],
                guard_sha256=actual['guard_sha256'], guard=collection_guard(actual, stage))

def probe_payload(context_path, endpoint):
    actual, stage = completed(context_path)
    return envelope('PROBE_REQUEST', probe_request(actual, stage, endpoint), (DEVICE / 'identity-probe.py').read_bytes())

def review_probe(context_path, probe_directory):
    actual, stage = completed(context_path); expected = probe_request(actual, stage, PEER)
    payload = envelope('PROBE_REQUEST', expected, (DEVICE / 'identity-probe.py').read_bytes())
    stdout, _, terminal = saved_transport(probe_directory, payload, PEER)
    need(terminal['returncode'] == 0 and terminal.get('primary_error') is None and not terminal.get('cleanup_errors'), 'probe transport not clean terminal0')
    report = json.loads(stdout); need(report['schema'] == expected['schema'] and report['request'] == expected, 'probe binding differs')
    probe = load(DEVICE / 'identity-probe.py', 'pm_postboot_probe_audit'); probe.EXPECTED_VERSION = probe.PROFILES[actual['profile']]
    before, after = report['identity_before'], report['identity_after']
    probe.check_identity(before, expected['guard']); probe.check_identity(after, expected['guard'])
    need(before == after and 0 < report['started_boottime_ns'] <= report['ended_boottime_ns'], 'probe boot/time bracket changed')
    return dict(actual=actual, stage=stage, new_boot_id=before['boot_id'], endpoint=PEER, report=report,
                stdout_sha256=sha(stdout), payload_sha256=sha(payload), terminal_sha256=sha((Path(probe_directory) / 'terminal-private.json').read_bytes()))

def make_request(context_path, camera_path, probe_directory):
    proof = review_probe(context_path, probe_directory); actual, stage = proof['actual'], proof['stage']
    camera_raw = Path(camera_path).read_bytes(); need(sha(camera_raw) == CAMERA, 'formal camera481 baseline changed')
    camera = json.loads(camera_raw); need(camera['validated'] is True, 'camera baseline unvalidated')
    guard = collection_guard(actual, stage); guard['new_boot_id'] = proof['new_boot_id']
    request = dict(schema='samurai-irq-native-usb-pm-postboot-readonly-v1', profile=actual['profile'], new_endpoint=PEER,
                   original_key_transport_verified=True, context_sha256=actual['context_sha256'], guard_sha256=actual['guard_sha256'],
                   guard=guard, stage=stage['stage_result'], stage_result_sha256=stage['result_sha256'], camera=camera,
                   activation_transaction_id=actual['activation_transaction_id'], activation_guard=actual['guard'], new_boot_id=proof['new_boot_id'],
                   identity_probe={key: proof[key] for key in ('stdout_sha256', 'payload_sha256', 'terminal_sha256')})
    device_module().validate_request(request)
    return request

def make_payload(request):
    source_check(); device_module().validate_request(request)
    return envelope('POSTBOOT_REQUEST', request, (DEVICE / 'device.py').read_bytes())

# Retain exact original atomic binding and complete raw-audit recomputation.
for function in (ORIGINAL.bind, ORIGINAL.evaluate_response):
    text = inspect.getsource(function)
    if function.__name__ == 'evaluate_response':
        text = text.replace("need(report['schema'] == request['schema']", "need(report['profile'] == request['profile'] and report['schema'] == request['schema']")
    exec(compile(text, '<original-' + function.__name__ + '>', 'exec'), globals())

def probe(context, output):
    code = probe_payload(context, PEER); out = PROFILE.output_path(context, output); out.mkdir(mode=0o700)
    PROFILE.send_readonly(out, code); return review_probe(context, out)

def collect(context, camera, probe_directory, output):
    out = PROFILE.output_path(context, output); bind(out, context, camera, probe_directory)
    PROFILE.send_readonly(out, (out / 'device-payload-private.py').read_bytes(), collection=True)
    result = evaluate_response(context, camera, probe_directory, out)
    (out / 'review-private.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('action', nargs='?', default='check-local', choices=['check-local', 'probe', 'collect'])
    for name in ('context', 'camera', 'probe-directory', 'output'): p.add_argument('--' + name)
    a = p.parse_args(); source_check()
    if a.action == 'check-local': result = dict(source_checked=True, device_accessed=False)
    elif a.action == 'probe': result = {'new_boot_verified': bool(probe(a.context, a.output)['new_boot_id'])}
    else: result = collect(a.context, a.camera, a.probe_directory, a.output)
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
