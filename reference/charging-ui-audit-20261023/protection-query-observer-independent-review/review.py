"""Read-only source/receipt binding; does not invoke author tests or builds."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
AUTHOR = REF / 'charging-oem-audit-20261023/protection-query-observer-candidate'
BASE = REF / 'charging-session-20261023/r8-source-integration/kernel-sources/drivers/power/supply'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise RuntimeError(message)

def function(source, name):
    match = re.search(r'^static\s+[^;{}]*\b' + re.escape(name) + r'\([^;{}]*\)\s*\{', source, re.M)
    require(match is not None, 'definition missing: ' + name)
    start = source.index('{', match.start())
    end, depth = start + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[match.start():end]

pins = {
    'delivery.json': '907fc1245576eee21b3d5231c25359f6d101e1f537ea8ff423ee21139392a304',
    'samurai-gauge-protection.c': '3e1e81a341a5df072cde2c57ec7505096c192e7b873cfbb2720375ae7f9b8f6d',
    'test-result.json': '6ed3a351b01b1bf2b75586348b3a87aca62ec0170a86aa30ee62a1baac721033',
    'build-result.json': 'a761f9ec3a0d37b1f9507e1fa9bb53fc3e4d2d8bc71ae4b9f998e6aa5702e567',
}
for name, expected in pins.items():
    require(digest(AUTHOR / name) == expected, 'frozen input changed: ' + name)
delivery = json.loads((AUTHOR / 'delivery.json').read_bytes())
for name, entry in delivery['files'].items():
    require(digest(AUTHOR / name) == entry['sha256'], 'delivery file hash: ' + name)
    require((AUTHOR / name).stat().st_size == entry['bytes'], 'delivery file size: ' + name)

sources = {name: (AUTHOR / name).read_text() for name in
           ['samurai-gauge-protection.c', 'gauge-i2c.h', 'gauge-protocol.h']}
source_pins = json.loads((AUTHOR / 'source-pins.json').read_bytes())
unchanged = {}
for key, expected in delivery['unchanged_actual_normal_functions'].items():
    name, func = key.split('::')
    require(digest(BASE / name) == source_pins[name]['sha256'], 'baseline hash: ' + name)
    old = function((BASE / name).read_text(), func)
    new = function(sources[name], func)
    require(new == old, 'normal function changed: ' + key)
    require(hashlib.sha256(new.encode()).hexdigest() == expected, 'function hash: ' + key)
    unchanged[key] = expected

test = json.loads((AUTHOR / 'test-result.json').read_bytes())
build = json.loads((AUTHOR / 'build-result.json').read_bytes())
for name, expected in test['tested_files'].items():
    require(digest(AUTHOR / name) == expected, 'tested source hash: ' + name)
provider = sources['samurai-gauge-protection.c']
names = ['sm_protection_read', 'sm_protection_capture_locked',
         'mac_evidence_capture_store', 'mac_evidence_show']
decl = provider[provider.index('static const unsigned int sm_evidence_commands'):
                provider.index('static struct platform_device *sm_board;')]
actual = decl + '\n' + '\n\n'.join(function(provider, n) for n in names) + '\n'
require(hashlib.sha256(actual.encode()).hexdigest() == test['actual_function_source_sha256'],
        'tested extracted actual function source')
for name in names:
    require(hashlib.sha256(function(provider, name).encode()).hexdigest() ==
            test['actual_functions'][name], 'tested function: ' + name)
require(test['passed'] and test['actual']['passed'] and
        test['actual']['actual_function_cases'] == 21 and
        test['compile_returncode'] == test['run_returncode'] == 0,
        'author test terminal receipt')
require(build['passed'] and build['returncode'] == 0 and build['owned_child_waited'] and
        build['only_private_object'] and not build['diagnostics'] and
        build['shared_original_inputs_unchanged'], 'author object terminal receipt')
require(build['test_receipt_sha256'] == digest(AUTHOR / 'test-result.json'), 'build/test binding')
require(build['builder_sha256'] == digest(AUTHOR / 'build-object.py'), 'builder binding')
for name, expected in build['source_sha256'].items():
    require(digest(AUTHOR / name) == expected, 'compiled source binding: ' + name)
require(build['object_sha256'] == delivery['object_sha256'] ==
        '939aee637dc018b8326a7efe5c5e4098bb9cc903eaf651dd0aefff6d0afa1965', 'object receipt binding')
require('-Werror' in build['command'] and '-DKBUILD_EXTRA_WARN1' in build['command'] and
        build['command'][-4:-2] == ['-c', '-o'], 'single W1/Werror object command')

result = {
    'schema': 'samurai-protection-query-observer-independent-review-v1',
    'passed': True,
    'conclusion': 'No new blocking issue found in the frozen observer scope by static review and receipt binding.',
    'reviewer_source_sha256': digest(Path(__file__)),
    'author_pins': pins,
    'delivery_files_verified': len(delivery['files']),
    'normal_functions_byte_exact': unchanged,
    'actual_extracted_test_source_sha256': test['actual_function_source_sha256'],
    'author_existing_evidence': {
        'actual_cases': 21,
        'six_old_real_packet_fixtures': 6,
        'new_three_status_replies_synthetic': True,
        'compile_returncode': 0,
        'test_returncode': 0,
        'private_object_returncode': 0,
        'private_object_sha256': build['object_sha256'],
        'object_binary_independently_reread': False,
    },
    'static_findings': [
        'Normal six-command allowlist, protection classification and normal Health/probe/lifetime functions remain unchanged; common transfer/validation refactor preserves the prior call sequence and error handling.',
        'Only explicit root-writable fixed capture selects the additional 0050/0052/0056 commands; no selector comes from sysfs text and no probe/poll/normal Health path calls the observer.',
        'The attempt is consumed before I/O, under p.lock. Complete validated 0001 identity must equal 2719 before BatteryStatus or remaining status queries.',
        'Lock order is p.lock then one adapter segment lock; the held segment uses only __i2c_smbus_xfer and __i2c_transfer, with no recursive adapter-locking API.',
        'First selection/transport/validation failure terminates the sequence. Exactly two returned messages authorize full_read; complete invalid frames remain available and incomplete transfers are explicitly unavailable.',
        'New mac_evidence show holds p.lock and reads only cached evidence. Existing protection_state show intentionally remains its old fresh-I/O interface.',
        'Capture writes only the existing 3e read-query selector, preserving its 1000..1500us wait; no NVM, FET, unseal, PF-enable or REG14 operation is added.',
        'Capture does not update normal health fields, last_error, latches or policy; complete/error=0 does not compare the two BatteryStatus values or claim compatibility/stability.',
    ],
    'review_actions': {
        'author_entrypoints_run': False,
        'tests_rerun': False,
        'compiler_or_linker_run': False,
        'old_codec149_rerun': False,
        'phone_SSH_USB_SDK_Git_or_storage_accessed': False,
        'author_files_modified': False,
    },
    'limits': [
        'Static source/receipt review is not real-pack protocol compatibility, TCA classification, Full/Charging policy or hardware acceptance.',
        'One attempt per bound instance is not a hard time limit; the synchronous adapter transaction and scheduling can still block normal provider readers.',
        'No new ko or deployment manifest exists; the compiled object receipt does not establish ABI, linked-module identity, installation or live results.',
        'No extra retry is implemented in this observer; adapter-core/hardware behavior is outside these fake I2C boundaries.',
    ],
}
(HERE / 'review-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'passed': True, 'delivery_files_verified': len(delivery['files']),
                  'normal_functions_byte_exact': len(unchanged),
                  'review_result_sha256': digest(HERE / 'review-result.json')}))
