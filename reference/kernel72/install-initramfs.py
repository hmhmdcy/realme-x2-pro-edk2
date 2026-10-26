from pathlib import Path
import hashlib
import json
import shutil

root = Path('/home/cy122/x2pro-linux/initramfs')
out = Path('/mnt/e/edk2-samurai-out/kernel72')
mirror = Path('/mnt/e/RealmeX2Pro edk2')
init = root / 'init'
before = init.read_bytes()
assert hashlib.sha256(before).hexdigest() == 'e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab'
(out / 'init-before').write_bytes(before)
hook = b'\n# SAMURAI_USB_NCM_SSH: independent of the EUD console and F1 path.\n/usr/sbin/samurai-usb start &\n'
needle = b'mount -t configfs configfs /sys/kernel/config 2>/dev/null\n'
assert before.count(needle) == 1
after = before.replace(needle, needle + hook)
assert after.replace(hook, b'') == before
init.write_bytes(after)
init.chmod(0o755)
for dirname in ('usr/sbin', 'usr/bin', 'usr/share/licenses', 'root/.ssh', 'etc/dropbear', 'run'):
    (root / dirname).mkdir(parents=True, exist_ok=True)
shutil.copyfile(out / 'dropbearmulti', root / 'usr/sbin/dropbearmulti')
(root / 'usr/sbin/dropbearmulti').chmod(0o755)
for name in ('dropbear', 'dropbearkey'):
    (root / ('usr/sbin/' + name)).symlink_to('dropbearmulti')
(root / 'usr/bin/scp').symlink_to('../sbin/dropbearmulti')
shutil.copyfile(mirror / 'linux-port/scripts/samurai-usb.sh', root / 'usr/sbin/samurai-usb')
(root / 'usr/sbin/samurai-usb').chmod(0o755)
pubkey = (out / 'id_ed25519.pub').read_text().strip() + '\n'
assert pubkey.startswith('ssh-ed25519 ')
(root / 'root/.ssh/authorized_keys').write_text(pubkey)
(root / 'root/.ssh/authorized_keys').chmod(0o600)
(root / 'root').chmod(0o700)
(root / 'root/.ssh').chmod(0o700)
# Per-device local host key; its contents are never mirrored into the repository.
shutil.copyfile(out / 'dropbear_ed25519_host_key', root / 'etc/dropbear/dropbear_ed25519_host_key')
(root / 'etc/dropbear/dropbear_ed25519_host_key').chmod(0o600)
(root / 'etc/dropbear').chmod(0o700)
for name, contents in {
    'passwd': 'root:x:0:0:root:/root:/bin/sh\n',
    'group': 'root:x:0:\n',
    'shells': '/bin/sh\n',
    'nsswitch.conf': 'passwd: files\ngroup: files\nshadow: files\n',
}.items():
    target = root / ('etc/' + name)
    assert not target.exists()
    target.write_text(contents)
    target.chmod(0o644)
shutil.copyfile('/home/cy122/x2pro-linux/refs/dropbear/dropbear-2026.94/LICENSE', root / 'usr/share/licenses/dropbear-LICENSE')
(out / 'init-after').write_bytes(after)
report = {'init_before_sha256': hashlib.sha256(before).hexdigest(),
          'init_after_sha256': hashlib.sha256(after).hexdigest(),
          'only_init_change': 'asynchronous samurai-usb hook after configfs mount',
          'private_host_key_archived': False, 'private_client_key_on_phone': False,
          'authorized_client_fingerprint': 'SHA256:MJFUR9BsjAXOdjFL6zVatq+XtOT+d5F4fYQV0SkDUTs'}
(out / 'initramfs-install.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
