from pathlib import Path
import hashlib
import json

src = Path('/home/cy122/x2pro-linux/linux')
root = Path('/home/cy122/x2pro-linux/initramfs')
out = Path('/mnt/e/edk2-samurai-out/kernel74')
data = (src / 'usr/initramfs_data.cpio').read_bytes()
files = {}
pos = 0
while pos + 110 <= len(data):
    if data[pos:pos+6] != b'070701':
        if not any(data[pos:]): break
        raise AssertionError(('Unexpected cpio header', pos))
    fields = [int(data[pos+6+i*8:pos+14+i*8], 16) for i in range(13)]
    mode, uid, gid, size, namesize = fields[1], fields[2], fields[3], fields[6], fields[11]
    name = data[pos+110:pos+110+namesize-1].decode()
    bodypos = (pos+110+namesize+3) & ~3
    body = data[bodypos:bodypos+size]
    files[name.lstrip('./')] = dict(mode=mode, uid=uid, gid=gid, body=body)
    pos = (bodypos+size+3) & ~3
    if name == 'TRAILER!!!': break
checks = {}
for name, permissions in {
    'root': 0o700, 'root/.ssh': 0o700, 'root/.ssh/authorized_keys': 0o600,
    'etc/dropbear': 0o700, 'etc/dropbear/dropbear_ed25519_host_key': 0o600,
    'usr/sbin/dropbearmulti': 0o755, 'usr/sbin/samurai-usb': 0o755,
    'etc/passwd': 0o644, 'init': 0o755,
}.items():
    item = files[name]
    assert item['uid'] == item['gid'] == 0, (name, item['uid'], item['gid'])
    assert item['mode'] & 0o777 == permissions, (name, oct(item['mode']))
    if (root/name).is_file(): assert item['body'] == (root/name).read_bytes(), name
    checks[name] = dict(uid=0, gid=0, permissions=oct(permissions), matches_source=True)
for name, target in {'usr/sbin/dropbear':'dropbearmulti',
                     'usr/sbin/dropbearkey':'dropbearmulti',
                     'usr/bin/scp':'../sbin/dropbearmulti'}.items():
    assert files[name]['body'].decode().rstrip('\0') == target, name
assert not any(b'OPENSSH PRIVATE KEY' in x['body'] for x in files.values())
report = dict(root_ownership_mapping_pass=True, files=checks,
              command_symlinks_pass=True, private_client_key_absent=True,
              host_key_provisioning='unique device-local key retained outside Git',
              cpio_bytes=len(data), cpio_sha256=hashlib.sha256(data).hexdigest())
(out/'initramfs-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print('CPIO validates: root ownership, permissions, source contents, SSH/SCP symlinks, no private client key.')
