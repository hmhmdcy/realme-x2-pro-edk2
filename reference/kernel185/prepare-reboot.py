"""Adapt the reviewed round-trip with one explicitly verified module override."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import host

ref = Path(__file__).resolve().parent
old = ref.parent / 'kernel184'
names = ['collect-preflash.py', 'check-quiesce.py', 'disable-crtc.py',
         'freeze-for-bootloader.sh', 'linux-restart2-bootloader.py',
         'quiesce-current183.sh', 'reboot-current.py', 'fastboot-reboot-current.py']
for name in names:
    value = (old / name).read_text().replace('k184', 'k185')
    value = value.replace('stage=184', 'stage=185').replace("'stage': 184", "'stage': 185")
    if name == 'collect-preflash.py':
        source = "shutil.copyfile('/var/lib/samurai/k132-preflash/new-module-tree.sha256',out / 'old132-module-tree.sha256')"
        replacement = '''original = Path('/var/lib/samurai/k132-preflash/new-module-tree.sha256').read_text().splitlines()
module_root = Path('/usr/lib/modules') / os.uname().release
target = 'kernel/drivers/bluetooth/hci_uart.ko'
baseline = json.loads(Path('/var/lib/samurai/k185-baseline/summary.json').read_text())
deployment = json.loads(Path('/var/lib/samurai/k185-deploy/summary.json').read_text())
assert deployment['default_module_path_updated'] and deployment['loaded_build_id_matches']
assert Path('/etc/bluetooth/main.conf').read_bytes() == Path('/var/lib/samurai/k185-policy/main.conf-before-private').read_bytes()
revised = []
overrides = 0
for line in original:
    digest, name = line.split(maxsplit=1)
    name = str(Path(name.lstrip('*')))
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    if name == target:
        assert digest == baseline['original_hci_uart_sha256']
        digest = deployment['candidate_sha256']
        overrides += 1
    assert hashlib.sha256((module_root / name).read_bytes()).hexdigest() == digest, name
    revised.append(digest + '  ' + name)
assert len(revised) == len(original) == 784 and overrides == 1
assert sum(line.split(maxsplit=1)[1].endswith('.ko') for line in revised) == 770
(out / 'old132-module-tree.sha256').write_text('\\n'.join(revised) + '\\n')
(out / 'module-override-validation.json').write_text(json.dumps(dict(module_files=770, total_tree_files=784,
    overrides=1, original_sha256=baseline['original_hci_uart_sha256'],
    replacement_sha256=deployment['candidate_sha256'], other_modules_unchanged=True), indent=2) + '\\n')'''
        assert source in value
        value = value.replace(source, replacement)
        # The captured boot must be the live deployment boot, not an old receipt.
        marker = "assert os.uname().version.startswith('#183 ')"
        value = value.replace(marker, marker + "\nassert Path('/proc/sys/kernel/random/boot_id').read_bytes() == Path('/var/lib/samurai/k185-deploy/boot-id-private.txt').read_bytes()", 1)
    path = ref / name
    assert not path.exists(), name
    path.write_text(value)
    if name.endswith('.sh'):
        subprocess.run(['sh', '-n', str(path)], check=True)
    else:
        subprocess.run([sys.executable, '-m', 'py_compile', str(path)], check=True)
print(json.dumps({'prepared': True, 'module_override_guard': True, 'partitions_to_flash': []}), flush=True)
if sys.argv[1:] != ['--capture']:
    raise SystemExit(0)
host.ssh('test ! -e /var/lib/samurai/k185-reboot-tools && mkdir -m700 /var/lib/samurai/k185-reboot-tools')
for name in names:
    if name in ['reboot-current.py', 'fastboot-reboot-current.py']:
        continue
    dest = '/tmp/k185-' + name if name in ['check-quiesce.py', 'disable-crtc.py', 'freeze-for-bootloader.sh'] else '/var/lib/samurai/k185-reboot-tools/' + name
    path = ref / name
    # Reviewed templates use the stable tool namespace in their guards.
    payload = path.read_text().replace('/var/lib/samurai/k185-tools/', '/var/lib/samurai/k185-reboot-tools/')
    path.write_text(payload)
    host.upload(path, dest)
    host.ssh('sha256sum -c -', input=(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + dest + '\n').encode())
for name in ['reboot-current.py']:
    path = ref / name
    path.write_text(path.read_text().replace('/var/lib/samurai/k185-tools/', '/var/lib/samurai/k185-reboot-tools/'))
result = host.ssh('python3 /var/lib/samurai/k185-reboot-tools/collect-preflash.py', timeout=55)
(host.PRIVATE / 'pre-reboot-capture-private.log').write_bytes(result.stdout + result.stderr)
print(json.dumps({'current_kernel183_and_partitions_verified': True, '770_modules_verified_with_one_override': True,
                  'no_transition_requested': True}))
