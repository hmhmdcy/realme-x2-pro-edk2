from pathlib import Path
import hashlib,json,re,struct,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel103';out=Path('/mnt/e/edk2-samurai-out/kernel103')
k=Path('/home/cy122/x2pro-linux/linux');init=k.parent/'initramfs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ns={};exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),ns)
def audio_canonical(blob):
    raw=ns['fdt_nodes'](blob);result=ns['canonical'](raw)
    codec='/soc@0/slim-ngd@171c0000/slim@1/codec@1,0'
    ph=struct.unpack('>I',raw[codec]['slim-ifc-dev'])[0]
    targets=[p for p,v in raw.items() if v.get('phandle')==struct.pack('>I',ph)]
    assert targets==['/soc@0/slim-ngd@171c0000/slim@1/ifd@0,0'],targets
    result[codec]['slim-ifc-dev']=targets
    return result
old=audio_canonical((out/'dtb-before').read_bytes())
new=audio_canonical((out/'dtb-audio').read_bytes())
assert not old.keys()-new.keys()
changed={p:sorted(n for n in old[p].keys()|new[p].keys() if old[p].get(n)!=new[p].get(n)) for p in old if old[p]!=new[p]}
amps=['/soc@0/geniqup@8c0000/i2c@890000/amplifier@'+a for a in ('39','3a')]
assert changed=={p:['compatible','maxim,interleave-mode','realme,pcm-channel','sound-name-prefix','vdd-supply'] for p in amps},changed
added=new.keys()-old.keys()
apr='/soc@0/remoteproc@17300000/glink-edge/apr'
expected={apr+'/service@4',apr+'/service@4/dais',apr+'/service@4/dais/dai@16',
 apr+'/service@7',apr+'/service@7/dais',apr+'/service@7/dais/dai@0',apr+'/service@7/dais/dai@1',
 apr+'/service@8',apr+'/service@8/routing','/soc@0/pinctrl@3100000/samurai-quat-audio-state',
 '/soc@0/pinctrl@3100000/samurai-quat-sleep-state','/sound'}
for n,children in [('playback-dai-link',['cpu']),('capture-dai-link',['cpu']),
                   ('speaker-dai-link',['cpu','platform','codec']),('headphone-dai-link',['cpu','platform','codec']),
                   ('microphone-dai-link',['cpu','platform','codec'])]:
    expected.add('/sound/'+n);expected.update('/sound/'+n+'/'+s for s in children)
assert added==expected,(added-expected,expected-added)
assert new[apr+'/service@7/dais']['iommus']==[['/soc@0/iommu@15000000',[0x1b21,0]]]
assert (out/'cpio-before').read_bytes()==(out/'cpio-after').read_bytes()
assert json.loads((out/'initramfs-before.json').read_text())=={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
allow={'arch/arm64/boot/dts/qcom/sm8150-samurai.dts','sound/soc/codecs/Kconfig','sound/soc/codecs/Makefile','sound/soc/qcom/Kconfig','sound/soc/qcom/Makefile'}
def chunks(s):return {c.splitlines()[0]:c for c in s.split('diff --git ')[1:] if c.splitlines()[0].split(' b/',1)[1] not in allow}
assert chunks((out/'kernel-source-before.patch').read_text())==chunks(subprocess.check_output(['git','diff','--binary'],cwd=k,text=True))
for n,p in [('max98937-samurai.c','sound/soc/codecs/max98937-samurai.c'),('samurai-audio.c','sound/soc/qcom/samurai-audio.c')]:assert (ref/n).read_bytes()==(k/p).read_bytes()
def config(p):return {m[1]:m[2] or 'n' for l in p.read_text().splitlines() if (m:=re.fullmatch(r'(?:# )?(CONFIG_\w+)(?:=(.+)| is not set)',l))}
a,b=config(out/'config-before'),config(out/'config-after')
delta={n:[a.get(n,'n'),b.get(n,'n')] for n in a.keys()|b.keys() if a.get(n,'n')!=b.get(n,'n')}
assert all(n.startswith('CONFIG_SND_SOC_') for n in delta),delta
for n in ('QCOM','SAMURAI','MAX98937_SAMURAI','WCD934X','QCOM_COMMON','QDSP6_ASM','QDSP6_AFE','QDSP6_ADM'):assert b['CONFIG_SND_SOC_'+n]=='y',n
assert b.get('CONFIG_SND_SOC_MAX98927','n')=='n'
assert b.get('CONFIG_SOUNDWIRE','n')=='n'
assert sha(k/'drivers/input/misc/aw8697-samurai.c')=='7f9d2cec9a982ec3d1fddb6e96d041750e7a32b45ae5caa1a407239f9e4ef443'
assert (out/'Image-audio').stat().st_size<63*1024*1024
report=dict(kernel_audit_pass=True,kernel_build=102,logical_stage=103,config_delta=delta,
 original_initramfs_files_preserved=True,initramfs_byte_identical=True,all_existing_modules_byte_identical=True,
 earlier_snapshots_preserved=True,other_dtb_nodes_semantically_preserved=True,dtb_added_nodes=sorted(added),dtb_changed_properties=changed,
 other_tracked_sources_unchanged=True,new_audio_sources_verified=True,image_bytes=(out/'Image-audio').stat().st_size,
 image_sha256=sha(out/'Image-audio'),dtb_sha256=sha(out/'dtb-audio'),cpio_sha256=sha(out/'cpio-after'),
 alsa_card_added=True,speaker_revision_required=0x43,calibration_or_nv_written=False,goal_complete=False)
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('SAMURAI_AUDIO_KERNEL_AUDIT_PASS')
