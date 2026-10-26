"""Keep439's per-frame audit, extending it to the signed four-camera cohort."""
from pathlib import Path
import host
HERE=Path(__file__).resolve().parent
source=(HERE.parent/'kernel439/check-hardware.py').read_text();source=source[:source.index("replay=state['replay']")]
source=source.replace("else 'r1'","else 'r2'")
source=source.replace(" text=(root/name/'client.log')", " model=summary['model']\n text=(root/name/'client.log')")
source=source.replace("assert cookie not in versions and v['enabled']=='0';versions[cookie]=v", "assert cookie not in versions and v['enabled']==('0' if cookie==1 or model=='imx471' else '1');versions[cookie]=v")
source=source.replace("q['enabled']=='0'", "q['enabled']==('0' if model=='imx471' else '1')")
source=source.replace("assert v['ccm']=='1';bootstrap", "assert v['ccm']==('1' if model=='imx471' else '0');bootstrap")
source=source.replace("assert pending is None and set(receipts)|discarded==set(prepares)==set(ccms)", "assert pending is None and set(receipts)|discarded==set(prepares)\n assert (set(ccms)==set(prepares)) if model=='imx471' else not ccms")
source=source.replace("assert len(matrix)==9 and any(abs(x-y)>1e-4 for x,y in zip(matrix,[1,0,0,0,1,0,0,0,1]))", "assert len(matrix)==9\n  if model=='imx471':assert any(abs(x-y)>1e-4 for x,y in zip(matrix,[1,0,0,0,1,0,0,0,1]))")
source=source.replace("(name=='scene-native')", "(not summary['isolated'])")
source=source.replace("struct.unpack_from('<I',packet,32)[0]==7", "struct.unpack_from('<I',packet,32)[0]==(7 if model=='imx471' else 5)")
source=source.replace("metadata=next(f for f in frames if int(f['sequence'])==sof);assert tuple(round(float(v)*128) for v in metadata['matrix'].split(','))==coeff", "metadata=next(f for f in frames if int(f['sequence'])==sof)\n if model=='imx471':assert tuple(round(float(v)*128) for v in metadata['matrix'].split(','))==coeff")
source=source.replace("'capture':name", "'capture':name,'model':model")
source=source.replace("'gtm_original_disabled_versions_observed'", "'gtm_original_switch_versions_observed'")
source=source.replace("'trace_packet_matches_applied_matrix_metadata':True", "'ipe_trace_matrix_matches_metadata':True if model=='imx471' else None,'matrix_domain':'IPE' if model=='imx471' else 'IFE'")
source+='''
raw_rows=[];raw_ipe=raw_images=raw_only_images=0
for name,summary in state['raw'].items():
 text=(root/name/'client.log').read_text();assert summary['passed'] and 'failed=0 result=0' in text and 'FIXTURE_RESTORATION result=0' in text
 assert 'IPE observation rejected' not in text and 'IPE_TONE_REJECT' not in text and 'IFE_GTM_REJECT' not in text
 pairs=re.findall(r'RawPair request=(\\d+) pix-sof=(\\d+) raw-sof=(\\d+) pix-start=(\\d+) raw-start=(\\d+) delta-ns=(\\d+) tolerance-ns=(\\d+) matched=(\\d+)',text)
 assert len(pairs)==summary['frames'] and all(p[1]==p[2] and int(p[5])<=int(p[6]) and p[7]=='1' for p in pairs)
 histories=re.findall(r'IPE_HISTORY_STOP epoch=1 prepared=(\\d+) committed=(\\d+) discarded=(\\d+) superseded=(\\d+) aborted=(\\d+) pending=(\\d+)',text);assert len(histories)==1
 prepared,committed,discarded,superseded,aborted,pending=map(int,histories[0]);assert not pending and not superseded
 images=re.findall(r'RAW_IMAGE request=(\\d+) format=(\\S+) sequence=(\\d+) timestamp=(\\d+) bytes=(\\d+) status=(\\d+) sample-hash=(\\d+)',text)
 for image in images:assert int(image[3])>0 and int(image[4])>0 and image[5]=='0' and int(image[6])>0
 if summary['kind']=='raw':
  assert len(images)==summary['frames'] and all(i[1]!='NV12' for i in images)
  assert not summary['ipe_completed'] and not committed and discarded==prepared==summary['frames'] and not aborted
  assert all(term not in text for term in ['PD10_READY ','IPE_TONE_PREPARE ','IPE_TONE_QUEUE '])
  assert re.search(r'IPE_TONE_STOP epoch=1 revision=0 pending=0',text)
  raw_only_images+=summary['frames']
 else:
  assert len(images)==2*summary['frames'] and sum(i[1]=='NV12' for i in images)==summary['frames']
  assert summary['ipe_completed']==committed==summary['frames'] and not discarded and not aborted
  assert len(re.findall(r'IPE_TONE_PREPARE ',text))>0 and text.count('PD10_READY ')>=summary['frames']
 raw_images+=summary['frames'];raw_ipe+=summary['ipe_completed']
 raw_rows.append(dict(capture=name,model=summary['model'],kind=summary['kind'],requests=summary['frames'],ipe_jobs=summary['ipe_completed'],observations_discarded=discarded,raw_pair_same_sof=True,passed=True))
assert len(raw_rows)==5 and state['raw']['s5kgw1-raw-raw']['frames']==72 and raw_only_images==90
assert s['completed']==all_images+raw_ipe
kernel=(root/'kernel-log-private.txt').read_text();assert kernel.count('A5 IPE frame completed request=')==s['completed']
previous=json.loads((P/'runtime-collected-r1/state.json').read_text());assert previous['terminal'] and not previous['passed'] and previous['formal_modules_restored'] and previous['services_restored'] and not previous['new_faults'] and previous['taint_after']==0
r=dict(stage=440,accepted_attempt=attempt,rows=rows,raw_rows=raw_rows,automatic_delivered_images=all_images,successful_automatic_math_commits=all_math,bootstrap_images=all_bootstrap,discarded_stop_proposals=all_discarded,raw_only_images=raw_only_images,dual_stream_images=raw_ipe,total_ipe_jobs=s['completed'],same_source_package_cohort_all_four_native_and_isolated=True,actual_gtm_wb_version_same_sof_pd10_and_success_history=True,front_original_tmc_gtm_ife_ccm_disabled_preserved=True,raw_only_metadata_observations_discarded_without_fake_ipe_history=True,initial_attempt_raw_only_failure_fixed_in_pipeline=True,formal_modules_services_resources_restored=True,new_faults=0,taint=0,installed=False,absolute_image_quality_accepted=False,full_goal_complete=False,passed=True)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\\n');print(json.dumps(r,indent=2))
'''
generated=host.PRIVATE/'hardware-audit-generated.py';generated.write_text(source)
exec(compile(source,str(generated),'exec'))
