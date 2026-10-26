"""Local-only request binding from a completed real Image502 adoption."""
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

sys.dont_write_bytecode = True
if sys.flags.optimize:
    raise RuntimeError('non-optimized Python required')
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
ADOPT_SOURCE = REF / 'charging-oem-audit-20261023/image502-adoption-candidate/adopt.py'
ADOPT_SHA = '1af20988d81b439348e5e04ceb477937faaf78944103134232167dc7463e93e3'
POST_SOURCE = REF / 'charging-oem-audit-20261023/image502-postboot-readonly/device.py'
POST_SHA = '8da495324ea341714f193d8406ec860a93733971599f2c50e8c51c7a88ba4ab2'
LIVE_SOURCE = REF / 'charging-management-20261023/live-session.py'
LIVE_SHA = '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
BASE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023')
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def source_check():
    for path, expected in [(ADOPT_SOURCE, ADOPT_SHA), (POST_SOURCE, POST_SHA), (LIVE_SOURCE, LIVE_SHA)]:
        body = path.read_bytes()
        if sha(body) != expected:
            raise ValueError('frozen input source changed: ' + str(path))
        ast.parse(body)
    if sha((HERE / 'pm-transaction.py').read_bytes()) != 'fd3fd4bef1e04dc8a29b5240cad8989d700021e353e081c0fcf0b297e4bda0a1':
        raise ValueError('primitive differs')
    for name in ['worker.py', 'trace-evidence.py', 'prepare-request.py']:
        ast.parse((HERE / name).read_bytes())


def adoption_module():
    source_check()
    spec = importlib.util.spec_from_file_location('reviewed_pm_adoption', ADOPT_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build_request(context, postboot, adoption, transaction, output_root, *, reviewer=None, pointer=None):
    """No network or device access. Tests inject only the reviewed-file boundary."""
    if not re.fullmatch(r'charging-pm-current-[a-z0-9][a-z0-9-]{0,32}', transaction):
        raise ValueError('unique new PM transaction required')
    if not Path(output_root).is_absolute():
        raise ValueError('absolute existing remote output parent required')
    module = reviewer if reviewer is not None else adoption_module()
    d, sources = module.review(context, postboot)  # actual seven-raw + collector audit
    a = Path(adoption).resolve()
    if a != Path(context).resolve().parent / 'adoption-01-private':
        raise ValueError('adoption must belong to the same actual transaction')
    facts = {}
    def read(name, path):
        raw = Path(path).read_bytes()
        facts[name] = {'path': str(Path(path).resolve()), 'sha256': sha(raw)}
        return json.loads(raw)
    actual = read('adopt_request', a / 'adopt-request-private.json')
    if actual != d:
        raise ValueError('adoption request differs from reviewed postboot originals')
    result = read('adopt_result', a / 'adoption-result-private.json')
    terminal = read('adopt_terminal', a / 'adopt-transport-terminal-private.json')
    reply = read('adopt_reply', a / 'adopt-stdout-private.json')
    endpoint = read('endpoint', a / 'new-endpoint-private.json')
    current = read('current_pointer', pointer if pointer is not None else BASE / 'boot-adoption-private.json')
    if not (result.get('passed') is True and result.get('guard_created') is True
            and result.get('old_pointer_backup_preserved') is True and result.get('old_guards_preserved') is True
            and terminal.get('terminal') is True and terminal.get('returncode') == 0 and type(terminal.get('pid')) is int
            and terminal['pid'] > 0):
        raise ValueError('actual adoption terminal/success evidence missing')
    for key, value in {'guard_created': True, 'fresh_validation_passed': True,
                       'boot_and_logdump_verified': True, 'transaction_id': d['transaction_id'],
                       'boot_id': d['boot'], 'guard': d['guard'],
                       'postboot_raw_sha256': d['postboot_raw_sha256']}.items():
        if reply.get(key) != value:
            raise ValueError('actual adoption reply differs: ' + key)
    expected = {'guard_path': d['guard'], 'Image502_verified': True, 'original_key_verified': True,
                'baseline481_verified': True, 'charging_manifest_sha256': d['manifest'],
                'candidate_boot_sha256': d['candidate_boot_sha256'],
                'candidate_logdump_sha256': d['candidate_logdump_sha256'],
                'postboot_raw_sha256': d['postboot_raw_sha256']}
    if current != expected or result.get('pointer') != current:
        raise ValueError('current adopted pointer is not this completed Image502 adoption')
    if not (endpoint.get('postboot_Image502_passed') is True and endpoint.get('observed_new_boot') == d['boot']
            and endpoint.get('guard_path') == d['guard'] and endpoint.get('original_key_verified') is True
            and endpoint.get('peer') == 'fe80::62:bcff:fe28:a101%29' and endpoint.get('interface_index') == 29
            and endpoint.get('host_key_alias') == '169.254.42.1'):
        raise ValueError('adopted endpoint differs')
    # The original payload must be the exact one whose reviewed source produced this reply.
    payload = (a / 'executed-adoption-source.py').read_bytes()
    if payload != module.payload(d, sources):
        raise ValueError('executed adoption source differs')
    facts['executed_adoption_source'] = {'path': str(a / 'executed-adoption-source.py'), 'sha256': sha(payload)}
    if not d['version'].startswith('#502 ') or d['guard'] != '/var/lib/samurai/image502-notify-live-001-adopted/boot-id-private.txt':
        raise ValueError('not the real completed Image502 adoption')
    embedded = {}
    for name, path, expected_sha in [('postboot', POST_SOURCE, POST_SHA), ('live_state', LIVE_SOURCE, LIVE_SHA)]:
        body = path.read_bytes()
        if sha(body) != expected_sha:
            raise ValueError('reviewed embedded source changed')
        embedded[name] = {'sha256': expected_sha, 'base64': base64.b64encode(body).decode()}
    request = {'schema': 'samurai-pm-current-evidence-v1', 'transaction': transaction,
               'output_root': str(output_root), 'adopted': d, 'pointer': current, 'provenance': facts,
               'sources': embedded,
               'bundle_sha256': {name: sha((HERE / name).read_bytes()) for name in ['worker.py', 'trace-evidence.py', 'pm-transaction.py']},
               'required_console_and_RTC_observation': True,
               'alarm_delay_seconds': 15, 'whole_system_acceptance_authority': 'root with synchronized host/data evidence'}
    return request


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bind-request', action='store_true')
    for key in ['context', 'postboot-directory', 'adoption-directory', 'transaction', 'output-root', 'output']:
        p.add_argument('--' + key)
    a = p.parse_args()
    source_check()
    if not a.bind_request:
        print(json.dumps({'local_sources_checked': True, 'runtime_request_created': False, 'device_accessed': False}))
        return
    request = build_request(a.context, a.postboot_directory, a.adoption_directory, a.transaction, a.output_root)
    target = Path(a.output)
    if not target.is_absolute():
        raise ValueError('absolute new private request path required')
    with target.open('x') as stream:
        json.dump(request, stream, indent=2)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    print(json.dumps({'request_sha256': sha(target.read_bytes()), 'device_accessed': False}))


if __name__ == '__main__':
    main()
