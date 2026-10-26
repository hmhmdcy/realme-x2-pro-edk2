from pathlib import Path
import runpy,subprocess,os,json,hashlib
runpy.run_path('/mnt/e/RealmeX2Pro edk2/reference/kernel129/ensure-rootfs-volume.py')
stage=Path('/home/cy122/pmos-samurai-rootfs129');out=Path('/mnt/e/edk2-samurai-out/kernel132');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel132')
raw=stage/'samurai-rootfs-f2fs-k132-device-fixed-restored.raw.img';dest=stage/'image-export132-fixed';install=stage/'tools/install-root'
assert raw.is_file() and raw.stat().st_size==119033245696 and not dest.exists()
assert (out/'sparse-fixed-validation.json').is_file() and 'Done:' in (out/'fsck-fixed-restored-private.log').read_text()
loop=subprocess.check_output(['losetup','--find','--show','--read-only',str(raw)],text=True).strip();assert loop.startswith('/dev/loop')
assert subprocess.check_output(['blockdev','--getro',loop],text=True).strip()=='1'
try:
    with (out/'image-export-fixed-private.txt').open('w') as log:
        p=subprocess.run([str(install/'usr/local/sbin/dump.f2fs'),'-r','-f','-P','-L','-o',str(dest),loop],stdout=log,stderr=subprocess.STDOUT,env=dict(os.environ,LD_LIBRARY_PATH=str(install/'usr/local/lib')),timeout=300)
    assert p.returncode==0
finally:
    subprocess.run(['losetup','-d',loop],check=True,timeout=10)
report=dict(native_f2fs_directory_export_exit=p.returncode,sparse_reconstructed_image_used=True,input_loop_kernel_readonly=True,loop_detached=True,export_in_private_e_volume=True,phone_not_used=True,content_verification_pending=True)
(ref/'image-export-fixed-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
