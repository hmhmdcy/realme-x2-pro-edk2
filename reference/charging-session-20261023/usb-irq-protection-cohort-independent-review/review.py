"""Read-only thin review of actual offline payloads; no author entry points."""
from pathlib import Path
import hashlib
import io
import json
import struct
import tarfile

HERE = Path(__file__).resolve().parent
AUTHOR = HERE.parents[1] / 'charging-ui-audit-20261023/usb-irq-protection-cohort-candidate'
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-irq-protection-cohort-private-01')
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def note(raw):
    assert raw[:6] == b'\x7fELF\x02\x01' and struct.unpack_from('<HH', raw, 16) == (1, 183)
    start = struct.unpack_from('<Q', raw, 40)[0]
    stride, count, index = struct.unpack_from('<HHH', raw, 58)
    assert stride == 64 and index < count and start + count * stride <= len(raw)
    rows = [struct.unpack_from('<IIQQQQIIQQ', raw, start + i * stride) for i in range(count)]
    def part(row):
        assert row[4] + row[5] <= len(raw)
        return raw[row[4]:row[4] + row[5]]
    names = part(rows[index])
    sections = {names[row[0]:].split(b'\0', 1)[0]: part(row) for row in rows if row[1] != 8}
    actual_note = sections[b'.note.gnu.build-id']
    assert len(actual_note) == 36 and actual_note[:16] == struct.pack('<III', 4, 20, 3) + b'GNU\0'
    modinfo = sections[b'.modinfo'].split(b'\0')
    assert b'intree=Y' in modinfo
    return sha(actual_note)


def differences(a, b, path=()):
    if isinstance(a, dict) and isinstance(b, dict):
        assert a.keys() == b.keys()
        return sum((differences(a[key], b[key], path + (key,)) for key in a), [])
    return [] if a == b else [path]


def read_archive(path, manifest, manifest_raw, identities):
    expected = {manifest['modules'][key]['target'].lstrip('/'): manifest['modules'][key]['sha256']
                for key in ('samurai-usb-input', 'samurai-gauge-protection')}
    expected['usr/share/samurai-charging/manifest.json'] = sha(manifest_raw)
    with tarfile.open(fileobj=io.BytesIO(path.read_bytes()), mode='r:gz') as tar:
        members = tar.getmembers()
        assert len(members) == 3 and len({m.name for m in members}) == 3
        assert {m.name for m in members} == set(expected)
        for member in members:
            assert member.isfile() and member.uid == member.gid == 0 and member.mode == 0o600
            assert member.uname == member.gname == 'root' and member.mtime == 0 and not member.pax_headers
            assert 0 < member.size < 200000
            raw = tar.extractfile(member).read()
            assert len(raw) == member.size and sha(raw) == expected[member.name]
            if member.name.endswith('.ko'):
                key = Path(member.name).stem
                assert note(raw) == identities[key]['resident_note_sha256']
            else:
                assert raw == manifest_raw
    return expected


def main():
    assert not (HERE / 'review-result.json').exists()
    delivery_raw = (AUTHOR / 'delivery.json').read_bytes()
    assert sha(delivery_raw) == '3d5b78bc4c7a6b476bfb97c2fbad3e0d76497c94e13bd755a8e4aaa0b032a07b'
    delivery = json.loads(delivery_raw)
    for name, expected in delivery['files'].items():
        raw = (AUTHOR / name).read_bytes()
        assert sha(raw) == expected['sha256'] and len(raw) == expected['bytes']
    result = json.loads((PRIVATE / 'result.json').read_bytes())
    assert result['passed'] and not result['installed'] and not result['device_or_SSH_USB_SDK_Git_accessed']
    for name, expected in result['files'].items():
        raw = (PRIVATE / name).read_bytes()
        assert sha(raw) == expected['sha256'] and len(raw) == expected['bytes']
    old_raw, new_raw = (PRIVATE / 'rollback-manifest.json').read_bytes(), (PRIVATE / 'manifest.json').read_bytes()
    old, new = json.loads(old_raw), json.loads(new_raw)
    assert sha(old_raw) == '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
    assert sha(new_raw) == '5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
    expected_delta = {('adapter_revision',)}
    for key in ('samurai-usb-input', 'samurai-gauge-protection'):
        expected_delta.add(('modules', key, 'sha256'))
        expected_delta.add(('installed_files', old['modules'][key]['target']))
    assert set(differences(old, new)) == expected_delta
    assert new['adapter_revision'] == 'usb-irq-protection-observer-01'
    cohort = json.loads((PRIVATE / 'cohort.json').read_bytes())
    assert cohort == json.loads((AUTHOR / 'cohort-manifest.json').read_bytes())
    archives = {}
    for mode, filename, manifest, raw in [('new', 'usb-irq-protection-payload.tar.gz', new, new_raw),
                                         ('old', 'rollback-r8-payload.tar.gz', old, old_raw)]:
        identities = {key: value[mode] for key, value in cohort['modules'].items()}
        archives[mode] = read_archive(PRIVATE / filename, manifest, raw, identities)
    assert cohort['required_carriers']['boot']['sha256'] == 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
    assert cohort['required_carriers']['native_DTB']['sha256'] == '13d359c4a78ed423d52f1d5e09345c7dc7032811fabe786952ac11e868adee9f'
    assert cohort['required_carriers']['logdump']['sha256'] == 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
    assert cohort['transition']['new_independent_guard_and_transaction_required']
    assert not cohort['transition']['prepared_Image502_transaction_reusable']
    assert not cohort['transition']['old_manager_loaded_matches_new_file_before_reboot_valid']
    assert not cohort['transition']['capture_issued']
    test = json.loads((AUTHOR / 'test-result.json').read_bytes())
    assert test['passed'] and test['actual_package_boundary_cases'] == 7
    for name, digest in test['tested_files'].items():
        assert sha((AUTHOR / name).read_bytes()) == digest
    review = {'passed': True, 'scope': 'actual frozen offline cohort bytes and narrow source review only',
              'author_delivery_sha256': sha(delivery_raw), 'author_file_count': len(delivery['files']),
              'private_result_sha256': sha((PRIVATE / 'result.json').read_bytes()),
              'manifest_difference_count': 5, 'forward_and_rollback_exact_three_regular_files': True,
              'archive_modules_AArch64_intree_notes_bound': True, 'archives': archives,
              'root_prior_actual_protection_nm_builtin_import_count': 31,
              'source_review': ['manifest only two module hashes and revision',
                                'manager614 ignores adapter_revision; real loaded_matches still requires new runtime notes',
                                'paired new DT and USB module; fixed Image502 baseline',
                                'stage-only disk/new vs resident/old requires fresh independent transaction',
                                'rollback does not blindly replace an adopted Image502 logdump'],
              'author_tests_rerun': False, 'build_or_device_access': False,
              'IRQ_runtime_or_2719_compatibility_accepted': False, 'new_blockers_found': []}
    (HERE / 'review-result.json').write_text(json.dumps(review, indent=2) + '\n')
    print(json.dumps({'passed': True, 'author_file_count': len(delivery['files']),
                      'review_sha256': sha((HERE / 'review-result.json').read_bytes())}))


if __name__ == '__main__':
    main()
