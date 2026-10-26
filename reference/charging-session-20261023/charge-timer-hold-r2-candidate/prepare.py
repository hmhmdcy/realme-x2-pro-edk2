"""Retain r1; count hardware-stop latency before pausing the timer."""
from pathlib import Path
import difflib,hashlib,json
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'charge-timer-hold-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
delivery=json.loads((OLD/'delivery.json').read_bytes())
assert delivery['passed'] and all(sha((OLD/n).read_bytes())==row['sha256'] for n,row in delivery['files'].items())
assert json.loads((OLD/'ko-result.json').read_bytes())['module_sha256']=='04ff91ca8f0a8a2312522df0c6f21218b877c18f150004c70050ffc8f4176fe4'
source=(OLD/'samurai-mp2650.c').read_text()
def replace(a,b):
 global source
 assert source.count(a)==1,a
 source=source.replace(a,b)
replace('bool timer_hold_confirmed;','bool timer_hold_confirmed;\n\tu64 timer_hold_since_ns;')
replace('bool healthy_full;','bool healthy_full, previously_held = c->timer_hold_confirmed;')
replace('sm_policy_reason_is_thermal(reason)));','sm_policy_reason_is_thermal(reason)), c->timer_hold_since_ns);')
replace('''				(!c->auto_requested || c->gauge_charge_stop || sm_policy_reason_is_thermal(reason));
			if (!ret) ret = c->stop_error;''','''				(!c->auto_requested || c->gauge_charge_stop || sm_policy_reason_is_thermal(reason));
			if (c->timer_hold_confirmed && !previously_held)
				c->timer_hold_since_ns = ktime_get_boottime_ns();
			if (!ret) ret = c->stop_error;''')
with (HERE/'samurai-mp2650.c').open('x') as f:f.write(source)
header=(OLD/'charge-cycle-hold.h').read_text().replace('int full_good, int confirmed_hold)','int full_good, int confirmed_hold, sm_cycle_ns held_since_ns)')
before='''	if (confirmed_hold && source == 1 && c->attached && !c->timed_out &&
	    now >= c->last_ns && c->anchor_ns <= c->last_ns)
		c->anchor_ns += now - c->last_ns;'''
after='''	sm_cycle_ns begin = held_since_ns > c->last_ns ? held_since_ns : c->last_ns;

	/* A stop can itself take time. Never exclude time before its readback.
	 * Repeated already-stopped polls retain the first confirmed timestamp.
	 */
	if (confirmed_hold && now < held_since_ns) {
		c->timed_out = 1;
		c->seconds = SM_CYCLE_LIMIT_SECONDS;
		return c->seconds;
	}
	if (confirmed_hold && source == 1 && c->attached && !c->timed_out &&
	    now >= begin && now >= c->last_ns && c->anchor_ns <= c->last_ns)
		c->anchor_ns += now - begin;'''
assert header.count(before)==1;header=header.replace(before,after)
with (HERE/'charge-cycle-hold.h').open('x') as f:f.write(header)
test=(OLD/'test-step.inc').read_text()
import re
test=re.sub(r'(sm_cycle_update_held\([^;\n]+), ([01])\)',r'\1, \2, 0)',test)
point='\tprintf("{\\"actual_step_sequences'
assert test.count(point)==1
extra='''	/* A slow successful stop is charged to active time, once. */
	sequences++;
	initialize(&c, &bus);bus.stop_delay_ns = NS(2);
	f = normal();f.sample.gauge_flags = 0x4000;
	CHECK(at(&c, 10, f) == -EAGAIN && c.timer_hold_confirmed && clock_ns == NS(12));
	CHECK(c.timer_hold_since_ns == NS(12));
	CHECK(at(&c, 43210, f) == -EAGAIN && c.sample.session_seconds == 12);
	CHECK(c.timer_hold_since_ns == NS(12));
	CHECK(at(&c, 43220, f) == -EAGAIN && c.sample.session_seconds == 12);
	CHECK(at(&c, 43221, normal()) == 0 && c.sample.session_seconds == 12 && enabled(&bus));
'''
test=test.replace(point,extra+'\n'+point)
with (HERE/'test-step.inc').open('x') as f:f.write(test)
runner=(OLD/'test.py').read_text().replace('charge-timer-hold-tests-03','charge-timer-hold-tests-04')
runner=runner.replace('struct sm_reattach_observation reattach;', 'struct sm_reattach_observation reattach;\\n\\tu64 timer_hold_since_ns;')
needle="test=prefix+(HERE/'test-step.inc').read_text()"
assert runner.count(needle)==1
runner=runner.replace(needle,"prefix=prefix.replace('int fail_stop_write;', 'int fail_stop_write;\\n\\tu64 stop_delay_ns;')\nprefix=prefix.replace('b->regs[reg] = value;', 'if (reg == 8 && (value & 0x18) == 8) clock_ns += b->stop_delay_ns;\\n\\tb->regs[reg] = value;')\n"+needle)
with (HERE/'test.py').open('x') as f:f.write(runner)
builder=(OLD/'build-ko.py').read_text().replace('charge-timer-hold-module-01','charge-timer-hold-module-02').replace('charge-timer-hold-module-private-01','charge-timer-hold-module-private-02')
with (HERE/'build-ko.py').open('x') as f:f.write(builder)
result=json.loads((OLD/'source-result.json').read_bytes())
result.update(candidate_C_sha256=sha(source.encode()),previous_offline_module_superseded='04ff91ca8f0a8a2312522df0c6f21218b877c18f150004c70050ffc8f4176fe4',stop_readback_timestamp_accounted=True,installed=False)
with (HERE/'source-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
baseline=(HERE.parent/'charger-reattach-observation-candidate/samurai-mp2650.c').read_text()
patch=''.join(difflib.unified_diff(baseline.splitlines(True),source.splitlines(True),fromfile='a/samurai-mp2650.c',tofile='b/samurai-mp2650.c'))
patch+=''.join(difflib.unified_diff([],header.splitlines(True),fromfile='/dev/null',tofile='b/charge-cycle-hold.h'))
with (HERE/'timer-hold.patch').open('x') as f:f.write(patch)
print(json.dumps(dict(prepared=True,previous_r1_preserved=True,phone_accessed=False)))
