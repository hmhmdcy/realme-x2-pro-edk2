from pathlib import Path
import runpy,subprocess,shutil,hashlib,json
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/ensure-build-volume.py')
mount=Path('/home/cy122/pmos-samurai-kernel118')
source=Path('/home/cy122/pmos-samurai-kernel116')
dest=mount/'camera120';out=Path('/mnt/e/edk2-samurai-out/kernel120')
assert shutil.disk_usage(mount).free>8*1024**3 and not dest.exists()
assert hashlib.sha256((source/'kernel/arch/arm64/boot/Image').read_bytes()).hexdigest()=='7ad5e8ffc60c2635649977d1100574574853708a4f6bc39090964a456554f275'
dest.mkdir()
subprocess.run(['cp','-a',str(source/'kernel'),str(dest/'kernel')],check=True,timeout=240)
subprocess.run(['cp','-a',str(source/'initramfs'),str(dest/'initramfs')],check=True,timeout=30)
k=dest/'kernel'
patch=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel118/dpu-final-read.patch')
if not patch.exists():
    candidates=list(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel118').glob('*final*patch'))
    assert len(candidates)==1
    patch=candidates[0]
subprocess.run(['git','apply','--check',str(patch)],cwd=k,check=True)
subprocess.run(['git','apply',str(patch)],cwd=k,check=True)
config=k/'.config';before=config.read_text()
assert '/home/cy122/pmos-samurai-kernel116/initramfs' in before
config.write_text(before.replace('/home/cy122/pmos-samurai-kernel116/initramfs',str(dest/'initramfs')))
subprocess.run([str(k/'scripts/config'),'--module','I2C_QCOM_CCI'],cwd=k,check=True)
report=dict(candidate=120,base_camera_candidate=116,display_final_read_118_included=True,source_on_e_build_volume=True,source116_image_preserved=True,phone_not_changed=True)
Path('/mnt/e/RealmeX2Pro edk2/reference/kernel120/candidate-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
