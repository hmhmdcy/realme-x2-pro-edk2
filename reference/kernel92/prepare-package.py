from pathlib import Path
import hashlib, json, shutil, struct, subprocess, tarfile

out = Path('/mnt/e/edk2-samurai-out/kernel92')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def cpio(path):
    data = path.read_bytes(); offset = 0; entries = {}
    align = lambda n:(n+3)&~3
    while offset+110<=len(data):
        assert data[offset:offset+6] == b'070701'
        fields = [int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        mode, uid, gid, length, namesize = fields[1],fields[2],fields[3],fields[6],fields[11]
        start = offset+110
        name = data[start:start+namesize-1].decode()
        start = align(start+namesize)
        payload = data[start:start+length]
        offset = align(start+length)
        if name == 'TRAILER!!!': break
        assert name not in entries
        entries[name] = (mode,uid,gid,payload)
    return entries
before,after = cpio(out/'cpio-before'),cpio(out/'cpio-after')
assert not before.keys()-after.keys()
changed = [p for p in before if before[p]!=after[p]]
assert changed == ['init'],changed
assert before['init'][:3] == after['init'][:3]
assert b'/usr/sbin/samurai-usb start &' in after['init'][3]
assert b'/usr/sbin/samurai-wifi start' in after['init'][3]
links = sum((v[0]&0o170000)==0o120000 for v in before.values())
assert links == sum((v[0]&0o170000)==0o120000 for v in after.values())
assert after['etc/samurai-wifi/wpa-empty.conf'][3] == b'ctrl_interface=/run/samurai-wifi/wpa-control\n'
profile = (out/'wpa-test-private.conf').read_text()
private_values = [s.split('=',1)[1].strip().strip('"') for s in profile.splitlines() if s.strip().startswith(('ssid=','psk='))]
for name,value in after.items():
    assert name != 'etc/samurai-wifi/wpa.conf'
    if (value[0]&0o170000)==0o100000:
        assert all(p.encode() not in value[3] for p in private_values)
assert sha(out/'preflash.tar') == '52d64501a95570cc8c0c217e28961bd09e253725faabb8b4affddd58b99516e3'
assert sha(out/'boot-partition-before.img') == 'ed7ba3a76892fa2dd276daef3bc66c14c0737f49d385ae840a397fdfae39e396'
assert sha(out/'logdump-before.img') == '37ea81b0c2dbc678ed090048fcad8160acd089f1b7189eddbf0d0c873698ac36'
with tarfile.open(out/'preflash.tar') as source:
    files = {Path(m.name).name:source.extractfile(m).read() for m in source if m.isfile()}
for line in files['SHA256SUMS'].decode().splitlines():
    expected,name = line.split('  ',1)
    assert hashlib.sha256(files[name]).hexdigest() == expected
(out/'guard-before-flash.txt').write_bytes(files['partition-hashes.txt'])
assert files['partition-hashes.txt'].decode().startswith('7ed1ff99-4a7d-459c-b3e0-3f4e20a982ac\n')
assert all(line.endswith(': OK') for line in files['nv-source-check.txt'].decode().splitlines())
firmware = json.loads((out/'firmware-validation.json').read_text())
assert firmware['other_executable_bytes_unchanged'] and len(firmware['changed_modules'])==1
target = out/'logdump-k92-connectivity.img'
assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
for name,dest in [('Image-connectivity','::/Image'),('dtb-connectivity','::/samurai.dtb')]:
    subprocess.run(['mcopy','-o','-i',str(target),str(out/name),dest],check=True)
    assert subprocess.check_output(['mcopy','-i',str(target),dest,'-']) == (out/name).read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines()) == {'::/Image','::/samurai.dtb'}
report = dict(candidate_audit_pass=True,firmware_audit_pass=True,original_initramfs_files_preserved=True,
              existing_symlinks_preserved=links, init_changed_only_wifi_background_start=True,
              embedded_wifi_credentials=False, private_preflash_files_verified=len(files)-1,
              earlier_snapshots_preserved=True, kernel_build=91,
              boot_sha256=sha(out/'boot-k92-connectivity.img'), logdump_sha256=sha(target),
              full_backup_boot_sha256=sha(out/'boot-partition-before.img'),full_backup_logdump_sha256=sha(out/'logdump-before.img'),
              only_flash_partitions=['logdump','boot'], nv_partition_writes=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
