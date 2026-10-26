from pathlib import Path
import hashlib, json, re, struct, subprocess
root=Path('/mnt/e/RealmeX2Pro edk2')
out=Path('/mnt/e/edk2-samurai-out/kernel101')
k=Path('/home/cy122/x2pro-linux/linux')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ns={}
exec((root/'reference/kernel93/verify-firmware.py').read_text().split('\ndt_audit=')[0],ns)
exec((root/'reference/kernel73/dtb-canonical.py').read_text(),ns)
old=ns['canonical'](ns['fdt_nodes']((out/'dtb-before').read_bytes()))
new=ns['canonical'](ns['fdt_nodes']((out/'dtb-adsp').read_bytes()))
adsp='/soc@0/remoteproc@17300000'
apr=adsp+'/glink-edge/apr'
assert new.keys()-old.keys()=={apr,apr+'/service@3'}
assert not old.keys()-new.keys()
changed={p:sorted(key for key in old[p].keys()|new[p].keys() if old[p].get(key)!=new[p].get(key)) for p in old if old[p]!=new[p]}
assert changed=={adsp:['firmware-name','status']},changed
assert new[adsp]['firmware-name']==b'qcom/sm8150/realme/samurai/adsp.mdt\0'.hex()
assert new[adsp]['status']==b'okay\0'.hex()
assert new[apr]['qcom,domain']==struct.pack('>I',4).hex()
assert new[apr+'/service@3']['qcom,protection-domain']==b'avs/audio\0msm/adsp/audio_pd\0'.hex()
assert new[adsp]['memory-region']==['/reserved-memory/memory@9b200000'],new[adsp]['memory-region']
parse={}
exec((root/'reference/kernel100/audit-kernel.py').read_text().split('before,after=')[0],parse)
before,after=parse['cpio'](out/'cpio-before'),parse['cpio'](out/'cpio-after')
assert not before.keys()-after.keys()
changed_files=[]
for name,(fields,content) in before.items():
    nf,nc=after[name]
    assert [fields[i] for i in (1,2,3,4,7,8,9,10)]==[nf[i] for i in (1,2,3,4,7,8,9,10)],name
    if content!=nc:changed_files.append(name)
assert set(changed_files)=={'usr/sbin/samurai-wifi','usr/sbin/samurai-radio-address'},changed_files
fw='lib/firmware/qcom/sm8150/realme/samurai/'
expected={fw+p.name for p in (out/'adsp-firmware').iterdir()}|{'usr/sbin/samurai-modem-remoteproc'}
assert after.keys()-before.keys()==expected
for p in (out/'adsp-firmware').iterdir():assert after[fw+p.name][1]==p.read_bytes()
for name in ('samurai-wifi','samurai-radio-address','samurai-modem-remoteproc'):
    assert after['usr/sbin/'+name][1]==(root/'reference/kernel101'/name).read_bytes()
def config(p):
    return {m[1]:m[2] or 'n' for line in p.read_text().splitlines() if (m:=re.fullmatch(r'(?:# )?(CONFIG_\w+)(?:=(.+)| is not set)',line))}
a,b=config(out/'config-before'),config(out/'config-after')
delta={name:[a.get(name),b.get(name)] for name in a.keys()|b.keys() if a.get(name,'n')!=b.get(name,'n')}
unexpected={name:value for name,value in delta.items() if not name.startswith(('CONFIG_SND','CONFIG_SOUND')) and name not in ('CONFIG_QCOM_APR','CONFIG_QCOM_PDR_HELPERS','CONFIG_HDMI')}
rust_metadata={'CONFIG_RUSTC_VERSION','CONFIG_RUSTC_LLVM_VERSION','CONFIG_RUSTC_LLVM_MAJOR_VERSION',
  'CONFIG_RUSTC_HAS_FILE_WITH_NUL','CONFIG_RUSTC_HAS_SUSPICIOUS_RUNTIME_SYMBOL_DEFINITIONS',
  'CONFIG_RUSTC_HAS_UNNECESSARY_TRANSMUTES','CONFIG_RUSTC_HAS_FILE_AS_C_STR','CONFIG_RUSTC_HAS_SPAN_FILE'}
assert not unexpected.keys()-rust_metadata,unexpected
assert a.get('CONFIG_RUST','n')==b.get('CONFIG_RUST','n')=='n'
assert delta['CONFIG_QCOM_PDR_HELPERS']==['m','y']
for name in ('CONFIG_SOUND','CONFIG_SND','CONFIG_SND_SOC','CONFIG_SND_SOC_QDSP6_CORE','CONFIG_QCOM_APR','CONFIG_INPUT_SAMURAI_AW8697'):assert b[name]=='y'
assert (root/'linux-port/dts/sm8150-samurai.dts').read_bytes()==(out/'workspace-dts-mirror-before').read_bytes()
assert (k/'drivers/input/misc/aw8697-samurai.c').read_bytes()==(root/'reference/kernel99/aw8697-samurai.c').read_bytes()
assert (k/'sound/soc/qcom/qdsp6/q6core.c').read_text().count('DEVICE_ATTR_RO(samurai_api)')==1
assert (out/'cpio-after').read_bytes()==(out/'cpio-after.before-core-query').read_bytes()
assert (out/'dtb-adsp').read_bytes()==(out/'dtb-adsp.before-core-query').read_bytes()
assert (out/'Image-adsp').stat().st_size<64*1024*1024-1024*1024
report=dict(kernel_audit_pass=True,kernel_build=100,logical_stage=101,config_delta=delta,
  original_initramfs_files_preserved=True,all_existing_modules_byte_identical=True,init_byte_identical=True,
  earlier_snapshots_preserved=True,cpio_content_changes=changed_files,cpio_added_private_firmware_files=17,
  cpio_added_helper_files=1,dtb_added_nodes=sorted(new.keys()-old.keys()),dtb_changed_properties=changed,
  other_dtb_nodes_semantically_preserved=True,motor_driver_unchanged=True,physical_vibration_deferred_by_user=True,
  image_bytes=(out/'Image-adsp').stat().st_size,image_sha256=sha(out/'Image-adsp'),dtb_sha256=sha(out/'dtb-adsp'),cpio_sha256=sha(out/'cpio-after'),
  native_core_reply_query_readonly=True,native_core_reply_timeout_not_accepted=True,
  rust_compiler_detection_metadata_delta=unexpected,rust_enabled=False,
  q6core_source_sha256=sha(k/'sound/soc/qcom/qdsp6/q6core.c'),
  hardware_tested=False,alsa_output_tested=False,goal_complete=False)
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('ADSP_KERNEL_AUDIT_PASS')
