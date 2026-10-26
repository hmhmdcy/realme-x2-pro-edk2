from pathlib import Path
import hashlib,json,re,struct,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel102'
out=Path('/mnt/e/edk2-samurai-out/kernel102');k=Path('/home/cy122/x2pro-linux/linux')
init=Path('/home/cy122/x2pro-linux/initramfs')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ns={}
exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),ns)
old=ns['canonical'](ns['fdt_nodes']((out/'dtb-before').read_bytes()))
new=ns['canonical'](ns['fdt_nodes']((out/'dtb-audio').read_bytes()))
added=new.keys()-old.keys()
base='/soc@0/slim-ngd@171c0000';codec=base+'/slim@1/codec@1,0'
expected={'/soc@0/dma-controller@17184000',base,base+'/slim@1',base+'/slim@1/ifd@0,0',codec,
 codec+'/gpio@42','/soc@0/pinctrl@3100000/samurai-wcd-irq-default-state',
 '/soc@0/geniqup@8c0000/i2c@890000/amplifier@39','/soc@0/geniqup@8c0000/i2c@890000/amplifier@3a'}
assert added==expected,(added,expected)
assert not old.keys()-new.keys()
changed={p:sorted(key for key in old[p].keys()|new[p].keys() if old[p].get(key)!=new[p].get(key)) for p in old if old[p]!=new[p]}
assert changed=={'/soc@0/geniqup@8c0000/i2c@890000':['clock-frequency','status']},changed
assert new[codec]['reset-gpios']==[['/soc@0/pinctrl@3100000',[143,0]]]
assert new[codec]['interrupts-extended']==[['/soc@0/pinctrl@3100000',[123,4]]]
for prop in ('vdd-buck-supply','vdd-buck-sido-supply','vdd-tx-supply','vdd-rx-supply','vdd-io-supply'):
    assert new[codec][prop]==['/pm8150-s4'],new[codec][prop]
assert new[codec]['qcom,micbias2-microvolt']==struct.pack('>I',2700000).hex()
assert (out/'cpio-before').read_bytes()==(out/'cpio-after').read_bytes()
manifest=json.loads((out/'initramfs-before.json').read_text())
assert manifest=={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
assert (root/'linux-port/dts/sm8150-samurai.dts').read_bytes()==(out/'workspace-dts-mirror-before').read_bytes()
before=(out/'kernel-source-before.patch').read_text()
after=subprocess.check_output(['git','diff','--binary'],cwd=k,text=True)
# Compare every tracked source except the single board DTS.
def chunks(s):
    return {c.splitlines()[0]:c for c in s.split('diff --git ')[1:] if 'a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts b/' not in c.splitlines()[0]}
assert chunks(before)==chunks(after)
def config(p):
    return {m[1]:m[2] or 'n' for line in p.read_text().splitlines() if (m:=re.fullmatch(r'(?:# )?(CONFIG_\w+)(?:=(.+)| is not set)',line))}
a,b=config(out/'config-before'),config(out/'config-after')
delta={n:[a.get(n,'n'),b.get(n,'n')] for n in a.keys()|b.keys() if a.get(n,'n')!=b.get(n,'n')}
allowed={'CONFIG_SLIMBUS','CONFIG_SLIM_QCOM_NGD_CTRL','CONFIG_MFD_WCD934X','CONFIG_GPIO_WCD934X','CONFIG_REGMAP_SLIMBUS'}
assert all(n in allowed or n.startswith('CONFIG_SND_SOC_') for n in delta),delta
for n in ('SLIMBUS','SLIM_QCOM_NGD_CTRL','MFD_WCD934X','GPIO_WCD934X','SND_SOC_WCD934X','SND_SOC_MAX98927','QCOM_BAM_DMA','SND_SOC_QDSP6_CORE'):
    assert b['CONFIG_'+n]=='y',n
assert b.get('CONFIG_SOUNDWIRE','n')==a.get('CONFIG_SOUNDWIRE','n')=='n'
assert (k/'drivers/input/misc/aw8697-samurai.c').read_bytes()==(root/'reference/kernel99/aw8697-samurai.c').read_bytes()
assert (out/'Image-audio').stat().st_size<63*1024*1024
report=dict(kernel_audit_pass=True,kernel_build=101,logical_stage=102,config_delta=delta,
 original_initramfs_files_preserved=True,initramfs_byte_identical=True,all_existing_modules_byte_identical=True,
 earlier_snapshots_preserved=True,dtb_added_nodes=sorted(added),dtb_changed_properties=changed,
 other_dtb_nodes_semantically_preserved=True,other_tracked_sources_unchanged=True,
 image_bytes=(out/'Image-audio').stat().st_size,image_sha256=sha(out/'Image-audio'),
 dtb_sha256=sha(out/'dtb-audio'),cpio_sha256=sha(out/'cpio-after'),
 alsa_card_added=False,pcm_or_output_tested=False,physical_vibration_deferred_by_user=True,goal_complete=False)
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('AUDIO_TRANSPORT_KERNEL_AUDIT_PASS')
