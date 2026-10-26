from pathlib import Path
import json,re,statistics
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE
report=json.loads((R/'controlled-rear-r2-validation.json').read_text());assert report['passed'] and len(report['frames'])==48
for name in ['i2c-control-trace-private.txt','stderr-private.txt']:
 host.download('/var/lib/samurai/k238-controlled-rear-r14-r2/'+name,P/('controlled-r2-'+name))
trace=(P/'controlled-r2-i2c-control-trace-private.txt').read_text();records=[]
for line in trace.splitlines():
 if 'i2c_write:' not in line:continue
 m=re.search(r'i2c_write: i2c-7 #0 a=010 f=0000 l=4 \[([0-9a-fA-F-]+)\]$',line);assert m,line;data=bytes.fromhex(m[1].replace('-',' '));assert len(data)==4
 records.append((int.from_bytes(data[:2],'big'),int.from_bytes(data[2:],'big')))
gains=[v for a,v in records if a==0x0204];exposures=[v for a,v in records if a==0x0202]
assert gains==[0,896,0] and exposures==[201,3216,201],(gains,exposures)
code=r'''
from pathlib import Path
import json
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k236-runtime/boot-id-private.txt').read_bytes();p=r/'k238-controlled-rear-r14-r2'
assert json.loads((p/'state-private.json').read_text())['exit_code']==0
print(json.dumps({f.name:f.read_text() for f in p.glob('cpu*-trace-stats-private.txt')}))
'''
r=host.ssh('python3 -',input=code.encode(),timeout=12);(P/'control-trace-cpu-stats-private.json').write_bytes(r.stdout);cpus=json.loads(r.stdout);assert len(cpus)==8
for name,text in cpus.items():
 for key in ['overrun','commit overrun','dropped events']:
  found=re.search(r'^'+key+r':\s*(\d+)\s*$',text,re.M);assert found and int(found[1])==0,(name,key)
phases=[]
header=Path('/home/cy122/x2pro-linux/libcamera214-root/candidate238-r14/usr/include/libcamera/libcamera/control_ids.h').read_text() if Path('/home/cy122/x2pro-linux/libcamera214-root/candidate238-r14/usr/include/libcamera/libcamera/control_ids.h').exists() else Path('/home/cy122/x2pro-linux/libcamera214-root/candidate238-r14/usr/include/libcamera/control_ids.h').read_text()
exposure_manual=int(re.search(r'ExposureTimeModeManual\s*=\s*(\d+)',header)[1]);gain_manual=int(re.search(r'AnalogueGainModeManual\s*=\s*(\d+)',header)[1])
assert [f['queued_index'] for f in report['frames']]==list(range(48))
assert all(f['phase']==f['queued_index']//12 and f['settled']==(f['queued_index']%12>=6) for f in report['frames'])
for phase in range(4):
 frames=[f for f in report['frames'] if f['phase']==phase];assert len(frames)==12
 settled=[f for f in frames if f['settled']];assert len(settled)==6
 target_exposure=2000 if phase in [0,3] else 32000;target_gain=8 if phase==2 else 1
 assert all(abs(f['exposure_us']-target_exposure)<=20 and abs(f['analogue_gain']-target_gain)<.03 and f['exposure_mode']==exposure_manual and f['gain_mode']==gain_manual for f in settled)
 phases.append(dict(phase=phase,settled_frames=6,exposure_us=sorted({f['exposure_us'] for f in settled}),analogue_gain=sorted({f['analogue_gain'] for f in settled}),
  mean=statistics.mean(f['mean'] for f in settled),stddev=statistics.mean(f['stddev'] for f in settled),quantile_p50=statistics.mean(f['quantiles_p10_p50_p90'][1] for f in settled),
  sample_min=min(f['byte_min'] for f in settled),sample_max=max(f['byte_max'] for f in settled),saturated_fraction=statistics.mean(f['saturated_fraction'] for f in settled)))
stats=dict(stage=238,frames=48,phases=phases,real_i2c_analogue_gain_codes=sorted(set(gains)),real_i2c_exposure_line_codes=sorted(set(exposures)),
 i2c_gain_write_request_order=[0,896,0],i2c_exposure_write_request_order=[201,3216,201],settled_capture_metadata_matches_four_targets=True,actual_cpu_statistics_path=True,trace_entries=len(records),all_eight_cpu_trace_loss_counters_zero=True,
 i2c_write_trace_is_send_request_not_ack_or_register_readback=True,transition_frame_delay_not_calibrated=True,
 optical_response_not_inferred_from_noise_alone=True,ambient_scene_no_reference_or_illumination=True,full_cleanup_passed=True)
(R/'control-response-analysis.json').write_text(json.dumps(stats,indent=2)+'\n');print(json.dumps(stats))
