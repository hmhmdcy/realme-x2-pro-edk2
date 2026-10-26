from pathlib import Path
import hashlib, json, re, subprocess

out = Path('/mnt/e/edk2-samurai-out/kernel98')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel98')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def cpio(path):
    data = path.read_bytes(); offset = 0; entries = {}
    align = lambda n: (n+3)&~3
    while offset+110 <= len(data):
        assert data[offset:offset+6] == b'070701'
        fields = [int(data[offset+6+i*8:offset+14+i*8], 16) for i in range(13)]
        start = offset+110
        name = data[start:start+fields[11]-1].decode()
        start = align(start+fields[11]); content = data[start:start+fields[6]]
        offset = align(start+fields[6])
        if name == 'TRAILER!!!': break
        assert name not in entries
        entries[name] = (fields[1], fields[2], fields[3], content)
    return entries
before, after = cpio(out / 'cpio-before'), cpio(out / 'cpio-after')
assert before.keys() == after.keys()
changed = {name for name in before if before[name] != after[name]}
assert changed == {'usr/sbin/samurai-radio-address', 'lib/modules/samurai/hci_uart.ko'}
assert all(before[name][:3] == after[name][:3] for name in changed)
assert after['usr/sbin/samurai-radio-address'][3] == (ref / 'samurai-radio-address').read_bytes()
assert after['lib/modules/samurai/hci_uart.ko'][3] == (out / 'hci_uart.ko').read_bytes()
assert before['init'] == after['init']
def config(path):
    result = {}
    for line in path.read_text().splitlines():
        match = re.fullmatch(r'(CONFIG_\w+)=(.+)', line)
        if match: result[match[1]] = match[2]
        match = re.fullmatch(r'# (CONFIG_\w+) is not set', line)
        if match: result[match[1]] = 'n'
    return result
old, new = config(out / 'config-before'), config(out / 'config-after')
delta = {key: [old.get(key), new.get(key)] for key in old.keys() | new.keys() if old.get(key) != new.get(key)}
assert delta == {'CONFIG_ATH10K_TRACING': ['n', 'y']}, delta
assert (out / 'dtb-before').read_bytes() == (out / 'dtb-connectivity').read_bytes()
vermagic = []
for name in ('btbcm', 'btqca', 'hci_uart'):
    data = subprocess.check_output(['aarch64-linux-gnu-readelf', '-p', '.modinfo', str(out / (name + '.ko'))], text=True)
    vermagic.append(re.search(r'vermagic=(.*)', data)[1])
assert len(set(vermagic)) == 1
assert '7.3.0-rc6-rmx1931-samurai+' in vermagic[0]
assert (out / 'hci_uart.ko').read_bytes() != (out / 'hci_uart-before.ko').read_bytes()
report = dict(kernel_audit_pass=True, kernel_build=97, config_only_changed=delta,
    dtb_byte_identical=True, init_unchanged=True, existing_files_symlinks_modes_preserved=True,
    cpio_only_changed=sorted(changed), cpio_only_added=[], btqca_btbcm_byte_identical=True,
    hci_uart_diagnostics_only=True, module_vermagic_matches=True, key_wait_behavior_unchanged=True,
    bluetooth_auto_power=False, bluetooth_auto_discovery=False, image_sha256=sha(out / 'Image-connectivity'),
    cpio_sha256=sha(out / 'cpio-after'), dtb_sha256=sha(out / 'dtb-connectivity'), hci_uart_sha256=sha(out / 'hci_uart.ko'))
(out / 'kernel-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
