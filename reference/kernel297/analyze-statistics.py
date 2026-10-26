"""Validate actual typed statistics, ROI population, and restart buffer coverage."""
from pathlib import Path
import hashlib,json,shlex,struct
import host
ROOT=Path(__file__).resolve().parent
capture=json.loads((ROOT/'stats-capture-validation.json').read_text())
assert capture['tool_exit']==0 and capture['actual_frames']==99 and capture['statistics_frames']==90
expected=[820560,410280,410280,2,820560,2,820560,820560,820560,None,820560]
phases=[]
for phase,total in enumerate(expected):
 if total is None:continue
 frame=phase*9+8
 command=f"from pathlib import Path;import sys;sys.stdout.buffer.write(Path('/var/lib/samurai/k297-stats-r1/frame-private-{frame}.qcst').read_bytes())"
 path=host.PRIVATE/f'stats-{frame}-private.qcst'
 if path.exists():data=path.read_bytes()
 else:
  data=host.ssh('python3 -c '+shlex.quote(command),timeout=15).stdout;path.write_bytes(data)
 assert len(data)==4112
 version,length,kind,flags,size=struct.unpack_from('<IIHHI',data)
 assert (version,length,kind,flags,size)==(1,4104,1,0,4104)
 bins=struct.unpack_from('<1024I',data,16)
 samples=[r for r in capture['statistics'] if r['phase']==phase]
 steady=[r for r in samples if r['frame']%9>=5]
 assert len(samples)==9 and len(steady)==4
 row=dict(phase=phase,frame=frame,expected_sum=total,actual_sum=sum(bins),
  steady_sums=[r['sum'] for r in steady],nonzero_bins=[dict(bin=i,count=n) for i,n in enumerate(bins) if n],
  steady_hashes=[format(r['hash'],'016x') for r in steady],
  buffer_indices=sorted({r['index'] for r in samples}),sequences=[r['sequence'] for r in samples],
  sha256=hashlib.sha256(data).hexdigest())
 row['sum_contract_passed']=row['actual_sum']==total and all(r['sum']==total for r in steady)
 row['steady_histogram_stable']=len(set(row['steady_hashes']))==1
 phases.append(row)
restart=all(r['buffer_indices']==[0,1,2] for r in phases if r['phase'] in [8,10])
report=dict(stage=297,kernel_build=297,sensor='s5k3m5',sensor_pattern=2,csid_pattern=0,
 input_width=2104,input_height=1560,image_frames=99,statistics_frames=90,statistics_bytes=4112,bins=1024,
 phases=phases,all_roi_population_contracts_passed=all(r['sum_contract_passed'] for r in phases),
 all_steady_histograms_stable=all(r['steady_histogram_stable'] for r in phases),
 image_restart_and_late_stats_start_all_three_buffers_seen=restart,
 exact_image_stats_sof_association_not_proven=True,scene_statistics_and_auto_exposure_not_yet_verified=True,
 no_cpu_histogram_substitution=True,no_userspace_mmio=True,
 full_isp_pipeline_and_iq_incomplete=True)
report['steady_roi_contracts_passed']=capture['passed'] and report['all_roi_population_contracts_passed'] and report['all_steady_histograms_stable'] and restart
startup=[r for r in capture['statistics'] if r['frame'] in [0,72,90]]
report['startup_packets']=[dict(frame=r['frame'],sequence=r['sequence'],sum=r['sum'],expected_sum=820560,valid=r['sum']==820560) for r in startup]
report['startup_statistics_valid']=all(r['valid'] for r in report['startup_packets'])
report['ready_for_automatic_exposure']=False
report['passed']=report['steady_roi_contracts_passed'] and report['startup_statistics_valid']
(ROOT/'statistics-pixel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='phases'},indent=2));assert report['passed']
