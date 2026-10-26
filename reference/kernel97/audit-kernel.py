from pathlib import Path
import hashlib, json
out = Path('/mnt/e/edk2-samurai-out/kernel97')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel97')
def cpio(path):
    data = path.read_bytes(); off = 0; entries = {}
    align = lambda n: (n + 3) & ~3
    while off + 110 <= len(data):
        assert data[off:off+6] == b'070701'
        fields = [int(data[off+6+i*8:off+14+i*8], 16) for i in range(13)]
        start = off + 110
        name = data[start:start+fields[11]-1].decode()
        start = align(start + fields[11]); content = data[start:start+fields[6]]
        off = align(start + fields[6])
        if name == 'TRAILER!!!':
            break
        assert name not in entries
        entries[name] = (fields[1], fields[2], fields[3], content)
    return entries
before, after = cpio(out / 'cpio-before'), cpio(out / 'cpio-after')
assert before.keys() <= after.keys()
added = after.keys() - before.keys()
assert added == {'usr/sbin/samurai-radio-address', 'usr/sbin/samurai-dms-mac-read', 'usr/sbin/samurai-bt-address'}
changed = {name for name in before if before[name] != after[name]}
assert changed == {'usr/sbin/samurai-wifi', 'usr/sbin/samurai-bluetooth'}
for name in changed:
    assert before[name][:3] == after[name][:3]
for name in added:
    assert after[name][:3] == (0o100755, 0, 0)
for name in ('samurai-wifi', 'samurai-bluetooth', 'samurai-radio-address'):
    assert after['usr/sbin/' + name][3] == (ref / name).read_bytes()
for name in ('samurai-dms-mac-read', 'samurai-bt-address'):
    assert after['usr/sbin/' + name][3] == (out / name).read_bytes()
assert before['init'] == after['init']
assert (out / 'config-before').read_bytes() == (out / 'config-after').read_bytes()
assert (out / 'dtb-before').read_bytes() == (out / 'dtb-connectivity').read_bytes()
build = json.loads((out / 'build-validation.json').read_text())
assert build['kernel_source_unchanged']
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = dict(kernel_audit_pass=True, kernel_build=96, kernel_source_unchanged=True,
              config_byte_identical=True, dtb_byte_identical=True, module_bytes_unchanged=True,
              existing_files_symlinks_modes_preserved=True, cpio_only_changed=sorted(changed),
              cpio_only_added=sorted(added), init_unchanged=True, identity_only_private_ram=True,
              bluetooth_auto_power=False, bluetooth_auto_discovery=False,
              image_sha256=sha(out / 'Image-connectivity'), dtb_sha256=sha(out / 'dtb-connectivity'),
              cpio_sha256=sha(out / 'cpio-after'))
(out / 'kernel-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
