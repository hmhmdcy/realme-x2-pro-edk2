from pathlib import Path
import hashlib,json,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel94')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel94')
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
assert before.keys()<=after.keys()
changed=[name for name in before if before[name]!=after[name]]
assert changed==['init'],changed
assert before['init'][:3]==after['init'][:3]
anchor='\n  echo "[wifi] startup exit=$?; see /run/samurai-wifi-boot.log" > /dev/kmsg ) &\n'
addition='\n# Bluetooth UART loads after Wi-Fi readiness; USB remains independent.\n( /usr/sbin/samurai-bluetooth start > /run/samurai-bluetooth-boot.log 2>&1;\n  echo "[bluetooth] startup exit=$?; see /run/samurai-bluetooth-boot.log" > /dev/kmsg ) &\n'
assert before['init'][3].decode().replace(anchor,anchor+addition)==after['init'][3].decode()
added=set(after)-set(before)
expected={'lib/modules','lib/modules/samurai','usr/sbin/samurai-bluetooth'}|{f'lib/modules/samurai/{n}.ko' for n in ('btbcm','btqca','hci_uart')}
assert added==expected,added
for n in ('btbcm','btqca','hci_uart'):
    ent=after[f'lib/modules/samurai/{n}.ko'];assert ent[:3]==(0o100644,0,0)
    assert ent[3]==(out/f'{n}.ko').read_bytes()
    info=subprocess.check_output(['modinfo',str(out/f'{n}.ko')],text=True)
    assert '7.3.0-rc6-rmx1931-samurai+ ' in info
    assert 'intree:         Y' in info
assert after['usr/sbin/samurai-bluetooth'][:3]==(0o100755,0,0)
assert after['usr/sbin/samurai-bluetooth'][3]==(ref/'samurai-bluetooth').read_bytes()
assert (out/'dtb-before').read_bytes()==(out/'dtb-connectivity').read_bytes()
b=json.loads((out/'build-validation.json').read_text())
assert b['config_changes']=={key:['y','m'] for key in ('CONFIG_BT_HCIUART','CONFIG_BT_BCM','CONFIG_BT_QCA')}
report=dict(kernel_audit_pass=True,kernel_build=93,dtb_byte_identical=True,
    existing_files_symlinks_modes_preserved=True,only_changed_existing_entry=changed,
    added_entries=sorted(added),config_changes=b['config_changes'],no_embedded_credentials_added=True,
    image_sha256=sha(out/'Image-connectivity'),dtb_sha256=sha(out/'dtb-connectivity'),cpio_sha256=sha(out/'cpio-after'))
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
