from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel102'
out=Path('/mnt/e/edk2-samurai-out/kernel102')
old=out.parent/'kernel101'
k=Path('/home/cy122/x2pro-linux/linux')
init=Path('/home/cy122/x2pro-linux/initramfs')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((out/'stock-contract-validation.json').read_text())['stock_contract_archive_audit_pass']
assert sha(k/'arch/arm64/boot/Image')=='6edfea9d5c23bd55b623b8f57f21937f1f8c3e63467b0437ffe5021ae8aab19d'
assert sha(k/'usr/initramfs_data.cpio')=='71f0fac2cb4251214ba33c86bf332e2367cbaf676f877c4030d1228e71c64ae7'
assert sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')=='2fac32706a56743294f17d108e207937b237be0ef2d1a7c27bff5bcf8fe57f46'
assert not (out/'config-before').exists()
pins=(out/'runtime-pins-retry2-private.txt').read_text(encoding='utf-8-sig')
for n in (37,51,52,123,143,148):
    assert f'pin {n} (GPIO_{n}): UNCLAIMED' in pins
assert 'pin 54 (GPIO_54): device 3-0020' in pins
dts=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
assert dts.read_bytes()==(root/'reference/kernel101/sm8150-samurai.dts.after').read_bytes()
for name,p in [('config-before',k/'.config'),('Image-before',k/'arch/arm64/boot/Image'),
 ('cpio-before',k/'usr/initramfs_data.cpio'),('dtb-before',k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'),
 ('dts-before',dts),('workspace-dts-mirror-before',root/'linux-port/dts/sm8150-samurai.dts')]:
    shutil.copyfile(p,out/name)
(out/'kernel-source-before.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=k))
manifest={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
(out/'initramfs-before.json').write_text(json.dumps(manifest,indent=2)+'\n')
original=dts.read_text()
after=original+'\n'+(ref/'samurai-audio-transport.dtsi').read_text()
dts.write_text(after)
(ref/'samurai-audio-dts.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),after.splitlines(True),fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts')))
(ref/'sm8150-samurai.dts.after').write_text(after)
args=['scripts/config']
for name in ('SLIMBUS','SLIM_QCOM_NGD_CTRL','MFD_WCD934X','GPIO_WCD934X',
             'SND_SOC_WCD934X','SND_SOC_MAX98927'):
    args+=['--enable',name]
# WCD934X's optional SOUNDWIRE dependency must not reduce the codec to a
# module. There are no SoundWire speaker slaves in this board fragment.
args+=['--disable','SOUNDWIRE']
subprocess.run(args,cwd=k,check=True)
(out/'preparation.json').write_text(json.dumps(dict(prepared=True,logical_stage=102,kernel_build=101,
  stock_dtbo_readonly=True,codec_transport='slim217,250',amplifiers=['maxim,max98927']*2,
  amp_i2c_gpio=[51,52],touch_reset_gpio54_preserved=True,initramfs_mutated=False,
  driver_source_mutated=False,alsa_card_added=False,pcm_or_speaker_output_tested=False,
  bluetooth_pair_or_connect=False,physical_vibration_deferred_by_user=True,goal_complete=False),indent=2)+'\n')
print('AUDIO_TRANSPORT_SOURCE_PREPARED')
