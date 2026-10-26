from pathlib import Path
import difflib, hashlib, json, re, shutil, subprocess
root=Path('/mnt/e/RealmeX2Pro edk2'); ref=root/'reference/kernel103'
out=Path('/mnt/e/edk2-samurai-out/kernel103'); old=out.parent/'kernel102'
k=Path('/home/cy122/x2pro-linux/linux'); init=k.parent/'initramfs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out/'preparation.json').exists()
assert sha(k/'arch/arm64/boot/Image')=='2672a9cdb0a90eb17be0e4b28f18a7fabf98ddaccb4f3b0043b166faa095a65e'
assert sha(k/'usr/initramfs_data.cpio')=='71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7'
assert (k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_bytes()==(root/'reference/kernel102/sm8150-samurai.dts.after').read_bytes()
base=(out/'baseline-boot-private.txt').read_text(encoding='utf-8-sig').splitlines()
assert base[0]==(old/'runtime-boot-id-after-private.txt').read_text().strip()
assert '#101 SMP PREEMPT' in base[1]
pins=(out/'audio-pins-before-private.txt').read_text(encoding='utf-8-sig')
for n in (37,137,138,139,148):assert f'pin {n} (GPIO_{n}): UNCLAIMED' in pins
paths=['.config','arch/arm64/boot/Image','usr/initramfs_data.cpio','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',
       'arch/arm64/boot/dts/qcom/sm8150-samurai.dts','sound/soc/codecs/Kconfig','sound/soc/codecs/Makefile',
       'sound/soc/qcom/Kconfig','sound/soc/qcom/Makefile']
names=['config-before','Image-before','cpio-before','dtb-before','dts-before','codec-Kconfig-before',
       'codec-Makefile-before','qcom-Kconfig-before','qcom-Makefile-before']
assert all(not (out/n).exists() for n in names)
for p,n in zip(paths,names):shutil.copyfile(k/p,out/n)
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
(out/'initramfs-before.json').write_text(json.dumps({str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()},indent=2)+'\n')
# No hand-entered register shifts: translate the actual MAX98937 enum.
oem=k.parent/'refs/realme-amp-git-k102/audio-kernel/asoc/codecs/max989xx'
h=(oem/'max98937.h').read_text(); c=(oem/'max98937.c').read_text()
addr={a:int(b,16) for a,b in re.findall(r'\b(MAX98937_\w+)\s*=\s*(0x[0-9a-fA-F]+)\s*,',h)}
contract={'PCM_Mode_Config':0x23,'PCM_Master_Mode':0x24,'PCM_Clock_setup':0x25,
          'PCM_Sample_rate_setup_1':0x26,'PCM_Sample_rate_setup_2':0x27,
          'PCM_to_speaker_monomix_A':0x28,'PCM_to_speaker_monomix_B':0x29,
          'PCM_Rx_Enables_A':0x18,'PCM_Tx_Enables_A':0x1a,'PCM_Tx_HiZ_Control_A':0x1c,
          'PCM_Tx_DOUT_Control_1':0x1e,'Boost_Control_1':0x41,'Boost_Control_3':0x40,
          'AMP_enables':0x39,'AMP_volume_control':0x36,'Speaker_Gain':0x3b,
          'Global_Enable':0x500,'REV_ID':0x600}
for name,value in contract.items():assert addr['MAX98937_'+name]==value,name
table=c.split('int max98937_reg_common_map[][2] = {',1)[1].split('\n};',1)[0]
table=re.sub(r'//[^\n]*','',table)
rows=[(a,int(b,16)) for a,b in re.findall(r'\{(MAX98937_\w+),\s*(0x[0-9a-fA-F]+)\}',table)]
assert len(rows)==55,len(rows)
assert len({addr[a] for a,b in rows})==len(rows)
assert dict(rows)['MAX98937_Meas_ADC_Thermal_Shutdown_Threshhold']==0x8c
assert dict(rows)['MAX98937_Meas_ADC_Thermal_Warning_Threshhold']==0x75
assert dict(rows)['MAX98937_Meas_ADC_Thermal_Hysteresis']==8
# OEM no-DSM safe gain: digital 44, analog PCM 1. Keep PDM nibble unchanged.
overrides={'MAX98937_AMP_volume_control':44,'MAX98937_Speaker_Gain':0x51}
lines=[f'\t{{0x{addr[a]:04x}, 0x{overrides.get(a,b):02x}}}, /* {a.removeprefix("MAX98937_")} */' for a,b in rows]
driver=ref/'max98937-samurai.c'
s=driver.read_text();assert s.count('/* SAMURAI_MAX37_VERIFIED_TABLE */')==1
s=s.replace('\t/* SAMURAI_MAX37_VERIFIED_TABLE */','\n'.join(lines));driver.write_text(s)
targets={'sound/soc/codecs/max98937-samurai.c':'max98937-samurai.c',
         'sound/soc/qcom/samurai-audio.c':'samurai-audio.c'}
for p,n in targets.items():assert not (k/p).exists();shutil.copyfile(ref/n,k/p)
p=k/'sound/soc/codecs/Kconfig'
p.write_text(p.read_text()+'''\nconfig SND_SOC_MAX98937_SAMURAI
\ttristate "Realme X2 Pro MAX98937 revision 0x43"
\tdepends on I2C && OF && GPIOLIB
\tselect REGMAP_I2C
\thelp
\t  Board-specific native I2S playback with fixed conservative gain.
''')
p=k/'sound/soc/codecs/Makefile';p.write_text(p.read_text()+'\nobj-$(CONFIG_SND_SOC_MAX98937_SAMURAI) += max98937-samurai.o\n')
p=k/'sound/soc/qcom/Kconfig';s=p.read_text();end='endif #SND_SOC_QCOM';assert s.count(end)==1
s=s.replace(end,'''config SND_SOC_SAMURAI
\ttristate "Realme X2 Pro QDSP6 audio"
\tdepends on QCOM_APR && I2C && OF && COMMON_CLK
\tselect SND_SOC_QDSP6
\tselect SND_SOC_QCOM_COMMON
\tselect SND_SOC_WCD934X
\tselect SND_SOC_MAX98937_SAMURAI
\thelp
\t  Native Q6ASM/ADM/AFE, WCD934x SLIM and dual MAX98937 for Samurai.

'''+end);p.write_text(s)
p=k/'sound/soc/qcom/Makefile';p.write_text(p.read_text()+'\nobj-$(CONFIG_SND_SOC_SAMURAI) += samurai-audio.o\n')
p=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts';before=p.read_text();after=before+'\n'+(ref/'samurai-audio-card.dtsi').read_text();p.write_text(after)
(ref/'sm8150-samurai.dts.after').write_text(after)
(ref/'samurai-audio-dts.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts')))
subprocess.run(['scripts/config','--enable','SND_SOC_QCOM','--enable','SND_SOC_SAMURAI','--enable','SND_SOC_MAX98937_SAMURAI','--disable','SND_SOC_MAX98927'],cwd=k,check=True)
(out/'preparation.json').write_text(json.dumps(dict(prepared=True,stage=103,kernel_build=102,register_contract=contract,
  oem_c_sha256=sha(oem/'max98937.c'),oem_h_sha256=sha(oem/'max98937.h'),common_table_rows=len(rows),gain_overrides=overrides,
  alsa_card_added=True,initramfs_mutated=False,nv_mutated=False,calibration_written=False,physical_vibration_deferred=True,
  bluetooth_pair_or_connect=False,goal_complete=False),indent=2)+'\n')
print('SAMURAI_AUDIO_SOURCE_PREPARED')
