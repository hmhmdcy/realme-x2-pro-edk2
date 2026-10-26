from pathlib import Path, PurePosixPath
import hashlib, json, re, shutil, subprocess, tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel109')
stage=Path('/home/cy122/pmos-samurai-kernel109')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel109')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((out/'preparation.json').read_text())
tests=json.loads((out/'panel-tests.json').read_text());assert tests['pass_actual_callbacks']
files={}
with tarfile.open(out/'preflash.tar') as tar:
    for m in tar:
        if not m.isfile():continue
        n=PurePosixPath(m.name);assert n.parts[0]=='k109-preflash-complete' and '..' not in n.parts
        files[str(PurePosixPath(*n.parts[1:]))]=tar.extractfile(m).read()
assert all(hashlib.sha256(files[n.removeprefix('./')]).hexdigest()==h for h,n in (line.split('  ',1) for line in files['SHA256SUMS'].decode().splitlines()))
guard=files['guard.txt'].decode();assert guard.splitlines()[0]==p['before_boot_id']
for name,key in [('boot-partition-before.img','expected_full_boot_sha256'),('logdump-before.img','expected_logdump_sha256')]:
    assert sha(out/name)==p[key] and p[key] in guard
(out/'guard-before-flash.txt').write_text(guard)
assert sha(out/'dtb-pmos')==sha(out/'dtb-before')
before={m.group(1):m.group(2) for m in re.finditer(r'^(CONFIG_\w+)=(.*)$',(out/'config-before').read_text(),re.M)}
after={m.group(1):m.group(2) for m in re.finditer(r'^(CONFIG_\w+)=(.*)$',(out/'config-after').read_text(),re.M)}
delta={n:dict(before=before.get(n),after=after.get(n)) for n in before.keys()|after.keys() if before.get(n)!=after.get(n)}
assert all(n.startswith('CONFIG_F2FS_') or n=='CONFIG_INITRAMFS_SOURCE' for n in delta)
source=Path('/home/cy122/x2pro-linux/linux')
assert subprocess.check_output(['git','diff','--binary'],cwd=source)==(out/'kernel-source-before.patch').read_bytes()
for n,h in json.loads((out/'untracked-before.json').read_text()).items():assert sha(source/n)==h
for n,h in json.loads((out/'initramfs-before.json').read_text()).items():
    assert sha(source.parent/'initramfs'/n)==h
    if n!='init':assert sha(stage/'initramfs'/n)==h
target=out/'logdump-k109-pmos.img';assert not target.exists()
shutil.copyfile(out/'logdump-before.img',target)
oldnames=set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())
assert oldnames=={'::/Image','::/samurai.dtb'}
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==(out/'dtb-pmos').read_bytes()
subprocess.run(['mcopy','-o','-i',str(target),str(out/'Image-pmos'),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==(out/'Image-pmos').read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())==oldnames
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==(out/'dtb-pmos').read_bytes()
assert sha(Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'))==sha(out/'dtb-pmos')
bootconfig=after.get('CONFIG_BOOT_CONFIG_EMBED_FILE','').strip('"')
if bootconfig:assert Path(bootconfig).is_file()
sparse=json.loads((out/'sparse-validation.json').read_text())
assert sparse['expanded_bytes']==p['userdata_bytes'] and sparse['payload_matches_raw_source']
assert sparse['sha256']==sha(out/'samurai-rootfs-f2fs.simg')
assert 'NATIVE_USERSPACE_VALIDATION_PASS' in (out/'userspace-validation.log').read_text()
root=stage/'rootfs'
key=(root/'etc/ssh/ssh_host_ed25519_key.pub').read_text().split()
(out/'known_hosts-pmos').write_text('169.254.42.1 '+key[0]+' '+key[1]+'\n')
ssh=(ref.parent/'kernel72/usb-ssh.ps1').read_text().replace('E:/edk2-samurai-out/kernel72/known_hosts','E:/edk2-samurai-out/kernel109/known_hosts-pmos')
(ref/'usb-ssh-pmos.ps1').write_text(ssh)
scp=(ref/'scp-private.ps1').read_text().replace('E:/edk2-samurai-out/kernel72/known_hosts','E:/edk2-samurai-out/kernel109/known_hosts-pmos')
(ref/'scp-pmos.ps1').write_text(scp)
report=dict(candidate_audit_pass=True,kernel_build=109,source_and_original_initramfs_preserved=True,dtb_byte_identical=True,firmware_boot_unchanged=True,config_delta=delta,full_backup_boot_sha256=sha(out/'boot-partition-before.img'),full_backup_logdump_sha256=sha(out/'logdump-before.img'),preflash_sha256=sha(out/'preflash.tar'),before_boot_id=p['before_boot_id'],image_sha256=sha(out/'Image-pmos'),cpio_sha256=sha(out/'cpio-pmos'),logdump_sha256=sha(target),rootfs_sha256=sparse['sha256'],rootfs_sparse_bytes=sparse['sparse_bytes'],userdata_bytes=p['userdata_bytes'],userdata_authorized=True,flash_partitions=['userdata','logdump'],nv_partition_writes=False,gpt_writes=False,rootfs_ui='console',goal_complete=False)
(out/'candidate-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('CANDIDATE109_CURRENT_KERNEL_F2FS_USERSPACE_BACKUPS_FAT_HASH_AUDIT_PASS')
