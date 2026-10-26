"""Audit determinism and coarse consumption independently of statistics export."""
from pathlib import Path
import hashlib,json,re,struct,zlib
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
def diff(a,b):
 return dict(different_bytes=sum(x!=y for x,y in zip(a,b)),luma_mean_absolute_difference=sum(abs(x-y) for x,y in zip(a[:307200],b[:307200]))/307200)
def replay(attempt):
 root=P/('runtime-collected-'+attempt);s=json.loads((root/'state.json').read_text())
 assert s['terminal'] and s['passed'] and s['formal_modules_restored'] and s['services_restored']
 assert not s['new_faults'] and s['taint_before']==s['taint_after']==0
 final=s['candidate_final_status'];assert final['jobs']==final['completed']==final['direct_completed']==4
 assert not any(final[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
 frames=[json.loads(l) for l in (root/'replay/client.log').read_text().splitlines() if l.startswith('{')]
 assert len(frames)==4 and len({r['full_hash'] for r in frames})==1 and frames[0]['pd10_hash']==frames[3]['pd10_hash']
 outputs=[];rows=[]
 for mode in range(4):
  assert frames[mode]['mode']==mode and frames[mode]['passed']
  raw=(root/f'replay/mode-{mode}-scratch-private.bin').read_bytes();request,size,crc,changed=struct.unpack_from('<4I',raw)
  assert request==(mode+1 if attempt=='r3' else 1) and size==46128 and len(raw)==size+16 and crc==zlib.crc32(raw[16:]) and changed==sum(x!=0xa7 for x in raw[16:])==0
  out=(root/f'replay/mode-{mode}-output-private.bin').read_bytes();assert len(out)==460800;outputs.append(out)
  rows.append(dict(mode=mode,input='real' if mode in [0,3] else 'neutral black' if mode==1 else 'neutral white',scratch_bytes=size,scratch_changed_bytes=changed,output_sha256=hashlib.sha256(out).hexdigest()))
 repeat=diff(outputs[0],outputs[3]);black=diff(outputs[0],outputs[1]);white=diff(outputs[0],outputs[2])
 assert repeat['different_bytes']==0 and black['different_bytes']>0 and white['different_bytes']>0
 fresh=s.get('fresh_capture')
 if attempt=='r2':
  assert s['live_sensor_capture'] and fresh['paired_frames']>=5 and fresh['fixture_restored'] and fresh['pattern']==0
  text=(root/'scene/capture.log').read_text();sof=fresh['selected_sof']
  for kind,name,size in [('full','full',460800),('ds4','pd10',46080)]:
   assert re.search(r'FRAME kind='+kind+r' .*sequence='+str(sof)+r' .*tail_changed=0 ',text)
   assert (root/f'scene/{kind}-{sof}.bin').read_bytes()==(root/f'replay/{name}-private.bin').read_bytes()
   assert (root/f'replay/{name}-private.bin').stat().st_size==size
 else:assert not s['live_sensor_capture']
 if attempt=='r3':
  assert s['persistent_ipe_session'] and final['starts']==final['stops']==1
  for mode,out in enumerate(outputs):assert out==(P/f'runtime-collected-r2/replay/mode-{mode}-output-private.bin').read_bytes()
 return dict(attempt=attempt,direct_jobs=4,live_sensor_capture=s['live_sensor_capture'],fresh_capture=fresh,rows=rows,
  repeat_real=repeat,real_vs_black=black,real_vs_white=white,persistent_ipe_session=attempt=='r3',starts=final['starts'],stops=final['stops'],formal_modules_services_resources_restored=True,new_faults=0,taint=0)
control=P/'control-collected-r1';cs=json.loads((control/'state.json').read_text());assert cs['terminal'] and cs['passed'] and cs['taint_after']==0 and not any(cs['new_faults'].values())
co=[(control/f'mode-{i}-output-private.bin').read_bytes() for i in range(4)]
off=diff(co[0],co[1]);ip=diff(co[2],co[3]);assert off['different_bytes']==0 and ip['different_bytes']>0
rows=[replay('r1'),replay('r2'),replay('r3')]
r=dict(stage=430,scope='Reversible fixed-size two-pass replay with stock424 tuning; includes fresh main sensor capture',
 source_commit=json.loads((HERE/'source-state.json').read_text())['commit'],build_attempt=1,
 formal_full_only_controls=dict(direct_jobs=4,ltm_off_repeat=off,ltm_ip_only_without_dc_repeat=ip),
 corrected_dual_pass_replays=rows,corrected_direct_jobs=12,total_new_direct_jobs_including_controls=16,
 cold_and_persistent_session_outputs_byte_identical=True,persistent_session_request_done_poll_verified=True,
 fixed_input_repeatability_verified=True,ltm_coarse_input_consumption_causal_evidence=True,
 conclusion_scope='Fixed FULL, real/black/white/repeated-real PD10; stock LTM enabled, ANR and TF disabled. Repeat equality removes the old uncontrolled-output confound.',
 dc_statistics_bytewise_writeout_verified=False,scratch_is_not_a_validated_dc_table_export=True,
 hardware_average_sram_bank_identity_and_reset_readout_complete=False,
 automatic_ipa_or_mathematical_history_commits=0,gtm_applied_version_association_verified=False,
 full_factory_auto_pipeline_complete=False,absolute_image_quality_calibration_accepted=False,installed=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
