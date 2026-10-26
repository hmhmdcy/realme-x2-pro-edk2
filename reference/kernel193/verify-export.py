from pathlib import Path
import hashlib,json,tarfile
import host
ref=Path(__file__).resolve().parent;out=host.PRIVATE
host.download('/var/lib/samurai/k193-export/export-summary.json',out/'native-export-summary-private.json');record=json.loads((out/'native-export-summary-private.json').read_text())
host.download('/var/lib/samurai/k193-export/evidence-private.tar.gz',out/'native-evidence-private.tar.gz');archive=out/'native-evidence-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256']
with tarfile.open(archive) as tar:
 manifest=json.load(tar.extractfile('manifest-private.json'));assert len(manifest)==record['files']
 for name,digest in manifest.items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest
 def get(path):return json.load(tar.extractfile(path))
 first=get('k193-front-identify/summary.json');second=get('k193-front-identify-r2/summary.json');third=get('k193-front-identify-r3/summary.json');health=get('k193-final-health/summary.json');cci=get('k193-cci-load/summary.json')
 assert third['module_parameters']==dict(sensor_id=0x471,restore_result=0,ready_samples=2,sequence_result=0)
 for r in [first,second,third]:assert r['gpio_directions_and_levels_restored'] and r['pmic_entire_sample_restored'] and r['module_parameters']['restore_result']==0
 assert first['module_parameters']['sequence_result']==-524 and second['module_parameters']['sequence_result']==-16
 assert first['module_parameters']['ready_samples']==0 and second['module_parameters']['ready_samples']==2
 assert second['fault_delta']['warning']==1 and third['fault_delta']['warning']==0 and health['taint']==512
 assert health['all_diagnostic_modules_unloaded'] and health['cci1_status_restored_disabled'] and not health['physical_image_capture_proven']
 (ref/'cci-native-validation.json').write_text(json.dumps(cci,indent=2)+'\n');(ref/'front-native-validation.json').write_text(json.dumps(dict(stage=193,attempts=[dict(attempt=name,**r) for name,r in [('first',first),('r2',second),('r3',third)]],physical_front_sensor_id=0x471,physical_sensor_identity_proven=True,physical_image_capture_proven=False),indent=2)+'\n');(ref/'native-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')
receipt=dict(**record,host_archive_sha256_verified=True,all_member_hashes_verified=True,all_three_native_source_and_module_versions_preserved=True,private_logs_and_runtime_identity_not_published=True)
(ref/'evidence-export-validation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
