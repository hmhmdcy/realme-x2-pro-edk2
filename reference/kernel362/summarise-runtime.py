from pathlib import Path
import json,sys
import host
HERE=Path(__file__).resolve().parent;runs={}
for name in sys.argv[1:]:
    d=json.loads((host.PRIVATE/('probe-'+name+'-observation.json')).read_text());s=d['state'];assert s['terminal'] and not d['worker_live']
    runs[name]=s['summary']
passed=[item for summary in runs.values() if summary['passed'] for item in summary['captures'].values()]
assert runs['r2']['passed'] and runs['r2']['captures']['main-isolated']['actual_transport_verified']
report=dict(stage=362,runs=runs,full_candidate_validation_passed=all(v['passed'] for k,v in runs.items() if k!='r1'),
    initial_ordering_failure_retained=not runs['r1']['passed'],patched_dispatcher_and_camss_and_common_ordering=True,
    isolated_frames=sum(x['frames'] for x in passed if x['isolation_requested']),
    threaded_frames=sum(x['frames'] for x in passed if not x['isolation_requested']),
    isolated_contexts=sum(x['isolation_requested'] for x in passed),optical_case_executed=True,
    absolute_optical_calibration_verified=False,installed=False)
(HERE/'runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='runs'},indent=2))
