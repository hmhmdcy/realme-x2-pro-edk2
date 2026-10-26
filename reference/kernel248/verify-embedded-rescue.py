"""Pin recovery SSH identity from the exact preserved kernel's builtin CPIO."""
from pathlib import Path
import hashlib,json,re,subprocess,zlib
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel248');expected=json.loads((R.parent/'kernel235/build-package-validation.json').read_text());image=P.parent/'kernel183/Image-k183-offline-stream-private';raw=image.read_bytes();assert hashlib.sha256(raw).hexdigest()==expected['kernel_image_preserved']
archives=[]
for match in re.finditer(b'\x1f\x8b\x08',raw):
 try:
  dec=zlib.decompressobj(16+zlib.MAX_WBITS);b=dec.decompress(raw[match.start():],64*1024*1024)
  if b.startswith((b'070701',b'070702')) and b'TRAILER!!!' in b:archives.append(b)
 except zlib.error:pass
assert len(archives)==1,len(archives);b=archives[0];pos=0;files={}
while pos+110<=len(b):
 h=b[pos:pos+110];assert h[:6] in [b'070701',b'070702'];v=[int(h[6+i*8:14+i*8],16) for i in range(13)];size,namesize=v[6],v[11];name=b[pos+110:pos+110+namesize-1].decode();start=(pos+110+namesize+3)&~3
 if name=='TRAILER!!!':break
 files[name.removeprefix('./')]=b[start:start+size];pos=(start+size+3)&~3
required=['init','usr/sbin/samurai-rootfs','usr/sbin/samurai-usb','etc/dropbear/dropbear_ed25519_host_key','root/.ssh/authorized_keys'];assert all(x in files for x in required)
rootfs=files['usr/sbin/samurai-rootfs'].decode();assert 'samurai-f2fs-rootfs01' in rootfs and 'diagnostic fallback' in rootfs and 'umount /newroot' in rootfs
assert b'/usr/sbin/samurai-usb start &' in files['init'] and b'dropbear -E -s -j -k' in files['usr/sbin/samurai-usb']
key=P/'embedded-rescue-host-key-private.bin';assert not key.exists();key.write_bytes(files['etc/dropbear/dropbear_ed25519_host_key']);key.chmod(0o600);sdk=Path('/home/cy122/x2pro-linux/gnss248-rescue-root-r2');x=subprocess.run(['qemu-aarch64','-L',str(sdk),str(sdk/'usr/bin/dropbearkey'),'-y','-f',str(key)],capture_output=True,check=True,timeout=20);(P/'embedded-rescue-host-public-key-private.txt').write_bytes(x.stdout);public=next(l for l in x.stdout.decode().splitlines() if l.startswith('ssh-ed25519 '));(P/'rescue-known-hosts-private').write_text('169.254.42.1 '+public+'\n')
current=json.loads((P/'current-auth-keys-private.json').read_text())['auth'];tokens=lambda t:{tuple(l.split()[:2]) for l in t.splitlines() if l.strip().startswith('ssh-')};assert tokens(files['root/.ssh/authorized_keys'].decode())&tokens(current)
v=dict(stage=248,exact_image183_sha256_matches_deployed_boot_manifest=True,builtin_cpio_archives=1,ram_fallback_and_usb_ssh_verified_in_image=True,authorized_key_matches_current_client=True,recovery_host_key_pinned_offline=True,no_accept_new_or_disabled_host_checking=True,filesystem_marker_gate_present=True,live_recovery_boot_not_yet_tested=True,no_phone_change=True)
(R/'embedded-rescue-validation.json').write_text(json.dumps(v,indent=2)+'\n');(P/'embedded-rescue-source-hashes-private.json').write_text(json.dumps({name:hashlib.sha256(files[name]).hexdigest() for name in required},indent=2)+'\n');print(json.dumps(v))
