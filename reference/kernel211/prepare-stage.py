from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077)
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel211');private.mkdir(mode=0o700)
previous=private.parent/'kernel210';shutil.copyfile(previous/'usb-ipv6-candidates-private.json',private/'usb-ipv6-candidates-private.json')
(here/'host.py').write_text((here.parent/'kernel210/host.py').read_text().replace("Path('/mnt/e/edk2-samurai-out/kernel210')","Path('/mnt/e/edk2-samurai-out/kernel211')"))
(here/'run-native.py').write_bytes((here.parent/'kernel210/run-native.py').read_bytes())
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');backup=private/'source-before';backup.mkdir(mode=0o700)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['drivers/media/i2c/imx471.c','.config','Module.symvers','modules.order','drivers/media/i2c/imx471.ko']
files={}
for name in names:
    p=k/name;shutil.copyfile(p,backup/name.replace('/','__'));files[name]=sha(p)
assert files['drivers/media/i2c/imx471.c']=='110977b81694bac72d9c87aec45367747b72526f9ea309863c0964c1af9f84d8'
assert files['.config']=='fbde369024fc3f7ef2cfec049844d246b74f6ec9d2b26416b4630c77a7795a6e'
files.update({n:sha(k/n) for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','arch/arm64/boot/dts/qcom/sm8150-samurai.dts']})
(backup/'hashes-private.json').write_text(json.dumps(files,indent=2)+'\n')
(backup/'git-diff-private.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
(backup/'git-status-private.txt').write_bytes(subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=k))
plan=dict(stage=211,previous_goal_turn='progress:210 changed static DT/config/modules, booted once, auto-bound front, captured6 accepted physical frames, established libcamera crop/DMA allocator gaps.',state='211 source/metadata backed up; native baseline pending. No211 product change or transition yet.',transport='reference/kernel211/host.py',guard='/var/lib/samurai/k210-runtime/boot-id-private.txt',transition_pending=False,gnss_environment='User confirmed indoors by window; do not repeat unchanged UTC/CNR experiments.',next='Fresh current phone/crop/heap-loader inventory; fix CROP break-to-EINVAL, verify heap provider loading/permissions, native/libcamera capture, guarded warm boot persistence. All five cameras and full peripheral goal retained.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
(here/'source-before-validation.json').write_text(json.dumps(dict(stage=211,source_and_build_metadata_backed_up=True,imx471_source_sha256=files['drivers/media/i2c/imx471.c'],config_sha256=files['.config'],no_source_mutation_yet=True),indent=2)+'\n')
print('211 transport and source backup prepared; previous turn classified as verified progress.')
