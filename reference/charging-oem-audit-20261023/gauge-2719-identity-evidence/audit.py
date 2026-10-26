"""Read fixed local identity/source caches only. No network or hardware API."""
from pathlib import Path
import hashlib,importlib.util,json,re
HERE=Path(__file__).resolve().parent
PRIVATE=Path('E:/edk2-samurai-out/charging-management-20261023/gauge-2719-identity-evidence-private-01')
sha=lambda raw:hashlib.sha256(raw).hexdigest()
spec=importlib.util.spec_from_file_location('saved_gauge_fingerprint',HERE/'identity-fingerprint.py')
codec=importlib.util.module_from_spec(spec);spec.loader.exec_module(codec)
inputs={
 'firmware_80':(Path('E:/edk2-samurai-out/kernel80/firmware-version.txt'),'7bdf619c59e1c79202bec4ea4012e0dbeb0d44106f74710c4c99e73ea863fc53'),
 'firmware_85':(Path('E:/edk2-samurai-out/kernel85/chemistry-query.txt'),'572ab13398aa75525baf9d54fe3e08f24006fd25f2bd84f68eed6e76655f725b'),
 'paired_identity':(Path('E:/edk2-samurai-out/kernel80/paired-identity.txt'),'3fc9015a42a804640976fdd904704cd5cc7ae9a53d8185beca6f0415df0cb765'),
 'oem_gauge':(Path('E:/edk2-samurai-out/kernel83/realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--drivers--power--oppo--gauge_ic--oplus_bq27541.c'),'0c4640c85570f1a83ea8db3e82a63d75d9fc2650c71fbbb8c247e471c10b7a87'),
 'oem_header':(Path('E:/edk2-samurai-out/kernel85/official-oplus_bq27541.h'),'58c68c362fc031eb73884a59e121ba25918e6728b37572df4116f8e1277e270e'),
 'board_dts':(Path('E:/edk2-samurai-out/kernel83/realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--arch--arm64--boot--dts--19781--sm8150-pmic-overlay.dtsi'),'f2f12882b42c1a5f7440d120b56ed38ee0ac2cb15fada2c6a0c3352f4c6f91e7'),
 'trm_text':(Path('E:/edk2-samurai-out/charging-management-20261023/ti-manual-private.txt'),'c5cfb494ed5dad0311a13f134702be09cd137ed2c4478b10143eab0c760327fc'),
 'oem_makefile':(Path('E:/edk2-samurai-out/kernel83/realme-kernel-opensource--realmeX2pro-X3-AndroidR-kernel-source--drivers--power--oppo--gauge_ic--Makefile'),None),
 'ti_family_html':(PRIVATE/'ti-firmware-family-private.html','3f3cf15d05fce2bd02281a28b652ec67532b304b8a23fbe3e343f9787c5972fc'),
 'github_directory_error':(PRIVATE/'official-gauge-directory-error.json',None),
}
raws={};pins={}
for name,(path,expected) in inputs.items():
    raw=path.read_bytes();assert expected is None or sha(raw)==expected,name
    raws[name]=raw;pins[name]=dict(path=str(path.resolve()),sha256=sha(raw),bytes=len(raw))
fw80=codec.decode_saved(raws['firmware_80']);fw85=codec.decode_saved(raws['firmware_85']);assert fw80==fw85
paired=raws['paired_identity'].decode();assert 'DeviceType request=000100 legacy_word=0xffa5 delay_us=1000 retries=0' in paired and paired.endswith('query_rc=0\n')
match=re.findall(r'^DeviceType extended_response=([0-9a-f]{72}) validation=0$',paired,re.M);assert len(match)==1
packet=bytes.fromhex(match[0]);assert packet[:2]==b'\x01\x00' and packet[35]==6 and (sum(packet[:4])+packet[34])&255==255
device_type=int.from_bytes(packet[2:4],'little');assert device_type==0x2719
source=raws['oem_gauge'].decode();dts=raws['board_dts'].decode();manual=raws['trm_text'].decode()
assert 'ddDDvvVVbbBBTTzzZZRREE' in manual and 'ttTT: Firmware type' in manual
assert 'qcom,batt_bq28z610;' in dts and '0x2719' not in source.lower()
html=raws['ti_family_html'].decode();assert 'not compatible with bq28z610 hardware' in html and 'R1B' in html
needles={
 'oem_legacy_hw_config':'static void bq27541_hw_config',
 'oem_legacy_fw_read':'bq27541_cntl_cmd(BQ27541_BQ27411_SUBCMD_FW_VER);',
 'oem_FFA5_current_override':'if (device_type == DEVICE_TYPE_BQ28Z610)',
 'oem_family_dt_read':'chip->batt_bq28z610 = of_property_read_bool',
}
lines={key:next(i for i,line in enumerate(source.splitlines(),1) if needle in line) for key,needle in needles.items()}
result=dict(schema='samurai-gauge-2719-saved-identity-evidence-v1',passed=True,
    device_type=dict(value='0x2719',legacy_word='0xffa5',full_frame_sha256=sha(packet),payload_le_hex=packet[2:4].hex()),
    firmware=fw80,identical_historical_firmware_frames=2,
    byte_order_observation=dict(device_type_payload='1927',firmware_first_two_bytes='2719',
        using_generic_le16_on_firmware_prefix_would_yield='0x1927',exact_firmware_word_byte_order_confirmed=False),
    field_layout_source=dict(url='https://www.ti.com/lit/pdf/sluua65',document='SLUUA65E June2023',section='12.2.2',printed_page=76,
        text_lines=[3286,3298],token='ddDDvvVVbbBBTTzzZZRREE',firmware_type_prose='ttTT',
        interpretation='raw fixed slices only; TT token is one byte while prose is inconsistent; no invented semantic conversion'),
    oem=dict(repository='realme-kernel-opensource/realmeX2pro-X3-AndroidR-kernel-source',commit='23172a1571bd91156032cc9fef16284a82b63d2c',
        source_lines=lines,dts_gauge_lines=[422,429],legacy_FFA5_is_catalog_model_mapping=False,
        exact_2719_mapping_in_inspected_gauge_source=False,firmware_loader_calls_in_inspected_gauge_source={key:source.count(key) for key in ('request_firmware','MODULE_FIRMWARE')},
        whole_repository_or_vendor_firmware_inventory_proven=False,
        directory_listing_attempt=json.loads(raws['github_directory_error'])),
    new_primary_constraint=dict(url='https://www.ti.com/tool/BQ28Z610-DEVICE-FW',release='R1B',
        hardware_incompatibility_explicit=True,applies_to_current_2719_hardware=None,current_hardware_class_identified=False,
        action='do not substitute the public R1B firmware or its device configuration for this unknown pack',
        firmware_downloaded=False),
    command_formats=dict(source='standard BQ28Z610 SLUUA65E, not exact2719 proof',commands={
        '0050':dict(name='SafetyAlert',payload=4,length=8,section='12.2.26'),
        '0052':dict(name='PFAlert',payload=4,length=8,section='12.2.28'),
        '0056':dict(name='GaugingStatus',payload=4,length=8,fourth_byte_reserved=True,section='12.2.32')},
        exact_2719_response_formats_confirmed=False,exact_2719_new_bits_confirmed=False),
    next_action=dict(repeat_0002_device_query_needed=False,
        exact_model_or_OEM_firmware_descriptor_required='match2719 plus full11-byte fingerprint; obtain exact firmware command/bit schema before new0050/52/56 query',
        new_queries_authorized=False,no_existing_Health_TCA_Full_or_whitelist_change=True),
    inputs=pins,device_accessed=False,firmware_downloaded_or_written=False,module_or_Image_build_performed=False)
(HERE/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(passed=True,device_type=result['device_type']['value'],firmware_payload=fw80['payload_hex'],exact_model=None,new_query_authorized=False)))
