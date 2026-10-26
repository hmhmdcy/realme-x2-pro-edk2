"""Saved-evidence authentication and read-only payloads. No transport implementation."""
from pathlib import Path
import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import os
import re
import sys

if sys.flags.optimize:
    raise RuntimeError('optimized Python disables device checks')
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent
DEVICE = HERE.parent / 'irq-cohort-postboot-readonly'
OPERATOR = HERE.parent / 'usb-irq-protection-fastboot-candidate'
PEER = 'fe80::62:bcff:fe28:a101%29'
ALIAS = '169.254.42.1'
VERSION = '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
IRQ_BOOT = 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
LOGDUMP = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
IMAGE = '085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'
CAMERA = '1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def need(value, message):
    if not value:
        raise ValueError(message)


def local(value):
    text = str(value).replace('\\', '/')
    return Path('/mnt/e/' + text[3:] if os.name != 'nt' and text.startswith('E:/') else text)


def read_json(path):
    return json.loads(Path(path).read_bytes())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_check():
    pins = read_json(HERE / 'host-source-pins.json')
    need(set(pins) == {'stage_proof_frozen', 'stage_proof', 'device_delivery',
                      'operator_delivery', 'completion_proof', 'key_transport'}, 'host source set differs')
    for name, entry in pins.items():
        need(sha(local(entry['path']).read_bytes()) == entry['sha256'], 'source changed: ' + name)
    need(pins['stage_proof']['sha256'] == '85c9cd2b728a547ba434322d47cc15d4aeb228ae77afebeb7edff1bd0422e093', 'pure stage source differs')
    need(pins['device_delivery']['sha256'] == 'b2c1d2de692b2d302450b0debbfdd50221b84790523829dc57b5c96ba271689b', 'device R2/archive3 differs')
    need(pins['key_transport']['sha256'] == '7f49a922e0babf167c77ad6e9bd7edf63e437418d5134e3d081fb8a0082a4f4c', 'original key source differs')
    for name in ('device_delivery', 'operator_delivery'):
        path = local(pins[name]['path']); delivery = read_json(path)
        if name == 'operator_delivery':
            need(delivery['passed'] is True and delivery['frozen'] is True, 'operator is not frozen')
        for relative, info in delivery['files'].items():
            digest = info['sha256'] if isinstance(info, dict) else info
            need(sha((path.parent / relative).read_bytes()) == digest, 'delivery changed: ' + relative)
    stage = load(HERE / 'stage-proof.py', 'irq_postboot_stage_source')
    stage.source_check()
    for name in ('host.py', 'identity-probe.py'):
        ast.parse((HERE / name).read_bytes())
    return pins


def completed(context_path):
    source_check()
    completion = load(OPERATOR / 'completion-proof.py', 'irq_postboot_completed_activation')
    actual = completion.review_completed_activation(context_path)
    need(actual['schema'] == 'samurai-usb-irq-protection-completed-activation-review-v1'
         and actual['saved_activation_commands_verified'] is True
         and actual['partitions_written'] == ['boot']
         and actual['candidate_boot_sha256'] == IRQ_BOOT
         and actual['retained_logdump_sha256'] == LOGDUMP,
         'completed boot-only activation is required')
    context, guard = actual['context'], actual['guard']
    stage = load(HERE / 'stage-proof.py', 'irq_postboot_actual_stage')
    reviewed = stage.review_stage(local(context['stage_directory']), local(context['stage_fetch_directory']),
                                  expected_transaction=guard['stage']['transaction_id'])
    need(guard['stage'] == stage.guard_stage_fields(reviewed), 'source stage projection differs')
    need(actual['source_boot_id'] == reviewed['source_boot_id'] == guard['boot_id'], 'stage/activation source boot differs')
    return actual, reviewed


def collection_guard(actual, stage):
    """Collection projection only. Never changes or creates an activation guard."""
    guard = actual['guard']
    return {'transaction_id': stage['transaction_id'], 'boot_id': guard['boot_id'],
            'kernel_release': guard['kernel_release'], 'source_kernel_version': guard['kernel_version'],
            'rootfs_release_sha256': guard['rootfs_release_sha256'],
            'soc_serial_sha256': guard['soc_serial_sha256'], 'compatible_sha256': guard['compatible_sha256'],
            'candidate_boot_sha256': IRQ_BOOT, 'partitions': ['boot'],
            'candidate_logdump_sha256': LOGDUMP, 'image502_sha256': IMAGE}


def envelope(name, request, source):
    return (name + '=' + repr(request) + '\n').encode() + source


def probe_request(actual, stage, endpoint):
    need(endpoint == PEER, 'only root-observed original-key peer is supported')
    return {'schema': 'samurai-irq-postboot-identity-probe-v1', 'new_endpoint': endpoint,
            'activation_transaction_id': actual['activation_transaction_id'],
            'context_sha256': actual['context_sha256'], 'guard_sha256': actual['guard_sha256'],
            'guard': collection_guard(actual, stage)}


def probe_payload(context_path, endpoint):
    actual, stage = completed(context_path)
    return envelope('PROBE_REQUEST', probe_request(actual, stage, endpoint),
                    (HERE / 'identity-probe.py').read_bytes())


def transport_argv(endpoint, *, collection=False):
    need(endpoint == PEER, 'endpoint differs from original-key observed peer')
    pins = source_check()
    key = load(local(pins['key_transport']['path']), 'irq_postboot_original_key')
    command = ('python3 -B - --execute --window-confirmed --new-endpoint ' + endpoint
               if collection else 'python3 -')
    return [key.SSH, '-6', '-T', *key.OPTIONS, '-o', 'HostKeyAlias=' + ALIAS,
            'root@' + endpoint, command]


def saved_transport(directory, expected_payload, endpoint, *, collection=False):
    """Authenticate the one original Popen and its exact input/output; never spawn."""
    directory = Path(directory)
    need((directory / 'executed-device-source.py').read_bytes() == expected_payload,
         'executed original-key source/request differs')
    child = read_json(directory / 'child-private.json')
    terminal = read_json(directory / 'terminal-private.json')
    argv = transport_argv(endpoint, collection=collection)
    need(type(child.get('pid')) is int and child['pid'] > 0
         and type(child.get('start_ticks')) is int and child['start_ticks'] > 0
         and child['argv'] == argv, 'actual original-key child identity is required')
    need(terminal['pid'] == child['pid'] and terminal['start_ticks'] == child['start_ticks']
         and terminal['argv'] == argv and terminal['terminal'] is True
         and type(terminal['returncode']) is int, 'same original child terminal is required')
    stdout = (directory / 'stdout-private.json').read_bytes()
    stderr = (directory / 'stderr-private.txt').read_bytes()
    need(terminal['stdout_sha256'] == sha(stdout) and terminal['stderr_sha256'] == sha(stderr),
         'original strict-key output hash differs')
    return stdout, stderr, terminal


def device_module():
    # Linux imports are used only for pure audit after binding; no main/collect.
    return load(DEVICE / 'device.py', 'irq_postboot_actual_device_audit')


def review_probe(context_path, probe_directory):
    actual, stage = completed(context_path)
    expected = probe_request(actual, stage, PEER)
    payload = envelope('PROBE_REQUEST', expected, (HERE / 'identity-probe.py').read_bytes())
    stdout, _, terminal = saved_transport(probe_directory, payload, PEER)
    need(terminal['returncode'] == 0 and terminal.get('primary_error') is None
         and not terminal.get('cleanup_errors'), 'identity probe transport did not terminate cleanly')
    report = json.loads(stdout)
    need(report['request'] == expected and report['schema'] == expected['schema'], 'identity probe binding differs')
    device = device_module()
    before, after = report['identity_before'], report['identity_after']
    device.check_identity(before, expected['guard']); device.check_identity(after, expected['guard'])
    need(before['boot_id'] == after['boot_id'], 'boot changed during identity probe')
    need(type(report['started_boottime_ns']) is int and type(report['ended_boottime_ns']) is int
         and 0 < report['started_boottime_ns'] <= report['ended_boottime_ns'], 'probe time order differs')
    return {'actual': actual, 'stage': stage, 'new_boot_id': before['boot_id'],
            'endpoint': PEER, 'report': report, 'stdout_sha256': sha(stdout),
            'payload_sha256': sha(payload), 'terminal_sha256': sha((Path(probe_directory) / 'terminal-private.json').read_bytes())}


def make_request(context_path, camera_path, probe_directory):
    proof = review_probe(context_path, probe_directory)
    actual, stage = proof['actual'], proof['stage']
    raw = Path(camera_path).read_bytes()
    need(sha(raw) == CAMERA, 'camera481 exact source is required')
    camera = json.loads(raw); need(camera['validated'] is True, 'camera481 formal baseline is not validated')
    return {'schema': 'samurai-usb-irq-protection-postboot-readonly-v1',
            'new_endpoint': proof['endpoint'], 'original_key_transport_verified': True,
            'context_sha256': actual['context_sha256'], 'guard_sha256': actual['guard_sha256'],
            'guard': collection_guard(actual, stage), 'stage': stage['stage_result'],
            'stage_result_sha256': stage['result_sha256'], 'camera': camera,
            'activation_transaction_id': actual['activation_transaction_id'],
            'activation_guard': actual['guard'], 'new_boot_id': proof['new_boot_id'],
            'identity_probe': {key: proof[key] for key in ('stdout_sha256', 'payload_sha256', 'terminal_sha256')}}


def make_payload(request):
    source_check()
    return envelope('POSTBOOT_REQUEST', request, (DEVICE / 'device.py').read_bytes())


def bind(out, context_path, camera_path, probe_directory):
    # Every actual source/activation/stage/new endpoint proof is reviewed before
    # checking/creating an output directory. No future materials are invented.
    request = make_request(context_path, camera_path, probe_directory)
    payload = make_payload(request)
    out = Path(out)
    need(out.is_absolute() and not out.exists(), 'new absolute private output is required')
    mask = os.umask(0o077)
    try:
        out.mkdir(mode=0o700)
        rows = {'request-private.json': (json.dumps(request, indent=2) + '\n').encode(),
                'device-payload-private.py': payload}
        for name, raw in rows.items():
            with (out / name).open('xb') as file:
                file.write(raw); file.flush(); os.fsync(file.fileno())
    finally:
        os.umask(mask)
    return {'request_sha256': sha(rows['request-private.json']), 'payload_sha256': sha(payload),
            'collection_transaction_id': request['guard']['transaction_id'],
            'activation_transaction_id': request['activation_transaction_id'],
            'new_boot_id': request['new_boot_id'], 'guard_created': False, 'device_accessed': False}


def evaluate_response(context_path, camera_path, probe_directory, capture_directory):
    """Read retained raw even when the collector failed; no recovery/control."""
    request = make_request(context_path, camera_path, probe_directory)
    payload = make_payload(request)
    stdout, _, terminal = saved_transport(capture_directory, payload, PEER, collection=True)
    public = {'passed': False, 'transport_returncode': terminal['returncode'],
              'guard_created': False, 'hardware_writes': 0, 'raw_retained': True,
              'physical_delivery_or_latency_accepted': False, 'device_or_transport_accessed': False}
    report = json.loads(stdout)
    need(report['schema'] == request['schema'] and report['transaction_id'] == request['guard']['transaction_id']
         and report['context_sha256'] == request['context_sha256']
         and report['guard_sha256'] == request['guard_sha256'], 'collector result binding differs')
    if 'collection_error' in report['result']:
        need(report['result'].get('passed') is False, 'collection failure cannot claim success')
        public['collection_error'] = report['result']['collection_error']
        public['message'] = report['result'].get('message')
        return public
    # Recompute from raw through the frozen actual device audit, rather than
    # accepting the device's passed label or an invented subset of the checks.
    actual = device_module().audit(report['raw'], request)
    need(report['result'] == actual, 'device result differs from actual frozen raw audit')
    need(report['raw']['identity_before']['boot_id'] == request['new_boot_id']
         and report['raw']['identity_after']['boot_id'] == request['new_boot_id'],
         'collector did not retain the actually probed new boot')
    public['checks'] = actual['checks']; public['errors'] = actual['errors']
    public['passed'] = (terminal['returncode'] == 0 and terminal.get('primary_error') is None
                        and not terminal.get('cleanup_errors') and actual['passed'] is True)
    return public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-local', action='store_true')
    parser.parse_args()
    source_check()
    print(json.dumps({'source_only': True, 'source_stage_or_activation_reviewed': False,
                      'runtime_request_generated': False, 'device_or_transport_accessed': False}))


if __name__ == '__main__':
    main()
