from pathlib import Path
import hashlib,json,tarfile,host
ref=Path(__file__).resolve().parent;out=host.PRIVATE
host.download('/var/lib/samurai/k195-export/export-summary.json',out/'native-export-summary-private.json');record=json.loads((out/'native-export-summary-private.json').read_text());host.download('/var/lib/samurai/k195-export/evidence-private.tar.gz',out/'native-evidence-private.tar.gz');archive=out/'native-evidence-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256']
with tarfile.open(archive) as tar:
 manifest=json.load(tar.extractfile('manifest-private.json'));assert len(manifest)==record['files']
 for n,h in manifest.items():assert hashlib.sha256(tar.extractfile(n).read()).hexdigest()==h
 def get(n):return json.load(tar.extractfile(n))
 cold=get('k195-pmic-coldprobe/summary.json');warm=get('k195-pmic-warmprobe/summary.json');vio=get('k195-vio-lookup/summary.json');health=get('k195-final-health/summary.json')
 attempts=[]
 for name,r in [('cold',cold),('warm',warm)]:
  assert r['before']==r['during_probe']==r['after_restore'] and r['bound_driver']=='pm8008' and len(r['regulators_during'])==7 and r['regulator_child_loaded'] and not r['writes'] and all(a['returncode']==0 for a in r['attempts']) and all(v==0 for v in r['fault_delta'].values())
  assert r['gpio1_before']==r['gpio1_during']==r['gpio1_after']==0 and r['gpio4_before']==r['gpio4_after']==1
  if name=='cold':assert r['reset_levels']==[0,1] and r['reset_address8']['sid']['data']==[2] and not r['reset_address4']['success']
  else:assert not r['reset_levels'] and r['reset_address4']['success'] and not r['reset_address8']['success']
  attempts.append(dict(attempt=name,normal_mfd_bound=True,seven_regulators_registered=True,seven_ldo_samples_unchanged=True,pmic_p_held_reset=True,q_gpio_restored=True,manual_sid_fallback_needed=False,fault_delta=r['fault_delta'],taint=r['taint']))
 assert vio['node_properties_restored'] and vio['same_regulator_object'] and vio['temporary_consumer_removed'] and vio['exact_of_supply_lookup_succeeded'] and vio['before_state']==vio['during_state']==vio['after_state'] and all(v==0 for v in vio['fault_delta'].values())
 pmic=dict(stage=195,module_sha256=json.loads((ref/'pmic-module-build-validation.json').read_text())['module_sha256'],normal_paths_pass_native_again=True,attempts=attempts,failure_reset_recovery_validated_by_host_fault_injection=True,native_i2c_or_gpio_fault_injected=False,all_temporary_modules_and_nodes_removed=True,full_phone_cold_boot_proven=False)
 for filename,r in [('pmic-native-validation.json',pmic),('vio-native-validation.json',vio),('native-health-validation.json',health)]: (ref/filename).write_text(json.dumps(r,indent=2)+'\n')
receipt=dict(**record,host_archive_sha256_verified=True,all_member_hashes_verified=True,cold_warm_vio_and_health_evidence_preserved=True,private_logs_and_runtime_identity_not_published=True);(ref/'evidence-export-validation.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
