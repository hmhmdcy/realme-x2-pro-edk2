from pathlib import Path
import json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((HERE/'boot-runtime-validation.json').read_text());assert d['passed'] and d['ipe_io_config_passed'] and d['ipe_session_lifecycle_passed'] and d['same_boot'] and not d['worker_live'] and not d['collector_live']
r=d['device_result'];text=(P/'collected-r1/kernel-log-private.txt').read_text()
markers=['SYS_INIT acknowledged','SYS_PING acknowledged','IPE create acknowledged type=2 active=1','IPE config region map acknowledged','IPE CONFIG_IO acknowledged scratch=48','IPE config region unmap acknowledged','IPE create acknowledged type=3 active=2','IPE config region map acknowledged','IPE CONFIG_IO acknowledged scratch=48','IPE config region unmap acknowledged','IPE destroy acknowledged active=1','IPE destroy acknowledged active=0','SYS_PC_PREP acknowledged','A5 stopped, cooperative=1 block_reset=0 pc_error=0','A5 DMA aliases retired','A5 PM reference released: 0','diagnostic run end ret=0 init=1 ping=1 pc=1','diagnostic overlay remove ret=0','diagnostic module exit end']
positions=[];offset=0
for marker in markers:offset=text.index(marker,offset)+len(marker);positions.append(offset)
command_words=(8+16+28*2+44*2+8+2*(56+40+56))//4
message_words=(r['init_bytes']+16+32*2+48*2+12+2*(44+56+44))//4
assert r['queue_state'][:4]==[command_words,command_words,message_words,message_words]==[120,120,133,133]
assert r['session_creates']==r['session_destroys']==r['session_peak']==2 and r['image_sessions']==r['image_frames']==0
assert r['io_configs']==r['config_maps']==r['config_unmaps']==2 and not r['config_fw_mapped'] and r['scratch_bytes']==[48,48]
m=re.search(r'\[\s*([\d.]+)\].*A5 CPU release',text);n=re.search(r'\[\s*([\d.]+)\].*A5 HFI response=1',text)
report=dict(stage=379,all_markers_ordered=True,two_distinct_simultaneous_ipe_rt_and_non_rt_handles=True,
 both_create_configure_and_destroy_acknowledged=True,each_session_config_map_and_unmap_acknowledged=True,io_configs=2,config_maps=2,config_unmaps=2,scratch_bytes=[48,48],
 remaining_sessions=0,image_frames_submitted=0,image_processing_verified=False,full_hfi_lifecycle_verified=True,
 command_queue_words=command_words,message_queue_words=message_words,messages=r['messages'],interrupts=r['interrupts'],
 exact_command_reply_wire_size_accounting_matches_runtime_indices=True,ready_response_latency_ms=round((float(n[1])-float(m[1]))*1000,3),
 same_boot=True,automatic_reset_observed=False,host_reset_sent=False,raw_evidence_private=True,passed=True)
(HERE/'io-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
