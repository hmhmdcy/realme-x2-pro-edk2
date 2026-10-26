"""Keep the validated feature evidence distinct from the failed final candidate."""
from pathlib import Path
import json
HERE=Path(__file__).resolve().parent
feature=json.loads((HERE/'hardware-validation.json').read_text())
assert feature['attempt']=='r5' and feature['total_ipe_completed']==206 and not feature['passed']
(HERE/'hardware-feature-validation.json').write_text(json.dumps(feature,indent=2)+'\n')
reasons={
 'r1':'1080p isolated child SIGSEGV after stop; complete details retained privately.',
 'r2':'1080p isolated map::at after synchronous focus reentered stop; core retained privately.',
 'r7':'720p isolated returned an error buffer while statistics accumulated, then pairing timeouts; child exit9. Full diagnostics retained privately.'}
for attempt,reason in reasons.items():
 p=HERE/f'runtime-{attempt}-validation.json';d=json.loads(p.read_text());assert d['state']['terminal'] and d['state']['failure']
 d['state']['failure']=reason;p.write_text(json.dumps(d,indent=2)+'\n')
last=json.loads((HERE/'runtime-r7-validation.json').read_text())
assert not last['state']['passed'] and last['state']['formal_modules_restored'] and last['state']['services_restored']
assert not last['worker_live'] and not last['client_live']
restored=json.loads((HERE/'current-state-validation.json').read_text());assert restored['passed']
r=dict(stage=441,last_attempt='r7',passed=False,release_ready=False,
 feature_evidence='hardware-feature-validation.json',feature_evidence_attempt='r5',
 same_sof_720p_1080p_and_causal_ltm_consumption_proven=True,
 isolated_stop_reentry_fixed=True,final_candidate_remaining_failure='isolated statistics backlog, error buffer and image pairing timeout',
 final_attempt_kernel_faults=len(last['state']['new_faults']),
 candidate_not_installed=True,formal440_restored=True,taint=0,full_goal_complete=False)
(HERE/'hardware-validation.json').write_text(json.dumps(r,indent=2)+'\n')
state=json.loads((HERE/'source-state.json').read_text());state.update(baseline_stage=440,build_pending=False,successful_build=5,statistics_pool_experiment_rejected=True)
(HERE/'source-state.json').write_text(json.dumps(state,indent=2)+'\n')
d=dict(stage=441,goal_active=True,phase='feature-evidence-established-final-isolated-backlog-failed',
 formal_release='440 r32/r27 with434 three modules, restored; current module epoch jobs0 and taint0',
 candidate_installed=False,full_goal_complete=False,
 retained_features=['native variable PD10 geometry and layouts','720p/1080p same-SOF automatic paths and causal LTM consumption evidence on r5','0053 synchronous finish stop-reentry fix'],
 rejected_experiment='0054 statistics pool increase reverted; final userspace build5 exactly matches build2',
 pending_candidate='explicit auxiliary FIFO restart classification: software contracts passed, full candidate runtime not accepted',
 latest_failure='r7 720p isolated statistics backlog produced an error buffer and pairing timeout; restored, no new kernel fault',
 next=['Profile bounded FULL/PD10/statistics/focus/parameter/IPE scheduling on the affected isolated path only','Keep strict SOF and GTM/WB identity, no failed-frame history commit','Accept final candidate before packaging or formal installation; then expand remaining sensor/mode/video/optical scope'],
 private_evidence='E:/edk2-samurai-out/kernel441 and phone k441-variable-pd10-r1..r7; all workers terminal; do not replay transactions')
(HERE/'IN-PROGRESS.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(r,indent=2))
