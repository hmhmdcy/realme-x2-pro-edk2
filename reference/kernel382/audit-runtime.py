"""Account for the complete real transaction independently of the worker."""
from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((HERE/'boot-runtime-validation.json').read_text());pixels=json.loads((HERE/'pixels-validation.json').read_text())
assert d['passed'] and d['image_control_completion_passed'] and d['same_boot'] and not d['worker_live'] and not d['collector_live'] and pixels['actual_pixel_transfer_verified'] and pixels['nv12_identity_or_expected_level_validation_passed']
r=d['device_result'];text=(P/'collected-r1/kernel-log-private.txt').read_text()
markers=['IPE reset ACKs verified before CPU release','A5 CPU release','SYS_INIT acknowledged','SYS_PING acknowledged','IPE create acknowledged type=2 active=1','IPE config region map acknowledged','IPE CONFIG_IO acknowledged scratch=48','IPE config region unmap acknowledged','IPE create acknowledged type=3 active=2','IPE config region map acknowledged','IPE CONFIG_IO acknowledged scratch=48','IPE config region unmap acknowledged','IPE frame completed request=1','IPE destroy acknowledged active=1','IPE destroy acknowledged active=0','SYS_PC_PREP acknowledged','A5 stopped, cooperative=1 block_reset=0 pc_error=0','A5 DMA aliases retired','A5 PM reference released: 0','diagnostic run end ret=0 init=1 ping=1 pc=1','diagnostic overlay remove ret=0','diagnostic module exit end']
offset=0
for marker in markers:offset=text.index(marker,offset)+len(marker)
command_words=(8+16+28*2+44*2+8+2*(56+40+56)+56+40+56)//4
message_words=(r['init_bytes']+16+32*2+48*2+12+2*(44+56+44)+44+72+44)//4
assert r['queue_state'][:4]==[command_words,command_words,message_words,message_words]==[158,158,173,173]
assert r['session_creates']==r['session_destroys']==r['session_peak']==2 and r['image_sessions']==0
assert r['image_frames']==r['frames_completed']==r['transfer_maps']==r['transfer_unmaps']==1
assert not r['ipe_dma_pending'] and not r['request_fw_mapped'] and r['ipe_reset_acks']==[3,3]
assert r['io_configs']==r['config_maps']==r['config_unmaps']==2 and r['scratch_bytes']==[48,48] and not r['config_fw_mapped']
assert r['messages']==16 and r['interrupts']==17 and not r['watchdogs'] and not r['protocol_errors']
m=re.search(r'\[\s*([\d.]+)\].*A5 CPU release',text);n=re.search(r'\[\s*([\d.]+)\].*A5 HFI response=1',text)
report=dict(stage=382,all_markers_ordered=True,two_distinct_simultaneous_ipe_rt_and_non_rt_handles=True,
 both_create_configure_and_destroy_acknowledged=True,io_configs=2,scratch_bytes=[48,48],ipe_preboot_reset_acks=[3,3],
 frame_submitted=1,frame_completed=1,frame_command_bytes=40,frame_ack_bytes=72,transfer_maps=1,transfer_unmaps=1,
 actual_pixel_transfer_verified=True,normal_nv12_levels_verified=True,full_iq_or_optical_calibration_proven=False,
 command_queue_words=command_words,message_queue_words=message_words,messages=r['messages'],interrupts=r['interrupts'],
 exact_wire_size_accounting_matches_runtime_indices=True,ready_response_latency_ms=round((float(n[1])-float(m[1]))*1000,3),
 cooperative_stop_without_global_block_reset=True,all_dma_pm_released=True,same_boot=True,automatic_reset_observed=False,host_reset_sent=False,raw_evidence_private=True,passed=True)
(HERE/'io-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
