"""Generate a local review candidate only. Never edit the charging reference."""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'charging-management-20261023/samurai-mp2650.c'
raw = SOURCE.read_text()
text = raw


def replace(old, new):
    global text
    if text.count(old) != 1:
        raise ValueError('integration anchor changed; inspect current source: ' + old[:100])
    text = text.replace(old, new)


replace('#include "mp2650-core.h"', '#include "mp2650-core.h"\n#include "charge-cycle.h"')
replace('bool auto_requested, latched, paused, session;',
        'bool auto_requested, latched, paused, sample_full;')
replace('ktime_t session_start, sampled_at;',
        'ktime_t sampled_at;\n\tstruct sm_charge_cycle cycle;')
replace('c->source_inhibit = false;', 'c->source_inhibit = false;\n\tc->sample_full = false;')
replace('''		c->session = false;''',
        '''		sm_cycle_update(&c->cycle, ktime_get_boottime_ns(), 0, 0);''')
replace('''	if (!c->session) {
		c->session_start = ktime_get_boottime();
		c->session = true;
	}
	s->session_seconds = ktime_to_ms(ktime_sub(ktime_get_boottime(),
						 c->session_start)) / 1000;
''', '')
replace('''	s->valid = 1;
	return 0;''', '''	c->sample_full = (status & 0x0c) == 0x0c;
	s->valid = 1;
	return 0;''')
replace('''	struct sm_target target = { 0 };
	int ret;

	ret = sm_collect(c, &c->sample);
	c->sampled_at = ktime_get_boottime();''', '''	struct sm_target target = { 0 }, validation_target;
	int ret, validation, source;

	ret = sm_collect(c, &c->sample);
	c->sampled_at = ktime_get_boottime();
	/* Full starts a new OEM charge period only after every other policy
	 * predicate has succeeded. Do not let Full clear an existing hard latch.
	 */
	validation = ret;
	if (!validation)
		validation = sm_policy(&c->sample, c->cell_ceiling_uv,
				       c->current_cap_ua, c->input_cap_ua,
				       &validation_target);
	source = c->sample.online ? 1 : !ret && c->sample.valid ? 0 : -1;
	c->sample.session_seconds = sm_cycle_update(&c->cycle,
		ktime_get_boottime_ns(), source,
		sm_cycle_full_allowed(c->sample_full, c->latched, validation));''')
replace('mutex_init(&c->lock);',
        'mutex_init(&c->lock);\n\tsm_cycle_init(&c->cycle, ktime_get_boottime_ns());')
(HERE / 'samurai-mp2650.candidate.c').write_text(text)
patch = ''.join(difflib.unified_diff(raw.splitlines(True), text.splitlines(True),
                                  fromfile='a/samurai-mp2650.c', tofile='b/samurai-mp2650.c'))
(HERE / 'charger-cycle.patch').write_text(patch)
(HERE / 'integration-source.json').write_text(json.dumps({
    'input': str(SOURCE), 'input_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'candidate_sha256': hashlib.sha256(text.encode()).hexdigest(),
    'original_edited': False, 'phone_accessed': False,
    'intended_use': 'Review only; root session may integrate with concurrent temperature fixes',
}, indent=2) + '\n')
print('candidate and patch exported; original unchanged')
