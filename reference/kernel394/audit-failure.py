from pathlib import Path
import hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
text=(P/'recovery-collected/pstore-console-ramoops-0').read_text();start=text.rfind('A5 retiring DMA aliases',0,text.rfind('FAULT_TEST dropped validated frame ACK once'));start=text.rfind('\n',0,start)+1;window=text[start:]
drop=re.search(r'\[\s*(\d+\.\d+)\].*FAULT_TEST dropped validated frame ACK once',window);timeout=re.search(r'\[\s*(\d+\.\d+)\].*A5 IPE frame failed ret=-110 hfi=0 status=0 queued=1 pending=1',window)
assert drop and timeout and window.count('FAULT_TEST dropped validated frame ACK once')==1
assert 'retained before reset pending=1 request_mapped=1 input_ref=1 output_ref=1' in window
assert 'A5 stopped, cooperative=0 block_reset=1' in window
assert 'before DMA retirement reset_acks=3,3 pending=0 request_mapped=0 input_ref=1 output_ref=1' in window
tail=window[window.index('FAULT_TEST dropped validated frame ACK once'):]
assert 'A5 DMA aliases retired' not in tail and 'PM reference released' not in tail
assert len(re.findall('A5 IPE frame completed request=1',window))==2
elapsed=float(timeout[1])-float(drop[1]);assert 4.5<elapsed<7
evidence=dict(stage=394,experiment='one_valid_frame_ack_loss_with_two_configured_contexts',experiment_passed=False,verified_reboot_interrupted=True,worker_terminal_file_missing_after_reboot=True,
 two_warmup_hardware_frames_completed=True,one_valid_frame_ack_discarded=True,actual_timeout_seconds=round(elapsed,6),command_enqueued_and_pending_at_timeout=True,request_fw_map_and_both_import_refs_retained_before_reset=True,
 a5_forced_block_reset_returned=True,both_ipe_reset_ack_masks=[3,3],pending_and_fw_mapping_cleared_only_after_quiesce=True,both_import_refs_still_present_before_retirement=True,
 alias_retirement_complete_not_observed=True,pm_release_not_observed=True,client_error_propagation_and_reopen_not_proven=True,no_panic_or_exact_pc_from_this_window=not any(s in tail for s in ['Kernel panic','Call trace:','pc :','SError']),
 last_observed_stage='after forced A5 reset and both IPE reset ACKs, before completed DMA alias retirement',precise_reboot_cause_proven=False,source_and_module_disk_pair_unchanged=True,normal393_recovery_evidence='postboot-validation.json',passed=False)
(HERE/'fault-experiment-validation.json').write_text(json.dumps(evidence,indent=2)+'\n')
# Verify the already retained primary sources; do not fetch or print the OEM code.
records=[]
for stage,manifest,leaf,names in [(352,'oem-icp-sources.json','hfi.c',['cam_hfi_disable_cpu']),(355,'oem-resource-sources.json','cam_icp_hw_mgr.c',['cam_icp_mgr_trigger_recovery','cam_icp_ipebps_reset','cam_icp_mgr_icp_power_collapse'])]:
 meta=json.loads((HERE.parent/('kernel'+str(stage))/manifest).read_text());row=next(r for r in meta['files'] if Path(r['path']).name==leaf);file=P.parent/('kernel'+str(stage))/'oem'/leaf;raw=file.read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
 s=raw.decode();functions=[]
 for name in names:
  m=re.search(r'(?:static )?(?:void|int)\s+'+name+r'\([^;]+?\n\{.*?^\}\n',s,re.S|re.M);assert m,name
  functions.append(dict(name=name,line=s[:m.start()].count('\n')+1,lines=m.group().count('\n'),calls_global_linux_reset_control='reset_control_assert(' in m.group(),uses_raw_global_camcc_bcr='ICP_BCR' in m.group()))
 records.append(dict(commit=meta['commit'],path=row['path'],sha256=row['sha256'],functions=functions))
assert all(not f['calls_global_linux_reset_control'] and not f['uses_raw_global_camcc_bcr'] for r in records for f in r['functions'])
audit=dict(stage=394,retained_oem_sources_verified=True,sources=records,prior375_cooperative_stop_evidence='../kernel375/README.md',current393_error_path_global_icp_bcr_before_alias_retirement=True,
 selected_oem_recovery_resets_ipe_bps_and_cpu_disable_functions_have_no_direct_global_bcr=True,indirect_resource_reset_call_graph_not_yet_fully_audited=True,global_reset_boundary_is_next_candidate_not_proven_mechanism=True,no_production_fix_or_relaxed_dma_ownership_applied=True,do_not_repeat_same_fault_until_recovery_sequence_revised_and_reviewed=True,passed=True)
(HERE/'recovery-source-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(dict(experiment_passed=False,actual_timeout_seconds=round(elapsed,6),retained_imports_proven=True,reset_acks=[3,3],full_recovery_not_proven=True,retained_oem_source_audit_passed=True)))
