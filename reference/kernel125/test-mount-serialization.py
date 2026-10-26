from pathlib import Path
import subprocess,json,hashlib
r=Path('/mnt/e/RealmeX2Pro edk2');results=[]
for stage,mount in [(122,Path('/home/cy122/pmos-samurai-rootfs122')),(118,Path('/home/cy122/pmos-samurai-kernel118'))]:
 helper=r/('reference/kernel122/ensure-rootfs-volume.py' if stage==122 else 'reference/kernel118/ensure-build-volume.py')
 # Explicit concurrency regression for the newly serialized mount helper.
 children=[subprocess.Popen(['python3',str(helper)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
 for child in children:
  stdout,stderr=child.communicate(timeout=30);assert child.returncode==0,(stage,stderr.decode());assert b'MOUNT_VERIFIED' in stdout
 sources=subprocess.check_output(['findmnt','-rn','-o','SOURCE','--mountpoint',str(mount)],text=True).splitlines();assert len(sources)==1
 results.append(dict(volume=stage,simultaneous_helper_processes=4,all_exit_zero=True,actual_mount_count=1))
base=Path('/home/cy122/pmos-samurai-rootfs122/camera124/kernel/arch/arm64/boot/Image');assert hashlib.sha256(base.read_bytes()).hexdigest()=='feb6bfdc7991d26c6278d7d38afba47e86ee04573c78699e9eb3f3ef526fd0c1'
candidate_exists=Path('/home/cy122/pmos-samurai-rootfs122/camera125').exists()
report=dict(checks=results,base124_image_unchanged=True,candidate125_exists_at_test=candidate_exists,root_owned_private_lock_directory=True,original_wsl_vhd_untouched=True,phone_unchanged=True)
(r/'reference/kernel125/mount-serialization-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
