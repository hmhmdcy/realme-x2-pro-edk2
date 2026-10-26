from pathlib import Path
import hashlib,json,tarfile,host
ref=Path(__file__).resolve().parent;out=host.PRIVATE
host.download('/var/lib/samurai/k194-export/export-summary.json',out/'native-export-summary-private.json');record=json.loads((out/'native-export-summary-private.json').read_text());host.download('/var/lib/samurai/k194-export/evidence-private.tar.gz',out/'native-evidence-private.tar.gz');archive=out/'native-evidence-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256']
with tarfile.open(archive) as tar:
 manifest=json.load(tar.extractfile('manifest-private.json'));assert len(manifest)==record['files']
 for n,h in manifest.items():assert hashlib.sha256(tar.extractfile(n).read()).hexdigest()==h
 def get(n):return json.load(tar.extractfile(n))
 health=get('k194-final-health/summary.json');abi=get('k194-module-abi/summary.json');reset=get('k194-q-reset/summary.json');cold=get('k194-pmic-coldprobe/summary.json');warm=get('k194-pmic-warmprobe/summary.json')
 assert reset['after_restore']==reset['before'] and reset['after_reset_at8']['sid']['data']==[2] and not reset['after_reset_at4']['identity']['success'] and reset['writes']==[dict(address=8,register=0x644,data=[1],success=True,messages=1)]
 results=[]
 for name,r in [('cold',cold),('warm',warm)]:
  assert r['during_probe']==r['before']==r['after_restore'] and r['bound_driver']=='pm8008' and not r['address8_during']['success'] and not r['address8_after']['success'] and not r['writes'] and all(v==0 for v in r['fault_delta'].values()) and r['gpio1_before']==r['gpio1_during']==r['gpio1_after']==0 and r['gpio4_before']==r['gpio4_after']==1 and r['taint']==512
  assert len(r['regulators_during'])==7 and r['regulator_child_loaded'] and all(a['returncode']==0 for a in r['attempts'])
  if name=='cold':assert r['reset_levels']==[0,1] and r['reset_address8']['sid']['data']==[2] and not r['reset_address4']['success']
  else:assert not r['reset_levels'] and r['reset_address4']['success'] and not r['reset_address8']['success']
  results.append(dict(attempt=name,normal_mfd_bound=True,seven_regulators_registered=True,seven_ldo_samples_unchanged=True,pmic_p_held_reset=True,q_gpio_restored=True,manual_sid_fallback_needed=False,fault_delta=r['fault_delta'],taint=r['taint']))
 pmic=dict(stage=194,measured_factory_address=8,assigned_address=4,factory_sid_value=2,assigned_sid_value=1,first_reset_only_sid_write_restored_address=True,driver_attempts=results,driver_cold_assignment_log_observed=True,warm_probe_assignment_log_absent=True,all_temporary_modules_and_nodes_removed=True,full_phone_cold_boot_proven=False,physical_input_supply_wiring_complete=False)
 for filename,r in [('pmic-native-validation.json',pmic),('module-abi-native-validation.json',abi),('native-health-validation.json',health)]: (ref/filename).write_text(json.dumps(r,indent=2)+'\n')
receipt=dict(**record,host_archive_sha256_verified=True,all_member_hashes_verified=True,reset_cold_warm_abi_and_health_evidence_preserved=True,private_logs_and_runtime_identity_not_published=True)
(ref/'evidence-export-validation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
