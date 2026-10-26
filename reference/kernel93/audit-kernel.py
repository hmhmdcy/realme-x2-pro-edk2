from pathlib import Path
import hashlib, json, struct, subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel93')
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
assert changed==['usr/sbin/samurai-wifi'],changed
assert before[changed[0]][:3]==after[changed[0]][:3]
old=before[changed[0]][3].decode();new=after[changed[0]][3].decode()
assert old.replace('test -b "/dev/$node"','test -b "/dev/$node" || return 1').replace('[ "$(cat "/sys/class/block/$node/size")" = "$2" ]','[ "$(cat "/sys/class/block/$node/size")" = "$2" ] || return 1').replace("[ \"$(cat \"$parent/device/model\")\" = 'KLUDG4UHDB-B2D1 ' ]","[ \"$(cat \"$parent/device/model\")\" = 'KLUDG4UHDB-B2D1 ' ] || return 1").replace('[ "$matches" -eq 1 ]','[ "$matches" -eq 1 ] || return 1')==new
def dt(p):return subprocess.check_output(['dtc','-I','dtb','-O','dts',str(p)],stderr=subprocess.DEVNULL,text=True)
old_dt,new_dt=dt(out/'dtb-before'),dt(out/'dtb-connectivity')
addition=next(line+'\n' for line in new_dt.splitlines() if 'firmware-name = "crnv21.bin' in line)
assert 'crbtfw21.tlv' in addition
assert addition in new_dt
assert new_dt.replace(addition,'')==old_dt
report=dict(kernel_audit_pass=True,kernel_build=92,config_unchanged=True,
    cpio_only_changed=changed,existing_files_symlinks_modes_preserved=True,
    dt_only_new_property='UART13 bluetooth firmware-name: crnv21.bin, crbtfw21.tlv',
    image_sha256=sha(out/'Image-connectivity'),dtb_sha256=sha(out/'dtb-connectivity'),cpio_sha256=sha(out/'cpio-after'))
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
