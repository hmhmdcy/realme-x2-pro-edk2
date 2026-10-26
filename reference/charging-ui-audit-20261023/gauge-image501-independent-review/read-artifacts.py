"""Read existing private outputs only; no imports of build runners or tools."""
from pathlib import Path
import gzip
import hashlib
import json
import struct

ORIGINAL = Path('/home/cy122/charging-management-20261023/gauge-image363-baseline-01/build')
CANDIDATE = Path('/home/cy122/charging-management-20261023/gauge-image501-B-repro-01/build')
ROOT = CANDIDATE.parent
HERE = Path(__file__).resolve().parent
sha = lambda raw: hashlib.sha256(raw).hexdigest()
OLD_ID = b'#363 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
NEW_ID = b'#501 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'


def sections(raw):
    h = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
    assert h[0][:6] == b'\x7fELF\x02\x01' and h[2] == 183
    table = [struct.unpack_from('<IIQQQQIIQQ', raw, h[6] + i*h[11]) for i in range(h[12])]
    names = raw[table[h[13]][4]:table[h[13]][4]+table[h[13]][5]]
    return [(names[s[0]:].split(b'\0', 1)[0].decode(), s) for s in table]


def main():
    report = {'scope': 'readonly existing artifact hash/ELF content comparison; no build, test suite, mount, SDK, device or Git call'}
    identity = {}
    for name in ['init/version.o', 'init/version-timestamp.o']:
        old = (ORIGINAL/name).read_bytes(); new = (CANDIDATE/name).read_bytes()
        assert old.count(OLD_ID) == 2 and old.replace(OLD_ID, NEW_ID) == new
        a, b = sections(old), sections(new)
        assert a == b
        changed = []
        for label, s in a:
            if s[1] == 8:
                continue
            x, y = old[s[4]:s[4]+s[5]], new[s[4]:s[4]+s[5]]
            if s[2] & 4:
                assert x == y
            if x != y:
                assert label in ['.data', '.rodata'] and x.replace(OLD_ID, NEW_ID) == y
                changed.append(label)
        identity[name] = {'old_sha256': sha(old), 'new_sha256': sha(new),
                          'whole_ELF_identity_substitution_only': True, 'changed_sections': changed,
                          'differing_byte_count': sum(x != y for x, y in zip(old, new)),
                          'executable_sections_identical': True}
    report['identity_objects'] = identity
    expected = {'usr/initramfs_data.cpio': 'fc1d27728b2ab7dc8c08b3a372b9f1a025a9db60faaad6b33001398e214c9669',
                'usr/initramfs_inc_data': '319b665d4bdbf9647efb1ae1055438e5a7990c69e7016190c9625de414b81678',
                'usr/initramfs_data.o': '2524437833f58ecd8410d6c1d740d0f412faaae85d3ae73c63d3f1f3607484de'}
    for name, digest in expected.items():
        assert sha((ORIGINAL/name).read_bytes()) == sha((CANDIDATE/name).read_bytes()) == digest
    report['initramfs_exact_original_sha256'] = expected
    image = (CANDIDATE/'arch/arm64/boot/Image').read_bytes()
    assert sha(image) == '3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'
    start = image.index(b'IKCFG_ST')+8; end = image.index(b'IKCFG_ED', start)
    config = gzip.decompress(image[start:end])
    assert sha(config) == '23e088a90736bbbc442c672d82b35c11bf04f7dc489f1c6afb1b03dc0d8f30ed'
    assert config == (CANDIDATE/'.config').read_bytes()
    bq = (CANDIDATE/'drivers/power/supply/bq27xxx_battery.o').read_bytes()
    assert sha(bq) == 'd6ef27a94d512ef8ffdc534f67874188a5a1f0cffb7e20662d2a712eb918741e'
    table = sections(bq); found = []
    for name, s in table:
        if s[1] != 2:
            continue
        strings = table[s[6]][1]; names = bq[strings[4]:strings[4]+strings[5]]
        for offset in range(s[4], s[4]+s[5], s[9]):
            sym = struct.unpack_from('<IBBHQQ', bq, offset)
            label = names[sym[0]:].split(b'\0', 1)[0]
            if label == b'samurai_instant_current':
                target_name, target = table[sym[3]]
                assert target[1] == 8 and target_name == '.bss' and sym[5] == 1
                found.append({'section': target_name, 'NOBITS_zero_initialized': True, 'bytes': sym[5]})
    assert len(found) == 1
    report.update(Image_sha256=sha(image), Image_bytes=len(image), embedded_config_sha256=sha(config),
                  bq_object_sha256=sha(bq), parameter_symbol=found)
    old_closure = json.loads((ORIGINAL.parent/'closure-final.json').read_bytes())
    new_closure = json.loads((ROOT/'closure-final.json').read_bytes())
    plan = HERE.parents[1]/'charging-oem-audit-20261023/gauge-image363-integration-plan'
    members = json.loads((plan/'link-inputs.json').read_bytes())['members']
    stub = json.loads((plan/'final-link-inputs.json').read_bytes())['libstub_members']
    changed = [n for n in members if old_closure[n] != new_closure[n]]
    assert set(changed) == {'drivers/power/supply/bq27xxx_battery.o', 'init/version.o'}
    assert all(old_closure[n] == new_closure[n] for n in stub)
    report.update(closure_receipt_changed_archive_leaves=changed, unchanged_archive_leaf_count=len(members)-2,
                  unchanged_libstub_count=len(stub), artifact_bytes_written=False, physical_validation=False)
    (HERE/'artifact-readback.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({'read_only_artifact_binding': True, 'Image_sha256': sha(image),
                      'unchanged_archive_leaf_count': len(members)-2, 'unchanged_libstub_count': len(stub)}))


if __name__ == '__main__':
    main()
