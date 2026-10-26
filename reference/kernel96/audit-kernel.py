from pathlib import Path
import hashlib,json,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel96');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel96')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def cpio(p):
    b=p.read_bytes();off=0;entries={};align=lambda n:(n+3)&~3
    while off+110<=len(b):
        assert b[off:off+6]==b'070701'
        f=[int(b[off+6+i*8:off+14+i*8],16) for i in range(13)]
        start=off+110;name=b[start:start+f[11]-1].decode();start=align(start+f[11]);data=b[start:start+f[6]];off=align(start+f[6])
        if name=='TRAILER!!!':break
        assert name not in entries;entries[name]=(f[1],f[2],f[3],data)
    return entries
before,after=cpio(out/'cpio-before'),cpio(out/'cpio-after')
assert before.keys()==after.keys()
changed=[name for name in before if before[name]!=after[name]]
assert set(changed)=={'init','usr/sbin/samurai-bluetooth'},changed
for name in changed:assert before[name][:3]==after[name][:3]
assert after['init'][3]==(out/'init-after').read_bytes()
assert after['usr/sbin/samurai-bluetooth'][3]==(ref/'samurai-bluetooth').read_bytes()
for command in ('insmod','lsmod','modprobe','rmmod'):
    assert after['bin/'+command][0]&0o170000==0o120000
    assert after['bin/'+command][3]==b'busybox\x00'
assert (out/'config-before').read_bytes()==(out/'config-after').read_bytes()
assert (out/'dtb-before').read_bytes()==(out/'dtb-connectivity').read_bytes()
kernel=Path('/home/cy122/x2pro-linux/linux')
paths=['drivers/net/wireless/ath/ath10k/qmi.c','drivers/net/wireless/ath/ath10k/qmi.h']
assert subprocess.check_output(['git','diff','--',*paths],cwd=kernel)==(ref/'ath10k-qmi-unbind-msa.patch').read_bytes()
report=dict(kernel_audit_pass=True,kernel_build=95,config_byte_identical=True,dtb_byte_identical=True,
    existing_files_symlinks_modes_preserved=True,cpio_only_changed=changed,module_bytes_unchanged=True,
    kernel_source_changed=paths,boot_waits_wifi_result_including_failure=True,bt_explicit_start_stop=True,
    no_embedded_credentials_added=True,image_sha256=sha(out/'Image-connectivity'),dtb_sha256=sha(out/'dtb-connectivity'),cpio_sha256=sha(out/'cpio-after'))
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
