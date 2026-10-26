from pathlib import Path
import hashlib,json,tarfile,time,host
ref=Path(__file__).resolve().parent;out=host.PRIVATE
host.download('/var/lib/samurai/k201-export-r2/export-summary.json',out/'native-export-summary-r2-private.json');receipt=json.loads((out/'native-export-summary-r2-private.json').read_text());host.download('/var/lib/samurai/k201-export-r2/evidence-private.tar.gz',out/'native-evidence-r2-private.tar.gz')
archive=out/'native-evidence-r2-private.tar.gz';assert hashlib.sha256(archive.read_bytes()).hexdigest()==receipt['archive_sha256']
with tarfile.open(archive) as tar:
 manifest=json.load(tar.extractfile('manifest-private.json'));assert len(manifest)==receipt['files']
 for name,digest in manifest.items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest
 def get(name):return json.load(tar.extractfile(name))
 initial=get('k201-validity-before/summary.json');fresh=get('k201-validity-after/summary.json');assert initial['start_utc_timestamp']==1790928000 and initial['duration_hours']==168 and fresh['start_utc_timestamp']==1792040400 and fresh['duration_hours']==168
 injection=get('k201-assistance/summary.json');assert injection['injection_ack'] and injection['bytes']==51331 and injection['same_mm_owner'] and injection['gps_enabled_final']==0 and not any(injection['fault_delta'].values())
 r1=get('k201-geoclue-test/client-result-private.json');assert not r1['started'] and r1['error_name']=='org.freedesktop.DBus.Error.AccessDenied'
 cleanup=get('k201-geoclue-test/separate-cleanup.json');assert cleanup['temporary_app_and_dropin_removed'] and cleanup['base_configuration_unchanged']
 trials=[]
 for folder,label in [('k201-geoclue-test-r2','fresh XTRA before manual UTC'),('k201-geoclue-utc-off','UTC/shutting-down'),('k201-geoclue-utc-online','UTC/online'),('k201-geoclue-auto','automatic helper first version'),('k201-geoclue-auto-final','automatic helper final version')]:
  data=get(folder+'/summary.json');assert data['client']['uid']==10000 and data['client']['started'] and data['client']['active'] and data['client']['stopped'] and data['client']['client_deleted'] and data['gps_enabled_observed'] and data['gnss_only_geoclue_test']
  assert data['test_config_and_identity_removed'] and data['normal_geoclue_permissions_restored'] and data['desktop_location_setting_restored'] and data['gps_enabled_final']==0 and data['signals_location_restored'] and data['refresh_rate_restored']
  assert data['checksum_failures']==0 and not any(data['fault_delta'].values()) and data['valid_gga']==data['active_rmc']==data['raw_fix_reports']==data['positive_cnr_fields']==data['client']['valid_location_events']==0
  trials.append(dict(label=label,elapsed_seconds=data['elapsed_seconds'],unique_nmea_within_trial=data['unique_nmea'],nmea_types=data['nmea_types'],valid_location_events=0,positive_cnr_fields=0))
 assert trials[0]['unique_nmea_within_trial']==4 and trials[1]['unique_nmea_within_trial']>=85 and 'GPGSV' in trials[2]['nmea_types']
 health=get('k201-final-health-r3/summary.json');assert health['taint']==0 and not any(health['fault_counts'].values()) and health['gps_enabled']==0 and health['mm_power_state']==3 and health['base_geoclue_configuration_exact'] and health['temporary_geoclue_test_policy_desktop_and_executable_removed']
 watch=get('k201-product-snapshot/watch-state.json');assert watch['source_sha256']=='cf3d92a46e619ceba30342fb2c063fb39ba9de5ddd2043e5dc0a5f59f39bef41' and watch['worker_starts']==watch['worker_completions']==1 and not watch['active'] and watch['last_result']['status']=='current' and watch['last_result']['download_count']==watch['last_result']['injection_count']==0 and watch['last_result']['utc_ack_and_completion'] and watch['last_result']['qmi_clients_released_and_closed']
 native=get('k201-assist-final/summary.json');assert native['actual_old191_payload_rejected_without_injection'] and native['all_qmi_clients_released_and_closed'] and native['gps_enabled_final']==0
 normalize=get('k201-idle-normalization/summary.json');normalize.pop('first_failed_client_left_refresh_and_signal_settings',None);normalize['causal_stage_not_proven']=True;assert normalize['after']==dict(Enabled=0,SignalsLocation=0,GpsRefreshRate=30)
 assert hashlib.sha256(tar.extractfile('k201-product-snapshot/samurai-gnss-assist.py').read()).hexdigest()==watch['source_sha256']
 (ref/'native-health-validation.json').write_text(json.dumps(health,indent=2)+'\n')
 flow=get('k201-real-expired-flow/summary.json');assert not flow['stale_window_established'] and not flow['old_injection_ack'] and flow['old_injection_error_name']=='org.freedesktop.ModemManager1.Error.Core.Aborted' and flow['final_file_current'] and flow['fallback_fresh_injection_requests']==0
 (ref/'controlled-expired-flow-validation.json').write_text(json.dumps(flow,indent=2)+'\n')
 (ref/'assist-native-validation.json').write_text(json.dumps(dict(stage=201,helper_source_sha256=watch['source_sha256'],idle_service_start_stop_passed=True,final_auto_gps_activation_started_one_worker=True,one_worker_completed=True,utc_ack_and_completion=True,all_qmi_clients_released_and_closed=True,valid_file_not_downloaded_or_reinjected=True,known_actual_old_payload_rejected=True,gps_sessions_not_started_by_helper=True,modem_power_not_changed_by_helper=True,cross_boot_automatic_validation_pending=True,full_automatic_expired_refresh_path_native_proven=False,controlled_old_file_injection_aborted_without_changing_current_window=True),indent=2)+'\n')
 (ref/'geoclue-native-validation.json').write_text(json.dumps(dict(stage=201,standard_uid10000_client_and_distinct_desktop_identity=True,gnss_only_test_sources=True,initial_global_desktop_location_switch_false=True,first_access_denied_and_cleanup_recovery_retained=True,trials=trials,final_desktop_switch_false_and_test_policy_removed=True,final_location_normalization=normalize,real_fix_not_obtained=True),indent=2)+'\n')
public={k:v for k,v in receipt.items() if k!='archive_sha256'};public.update(host_archive_sha256_verified=True,all_member_hashes_verified=True,nmea_config_bus_identity_and_all_archive_fingerprints_private=True,initial_failures_and_cleanup_retained=True)
(ref/'evidence-export-validation.json').write_text(json.dumps(public,indent=2)+'\n');print(json.dumps(public))
