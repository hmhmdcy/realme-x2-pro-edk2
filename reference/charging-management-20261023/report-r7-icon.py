"""Summarize retained completed capture; no device or network access."""
from pathlib import Path
import json

REF=Path(__file__).resolve().parent
PRIVATE=Path('/mnt/e/edk2-samurai-out')
run=PRIVATE/'charging-ui-audit-20261023/icon-capture-r7/charging-icon-r7-20261023-01'
capture=run/'fetch-1792745336794130814/capture'
result=json.loads((capture/'result.json').read_text())
raw=json.loads((capture/'capture-private.json').read_text())
fetch=[json.loads(p.read_text()) for p in run.glob('fetch-*-result.json')]
assert len(fetch)==1 and fetch[0]['cleanup_confirmed'] and fetch[0]['identity_unchanged']
assert result['physical_cycle_passed'] and result['terminal_reason']=='cycle_complete'
fresh=json.loads((PRIVATE/'charging-management-20261023/r7-replug/fresh-source-stdout-private.json').read_text())
handoff=json.loads((REF/'r7-handoff-result.json').read_text())
assert handoff['passed'] and handoff['effective_source_budget_ua']==100000
report={k:result[k] for k in ['scope','physical_cycle_passed','screen_latency_verified','terminal_reason',
 'sample_count','kernel_event_count','dbus_signal_count','monitor_complete','raw_cycle_evidence',
 'clock_mapping','dbus_parse_errors','edges','notes']}
report.update(manifest_sha256=handoff['manifest_sha256'],worker_exited=True,cleanup_confirmed=True,
 identity_unchanged=True,first_sample=raw['samples'][0],last_sample=raw['samples'][-1],
 subjective_feedback={'detach':'用户感觉图标切换明显快了一点',
                      'attach':'用户长时间未见图标变化','screen_acceptance_passed':False},
 source_after_capture=fresh['source'],pmic_after_capture=fresh['pmic'],
 upower_later_snapshot=fresh['upower'],later_snapshot_scope='after capture; exact State transition time not observed',
 last_handoff_sample=handoff['sample'],last_handoff_limits=handoff['limits'],
 conclusion='Real removal/reconnection captured. CDP1.5A became SDP100mA; battery net current remained negative in the recorded reconnect interval. No reconnect State signal in that interval, not a measured screen rendering delay.',
 physical_float_branch_observed=False,usb500_accepted=False,pm_resume_accepted=False)
(REF/'icon-r7-capture-result.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:report[k] for k in ['physical_cycle_passed','sample_count','worker_exited','cleanup_confirmed','screen_latency_verified']},indent=2))
