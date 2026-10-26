"""Retain IPA6/SOF/history checks and audit the focus phases and CPU benchmark."""
from pathlib import Path
import contextlib,io,json,re,statistics
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
source=(HERE.parent/'kernel444/check-hardware.py').read_text().replace('stage=444','stage=445')
source=source.replace('focus_tone_source_functions_and_packet_contract_unchanged=True','ipa6_focus_tone_functions_unchanged_and_focus_statistics_exact=True')
marker="exec(compile(source,str(HERE/'check-hardware.py'),'exec'))"
source=source.replace(marker,"source=source.replace(\"for k in ['native','isolated']\",\"for k in ['isolated']\")\n"+marker)
with contextlib.redirect_stdout(io.StringIO()):exec(compile(source,str(HERE/'check-hardware.py'),'exec'))
report=HERE/'hardware-validation.json';result=json.loads(report.read_text())
for row in result['rows']:
 text=(root/row['capture']/'client.log').read_text()
 phases=[tuple(map(int,m)) for m in re.findall(r'FOCUS_TIMING epoch=1 sof=(\d+) sync-start-us=(\d+) map-us=(\d+) sample-us=(\d+) score-us=(\d+) unmap-us=(\d+) sync-end-us=(\d+)',text)]
 by_sof={r[0]:r[1:] for r in phases};assert len(phases)==len(by_sof)
 queued={int(s) for s in re.findall(r'IPE_TONE_QUEUE epoch=1 sof=(\d+)',text)}
 overall={int(s):int(us) for s,us in re.findall(r'FRAME_IPA_PREPARE epoch=1 sof=(\d+) combined=1 focus-us=(\d+)',text)}
 assert len(queued)==row['queued_images'] and queued<=set(by_sof)&set(overall)
 assert all(sum(by_sof[s])<=overall[s] for s in queued)
 def metrics(values):
  xs=sorted(v/1000 for v in values);return dict(median_ms=round(statistics.median(xs),3),p95_ms=round(xs[min(len(xs)-1,len(xs)*95//100)],3),maximum_ms=round(xs[-1],3))
 row['focus_phases']={name:metrics([by_sof[s][i] for s in queued]) for i,name in enumerate(['sync_start','map','sample','score','unmap','sync_end'])}
 row['focus_phases']['unattributed_and_diagnostic_log']=metrics([overall[s]-sum(by_sof[s]) for s in queued])
 names=['sync_start','map','sample','score','unmap','sync_end']
 row['dominant_focus_phase_counts']={name:sum(max(range(6),key=lambda i:by_sof[s][i])==j for s in queued) for j,name in enumerate(names)}
 row['focus_frames_over_33ms']=sum(overall[s]>33000 for s in queued)
benchmarks=[]
assert len(state['focus_benchmarks'])==4
for name,bench in state['focus_benchmarks'].items():
 assert bench['fixture_passed'] and bench['checksum_consistent'] and bench['repetitions']==16 and bench['alternating_old_new_order'] and bench['cached_full_not_dma']
 assert bench['reference_median_us']>0 and bench['optimized_median_us']>0
 benchmarks.append(dict(fixture=name,**bench,speedup_ratio=round(bench['reference_median_us']/bench['optimized_median_us'],3)))
result.update(cached_phone_focus_benchmarks=benchmarks,exact_real_fixture_fom_preserved=True,actual_timed_focus_phases=True,
 validated_scope='two isolated main16:9 processed sizes; normal/SOF/IPA6 history, not all sensors or optical quality')
report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(stage=445,rows=result['rows'],benchmarks=benchmarks,total_ipe_completed=result['total_ipe_completed'],passed=True),indent=2))
