"""Host-only read inventory. Never chroot, bind, install or run cached SDK tools."""
from pathlib import Path
import hashlib,json,os,shutil,struct
ROOTS=[Path('/home/cy122/x2pro-linux/libcamera214-root'),Path('/home/cy122/pmos-samurai-rootfs01/work/rootfs')]
DEPS='appstream-dev callaudiod-dev elogind-dev evince-dev evolution-data-server-dev feedbackd-dev gcr-dev gettext-dev glib-dev gmobile-dev gnome-bluetooth-dev gnome-desktop-dev gtk+3.0-dev libadwaita-dev libgudev-dev libhandy1-dev libsecret-dev linux-pam-dev meson modemmanager-dev networkmanager-dev polkit-elogind-dev pulseaudio-dev py3-docutils qrcodegen-dev upower-dev wayland-dev wayland-protocols'.split()
sha=lambda b:hashlib.sha256(b).hexdigest()
result={'scope':'only host filesystem metadata and installed database; no SDK tool invoked or shared write',
        'host_uid':os.geteuid(),'host_tools':{n:shutil.which(n) for n in ['abuild','meson','ninja','aarch64-alpine-linux-musl-gcc','aarch64-linux-musl-gcc']},'roots':[]}
for root in ROOTS:
    row={'path':str(root),'exists':root.is_dir(),'mountpoint':os.path.ismount(root)}
    db=root/'lib/apk/db/installed';world=root/'etc/apk/world'
    if db.is_file():
        before=db.read_bytes();packages={}
        for block in before.decode().split('\n\n'):
            fields={line.split(':',1)[0]:line.split(':',1)[1] for line in block.splitlines() if ':' in line}
            if 'P' in fields:packages[fields['P']]=fields
        row['installed_db_sha256']=sha(before)
        row['selected_packages']={p:{k:packages[p].get(k) for k in ['V','A','c']} for p in ['phosh','upower','abuild','build-base','gcc','musl-dev','gtk+3.0-dev','upower-dev'] if p in packages}
        row['present_required_makedepends']={p:packages[p]['V'] for p in DEPS if p in packages}
        row['missing_required_makedepends']=[p for p in DEPS if p not in packages]
        row['db_unchanged_after_reads']=db.read_bytes()==before
    if world.is_file():row['world_sha256']=sha(world.read_bytes())
    row['tool_files']={p:(root/p).is_file() for p in ['usr/bin/abuild','usr/bin/meson','usr/bin/ninja','usr/bin/gcc','lib/ld-musl-aarch64.so.1']}
    gcc=root/'usr/bin/gcc'
    if gcc.is_file():
        with gcc.open('rb') as f:head=f.read(64)
        row['gcc_ELF_machine']=struct.unpack_from('<H',head,18)[0] if head[:4]==b'\x7fELF' else None
    result['roots'].append(row)
print(json.dumps(result,indent=2))
