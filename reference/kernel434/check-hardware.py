"""Accept physical GTM functionality, bank repeatability and SOF association."""
from pathlib import Path
import collections,hashlib,json,struct,sys
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
state=json.loads((P/'runtime-collected-r2/state.json').read_text())
assert state['terminal'] and state['passed'] and state['formal_modules_restored'] and state['services_restored'] and not state['new_faults'] and state['taint_before']==state['taint_after']==0
for key in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error']:assert not state['candidate_final_status'][key]
assert state['candidate_final_status']['jobs']==0 # This probe exercises IFE, not IPE.
for key in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes']:assert not state['after_core'][key]
all_groups={};metrics=[]
for attempt in ['r1','r2']:
 analysis=json.loads((HERE/('capture-analysis-'+attempt+'.json')).read_text());groups=analysis['captures']['pattern']['packet_groups'];assert len(groups)==9
 assert analysis['captures']['pattern']['joined_same_sof']==61
 by={r['packet_index']:r for r in groups};all_groups[attempt]=by
 for phase,row in by.items():
  assert row['generations']==[phase+1] and row['banks']==[([0,1,0,1,0,1,0,0,1][phase])]
  assert len(row['full_active_hash_counts'])==len(row['pd10_active_hash_counts'])==1
  assert next(iter(row['full_active_hash_counts'].values()))==row['frames']>=5
 for kind in ['full','pd10']:
  h=lambda p:next(iter(by[p][kind+'_active_hash_counts']))
  assert h(0)==h(1)==h(7)==h(8) and len({h(0),h(2),h(3),h(4)})==4
  assert h(3)==h(5)==h(6) # Repeated stock LUT across both physical banks.
 for phase,row in by.items():
  seq=row['sof'][len(row['sof'])//2];raw=(P/('runtime-collected-'+attempt)/'pattern'/('full-'+str(seq)+'.bin')).read_bytes()
  assert len(raw)==460800
  metrics.append(dict(attempt=attempt,packet_index=phase,sof=seq,mean_y=sum(raw[:307200])/307200))
for phase in range(9):
 for kind in ['full','pd10']:assert all_groups['r1'][phase][kind+'_active_hash_counts'].keys()==all_groups['r2'][phase][kind+'_active_hash_counts'].keys()
scene=json.loads((HERE/'capture-analysis-r2.json').read_text())['captures']['scene'];assert scene['joined_same_sof']==19 and [r['packet_index'] for r in scene['packet_groups']]==[0,3,7]
scene_metrics=[];sys.path.insert(0,str(HERE.parent/'kernel423'));from nv12 import render
for row in scene['packet_groups']:
 p=row['packet_index'];ys=[]
 for seq in row['sof']:
  raw=(P/'runtime-collected-r2/scene'/('full-'+str(seq)+'.bin')).read_bytes();assert len(raw)==460800;ys.append(sum(raw[:307200])/307200)
 seq=row['sof'][len(row['sof'])//2];raw=(P/'runtime-collected-r2/scene'/('full-'+str(seq)+'.bin')).read_bytes();render(raw,P/('scene-packet-'+str(p)+'-private.png'))
 scene_metrics.append(dict(packet_index=p,frames=len(ys),mean_y_min=min(ys),mean_y_max=max(ys)))
old=json.loads((P/'runtime-collected-r1/state.json').read_text());assert not old['passed'] and old['formal_modules_restored'] and old['taint_after']==0 and not old['new_faults']
r=dict(stage=434,kernel_commit=json.loads((HERE/'source-state.json').read_text())['commit'],candidate_module_sha256=next(r['sha256'] for r in json.loads((HERE/'intree-build-validation.json').read_text())['modules'] if r['name']=='qcom-camss'),
 scope='Main S5KGW1 4608x3456 input; FULL NV12 640x480 and actual PD10 160x120; fixed exposure; IFE-only GTM probe',
 accepted_attempt='r2',pattern_same_sof_sets=61,scene_same_sof_sets=19,gtm_pattern_phases=9,gtm_scene_phases=3,
 identity_equals_disable=True,diagnostic_half_gain_changes_full_and_pd10=True,two_original_tmc11_luts_change_full_and_pd10=True,repeated_original_lut_equal_across_both_gtm_banks=True,
 pattern_hashes_identical_before_and_after_reopen_fix=True,actual_ack_receipts_match_pixel_transitions_by_sof=True,statistics_payload_receipts_validated=True,parameter_queue_copy_survives_userspace_mutation=True,
 stopped_stream_reopen_fixed_in_driver=True,earlier_attempt=dict(attempt='r1',pattern_frames=61,scene_frames=0,scene_error='FULL STREAMON ENODATA: stale PIX RUP deferred the entire initial DS4/GTM packet',formal_environment_restored=True,taint=0),
 discontinuous_sof_observed_in_pattern_probe=True,continuous_cadence_verified=False,pattern_mean_y=metrics,scene_mean_y=scene_metrics,
 ife_and_pd10_physically_verified=True,ipe_jobs_this_probe=0,production_ipa_integrated=False,gtm_version_math_history_association_complete=False,internal_dc_average_sram_dump=False,full_factory_pipeline_complete=False,absolute_image_quality_accepted=False,
 formal_modules_services_resources_restored=True,new_faults=0,taint_after=0,installed=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
