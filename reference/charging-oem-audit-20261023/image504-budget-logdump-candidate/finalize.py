"""Read-only final binding of the single completed private FAT execution."""
from pathlib import Path
import hashlib
import json
import os

HERE = Path(__file__).resolve().parent
PRIVATE = Path('E:/edk2-samurai-out/charging-management-20261023/image504-budget-logdump-private-01')
SOURCE_SHA = 'fd7cdc02ac1630d4d69ec3edeb3e4bc0322110e18635b829a4a1a1289910ae8c'
RESULT_SHA = 'f1cdce8c66bf3a1c670a64ee1306f5af56efc79ad142f950364b0c311bad938d'
IMAGE = 'f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'
ROLLBACK = 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
CANDIDATE = '4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83'

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while data := f.read(1024 * 1024):
            h.update(data)
    return h.hexdigest()

def info(path):
    return {'sha256': digest(path), 'bytes': path.stat().st_size}

def read(path):
    return json.loads(path.read_bytes())

def windows(path):
    assert path.startswith('/mnt/e/')
    return Path('E:/' + path[len('/mnt/e/'):])

def main():
    assert digest(HERE / 'source-delivery.json') == SOURCE_SHA
    source = read(HERE / 'source-delivery.json')
    assert source['passed'] and len(source['files']) == 10
    for name, expected in source['files'].items():
        assert info(HERE / name) == expected, name
    assert digest(HERE / 'logdump-result.json') == RESULT_SHA
    result = read(HERE / 'logdump-result.json')
    private = read(PRIVATE / 'result.json')
    owner = read(HERE / 'execution-receipt.json')
    assert result['passed'] is True and private['passed'] is True
    assert owner['original_exec_session_id'] == 47694
    assert owner['original_exec_terminal'] is True and owner['original_exec_exit_code'] == 0
    assert private['host_linux_pid'] == owner['packager_pid'] == 579
    assert result['private_result_sha256'] == owner['private_result_sha256'] == digest(PRIVATE / 'result.json')
    assert owner['public_result_sha256'] == RESULT_SHA
    actual = [{key: cmd[key] for key in ('stage', 'pid', 'terminal', 'returncode')} for cmd in private['commands']]
    assert actual == owner['original_tools']
    assert len(actual) == 3 and all(cmd['terminal'] is True and cmd['returncode'] == 0 for cmd in actual)
    assert result['commands_sha256'] == hashlib.sha256(json.dumps(private['commands'], sort_keys=True).encode()).hexdigest()
    for key in ('only_Image_file_changed', 'other_entries_and_contents_exact',
                'all_non_Image_bytes_exact', 'Image_readback_exact', 'fsck_readonly_passed',
                'parent_inputs_unchanged', 'parent_mountinfo_unchanged', 'no_device_or_deployment'):
        assert result[key] is True, key
    assert private['inputs_before'] == private['inputs_after']
    assert result['actual_phone_502_adoption_claimed'] is False
    assert result['Image504_sha256'] == result['Image504']['sha256'] == IMAGE
    assert result['Image504']['bytes'] == 59243008
    assert result['rollback_logdump_sha256'] == result['rollback']['sha256'] == ROLLBACK
    assert result['candidate']['sha256'] == result['logdump_sha256'] == CANDIDATE
    assert result['candidate']['bytes'] == result['logdump_bytes'] == 67108864
    assert result['candidate']['path'] == result['logdump_path']
    candidate = windows(result['candidate']['path'])
    rollback = windows(result['rollback']['path'])
    assert candidate.resolve() == (PRIVATE / 'logdump-image504-private.img').resolve()
    assert info(candidate) == {'sha256': CANDIDATE, 'bytes': 67108864}
    assert info(rollback) == {'sha256': ROLLBACK, 'bytes': 67108864}
    assert info(PRIVATE / 'Image-readback') == {'sha256': IMAGE, 'bytes': 59243008}
    for name, expected in private['artifacts'].items():
        assert digest(PRIVATE / name) == expected, name
    files = list(source['files']) + ['source-delivery.json', 'logdump-result.json',
                                    'execution-receipt.json', 'BUILD.md', 'finalize.py']
    delivery = {
        'schema': 'samurai-image504-budget-logdump-completed-v1',
        'passed': True,
        'scope': 'private saved-candidate502 FAT Image504 replacement; not deployed',
        'files': {name: info(HERE / name) for name in files},
        'source_delivery_sha256': SOURCE_SHA,
        'source_plan_ten_files_unchanged': True,
        'candidate': dict(result['candidate'], path=candidate.as_posix()),
        'rollback': dict(result['rollback'], path=rollback.as_posix()),
        'Image504': result['Image504'],
        'unchanged_boot_sha256': '97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695',
        'FAT_DTB_sha256': 'a82383fa30609bb5e1400f8af12055abdbca7373734c983549d9f437afae2cc5',
        'frozen_build_delivery_sha256': '88aa96af5b451c7778503f89b549f8d7abd131bd8cf330c87368e7552147b482',
        'private_result_sha256': result['private_result_sha256'],
        'FAT_verification_sha256': private['artifacts']['FAT-verification.json'],
        'original_exec_terminal0': True,
        'original_three_tools_terminal0': True,
        'only_Image_file_changed': True,
        'Image_readback_exact': True,
        'fsck_readonly_passed': True,
        'parent_inputs_and_mountinfo_unchanged': True,
        'provider2691_may_pair_but_not_installed': True,
        'current_or_future502_adoption_claimed': False,
        'new_guard_request_or_deployment_binding_created': False,
        'kernel_build_or_ABI_rerun': False,
        'device_storage_SDK_or_Git_used': False,
        'physical_latency_validated': False,
        'archive': {'explicit_source_text_json_whitelist': files, 'recursive_scan': False}
    }
    path = HERE / 'delivery.json'
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(delivery, f, indent=2); f.write('\n'); f.flush(); os.fsync(f.fileno())
    print(json.dumps({'passed': True, 'delivery_sha256': digest(path), 'candidate': delivery['candidate']}))

if __name__ == '__main__':
    main()
