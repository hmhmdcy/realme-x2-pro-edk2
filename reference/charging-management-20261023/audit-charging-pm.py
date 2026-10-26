"""Audit actual installed PM callbacks from the retained trace, offline."""
from pathlib import Path
import json
import re
import sys

ref=Path(__file__).resolve().parent
revision = sys.argv[1] if len(sys.argv) > 1 else None
assert revision in [None, 'r5']
if revision == 'r5':
    raise SystemExit('Retired r5 acceptance: use charging-ui-audit-20261023/audit-pm-r5-qualified.py; '
                     'the retained r5 runtime boolean does not verify the planned RTC window.')
p=Path('/mnt/e/edk2-samurai-out/charging-management-20261023') / ('pm-' + revision if revision else 'pm')
result=json.loads((p/'runtime-result.json').read_text())
before=json.loads((p/'sample-before-private.json').read_text())
after=json.loads((p/'sample-after-private.json').read_text())
initial=json.loads((p/'before-private.json').read_text())
final=json.loads((p/'after-private.json').read_text())
pending={};records=[]
start=re.compile(r'\s(\d+\.\d+): device_pm_callback_start: (\S+) (\S+), parent: [^,]+, ([^\[]*)\[([^\]]+)\]')
end=re.compile(r'\s(\d+\.\d+): device_pm_callback_end: (\S+) (\S+), err=(-?\d+)')
targets={'0-005c','samurai-usb-input','5-0055','samurai-gauge-protection'}
for line in (p/'pm-trace-private.txt').read_text().splitlines():
    m=start.search(line)
    if m and m[3] in targets:
        assert m[3] not in pending
        pending[m[3]]={'device':m[3],'driver':m[2],'ops':m[4].strip(),'phase':m[5],'start':float(m[1])}
    m=end.search(line)
    if m and m[3] in targets:
        assert m[3] in pending
        record=pending.pop(m[3]);record.update(end=float(m[1]),error=int(m[4]));records.append(record)
assert not pending and records

def event(device,phase):
    # Empty ops is the separate prepare/complete wrapper carrying the same
    # PM event verb, not the driver's normal suspend/resume invocation.
    rows=[r for r in records if r['device']==device and r['phase']==phase and r['ops']]
    assert len(rows)==1 and rows[0]['error']==0,(device,phase,rows)
    return rows[0]

cs=event('0-005c','suspend');cr=event('0-005c','resume')
us=event('samurai-usb-input','suspend');ur=event('samurai-usb-input','resume')
assert cs['end']<=us['start'] and ur['end']<=cr['start']
gs=event('5-0055','suspend');gr=event('5-0055','resume')
assert cs['end']<=gs['start'] and gr['end']<=cr['start']
config=lambda d:{k:v for k,v in d['registers'].items() if k!='13'}
assert config(initial)==config(final)
assert result['charging_resumed_healthy']
full_reset = bool(revision and int(final['registers']['13']) & 0x0c == 0x0c and after['session_seconds'] <= 1)
assert full_reset or after['session_seconds']>=before['session_seconds']+int(result['residency_seconds'])-1
callbacks=bool(result['same_boot'] and result['charging_resumed_healthy'] and result['camera_and_four_services_unchanged'])
report=dict(result)
report.update(trace_audit_pending=False,callbacks=records,charger_stop_and_fresh_resume_passed=callbacks,
    supplier_pm_order_verified=True,charger_configuration_preserved=True,boottime_session_retains_sleep=True,
    rtc_s2idle_residency_proved=bool(result['residency_seconds']>=1 and result['rtc_irq_delta']==1))
report['passed']=bool(callbacks and result['runtime_passed'])
if revision:
    report['full_cycle_reset_after_sleep'] = full_reset
    report['manifest_sha256'] = 'f1a885e2ca9c3226ca50d94f39c17c3cae5411b1047696976975df976aa971cf'
(ref/('charging-pm-' + revision + '-result.json' if revision else 'charging-pm-result.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
