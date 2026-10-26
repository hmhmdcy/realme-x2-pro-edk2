from pathlib import Path
import hashlib,json,tarfile
import host
out=host.PRIVATE;ref=Path(__file__).resolve().parent
host.download('/var/lib/samurai/k192-export/export-summary.json',out/'native-export-summary-private.json')
info=json.loads((out/'native-export-summary-private.json').read_text())
host.download('/var/lib/samurai/k192-export/evidence-private.tar.gz',out/'native-evidence-private.tar.gz')
archive=out/'native-evidence-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==info['archive_sha256']
with tarfile.open(archive) as tar:
 manifest=json.load(tar.extractfile('manifest-private.json'))
 assert len(manifest)==info['files']
 for name,digest in manifest.items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest
 def get(name):return json.load(tar.extractfile(name))
 first=get('k192-pmic-a-release/summary.json');levels=get('k192-reset-levels/summary.json');health=get('k192-final-health-r3/summary.json');front=get('k192-front-reset/summary.json')
 assert first['before_second']==first['after_second'] and first['restored_first_level']==0
 assert first['during_first']['identity']['data']==first['before_second']['identity']['data']==[0,0,0,1,0x51,0x2c]
 assert not first['after_first_identity']['success'] and first['after_first_identity']['errno']==6
 assert first['pmic_register_data_writes']==0 and first['second_reset_line_changed'] is False
 assert levels['configuration_unchanged'] and all(r['flags']==4 and r['physical_value']==0 and not r['consumer'] for r in front)
 (ref/'native-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')
 pmic=dict(stage=192,controller='i2c@890000',linux_adapter=1,shared_audio_amplifiers_preserved=True,primary_addresses=[8,4],secondary_addresses=[9,5],identity_bytes=[0,0,0,1,0x51,0x2c],pm8150l_reset_gpio_numbers=[1,4],original_physical_levels=[0,1],first_pmic_replies_after_reset_release=True,first_restored_to_original_reset=True,first_post_restore_nack=True,second_entire_register_snapshot_unchanged=True,sid_config_first=first['during_first']['sid_config']['data'][0],sid_config_second=first['before_second']['sid_config']['data'][0],global_enable_bits=[first['during_first']['chip_enable']['data'][0],first['before_second']['chip_enable']['data'][0]],all_ldo_enable_bytes_zero=True,pmic_register_data_writes=0,ldo_or_vset_writes=0,first_gpio_request_sequence=first['levels_requested'],second_reset_changes=0,physical_sensor_id_read=False,physical_camera_accepted=False)
 assert all(x['enable']['data']==[0] for k in ['during_first','before_second'] for x in first[k]['ldos'])
 (ref/'pmic-native-validation.json').write_text(json.dumps(pmic,indent=2)+'\n')
 receipt=dict(**info,host_archive_sha256_verified=True,all_member_hashes_verified=True,raw_logs_gpio_register_snapshots_and_identity_private=True)
 (ref/'evidence-export-validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt))
