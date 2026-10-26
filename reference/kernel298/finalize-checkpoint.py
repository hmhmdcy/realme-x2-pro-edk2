"""Record the user's normal-scene choice and verified OEM source discovery."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];P=host.PRIVATE
load=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=load(P/'oem-tuning-inventory-private.json');source=load(P/'imx319-tuning-source-private.json');container=load(P/'imx319-tuning-container-private.json');symbols=load(P/'imx319-tuning-symbols-private.json')
assert inventory['unmounted'] and source['unmounted'] and container['private_source_transferred_and_verified']
row=source['files'][0];assert sha(P/'sunny-imx319-tuning-private.bin')==row['sha256']
counts={name:sum(r['name']==name for r in symbols['symbols']) for name in ['bls12_ife','bls12_bps','cc12_ife','AWBExtensionParam']}
report=dict(stage=298,source_partition='vendor',readonly_noload_noexec=True,unmounted=True,no_oem_code_executed=True,
 vendor_camera_files=len(inventory['files']),chromatix_header_files=sum(r['chromatix_header'] for r in inventory['files']),
 tuning_file='lib64/camera/com.qti.tuned.sunny_imx319.bin',bytes=row['bytes'],sha256=row['sha256'],
 container_sections=container['sections'],symbol_count=len(symbols['symbols']),identified_parameter_roots=counts,
 tuning_binary_and_symbols_kept_private=True,calibration_values_not_accepted=True,
 candidate_bls_schema_layout_units_mode_selection_and_independent_decoder_crosscheck_pending=True,
 tuning_not_installed=True,unit_eeprom_otp_not_read_or_written=True,
 user_selected_normal_scene_comparison_without_dark_cover=True,
 source_scripts={n:sha(HERE/n) for n in ['oem-tuning-inventory.py','collect-imx319-tuning.py','inspect-tuning-symbols.py','inspect-bls-candidate.py']})
(HERE/'oem-tuning-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
for name in ['README.md']:
 p=HERE/name;s=p.read_text().replace('本轮遮光询问尚未收到确认，没有把实景截距升级为标定。','用户选择先做正常场景对照、暂不遮光，没有把实景截距升级为暗场标定。')
 s+='\n本轮进一步只读提取并核验原厂 `com.qti.tuned.sunny_imx319.bin`（15389568字节），识别14195符号及IFE/BPS BLS、CC12和AWB段；布局／单位／模式选择与独立解码仍需交叉验证，数值尚未装入调校。[提取事实与哈希](oem-tuning-source-validation.json)\n';p.write_text(s)
p=ROOT/'NEXT-SESSION.md';s=p.read_text().replace('遮光询问尚无确认，不能把实景截距当暗场标定','用户选择正常场景、暂不遮光，不能把实景截距当暗场标定')
s=s.replace('先补遮光暗场与曝光／增益／温度依赖，','已只读提取本机Sunny IMX319原厂调校包并识别BLS／CC／AWB段，数值待布局／单位／模式交叉验证；先复用这些来源，再补需要的暗场与曝光／增益／温度依赖，')
assert len(s.encode())<=6500;p.write_text(s)
p=HERE/'update-checkpoints.py';s=p.read_text().replace('遮光询问尚无确认，不能把实景截距当暗场标定','用户选择正常场景、暂不遮光，不能把实景截距当暗场标定');p.write_text(s)
for name,prefix in [('linux-port/camera/deployment-lock.json','../../'),('linux-port/camera/kernel/source-lock.json','../../../')]:
 p=ROOT/name;d=load(p);d.update(user_selected_normal_scene_without_dark_cover=True,factory_tuning_source_evidence=prefix+'reference/kernel298/oem-tuning-source-validation.json',factory_tuning_values_not_yet_accepted=True);p.write_text(json.dumps(d,indent=2)+'\n')
# The sync workflow regenerates this index. Hash its generated form, not a manual banner.
subprocess.run(['python3',str(ROOT/'linux-port/scripts/generate-session-index.py')],check=True)
p=HERE/'checkpoint-validation.json';d=load(p)
for n in d['files']:d['files'][n]=dict(bytes=(ROOT/n).stat().st_size,sha256=sha(ROOT/n))
d.update(generated_index_finalized=True,user_selected_normal_scene_without_dark_cover=True,factory_tuning_values_not_yet_accepted=True)
p.write_text(json.dumps(d,indent=2)+'\n')
print('Generated index hash finalized; user scene choice and verified OEM source recorded.')
