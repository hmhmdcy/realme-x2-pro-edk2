from pathlib import Path
import ast
ref=Path(__file__).resolve().parent
s=(ref/'export-native.py').read_text().replace("out=root/'k201-export'","out=root/'k201-export-r2'").replace("if d.is_dir() and d!=out", "if d.is_dir() and not d.name.startswith('k201-export')")
ast.parse(s);(ref/'export-native-r2.py').write_text(s)
s=(ref/'verify-export.py').read_text().replace('k201-export/','k201-export-r2/').replace('native-export-summary-private.json','native-export-summary-r2-private.json').replace('native-evidence-private.tar.gz','native-evidence-r2-private.tar.gz').replace('k201-final-health-r2/summary.json','k201-final-health-r3/summary.json')
s=s.replace("normalize=get('k201-idle-normalization/summary.json');", "normalize=get('k201-idle-normalization/summary.json');normalize.pop('first_failed_client_left_refresh_and_signal_settings',None);normalize['causal_stage_not_proven']=True;")
s=s.replace("(ref/'assist-native-validation.json').write_text", "flow=get('k201-real-expired-flow/summary.json');assert not flow['stale_window_established'] and not flow['old_injection_ack'] and flow['old_injection_error_name']=='org.freedesktop.ModemManager1.Error.Core.Aborted' and flow['final_file_current'] and flow['fallback_fresh_injection_requests']==0\n (ref/'controlled-expired-flow-validation.json').write_text(json.dumps(flow,indent=2)+'\\n')\n (ref/'assist-native-validation.json').write_text")
s=s.replace('cross_boot_automatic_validation_pending=True', 'cross_boot_automatic_validation_pending=True,full_automatic_expired_refresh_path_native_proven=False,controlled_old_file_injection_aborted_without_changing_current_window=True')
ast.parse(s);(ref/'verify-export-r2.py').write_text(s)
print('K201_FINAL_EXPORT_INCLUDES_CONTROLLED_ABORT_RECOVERY_AND_ORIGINAL_ARCHIVE_PRESERVED')
