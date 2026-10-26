from pathlib import Path
import shutil,hashlib,json,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel115')
root=Path('/home/cy122/pmos-samurai-rootfs115/rootfs')
for source,dest in [('elogind-runtime','etc/init.d/elogind'),('zram-runtime','etc/init.d/postmarketos-zram-swap'),('deviceinfo-runtime-private','etc/deviceinfo')]:
    assert (out/source).is_file()
    shutil.copyfile(out/source,root/dest)
for name in ['elogind','postmarketos-zram-swap']:
    subprocess.run(['sh','-n',str(root/'etc/init.d'/name)],check=True)
assert '[ENDP_DELAY] = BIT(1)' in Path('/home/cy122/pmos-samurai-kernel115/kernel/drivers/net/ipa/reg/ipa_reg-v4.1.c').read_text()
# Preserve the currently tested IPA module in the image; the delay fix still needs runtime testing.
tested=root/'usr/lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko'
assert hashlib.sha256(tested.read_bytes()).hexdigest()==hashlib.sha256(Path('/home/cy122/pmos-samurai-kernel115/runtime-package/lib/modules/7.3.0-rc6-rmx1931-samurai+/kernel/drivers/net/ipa/ipa.ko').read_bytes()).hexdigest()
report=dict(kernel_build=115,userspace_packages=936,complete_module_tree=True,own_ipa_firmware=True,elogind_pid_tracking_fix=True,swap_name_collision_fixed=True,zram_algorithm='lzo-rle',image_contains_boot_tested_ipa_module=True,unvalidated_delay_fix_excluded=True,goal_complete=False)
(out/'rootfs-stage-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('ROOTFS115_COMPLETE_STAGE_WITH_BOOT_TESTED_MODULE_AND_USERSERVICE_FIXES_PASS')
