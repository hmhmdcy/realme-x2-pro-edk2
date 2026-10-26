"""Read metadata/ELF/APK databases only. Never run target tools or change a rootfs."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import struct

sha = lambda b: hashlib.sha256(b).hexdigest()
SEED = Path('/home/cy122/x2pro-linux/libcamera214-root')
OUT = Path('/mnt/e/RealmeX2Pro edk2/reference/charging-oem-audit-20261023/phosh-build-readiness-501')
deps = 'appstream-dev callaudiod-dev elogind-dev evince-dev evolution-data-server-dev feedbackd-dev gcr-dev gettext-dev glib-dev gmobile-dev gnome-bluetooth-dev gnome-desktop-dev gtk+3.0-dev libadwaita-dev libgudev-dev libhandy1-dev libsecret-dev linux-pam-dev meson modemmanager-dev networkmanager-dev polkit-elogind-dev pulseaudio-dev py3-docutils qrcodegen-dev upower-dev wayland-dev wayland-protocols'.split()


def elf(path):
    p = Path(path)
    row = {'path': str(p), 'exists': p.is_file(), 'symlink': p.is_symlink()}
    if not p.is_file():
        return row
    row['resolved'] = str(p.resolve())
    with p.open('rb') as f:
        head = f.read(64)
        if head[:4] == b'\x7fELF':
            row['machine'] = struct.unpack_from('<H', head, 18)[0]
            if head[4:6] == bytes([2, 1]):
                phoff = struct.unpack_from('<Q', head, 32)[0]
                entsize, count = struct.unpack_from('<HH', head, 54)
                for i in range(count):
                    f.seek(phoff + i * entsize)
                    ph = f.read(entsize)
                    if struct.unpack_from('<I', ph)[0] == 3:
                        off, size = struct.unpack_from('<Q', ph, 8)[0], struct.unpack_from('<Q', ph, 32)[0]
                        f.seek(off)
                        row['interpreter'] = f.read(size).rstrip(b'\0').decode()
    return row


def text_if(path):
    p = Path(path)
    return p.read_text(errors='replace') if p.is_file() else None


raw = (SEED / 'lib/apk/db/installed').read_bytes()
world = (SEED / 'etc/apk/world').read_bytes()
packages = {}
for block in raw.decode().split('\n\n'):
    fields = dict(line.split(':', 1) for line in block.splitlines() if ':' in line)
    if 'P' in fields:
        packages[fields['P']] = fields
tools = ['qemu-aarch64-static', 'qemu-aarch64', 'aarch64-alpine-linux-musl-gcc',
         'aarch64-linux-musl-gcc', 'aarch64-linux-gnu-gcc', 'abuild', 'apk',
         'meson', 'ninja', 'proot', 'bwrap', 'unshare', 'chroot', 'readelf']
host_tools = {name: shutil.which(name) for name in tools}
binfmt = {}
b = Path('/proc/sys/fs/binfmt_misc')
if b.is_dir():
    for p in b.iterdir():
        if p.name != 'register' and p.is_file():
            value = p.read_text(errors='replace')
            if p.name in ['status', 'qemu-aarch64'] or 'aarch64' in value:
                binfmt[p.name] = value
qemu_meta = [elf(p) for p in ['/usr/bin/qemu-aarch64-static', '/usr/bin/qemu-aarch64', '/usr/libexec/qemu-binfmt/aarch64-binfmt-P']]

cache_roots = [SEED/'var/cache/apk', SEED/'etc/apk/cache', Path('/home/cy122/pmos-samurai-rootfs01/work'),
               Path('/home/cy122/.cache/pmbootstrap'), Path('/home/cy122/.cache/apk')]
caches = []
for root in cache_roots:
    row = {'path': str(root), 'exists': root.exists(), 'resolved': str(root.resolve())}
    found = []
    if root.is_dir():
        for base, dirs, files in os.walk(root, followlinks=False):
            level = len(Path(base).relative_to(root).parts)
            dirs[:] = [d for d in dirs if d not in ['rootfs', 'chroot_native', 'chroot_rootfs_samurai', '.git', 'src', 'build']] if level < 3 else []
            for name in files:
                if name.endswith(('.apk', '.adb')) or name.startswith('APKINDEX') or name == 'apk.static':
                    p = Path(base) / name
                    found.append({'path': str(p), 'bytes': p.stat().st_size})
    row['files'] = found
    caches.append(row)

selected = set(deps + ['phosh', 'libphosh', 'upower', 'gtk+3.0', 'libhandy1', 'gmobile', 'musl',
                     'gcc', 'binutils', 'abuild', 'apk-tools', 'build-base', 'pkgconf',
                     'gobject-introspection-dev', 'gi-docgen', 'vala', 'samurai', 'xvfb-run', 'xmlstarlet'])
report = {
    'scope': 'Read-only host and seed metadata; no target tool, chroot, package solve/download/install or build executed',
    'uid': os.geteuid(), 'host_tools': host_tools, 'qemu_ELF': qemu_meta, 'binfmt': binfmt,
    'seed': {'path': str(SEED), 'mountpoint': os.path.ismount(SEED), 'installed_db_sha256': sha(raw),
             'world_sha256': sha(world), 'repositories': text_if(SEED/'etc/apk/repositories'),
             'abuild_conf': text_if(SEED/'etc/abuild.conf'),
             'selected_packages': {p: {k:packages[p].get(k) for k in ['V','A','c','D','p']} for p in sorted(selected) if p in packages},
             'present_makedepends': {p:packages[p]['V'] for p in deps if p in packages},
             'missing_makedepends': [p for p in deps if p not in packages],
             'gcc': elf(SEED/'usr/bin/gcc'),
             'pkgconfig_directories': [str(p) for p in [SEED/'usr/lib/pkgconfig', SEED/'usr/share/pkgconfig'] if p.is_dir()]},
    'apk_caches': caches,
    'free_bytes_home': os.statvfs('/home/cy122').f_bavail * os.statvfs('/home/cy122').f_frsize,
}
assert (SEED/'lib/apk/db/installed').read_bytes() == raw
assert (SEED/'etc/apk/world').read_bytes() == world
report['seed_db_and_world_unchanged'] = True
report['inventory_source_sha256'] = sha(Path(__file__).read_bytes())
(OUT/'inventory-result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'host_tools': host_tools, 'binfmt': binfmt, 'qemu_ELF':qemu_meta,
                  'missing_makedepends': report['seed']['missing_makedepends'],
                  'cached_package_files': [len(r['files']) for r in caches],
                  'seed_db_and_world_unchanged': True, 'result_sha256':sha((OUT/'inventory-result.json').read_bytes())}, indent=2))
