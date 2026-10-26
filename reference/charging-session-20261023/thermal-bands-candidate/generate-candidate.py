"""Generate a minimal independent r6 delta; never writes the frozen source."""
from pathlib import Path
import hashlib
import json
import shutil

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / 'kernel-v2'
receipt = json.loads((BASE / 'test-result.json').read_text())
names = list(receipt['candidate_files'])
before = {n: hashlib.sha256((BASE / n).read_bytes()).hexdigest() for n in names}
assert before == receipt['candidate_files'], 'frozen v2 differs from reviewed receipt'
(HERE / 'baseline').mkdir(exist_ok=True)
for name in names:
    shutil.copyfile(BASE / name, HERE / 'baseline' / name)
    shutil.copyfile(BASE / name, HERE / name)

def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)

core = (HERE / 'mp2650-core.h').read_text()
start = core.index('enum sm_thermal_hold')
end = core.index('/* The existing cell target', start)
core = core[:start] + '#include "thermal-bands.h"\n\n' + core[end:]
core = replace(core, 'static inline int sm_policy_with_reason(', 'static inline int sm_policy_with_band_reason(')
core = replace(core, 'int current_cap_ua, int input_cap_ua,\n\t\t\t   struct sm_target *out, enum sm_policy_reason *reason)',
               'int current_cap_ua, int input_cap_ua, int band,\n\t\t\t   struct sm_target *out, enum sm_policy_reason *reason)')
old = '\tcell_max = s->cell1_uv > s->cell2_uv ? s->cell1_uv : s->cell2_uv;'
core = replace(core, old, '''\t/* One OEM effective status selects CC/CV/OVP and Full/recharge. The
\t * immutable original temperature stop still has priority above this.
\t */
\tif (band != SM_POLICY_STATIC_BAND) {
\t\tif (band < 0 || band >= 6) {
\t\t\t*reason = SM_POLICY_REASON_TEMPERATURE;
\t\t\treturn -ERANGE;
\t\t}
\t\tb = &sm_oem_bands[band];
\t}
''' + old)
point = '/* Compatibility wrapper: existing callers retain their return codes. */'
wrapper = '''/* Stateless compatibility entry point for existing callers/tests. The
 * driver uses sm_policy_with_band_reason with its single live thermal state.
 */
static inline int sm_policy_with_reason(const struct sm_sample *s, int cell_ceiling_uv,
\t\t\t   int current_cap_ua, int input_cap_ua,
\t\t\t   struct sm_target *out, enum sm_policy_reason *reason)
{
\treturn sm_policy_with_band_reason(s, cell_ceiling_uv, current_cap_ua,
\t\t\tinput_cap_ua, SM_POLICY_STATIC_BAND, out, reason);
}

'''
core = replace(core, point, wrapper + point)
(HERE / 'mp2650-core.h').write_bytes(core.encode())

full = (HERE / 'oem-full-cycle.h').read_text()
full = replace(full, '\tint temp_decic, max_cell_uv, gauge_current_ua, cell_target_uv;',
               '\tint temp_decic, max_cell_uv, gauge_current_ua, cell_target_uv;\n\tint policy_band_valid, policy_band;')
full = replace(full, '\tif (!in->valid || !in->policy_good || !in->protection_good ||\n\t    (band = sm_oem_full_band(in->temp_decic)) < 0 ||',
'''\t/* Legacy callers may use the raw lookup. The live driver supplies the
\t * same effective band used by its already validated policy target.
\t */
\tband = in->policy_band_valid ? in->policy_band : sm_oem_full_band(in->temp_decic);
\tif (!in->valid || !in->policy_good || !in->protection_good ||
\t    sm_oem_full_band(in->temp_decic) < 0 || band < 0 || band >= 6 ||''')
(HERE / 'oem-full-cycle.h').write_bytes(full.encode())

c = (HERE / 'samurai-mp2650.c').read_text()
c = replace(c, '\t\tc->thermal.hold = SM_THERMAL_NONE;', '\t\tc->thermal = (struct sm_thermal_state){ 0 };')
c = replace(c, '''\t\tthermal_hold = sm_thermal_gate(&c->thermal, c->sample.temp_decic, 1);
\t\tif (!validation && thermal_hold)''', '''\t\tthermal_hold = sm_thermal_gate(&c->thermal, c->sample.temp_decic, 1);
\t\t/* Re-evaluate the complete policy against that same effective band.
\t\t * Only fresh non-hard-failing samples can advance this history.
\t\t */
\t\tvalidation = sm_policy_with_band_reason(&c->sample, c->cell_ceiling_uv,
\t\t\tc->current_cap_ua, c->input_cap_ua, c->thermal.band,
\t\t\t&validation_target, &reason);
\t\tif (!validation && thermal_hold)''')
c = replace(c, '\t\t.temp_decic = c->sample.temp_decic,',
'''\t\t.temp_decic = c->sample.temp_decic,
\t\t.policy_band_valid = 1,
\t\t.policy_band = c->thermal.initialized ? c->thermal.band : SM_POLICY_STATIC_BAND,''')
c = replace(c, '''\t\tret = sm_policy_with_reason(&c->sample, c->cell_ceiling_uv,
\t\t\t\tc->current_cap_ua, c->input_cap_ua, &target, &reason);''',
'''\t\tret = sm_policy_with_band_reason(&c->sample, c->cell_ceiling_uv,
\t\t\tc->current_cap_ua, c->input_cap_ua,
\t\t\tc->thermal.initialized ? c->thermal.band : SM_POLICY_STATIC_BAND,
\t\t\t&target, &reason);''')
c = replace(c, 'thermal_inhibit=%d cycle_timeout=%d ', 'thermal_inhibit=%d thermal_band=%d band_pre_shake=%d cycle_timeout=%d ')
c = replace(c, '\t\tc->source_inhibit, c->thermal_reason, c->cycle.timed_out,',
'''\t\tc->source_inhibit, c->thermal_reason,
\t\tc->thermal.initialized ? c->thermal.band : SM_POLICY_STATIC_BAND,
\t\tc->thermal.initialized ? c->thermal.pre_shake : SM_THERMAL_PRE_INVALID,
\t\tc->cycle.timed_out,''')
(HERE / 'samurai-mp2650.c').write_bytes(c.encode())
(HERE / 'baseline.json').write_text(json.dumps(before, indent=2) + '\n')
assert before == {n: hashlib.sha256((BASE / n).read_bytes()).hexdigest() for n in names}
print(json.dumps({'generated': True, 'frozen_v2_unchanged': True, 'files': names + ['thermal-bands.h']}))
