from pathlib import Path
import hashlib,json,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel116');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel116')
k=Path('/home/cy122/pmos-samurai-kernel116/kernel');old=Path('/home/cy122/pmos-samurai-kernel115/kernel')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
log=(out/'kernel-full-build.log').read_text();assert 'Error ' not in log and 'error:' not in log
files={name:sha(k/name) for name in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','drivers/media/platform/qcom/camss/qcom-camss.ko','drivers/net/ipa/ipa.ko','usr/initramfs_data.cpio']}
assert files['arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']==sha(old/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')
assert sha(old/'arch/arm64/boot/Image')=='66e749a8e9902c5675af736706c193b645d7e1ab49f71980e5c0c652db45bfa2'
assert (k/'drivers/net/ipa/reg/ipa_reg-v4.1.c').read_bytes()==(old/'drivers/net/ipa/reg/ipa_reg-v4.1.c').read_bytes()
config=(k/'.config').read_text();assert 'CONFIG_VIDEO_QCOM_CAMSS=m\n' in config
assert b'#116 SMP PREEMPT' in subprocess.check_output(['strings',str(k/'vmlinux')])
subprocess.run(['git','diff','--check','--','drivers/media/platform/qcom/camss'],cwd=k,check=True)
report=dict(kernel_candidate=116,full_image_modules_dtb_build_pass=True,media_camss_configured=True,
 own_dt_csiphy_v1_1_reference_generation_port=True,regulator_bulk_api_adapted=True,
 dts_identical_to_115=True,ipa_delay_fix_preserved=True,baseline_115_image_preserved=True,
 image_and_module_hashes=files,cphy_dma_icc_qos_not_ported=True,physical_camera_nodes_not_enabled=True,not_deployed=True,goal_complete=False)
for folder in [out,ref]: (folder/'kernel-build-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
