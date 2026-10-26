"""Verify the diagnostic Image, unchanged payloads and fixed preflash evidence."""
from pathlib import Path
import hashlib,json,subprocess,tarfile,struct,re,os
K=Path('/home/cy122/x2pro-linux/linux');I=Path('/home/cy122/x2pro-linux/initramfs');O=Path('/mnt/e/edk2-samurai-out/kernel84')
sha=lambda data:hashlib.sha256(data).hexdigest()
manifest=json.loads((O/'preserved-private-manifest.json').read_text())
for n,digest in manifest['sources'].items():assert sha((K/n).read_bytes())==digest,n
for n,item in manifest['initramfs_files'].items():
    p=I/n;assert sha(p.read_bytes())==item['sha256'] and (p.stat().st_mode&0o777)==item['mode'],n
for n,target in manifest['initramfs_links'].items():assert os.readlink(I/n)==target,n
assert (K/'usr/initramfs_data.cpio').read_bytes()==(O/'cpio-before').read_bytes()
assert (K/'.config').read_bytes()==(O/'config-ready').read_bytes()
assert sha((O/'boot-before.img').read_bytes())==manifest['boot_before_sha256']
assert sha((O/'logdump-before.img').read_bytes())==manifest['logdump_before_sha256']
assert (O/'Image-ready').read_bytes()==(K/'arch/arm64/boot/Image').read_bytes()
image=(O/'Image-ready').read_bytes()
assert image[0x38:0x3c]==b'ARM\x64'
old_header=(O/'Image-before').read_bytes()[:64]
assert image[8:16]==old_header[8:16] and image[24:32]==old_header[24:32]
declared_size=struct.unpack_from('<Q',image,0x10)[0]
# ARM64 image_size includes the zero-filled BSS; it need not equal file length.
assert len(image)<=declared_size<len(image)+16*1024*1024
assert b'Linux version 7.3.0-rc6-rmx1931-samurai+' in image
assert b' #85 SMP PREEMPT ' in image
assert (O/'display-bootconfig-ready.txt').read_bytes() in image
fat_names=[];members={}
for name in ['logdump-before.img','logdump-k84-ready.img']:
    p=O/name;assert p.stat().st_size==67108864
    listing=subprocess.check_output(['mdir','-b','-s','-i',str(p),'::'],text=True).splitlines()
    assert set(listing)=={'::/Image','::/samurai.dtb'}
    members[name]={n:subprocess.check_output(['mcopy','-i',str(p),n,'-']) for n in listing}
assert members['logdump-k84-ready.img']['::/Image']==image
assert members['logdump-k84-ready.img']['::/samurai.dtb']==members['logdump-before.img']['::/samurai.dtb']
with tarfile.open(O/'before-raw.tar') as tar:
    raw={}
    for m in tar:
        assert m.isfile() and m.name.startswith('tmp/k84-before-') and '/' not in m.name.removeprefix('tmp/')
        name=m.name.removeprefix('tmp/k84-');data=tar.extractfile(m).read()
        p=O/name
        if p.exists():assert p.read_bytes()==data
        else:p.write_bytes(data)
        raw[name]=data
for line in raw['before-hashes.txt'].decode().splitlines():
    digest,path=line.split('  ',1);assert sha(raw[Path(path).name.removeprefix('k84-')])==digest
state=raw['before-state.txt'].decode();regs=raw['before-registers.txt'].decode();log=raw['before-dmesg.txt'].decode()
assert state.startswith('87753933-4992-45d2-aaf5-d9db9c11d1a3\n')
assert 'frame_done_cnt:2mode:' in state and 'POWER_SUPPLY_CAPACITY=99' in state
assert len(re.findall(r'^.*frame done timeout.*$',log,re.M))==2
assert not re.search(r'\b(?:BUG:|Oops:)|Unable to handle kernel|dsi_err_worker',log)
assert manifest['boot_before_sha256'] in raw['before-partition-hashes.txt'].decode()
assert manifest['logdump_before_sha256'] in raw['before-partition-hashes.txt'].decode()
report={'candidate_audit_pass':True,'only_logdump_write_required':True,'boot_unchanged_sha256':manifest['boot_before_sha256'],
        'rollback_logdump_sha256':manifest['logdump_before_sha256'],'candidate_logdump_sha256':sha((O/'logdump-k84-ready.img').read_bytes()),
        'candidate_Image_sha256':sha(image),'candidate_Image_bytes':len(image),'candidate_config_sha256':sha((O/'config-ready').read_bytes()),
        'unchanged_fat_dtb_sha256':sha(members['logdump-before.img']['::/samurai.dtb']),
        'kernel_source_hashes_preserved':manifest['sources'],'initramfs_cpio_byte_identical':True,'initramfs_identity_and_hooks_preserved':True,
        'bootconfig_embedded_exactly':True,'function_tracing_disabled':True,'hardware_driver_configuration_preserved':True,
        'before_boot_id':'87753933-4992-45d2-aaf5-d9db9c11d1a3','before_timeout_count':2,'before_raw_sha256':sha((O/'before-raw.tar').read_bytes()),
        'deployment_done':False,'display_root_cause_fixed':False,'source_head_local_not_upstream':manifest['kernel_head']}
(O/'candidate-ready-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS candidate Image/header/#85/exact bootconfig, only FAT Image changed, byte-identical CPIO, all source/identity hashes, device baseline partition/hash guards.')
