from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077);here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel214');private.mkdir(mode=0o700)
prior=here.parent/'kernel213';negative=json.loads((prior/'transport-recovery-validation.json').read_text());assert negative==dict(strict_original_key_wifi_responsive=False)
(here/'initial-connection-validation.json').write_text(json.dumps(dict(stage=214,strict_original_key_wifi_responsive=False,no_device_mutation=True),indent=2)+'\n')
historical=Path('/home/cy122/edk2-samurai/repo/Platform/Realme/sm8150/reference/kernel213/transport-recovery-validation.json');old=json.loads(historical.read_text());assert old['strict_original_key_wifi_responsive'] and old['current213_guard_verified'] and old['taint']==0
(private/'213-probe-overwritten-negative-private.json').write_text(json.dumps(negative,indent=2)+'\n');(prior/'transport-recovery-validation.json').write_bytes(historical.read_bytes())
archive=repo/'archive/NEXT-SESSION-through213-2026-10-16.md';assert not archive.exists();archive.write_bytes((repo/'NEXT-SESSION.md').read_bytes())
native=Path('/home/cy122/pmos-samurai-rootfs01/work/chroot_native')
inventory=dict(qemu=shutil.which('qemu-aarch64'),qemu_version=subprocess.check_output(['qemu-aarch64','--version'],text=True).splitlines()[0],native_chroot_present=native.is_dir(),native_candidate_tools=[str(p.relative_to(native)) for p in (native/'usr/bin').iterdir() if any(s in p.name for s in ['aarch64','gcc','g++','abuild','pmbootstrap','qemu'])],native_cross_gcc_dirs=[str(p) for p in (native/'usr/lib/gcc').glob('*/*')],binfmt_files=[str(p) for p in Path('/proc/sys/fs/binfmt_misc').glob('*')],host_tools={n:shutil.which(n) for n in ['meson','ninja','aarch64-linux-gnu-g++','qemu-aarch64','pmbootstrap','patch','pkg-config']})
instructions={}
for root in [Path('/'),Path('/home'),Path('/home/cy122'),native.parent.parent,native.parent,Path('/home/cy122/pmos-samurai-rootfs01/pmaports'),Path('/home/cy122/pmos-samurai-rootfs01/pmaports/temp'),Path('/home/cy122/pmos-samurai-rootfs01/pmaports/temp/libcamera')]:
    p=root/'AGENTS.md'
    if p.is_file():instructions[str(p)]=p.read_text()
inventory['applicable_instruction_files']=instructions
(private/'host-build-inventory-private.json').write_text(json.dumps(inventory,indent=2)+'\n')
plan=dict(stage=214,previous_goal_turn_classification='progress:213 source fix and actual synchronized RAW/fixed-white A/B proved CPU ISP first-frame defect and candidate repair; device products unchanged. Later transport failed and archive recovery incomplete.',device_guard='/var/lib/samurai/k213-baseline/boot-id-private.txt',device_transport='reference/kernel213/host.py with private selected Wi-Fi',device_mutation_performed=False,transition_pending=False,next='Use existing host Alpine cross-build facilities or ARM emulator to preserve original libcamera auto,virtual pipelines, IPAs/proxies/tools/tuning, integrate3 verified patches, build signed reproducible camera packages. Restore fresh authenticated device guard before installation. Fix camera source sync coverage. Full peripheral goal active.')
(private/'current-work-private.json').write_text(json.dumps(plan,indent=2)+'\n')
print(json.dumps(inventory))
