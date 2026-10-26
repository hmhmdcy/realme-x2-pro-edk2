"""Bind saved terminal facts without re-executing extraction or scanning data."""
from pathlib import Path
import hashlib
import json
import os

HERE = Path(__file__).resolve().parent
PRIVATE = Path('E:/edk2-samurai-out/charging-oem-audit-20261023/gauge-2719-vendor-extract-private-01')
SOURCE = '4639f6b8ceead1fc6aa335f7f938ff38b120706766cc234141428394989a6d5b'
RESULT = '9aa75a2d5bac3c2bd34b27ccfd0a3c4b9949dbc45dadbb3cca7136814b4c4000'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())

def main():
    assert digest(HERE / 'delivery.json') == SOURCE
    source = json.loads((HERE / 'delivery.json').read_bytes())
    assert source['passed'] and len(source['files']) == 8
    for name, expected in source['files'].items():
        p = HERE / name
        assert {'sha256': digest(p), 'bytes': p.stat().st_size} == expected, name
    assert digest(PRIVATE / 'result-private.json') == RESULT
    r = json.loads((PRIVATE / 'result-private.json').read_bytes())
    owner = json.loads((HERE / 'execution-receipt.json').read_bytes())
    node = json.loads((PRIVATE / 'node-stdout-private.json').read_bytes())
    assert r['passed'] is True and r['decoded'] == node and node['passed'] is True
    assert owner['original_exec_session_id'] == 91865
    assert owner['original_exec_terminal'] is True and owner['original_exec_exit_code'] == 0
    assert r['pid'] == owner['original_python_pid'] == 223208
    assert r['node_command']['pid'] == owner['original_node_pid'] == 212548
    assert r['node_command']['terminal'] is True and r['node_command']['returncode'] == 0
    assert r['plan_sha256'] == owner['private_plan_sha256'] == digest(PRIVATE / 'plan-private.json')
    assert r['compressed']['EOF_and_ZIP_CRC_checked'] is True
    assert r['compressed']['bytes'] == node['input_bytes'] == node['engine_bytes_written'] == 699830594
    assert r['compressed']['crc32'] == '43496d61'
    assert r['compressed']['sha256'] == node['input_sha256'] == 'c4e6c9808451f180dce0ea94a80bb34870df1f94996d99ce0ccaab0531c29246'
    assert node['output_forwarded_bytes'] == node['output_file_bytes'] == r['image']['new_bytes_consumed'] == 1613049856
    assert node['output_sha256'] == r['image']['new_sha256'] == '6238599745f01afc1fa3df5a20ff57bacbc852d681ff288e9f81ff46f7c9a29e'
    assert r['image']['EOF_checked'] is True
    assert r['image']['bytes'] == 1711276032
    assert r['image']['sha256'] == '905a0f0477b1edcd686fa059bfedc9aea79b6cc2107c472190d62f125abd7f0c'
    assert r['source_before'] == r['source_after']
    for key in ('source_stat_and_small_members_unchanged', 'tools_and_sources_unchanged'):
        assert r[key] is True
    assert r['source_whole_file_sha256_verified'] is False
    artifacts = {}
    for name, data in [('vendor.new.dat.br', r['compressed']), ('vendor.new.dat', {'bytes': node['output_file_bytes'], 'sha256': node['output_sha256']}), ('vendor.img', r['image'])]:
        path = PRIVATE / name; assert path.stat().st_size == data['bytes']
        artifacts[name] = {'path': path.as_posix(), 'bytes': data['bytes'], 'sha256': data['sha256']}
    result = {'schema': 'samurai-vendor-only-actual-extract-v1', 'passed': True,
        'original_exec_session_id': 91865, 'original_parent_pid': 223208, 'original_parent_terminal0': True,
        'original_node_pid': 212548, 'original_node_terminal0': True,
        'private_result_sha256': RESULT, 'source_delivery_sha256': SOURCE,
        'source_plan_eight_files_unchanged': True, 'artifacts': artifacts,
        'compressed_CRC32': r['compressed']['crc32'], 'compressed_EOF_CRC_verified': True,
        'node_input_bytes': node['input_bytes'], 'node_engine_bytesWritten': node['engine_bytes_written'],
        'node_output_bytes': node['output_file_bytes'], 'reconstruction_new_SHA_and_EOF_verified': True,
        'source_stat_and_small_members_unchanged': True, 'tools_and_sources_unchanged': True,
        'source_whole_file_hash_or_signature_verified': False,
        'reconstructed_filesystem_type_verified': False, 'pack_descriptor_or_2719_semantics_verified': False,
        'debugfs_indexer_or_device_accessed': False,
        'small_private_receipts': {name: digest(PRIVATE / name) for name in ('result-private.json', 'node-stdout-private.json', 'node-stderr-private.log', 'vendor.transfer.list')},
        'finalizer_artifact_sizes_rechecked': True, 'finalizer_rehashed_or_redecoded_large_payload': False}
    save_new(HERE / 'actual-result.json', result)
    files = list(source['files']) + ['delivery.json', 'execution-receipt.json', 'BUILD.md', 'freeze-actual.py', 'actual-result.json']
    delivery = {'schema': 'samurai-vendor-only-actual-delivery-v1', 'passed': True,
        'scope': 'single completed offline vendor extraction; not pack/model verification',
        'files': {name: {'sha256': digest(HERE / name), 'bytes': (HERE / name).stat().st_size} for name in files},
        'source_delivery_sha256': SOURCE, 'private_result_sha256': RESULT, 'artifacts': artifacts,
        'actual_parent_and_original_Node_terminal0': True, 'source_plan_eight_files_unchanged': True,
        'no_system_device_mount_SDK_storage_or_Git_action': True,
        'archive': {'explicit_source_text_json_whitelist': files, 'recursive_scan': False}}
    save_new(HERE / 'actual-delivery.json', delivery)
    print(json.dumps({'passed': True, 'actual_delivery_sha256': digest(HERE / 'actual-delivery.json'),
                      'actual_result_sha256': digest(HERE / 'actual-result.json'), 'image': artifacts['vendor.img']}))

if __name__ == '__main__':
    main()
