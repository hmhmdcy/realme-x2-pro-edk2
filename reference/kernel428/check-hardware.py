"""Check real FULL/DS4 pairing, starvation gaps, active bytes and restoration."""
from pathlib import Path
import hashlib,json,re
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
d=json.loads((HERE/'capture-runtime-r6-validation.json').read_text());s=d['state'];assert s['terminal'] and s['passed'] and not d['worker_live'] and not d['client_live']
assert s['formal_modules_restored'] and s['services_restored'] and not s['new_faults'] and s['taint_before']==s['taint_after']==512
root=P/'capture-collected-r6';rows=[]
for model in ['s5kgw1','s5k3m5','imx471','imx319']:
 for kind in ['pattern','scene']:
  name=model+'-'+kind;text=(root/name/'capture.log').read_text();streams={'full':{},'ds4':{}};order=[]
  for line in text.splitlines():
   if not line.startswith('FRAME '):continue
   r=dict(re.findall(r'([a-z_]+)=([^ ]+)',line));stream=r['kind'];seq=int(r['sequence']);assert seq not in streams[stream]
   assert int(r['bytes'])==(460800 if stream=='full' else 46080) and int(r['changed'])>0 and int(r['tail_changed'])==0
   if streams[stream]:assert seq>max(streams[stream])
   streams[stream][seq]=r;order.append((stream,seq))
  full,ds4=streams['full'],streams['ds4'];assert len(ds4)==18 and len(full)>=24
  assert set(ds4)<=set(full),'Each coarse frame must have a completed FULL partner in this probe'
  deltas=[abs(int(r['timestamp_us'])-int(full[seq]['timestamp_us'])) for seq,r in ds4.items()];assert max(deltas)<5000
  seqs=list(ds4);gaps=[b-a for a,b in zip(seqs,seqs[1:]) if b-a>1];assert len(gaps)==1
  after=text.split('DS4_STOP_FULL_CONTINUES\n')[1];assert after.count('FRAME kind=full ')>=6 and 'FRAME kind=ds4 ' not in after
  active_hashes=[];padding_changes=0;saved=0
  for seq,r in ds4.items():
   path=root/name/('ds4-'+str(seq)+'.bin');assert path.exists();raw=path.read_bytes();assert len(raw)==46080
   seed=0xa5^(int(r['index'])*0x31);active=b''.join(raw[y*768:y*768+640] for y in range(60))
   for y in range(60):
    for x in range(640,768):
     i=y*768+x;padding_changes+=raw[i]!=(seed^((i*197+(i>>8)*31)&255))
   active_hashes.append(hashlib.sha256(active).hexdigest());saved+=1
  assert padding_changes==0
  if kind=='pattern':assert len(set(active_hashes))==1
  else:assert len(set(active_hashes))>1
  rows.append(dict(model=model,kind=kind,full_frames=len(full),ds4_frames=len(ds4),paired_frames=len(ds4),timestamps_are_completion_times=True,max_pair_completion_timestamp_delta_us=max(deltas),
   starvation_gap_in_sofs=gaps[0],full_frames_after_ds4_stop=after.count('FRAME kind=full '),all_mmap_tails_unchanged=True,
   pd10_row_padding_unchanged=True,saved_ds4_frames=saved,distinct_active_payloads=len(set(active_hashes)),passed=True))
kernel=(root/'kernel-log-private.txt').read_text();irq=[(int(a,16),int(b,16)) for a,b in re.findall(r'DS4 bringup irq top=([0-9a-f]+)/([0-9a-f]+)',kernel)]
assert len(irq)==32 and all(not(b&0xefff7e80) for a,b in irq) and 'zoom=00005519' in kernel
assert s['after_status']['jobs']==s['after_status']['completed']==s['after_status']['failed']==s['after_status']['cancelled']==0 and s['after_status']['owner_refs']==53
assert not any(s['after_core'][k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','mapped_bytes','ipe_dma_pending','imported_buffers'])
r=dict(stage=428,scope='Four cameras sequentially, one existing board mode each, 640x480 FULL plus160x120 PD10',
 maintained_commit=json.loads((HERE/'source-state.json').read_text())['commit'],candidate_camss_sha256='a9096d39b368eff3c59c133fd03e493d65294edc0635cf6c5ded46df9f5050c7',
 original_precrop_enabled_on_hardware=True,rows=rows,total_ds4_frames=sum(r['ds4_frames'] for r in rows),total_paired_full_frames=sum(r['paired_frames'] for r in rows),
 total_simultaneous_full_frames=sum(r['full_frames'] for r in rows),extra_full_only_control_frames=24,
 sampled_first_four_sofs_per_stream_show_no_original_camif_error_bits=True,all_irq_error_types_or_fault_injection_not_claimed=True,
 formal_modules_services_and_resources_restored=True,taint_unchanged=True,ipe_jobs=0,automatic_ipa_or_full_ltm_dc_chain_not_claimed=True,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
