from pathlib import Path
import hashlib, json, subprocess

stage=Path('/home/cy122/pmos-samurai-kernel114')
kernel=stage/'kernel'
out=Path('/mnt/e/edk2-samurai-out/kernel114')
sources=out/'primary-reference/aports/device/testing/linux-oneplus-hotdog-mainline616'
assert not (kernel/'drivers/net/ipa/data/ipa_data-v4.1.c').exists()
patch=next(sources.glob('0144-*.patch'))
# Linux 7.3 also has 5.2 platform data; retain it while adding 4.1.
text=patch.read_text()
start=text.index('diff --git a/drivers/net/ipa/data/')
adjusted=out/'0144-driver-without-older-makefile.patch'
adjusted.write_text(text[start:])
subprocess.run(['git','apply','--check',str(adjusted)],cwd=kernel,check=True)
subprocess.run(['git','apply',str(adjusted)],cwd=kernel,check=True)
makefile=kernel/'drivers/net/ipa/Makefile'
original=makefile.read_text()
assert original.count('3.1 3.5.1 4.2')==2
makefile.write_text(original.replace('3.1 3.5.1 4.2','3.1 3.5.1 4.1 4.2'))
for number in ['0145','0147']:
    p=next(sources.glob(number+'-*.patch'))
    subprocess.run(['git','apply','--check',str(p)],cwd=kernel,check=True)
    subprocess.run(['git','apply',str(p)],cwd=kernel,check=True)
p=next(sources.glob('0146-*.patch'))
subprocess.run(['git','apply','--check','--include=arch/arm64/boot/dts/qcom/sm8150.dtsi',str(p)],cwd=kernel,check=True)
subprocess.run(['git','apply','--include=arch/arm64/boot/dts/qcom/sm8150.dtsi',str(p)],cwd=kernel,check=True)
assert '&ipa {' not in (kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_text()
report=dict(ipa_driver_ported=True,makefile_retains_5_2=True,shared_soc_node_disabled=True,
            foreign_handset_board_diff_excluded=True,firmware_not_deployed=True,
            device_tree_not_deployed=True,new_kernel_not_deployed=True,
            own_downstream_ipa_version_4_1_confirmed=True,
            unresolved=['own_handset_imem_and_clock_verification','ipa_firmware_source_and_loader_mode','ipa_ssr_timeout_followup','runtime_probe_and_qmi_net_mapping'])
(out/'ipa-port-preparation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
