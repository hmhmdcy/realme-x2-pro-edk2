"""Measure real-scene statistics response and retain the invalid startup packet."""
from pathlib import Path
import hashlib,json,shlex,struct
import host
ROOT=Path(__file__).resolve().parent
capture=json.loads((ROOT/'optical-capture-validation.json').read_text());assert capture['passed']
rows=capture['statistics'];assert len(rows)==18
phases=[]
for phase,frame in enumerate([5,11,17]):
 command=f"from pathlib import Path;import sys;sys.stdout.buffer.write(Path('/var/lib/samurai/k297-optical-r1/frame-private-{frame}.qcst').read_bytes())"
 data=host.ssh('python3 -c '+shlex.quote(command),timeout=15).stdout
 p=host.PRIVATE/f'optical-stats-{frame}-private.qcst';assert not p.exists();p.write_bytes(data)
 assert len(data)==4112 and struct.unpack_from('<IIHHI',data)==(1,4104,1,0,4104)
 bins=struct.unpack_from('<1024I',data,16)
 stable=[r for r in rows if r['phase']==phase and r['frame']%6>=2]
 phases.append(dict(phase=phase,frame=frame,exposure_code=3000 if phase==1 else 500,
  population=sum(bins),expected_population=499392,mean_bin=sum(i*n for i,n in enumerate(bins))/sum(bins),
  nonzero_bins=sum(n!=0 for n in bins),all_steady_populations_valid=all(r['sum']==499392 for r in stable),
  steady_mean_bins=[r['weighted']/r['sum'] for r in stable],sha256=hashlib.sha256(data).hexdigest()))
invalid=[dict(frame=r['frame'],sequence=r['sequence'],population=r['sum'],expected_population=499392) for r in rows if r['sum']!=499392]
response=all(r['population']==499392 and r['all_steady_populations_valid'] for r in phases) and phases[1]['mean_bin']>phases[0]['mean_bin']+2 and abs(phases[2]['mean_bin']-phases[0]['mean_bin'])<1
report=dict(stage=297,kernel_build=297,sensor='imx319',input_width=1632,input_height=1224,statistics_frames=18,
 sensor_and_csid_tpg_disabled=True,no_userspace_mmio=True,no_cpu_histogram_substitution=True,phases=phases,
 stable_exposure_response_and_return_passed=response,invalid_packets=invalid,
 all_packets_valid=not invalid,statistics_initialization_or_first_valid_frame_fix_required=bool(invalid),
 initial_packet_delivered_without_error_flag=bool(invalid),ready_for_automatic_exposure=False,
 exact_image_stats_sof_association_not_proven=True,private_histograms_not_published=True)
(ROOT/'optical-statistics-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2));assert response and not invalid
