from pathlib import Path
import hashlib,json,re
import host,storage
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;read=lambda p:json.loads(p.read_text())
runtime=read(HERE/'pipeline-runtime-r5-validation.json');assert runtime['passed'] and runtime['terminal']
assert not any(runtime[k] for k in ['worker_live','collector_live','client_process_live'])
assert not runtime['collector_result']['timeout']
client=runtime['client_report'];assert client['passed'] and client['services_restored'] and len(client['captures'])==7
logs=P/'collected-r5';rows=[]
for model in ['imx471','imx319','s5k3m5','s5kgw1']:
 text=(logs/('gst-'+model+'.log')).read_text();assert text.count('IPE enabled ')==1
 match=re.search(r'GST_RESULT frames=(\d+).*bus-errors=(\d+) result=(\d+)',text);assert match and int(match[1])==12 and match[2]==match[3]=='0'
 assert client['captures'][model]['ipe_completed']>=12
 rows.append(dict(case=model,application_frames=12,**client['captures'][model]))
for kind in ['dual','raw']:
 text=(logs/('raw-'+kind+'.log')).read_text();assert 'failed=0 result=0' in text
 pairs=re.findall(r'RawPair .*delta-ns=(\d+).*matched=(\d+)',text);assert len(pairs)>=6 and all(x[1]=='1' for x in pairs)
 assert bool('IPE enabled ' in text)==(kind=='dual')
 rows.append(dict(case='raw-'+kind,application_requests=6,max_raw_pair_delta_ns=max(int(x[0]) for x in pairs),**client['captures']['raw-'+kind]))
text=(logs/'isolated-main.log').read_text();assert text.count('IPE enabled ')==1
assert '/var/lib/samurai/k387-pipeline-r5/lib/libcamera.so.0.7.2' in text
assert client['captures']['isolated-main']['actual_isolation_verified']
assert text.count('ADAPT_PHASE ')==5 and text.count('GAMMA_APPLIED ')==1 and 'failed=0 result=0' in text
rows.append(dict(case='isolated-main',**client['captures']['isolated-main']))
source=storage.candidate()/'src/libcamera-v0.7.2'
library_sha=hashlib.sha256((source/'output/src/libcamera/libcamera.so.0.7.2').read_bytes()).hexdigest()
assert library_sha==read(HERE/'runtime-build-validation.json')['library_sha256']==hashlib.sha256((P/'libcamera.so.0.7.2').read_bytes()).hexdigest()
for p in ['src/libcamera/pipeline/camss-vfe/camss_ipe.cpp','src/libcamera/pipeline/camss-vfe/camss_ipe.h']:
 assert (source/p).read_bytes()==(HERE/Path(p).name).read_bytes()
last=runtime['device_result'];assert last['session_creates']==last['session_destroys']==last['session_peak']==1
assert last['image_frames']==last['frames_completed']==last['transfer_maps']==last['transfer_unmaps']
assert not last['watchdogs'] and not last['protocol_errors'] and last['init_done'] and last['pc_done']
state=runtime['m2m_after_client'];assert state['jobs']==state['completed']+state['cancelled'] and state['failed']==0
report=dict(stage=387,run='r5',cases=rows,final_candidate_library_sha256=library_sha,ipe_jobs=state['jobs'],ipe_completed=state['completed'],ipe_cancelled=state['cancelled'],ipe_processing_errors=state['failed'],firmware_runs=state['starts'],
 actual_libcamera_pipeline_and_dmabuf_import=True,original_ife_timestamp_and_raw_sof_preserved=True,isolated_ipa_control_regression=True,all_four_processed_cameras=True,raw_only_no_ipe=True,full_pixel_identity_not_repeated=True,zero_copy=False,permanently_installed=False,full_camera_goal_complete=False,passed=True)
(HERE/'pipeline-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
