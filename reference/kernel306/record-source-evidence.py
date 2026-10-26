"""Publish fingerprints and scope, keeping vendor payloads and scene data private."""
from pathlib import Path
import hashlib,json,subprocess
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
transfer=json.loads((P/'tele-tuning-transfer-validation-private.json').read_text())
assert transfer['host_phone_transfer_verified'] and transfer['readonly_noload_noexec'] and transfer['unmounted']
export=json.loads((HERE/'tele-bls-export-validation.json').read_text())
assert export['all19_ife_modes_exported'] and export['independent_reader_and_direct_decoder_agree']
direct=json.loads((P/'tele-bls-direct-private.json').read_text())
ife=[r for r in direct['roots'] if r['name']=='bls12_ife']
bps=[r for r in direct['roots'] if r['name']=='bls12_bps']
assert len(ife)==19 and all(r['enabled']==1 and {tuple(x['values']) for x in r['leaves']}=={(960,0,0,0,0)} for r in ife)
report=dict(stage=306,original_factory_source='lib64/camera/com.qti.tuned.qtech_s5k3m5sx.bin',
 source_bytes=transfer['source_bytes'],source_sha256=transfer['source_sha256'],
 current_factory_vendor_readonly_noload_noexec=True,unmounted=True,host_transfer_hash_verified=True,
 original_factory_parser_crosscheck=True,ife_roots=19,ife_regions=152,all_ife_enabled=True,
 all_ife_offset_u14=960,all_ife_thresholds_zero=True,bps_roots=len(bps),bps_regions=48,
 bps_offsets_u14=sorted(set(x['values'][0] for r in bps for x in r['leaves'])),
 bps_factory_parser_not_run=True,bps_values_not_used_for_ife=True,
 common_subtraction_u16=3840,explicit_common_normalization_q11=2175,
 actual_common_normalization_gain_q7=136,
 per_unit_module_supplier_not_verified=True,individual_dark_calibration_complete=False,
 full_factory_mode_selection_not_reimplemented=True,full_factory_iq_pipeline_not_recreated=True,
 product_tuning_not_installed=True,no_eeprom_otp_nv_write=True)
(HERE/'factory-source-validation.json').write_text(json.dumps(report,indent=2)+'\n')
pins=json.loads((P/'awb-primary-source-pins-private.json').read_text())
for row in pins['primary_source_pins']:
 data=(P/'awb-primary'/Path(row['path']).name).read_bytes()
 assert hashlib.sha256(data).hexdigest()==row['sha256'] and len(data)==row['bytes']
repo=Path('/home/cy122/x2pro-linux/refs/realme-x2pro-androidr-project-k112')
remote=subprocess.check_output(['git','-C',str(repo),'remote','get-url','origin'],text=True).strip()
assert remote.startswith('https://github.com/') and '@' not in remote.split('://',1)[1]
for row in pins['primary_source_pins']:
 if 'commit' in row:row['repository_url']=remote
pins.update(primary_sources_rechecked=True,awb_bg_bus_client=15,bhist_bus_client=16,
 native_regular_region_bytes=24,regular_output_channels=['R','B','Gr','Gb'],
 native_channel_sum_bits=30,native_channel_count_bits=16,
 register_bitfield_and_dma_lifetime_validation_pending=True,not_implemented_or_hardware_validated=True)
(HERE/'awb-primary-source-validation.json').write_text(json.dumps(pins,indent=2)+'\n')
print(json.dumps(report,indent=2))
print('Pinned eight primary AWB sources; no AWB hardware claim.')
