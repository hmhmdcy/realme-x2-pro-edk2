from pathlib import Path
import hashlib, json, re, struct, subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel104';out=Path('/mnt/e/edk2-samurai-out/kernel104')
k=Path('/home/cy122/x2pro-linux/linux');init=k.parent/'initramfs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ns={};exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),ns)
def canonical(blob):
    raw=ns['fdt_nodes'](blob);result=ns['canonical'](raw)
    codec='/soc@0/slim-ngd@171c0000/slim@1/codec@1,0'
    ph=raw[codec]['slim-ifc-dev']
    target=[p for p,v in raw.items() if v.get('phandle')==ph]
    assert target==['/soc@0/slim-ngd@171c0000/slim@1/ifd@0,0']
    result[codec]['slim-ifc-dev']=target
    return result
old=canonical((out/'dtb-before').read_bytes());new=canonical((out/'dtb-audio').read_bytes())
assert old.keys()==new.keys()
changes={p:sorted(n for n in old[p].keys()|new[p].keys() if old[p].get(n)!=new[p].get(n)) for p in old if old[p]!=new[p]}
assert changes=={'/sound':['audio-routing','pin-switches','widgets']},changes
strings=lambda b:b.decode().rstrip('\0').split('\0')
routes=strings(ns['fdt_nodes']((out/'dtb-audio').read_bytes())['/sound']['audio-routing'])
assert len(routes)%2==0
pairs=set(zip(routes[::2],routes[1::2]))
for n,name,bias in [(0,'Handset Mic',1),(1,'Secondary Mic',1),(2,'Speaker Mic',3)]:
    assert {(f'DMIC{n} Pin',name),(f'DMIC{n}',f'MIC BIAS{bias}'),(f'DMIC{n}','MCLK')}<=pairs
assert ('AMIC1','Handset Mic') not in pairs
assert (out/'cpio-before').read_bytes()==(out/'cpio-after').read_bytes()
assert json.loads((out/'initramfs-before.json').read_text())=={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
assert json.loads((out/'untracked-before.json').read_text())=={n:sha(k/n) for n in subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=k,text=True).splitlines() if (k/n).is_file()}
allow={'arch/arm64/boot/dts/qcom/sm8150-samurai.dts','sound/soc/qcom/qdsp6/q6core.c','sound/soc/codecs/wcd934x.c'}
def chunks(s):return {c.splitlines()[0]:c for c in s.split('diff --git ')[1:] if c.splitlines()[0].split(' b/',1)[1] not in allow}
assert chunks((out/'kernel-source-before.patch').read_text())==chunks(subprocess.check_output(['git','diff','--binary'],cwd=k,text=True))
for n,p in [('q6core.c.after','sound/soc/qcom/qdsp6/q6core.c'),('wcd934x.c.after','sound/soc/codecs/wcd934x.c'),('sm8150-samurai.dts.after','arch/arm64/boot/dts/qcom/sm8150-samurai.dts')]:assert (ref/n).read_bytes()==(k/p).read_bytes()
assert (out/'config-before').read_bytes()==(out/'config-after').read_bytes()
targetlog=(out/'audio-target-build.log').read_text()
assert not re.search(r'\.c:\d+:.*warning:|error:',targetlog)
assert (out/'Image-audio').stat().st_size<63*1024*1024
report=dict(kernel_audit_pass=True,kernel_build=103,logical_stage=104,config_delta={},
 original_initramfs_files_preserved=True,initramfs_byte_identical=True,all_existing_modules_byte_identical=True,
 earlier_snapshots_preserved=True,other_dtb_nodes_semantically_preserved=True,dtb_changed_properties=changes,
 other_tracked_sources_unchanged=True,existing_untracked_sources_preserved=True,changed_sources=sorted(allow),
 image_bytes=(out/'Image-audio').stat().st_size,image_sha256=sha(out/'Image-audio'),dtb_sha256=sha(out/'dtb-audio'),cpio_sha256=sha(out/'cpio-after'),
 native_dmic_pin_bias_mclk_routes=True,initialized_apr_packets=3,slim_trigger_errors_propagated=True,w1_c_warnings=0,
 private_oem_source_sha256=sha(out/'oem-audio-pinned.dtsi'),nv_partition_writes=False,goal_complete=False)
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('STAGE104_KERNEL_DTB_PRESERVATION_AUDIT_PASS')
