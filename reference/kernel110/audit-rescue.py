from pathlib import Path
import hashlib,json,shutil,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel110')
base=out.parent/'kernel109'
stage=Path('/home/cy122/pmos-samurai-kernel110')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(out/'dtb-rescue')==sha(base/'dtb-pmos')
def config(path):
    return dict(line.split('=',1) for line in path.read_text().splitlines() if line.startswith('CONFIG_') and '=' in line)
old=config(base/'config-after');new=config(out/'config-after')
delta={key:(old.get(key),new.get(key)) for key in old.keys()|new.keys() if old.get(key)!=new.get(key)}
assert set(delta)=={'CONFIG_INITRAMFS_SOURCE'}
init=(stage/'initramfs/init').read_text()
assert '[rescue110]' in init and '. /usr/sbin/samurai-rootfs' not in init
assert '/usr/sbin/samurai-wifi start' not in init and '/usr/sbin/samurai-bluetooth boot' not in init
image=out/'logdump-rescue110.img'
assert not image.exists()
shutil.copyfile(base/'logdump-k109-pmos.img',image)
subprocess.run(['mcopy','-o','-i',str(image),str(out/'Image-rescue'),'::/Image'],check=True)
subprocess.run(['mcopy','-i',str(image),'::/Image',str(out/'Image-from-fat')],check=True)
subprocess.run(['mcopy','-i',str(image),'::/samurai.dtb',str(out/'dtb-from-fat')],check=True)
assert sha(out/'Image-from-fat')==sha(out/'Image-rescue')
assert sha(out/'dtb-from-fat')==sha(base/'dtb-pmos')
assert image.stat().st_size==67108864
result=dict(stage=110,role='diagnostic-rescue',candidate_audit_pass=True,
    kernel_build=110,dtb_byte_identical_to_deployed109=True,
    config_delta_keys=sorted(delta),userdata_mount_on_boot=False,
    automatic_radio_services=False,partitions_flashed=[],deployed=False,
    logdump_sha256=sha(image),image_sha256=sha(out/'Image-rescue'))
(out/'rescue-validation.json').write_text(json.dumps(result,indent=2)+'\n')
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel110/rescue-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('RESCUE110_CANDIDATE_AUDITED_NOT_DEPLOYED')
