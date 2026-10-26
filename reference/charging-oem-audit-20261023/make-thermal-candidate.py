"""Build an isolated candidate; never edits the production charging directory."""
from pathlib import Path
import difflib
import hashlib
import json

root = Path(__file__).resolve().parent
production = root.parent / 'charging-management-20261023'
candidate = root / 'thermal-candidate'
candidate.mkdir(exist_ok=True)
old = (production / 'mp2650-core.h').read_text()
old_sha = hashlib.sha256((production / 'mp2650-core.h').read_bytes()).hexdigest()
expected = json.loads((root / 'audit.json').read_text())['files']['core']['sha256']
assert old_sha == expected, 'Core changed since OEM audit; rebase explicitly'

helper = '''enum sm_policy_reason {
\tSM_POLICY_REASON_NONE,
\tSM_POLICY_REASON_TEMPERATURE,
\tSM_POLICY_REASON_BAND_OVP,
};

static inline int sm_policy_reason_is_thermal(enum sm_policy_reason reason)
{
\treturn reason == SM_POLICY_REASON_TEMPERATURE ||
\t\treason == SM_POLICY_REASON_BAND_OVP;
}

enum sm_thermal_hold { SM_THERMAL_NONE, SM_THERMAL_COLD, SM_THERMAL_HOT };
struct sm_thermal_state { enum sm_thermal_hold hold; };

/* OEM outer-boundary recovery hysteresis: 2 C (oplus_charger.c 4174-4266).
 * Only eligible fresh samples may update history. The caller first evaluates
 * all non-thermal errors; a thermal hold must never conceal an IO/hard fault.
 * This deliberately preserves the existing strict half-open stop boundaries.
 */
static inline int sm_thermal_gate(struct sm_thermal_state *state,
\t\t\t\t  int temp_decic, int eligible)
{
\tconst int cold = sm_oem_bands[0].low;
\tconst int hot = sm_oem_bands[sizeof(sm_oem_bands) /
\t\t\t\t       sizeof(sm_oem_bands[0]) - 1].high;

\tif (!eligible)
\t\treturn state->hold != SM_THERMAL_NONE;
\tif (temp_decic < cold)
\t\tstate->hold = SM_THERMAL_COLD;
\telse if (temp_decic >= hot)
\t\tstate->hold = SM_THERMAL_HOT;
\telse if ((state->hold == SM_THERMAL_COLD && temp_decic < cold + 20) ||
\t\t (state->hold == SM_THERMAL_HOT && temp_decic > hot - 20))
\t\treturn 1;
\telse
\t\tstate->hold = SM_THERMAL_NONE;
\treturn state->hold != SM_THERMAL_NONE;
}

'''
new = old.replace('/* The existing cell target is an upper ceiling, never an inferred safe target. */',
                  helper + '/* The existing cell target is an upper ceiling, never an inferred safe target. */', 1)
new = new.replace('static inline int sm_policy(const struct sm_sample *s, int cell_ceiling_uv,',
                  'static inline int sm_policy_with_reason(const struct sm_sample *s, int cell_ceiling_uv,', 1)
new = new.replace('int current_cap_ua, int input_cap_ua,\n\t\t\t   struct sm_target *out)',
                  'int current_cap_ua, int input_cap_ua,\n\t\t\t   struct sm_target *out, enum sm_policy_reason *reason)', 1)
new = new.replace('\tconst struct sm_band *b = 0;\n\n\t*out',
                  '\tconst struct sm_band *b = 0;\n\tenum sm_policy_reason unused;\n\n\tif (!reason) reason = &unused;\n\t*reason = SM_POLICY_REASON_NONE;\n\t*out', 1)
new = new.replace('\tfor (i = 0; i < sizeof(sm_oem_bands)',
                  '\t/* A globally invalid target ceiling must not be hidden by a\n'
                  '\t * simultaneous temperature or band-voltage inhibit. */\n'
                  '\tif (cell_ceiling_uv < 3712500)\n\t\treturn -ERANGE;\n'
                  '\tfor (i = 0; i < sizeof(sm_oem_bands)', 1)
new = new.replace('\tif (!b)\n\t\treturn -ERANGE;',
                  '\tif (!b) {\n\t\t*reason = SM_POLICY_REASON_TEMPERATURE;\n\t\treturn -ERANGE;\n\t}', 1)
new = new.replace('\tif (cell_max > b->cell_ovp_uv)\n\t\treturn -EOVERFLOW;',
                  '\tif (cell_max > b->cell_ovp_uv) {\n\t\t*reason = SM_POLICY_REASON_BAND_OVP;\n\t\treturn -EOVERFLOW;\n\t}', 1)
new = new.replace('static inline int sm_update(',
                  '''/* Compatibility wrapper: existing callers retain their return codes. */
static inline int sm_policy(const struct sm_sample *s, int cell_ceiling_uv,
\t\t\t   int current_cap_ua, int input_cap_ua,
\t\t\t   struct sm_target *out)
{
\treturn sm_policy_with_reason(s, cell_ceiling_uv, current_cap_ua,
\t\t\t\t     input_cap_ua, out, 0);
}

static inline int sm_update(''', 1)
assert new.count('sm_policy_with_reason(') == 2
assert new.count('enum sm_policy_reason *reason)') == 1
(candidate / 'mp2650-core.h').write_bytes(new.encode('utf-8'))
for name in ('oem-profile.h', 'test-core.c'):
    (candidate / name).write_bytes((production / name).read_bytes())
label = 'reference/charging-management-20261023/mp2650-core.h'
patch = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                  fromfile='a/' + label, tofile='b/' + label))
(root / 'thermal-core.patch').write_bytes(patch.encode('utf-8'))
(root / 'thermal-base.json').write_text(json.dumps({
    'base_core_sha256': old_sha,
    'candidate_core_sha256': hashlib.sha256((candidate / 'mp2650-core.h').read_bytes()).hexdigest(),
    'production_sources_modified': False,
}, indent=2) + '\n')
print('isolated thermal candidate prepared')
