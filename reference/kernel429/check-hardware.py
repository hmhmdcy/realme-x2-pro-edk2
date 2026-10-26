"""Audit transport success separately from failed DC/repeatability acceptance."""
from pathlib import Path
import hashlib,json,struct,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
root=P/'runtime-collected-r2';s=json.loads((root/'state.json').read_text())
assert s['terminal'] and s['passed'] and s['formal_modules_restored'] and s['services_restored']
assert not s['new_faults'] and s['taint_before']==s['taint_after']==512
final=s['candidate_final_status'];assert final['jobs']==final['completed']==final['direct_completed']==4
assert not any(final[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
lines=(root/'replay/client.log').read_text().splitlines();frames=[json.loads(l) for l in lines if l.startswith('{')]
assert len(frames)==4 and {r['full_hash'] for r in frames}=={frames[0]['full_hash']}
assert frames[0]['pd10_hash']==frames[3]['pd10_hash']
outputs=[];rows=[]
for mode in range(4):
 r=frames[mode];assert r['mode']==mode and r['passed']
 raw=(root/f'replay/mode-{mode}-scratch-private.bin').read_bytes();request,size,crc,changed=struct.unpack_from('<4I',raw)
 assert request==1 and size==71488 and len(raw)==size+16
 assert crc==zlib.crc32(raw[16:]) and changed==sum(x!=0xa7 for x in raw[16:])==0
 out=(root/f'replay/mode-{mode}-output-private.bin').read_bytes();assert len(out)==460800;outputs.append(out)
 rows.append(dict(mode=mode,origin='real PD10' if mode in [0,3] else 'neutral black counterfactual' if mode==1 else 'neutral white counterfactual',
  scratch_bytes=size,scratch_changed_from_prefill_bytes=changed,output_sha256=hashlib.sha256(out).hexdigest(),driver_completion=True))
repeat_differences=sum(a!=b for a,b in zip(outputs[0],outputs[3]));assert repeat_differences>0
yerror=sum(abs(a-b) for a,b in zip(outputs[0][:307200],outputs[3][:307200]))/307200
r=dict(stage=429,scope='Temporary two-core paired-source m2m replay; transport and evidence audit only',
 actual_source_commit='2e199f338780c1508a95bd69485ad198a17b3487',actual_build_attempt=1,
 complete_direct_jobs=4,full_and_pd10_origin_same_sof_from428=True,source_sof=17,source_camera='s5kgw1',
 live_sensor_capture=False,automatic_ipa_or_mathematical_history_commit=False,rows=rows,
 repeat_real_output_different_bytes=repeat_differences,repeat_real_luma_mean_absolute_difference=yerror,
 dc_statistics_writeout_verified=False,ltm_dc_consumption_verified=False,
 counterfactual_output_difference_not_causal_proof_because_real_repeat_also_differs=True,
 formal_modules_services_and_resources_restored_after_r2=True,new_related_faults_in_r2=0,
 later_r3_diagnostic_fault_and_subsequent_recovery_recorded_separately=True,
 feature_acceptance_passed=False,evidence_and_transport_audit_passed=True,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n')
s=json.loads((P/'runtime-collected-r3/state.json').read_text());kernel=(P/'runtime-collected-r3/kernel-log-private.txt').read_text()
assert s['terminal'] and not s['passed'] and s['taint_after']==640 and not s.get('formal_modules_restored')
assert 'level 3 translation fault' in kernel and 'pc : readl+' in kernel and 'run_colour_status+' in kernel
fixed=json.loads((HERE/'source-validation.json').read_text());assert fixed['faulting_mmio_diagnostic_absent'] and fixed['latest_fixed_build']==3
i=dict(stage=429,scope='Incident evidence audit; not a successful experiment or recovery',
 experiment_passed=False,worker_terminal=True,client_was_uninterruptible=True,client_wait_channel='v4l2_m2m_cancel_job',
 new_oops_caused_by_added_mmio_diagnostic=True,diagnostic_used_pps_offset_outside_mapped_ipe_top_window=True,
 faulting_diagnostic_removed_in_commit=fixed['commit'],unsafe_core_build2_forbidden=True,fixed_core_build3_not_hardware_validated=True,
 old_boot_formal_modules_and_services_not_restored=True,normal_busybox_reboot_requested_once=True,
 new_boot_not_yet_verified=True,ssh_connection_refused_on_latest_probe=True,user_physical_restart_requested=True,
 formal_disk_modules_unchanged=True,flash_nv_otp_persist_untouched=True,forced_unload_or_unsafe_dma_release_not_attempted=True,
 evidence_audit_passed=True,device_recovery_complete=False,passed=True)
if (HERE/'camera-recovery-validation.json').exists():
 recovery=json.loads((HERE/'camera-recovery-validation.json').read_text())
 if recovery['passed']:
  i.update(scope='Historical r3 incident audit plus subsequent verified physical-restart recovery',
   new_boot_not_yet_verified=False,ssh_connection_refused_on_latest_probe=False,device_recovery_complete=True,
   physical_restart_confirmed_by_user=True,new_boot_and_formal_modules_verified=True,
   formal_four_camera_recovery_frames=sum(r['frames'] for r in recovery['captures'].values()),
   desktop_services_restored=True,recovery_taint=0)
  if (HERE/'single-core-hardware-validation.json').exists():
   fixed_hw=json.loads((HERE/'single-core-hardware-validation.json').read_text())
   assert fixed_hw['passed'];i.update(fixed_core_build3_not_hardware_validated=False,fixed_core_build3_direct_jobs=4)
(HERE/'incident-validation.json').write_text(json.dumps(i,indent=2)+'\n')
print(json.dumps(dict(transport=r,incident=i),indent=2))
