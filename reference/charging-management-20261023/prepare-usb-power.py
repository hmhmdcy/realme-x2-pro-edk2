"""Prepare a reviewed 500mA USB configuration request, no phone operations."""
from pathlib import Path
import hashlib
import json
import subprocess

ref = Path(__file__).resolve().parent
root = ref.parents[1]
out = Path('/mnt/e/edk2-samurai-out/charging-management-20261023/usb-power500')
out.mkdir(parents=True, exist_ok=True, mode=0o700)
before = json.loads((out.parent / 'usb-hotplug-r2/usb-services-before-private.json').read_text())
migration = '''# Migrate an initramfs-owned configuration only through re-enumeration.
# The host must fetch the changed descriptor before its new budget is used.
if [ "$(cat "$g/configs/c.1/MaxPower")" != 500 ]; then
    bound=$(cat "$g/UDC")
    test -z "$bound" || test "$bound" = "$udc"
    if [ -n "$bound" ]; then printf '\\n' >"$g/UDC"; fi
    echo 500 >"$g/configs/c.1/MaxPower"
fi
'''
needle = 'if [ -z "$(cat "$g/UDC")" ]; then'
files = {}
for target, entry in before.items():
    text = entry['text']; assert text.count('echo 100 >') == 1
    after = text.replace('echo 100 >', 'echo 500 >')
    if target == '/usr/local/sbin/samurai-usb':
        old_guard = 'if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then'
        assert after.count(old_guard) == 1 and after.count(needle) == 1
        after = after.replace(old_guard, old_guard.removesuffix('; then') + ' && [ "$(cat "$g/configs/c.1/MaxPower")" = 500 ]; then')
        after = after.replace(needle, migration + needle)
    name = 'local-samurai-usb.sh' if '/local/' in target else 'diagnostic-samurai-usb.sh'
    path = out / name; path.write_text(after)
    subprocess.run(['sh', '-n', str(path)], check=True)
    files[target] = {'before_sha256': entry['sha256'], 'after_sha256': hashlib.sha256(after.encode()).hexdigest(),
                     'candidate': str(path), 'canonical': entry['resolved'], 'text': after}
# Keep both repository creation paths correct, with runtime migration in the
# persistent distro service. No kernel/Image/initramfs rebuild is required.
for relative in ['linux-port/scripts/samurai-usb.sh',
                 'linux-port/packages/samurai-platform/usr_sbin_samurai-usb']:
    path = root / relative; text = path.read_text(); assert text.count('echo 100 >') == 1
    text = text.replace('echo 100 >', 'echo 500 >')
    if '/packages/' in relative:
        assert text.count(needle) == 1
        text = text.replace(needle, migration + needle)
    path.write_text(text)
    subprocess.run(['sh', '-n', str(path)], check=True)
request = {'files': files, 'descriptor_before_ma': 100, 'descriptor_after_ma': 500,
           'guard': '/var/lib/samurai/k449-adopted/boot-id-private.txt',
           'manifest_sha256': '34d46f4cf449f0c7a50590e0de3c07d84762c19ef1dd1a22e20f6cf66a24d5a7'}
(out / 'request-private.json').write_text(json.dumps(request, indent=2))
print(json.dumps({'prepared': True, 'shell_syntax_passed': True,
                  'file_changes': {name: {k: v for k, v in entry.items() if k != 'text'}
                                   for name, entry in files.items()}}, indent=2))
