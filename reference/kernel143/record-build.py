from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import tarfile

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
stage=Path('/home/cy122/pmos-samurai-kernel136')
root=stage/'kernel'
def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda:file.read(4*1024*1024),b''):digest.update(block)
    return digest.hexdigest()
source=json.loads(ref.joinpath('source-validation.json').read_text())
tests=json.loads(ref.joinpath('actual-function-test-validation.json').read_text())
assert sha(root/'drivers/tty/serial/eud.c')==source['candidate_source_sha256']==tests['candidate_source_sha256']
assert tests['actual_function_cases']==16 and tests['results']['asan-ubsan']['returncode']==0
release=root.joinpath('include/config/kernel.release').read_text().strip()
assert release=='7.3.0-rc6-rmx1931-samurai-k132+'
assert '#143 SMP PREEMPT' in subprocess.check_output(['strings',str(root/'arch/arm64/boot/Image')],text=True)
assert root.joinpath('.config').read_bytes()==out.joinpath('config-before-private').read_bytes()
assert sha(root/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')=='97501daa5639223c018a19c120bce1dbcf45f60abcd404c406c4ee67821d6aa8'
assert out.joinpath('threaded-console-depmod-private.log').stat().st_size==0
logs='\n'.join(out.joinpath(name).read_text() for name in ['threaded-console-objects-build-private.log','threaded-console-image-build-private.log'])
assert not re.search(r'\b(?:warning|error):',logs)
with tarfile.open(out.parent/'kernel132/modules-k132-private.tar.gz') as archive:
    expected={m.name:archive.extractfile(m).read() for m in archive if m.isfile() and m.name.endswith('.ko')}
assert len(expected)==770
module_root=stage/'modules-root143'
actual={str(p.relative_to(module_root)):p for p in module_root.rglob('*.ko')}
assert actual.keys()==expected.keys()
assert all(actual[name].read_bytes()==content for name,content in expected.items())
for name in ['btbcm','btqca','hci_uart']:
    assert stage.joinpath('initramfs/lib/modules/samurai/'+name+'.ko').read_bytes()==expected[f'lib/modules/{release}/kernel/drivers/bluetooth/{name}.ko']
image=out/'Image-k143-threaded-console-private'
assert not image.exists()
shutil.copy2(root/'arch/arm64/boot/Image',image)
baseline=out.parent/'kernel132/logdump-k132-charger.img'
assert sha(baseline)=='db6b966975b987cd51e91f9488185b0a5e4a557755cc3b7043f0e6550aa19751'
target=out/'logdump-k143-threaded-console.img'
assert not target.exists()
shutil.copyfile(baseline,target)
subprocess.run(['mcopy','-o','-i',str(target),str(image),'::/Image'],check=True)
assert subprocess.check_output(['mcopy','-i',str(target),'::/Image','-'])==image.read_bytes()
assert subprocess.check_output(['mcopy','-i',str(target),'::/samurai.dtb','-'])==root.joinpath('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()
assert set(subprocess.check_output(['mdir','-b','-s','-i',str(target),'::'],text=True).splitlines())=={'::/Image','::/samurai.dtb'}
check=subprocess.run(['fsck.fat','-n',str(target)],capture_output=True)
out.joinpath('threaded-console-fat-check-private.txt').write_bytes(check.stdout+check.stderr)
assert check.returncode==0
artifacts=[('boot',out.parent/'kernel132/boot-partition-k132-charger.img'),('logdump',target),
    ('modules',out.parent/'kernel132/modules-k132-private.tar.gz'),('rootfs',out.parent/'kernel132/samurai-rootfs-f2fs-k132-device-fixed.simg')]
records=[dict(role=role,bytes=path.stat().st_size,sha256=sha(path),artifact_path=str(path)) for role,path in artifacts]
report=dict(stage=143,kernel_build=143,current_phone_kernel_build_before_deploy=140,software_generation=132,
    release=release,unsubmitted_unwind139_preserved=True,diagnostics140_preserved=True,
    eud_nbcon_threaded_normal_output=True,eud_frame_pacing_and_rx_protocol_preserved=True,
    eud_unsafe_panic_only_atomic_callback=True,host_actual_function_cases=16,
    image_sha256=sha(image),image_bytes=image.stat().st_size,
    all_770_modules_byte_identical132=True,initramfs_bt_modules_match=True,dtb_byte_identical132=True,
    boot132_reused=True,complete_rootfs132_reused=True,four_artifacts_fresh_hash_verified=True,
    artifacts=records,fat_readback_exact=True,fat_readonly_check_pass=True,
    kernel_build_no_warnings=True,depmod_no_diagnostics=True,
    flash_partitions=['logdump'],deployed=False,actual_runtime_verified=False,
    display_accepted=False,gpu_accepted=False,charging_accepted=False,goal_complete=False)
for folder in [ref,out]:folder.joinpath('threaded-console-build-package-validation.json').write_text(json.dumps(report,indent=2)+'\n')
preparation=json.loads(ref.joinpath('source-preparation-validation.json').read_text())
preparation['kernel_build_completed']=True
ref.joinpath('source-preparation-validation.json').write_text(json.dumps(preparation,indent=2)+'\n')
print(json.dumps({key:value for key,value in report.items() if key!='artifacts'},indent=2))
