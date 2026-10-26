"""Bind retained source and validation receipts. Does not import or run candidates."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
CANDIDATE = REF / 'charging-oem-audit-20261023/apsd-pd5v-client-bridge-candidate'
PD_OLD = REF / 'charging-oem-audit-20261023/pd5v-owner-context-r2'
OWNER_OLD = REF / 'charging-session-20261023/apsd-session-owner-candidate'
read = lambda p: json.loads(p.read_bytes())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
delivery = read(CANDIDATE / 'delivery.json')
for name, digest in delivery['files'].items(): assert sha(CANDIDATE / name) == digest, name
assert sha(CANDIDATE / 'samurai-apsd-owner.c') == 'd05d4f81f8427cfbe7cd37c458b538d0ee60a2e9422c243cdf13fa6ba246d979'
assert sha(CANDIDATE / 'qcom_pmic_typec_5v.c') == 'b3b9a18e8c581a99f57083eeeadc9af9783c0e03b28cf60f1e796fd6d1558d52'
for path, digest in read(CANDIDATE / 'source-inputs.json').items(): assert sha(REF / path) == digest

def function(text, name):
    match = re.search(r'^[\w \t*]+\b' + re.escape(name) + r'\s*\([^;{}]*\)\s*\{', text, re.M)
    assert match, name
    # Preserve offsets while excluding braces in comments and C literals.
    masked = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'',
                    lambda m: ' ' * len(m.group()), text, flags=re.S)
    depth = 0
    for index in range(match.end() - 1, len(masked)):
        if masked[index] == '{': depth += 1
        elif masked[index] == '}':
            depth -= 1
            if depth == 0: return text[match.start():index + 1]
    raise ValueError(name)

old_pd = (PD_OLD / 'qcom_pmic_typec_5v.c').read_text()
new_pd = (CANDIDATE / 'qcom_pmic_typec_5v.c').read_text()
unchanged = read(CANDIDATE / 'unchanged-functions.json')
for name in unchanged['PD_R2_function_bodies']:
    assert function(old_pd, name) == function(new_pd, name), name
for name, digest in unchanged['DWC_files'].items():
    assert sha(CANDIDATE / name) == digest and (CANDIDATE / name).read_bytes() == (OWNER_OLD / name).read_bytes()
owner = (CANDIDATE / 'samurai-apsd-owner.c').read_text()
gate = function(owner, 'owner_entry_gate')
assert 'return -EOPNOTSUPP;' in gate and 'owner_enter_windows' not in gate
status = function(new_pd, 'qcom_pmic_typec_5v_status')
for forbidden in ['regmap_read(', 'regmap_write(', 'regmap_update_bits(', 'regulator_enable(', 'regulator_disable(']:
    assert forbidden not in status

test = read(CANDIDATE / 'test-result.json')
assert test['passed'] and test['exit_code'] == 0 and test['affected_groups'] == 14
for name, digest in test['tested_files'].items(): assert sha(CANDIDATE / name) == digest
fixture = CANDIDATE / 'test-private/actual-bridge.c'
assert sha(fixture) == test['actual_fixture_sha256']
clean = lambda text: '\n'.join(line for line in text.splitlines() if not line.startswith('#include')) + '\n'
actual_fixture = fixture.read_text()
assert clean(owner) in actual_fixture and clean(new_pd) in actual_fixture
assert (CANDIDATE / 'test-private/run.txt').read_text().splitlines() == test['groups']
assert (CANDIDATE / 'test-private/compile.txt').stat().st_size == 0
assert '-fsanitize=address,undefined' in test['compile_command'] and '-Werror' in test['compile_command']
build = read(CANDIDATE / 'build-result.json')
assert build['passed'] and build['shared_before'] == build['shared_after'] and build['shared_unchanged']
assert [(x['name'], x['returncode'], x['diagnostic_bytes']) for x in build['phases']] == [
    ('owner-current-m', 0, 0), ('owner-future-builtin', 0, 0)]
for name, digest in build['sources'].items(): assert sha(CANDIDATE / name) == digest
prior = CANDIDATE / 'history/build-before-abort-gates.json'
assert sha(prior) == build['unchanged_PD_object_reused']['receipt_sha256']
prior_build = read(prior)
assert prior_build['sources']['qcom_pmic_typec_5v.c'] == sha(CANDIDATE / 'qcom_pmic_typec_5v.c')
assert prior_build['sources']['qcom_pmic_typec_5v.h'] == sha(CANDIDATE / 'qcom_pmic_typec_5v.h')

result = {
    'scope': 'narrow bridge metadata/first-off/lease/sink and lifetime review, not full APSD authorization',
    'no_new_blocker_found': True,
    'delivery_sha256': sha(CANDIDATE / 'delivery.json'),
    'owner_sha256': sha(CANDIDATE / 'samurai-apsd-owner.c'),
    'metadata_source_sha256': sha(CANDIDATE / 'qcom_pmic_typec_5v.c'),
    'patch_sha256': sha(CANDIDATE / 'bridge.patch'),
    'reviewed': [
        'default-n plus explicit OF properties; current TYPEC_QCOM_PMIC=m refused',
        'metadata verifies exact bound typec and source parent/regmap; binding serial nonzero/nonreused/overflow refused',
        'metadata initialized is not lease or PD/route permission',
        'present-at-start waits first off; retained R2 fresh stable off/vSafe0 acquisition precedes sink eligibility',
        'binding rechecked after acquire; replacement cannot inherit prior prepared state',
        'sticky provider I/O errors remain FAILED; known blocked/no-error cancellation is distinguished',
        'real primary owner kref, PD quiesce extra pin, callback outside PD lock, registry-serialized join/release',
        'worker never takes owner registry; failed restore retains lease/tokens; late callback cannot access removed DWC',
        'once attempted history survives PM/UDC/provider rebind until actual detach',
        'unconditional EOPNOTSUPP still prevents analog windows and 1341 transfer'],
    'unchanged_PD_R2_functions_byte_equal': list(unchanged['PD_R2_function_bodies']),
    'unchanged_DWC_files_byte_equal': list(unchanged['DWC_files']),
    'validation': {'test_receipt_sha256': sha(CANDIDATE / 'test-result.json'),
                   'groups': 14, 'full_actual_owner_and_PD_bodies_in_retained_fixture': True,
                   'ASan_UBSan_Werror_receipt_bound': True, 'tests_rerun': False,
                   'build_receipt_sha256': sha(CANDIDATE / 'build-result.json'),
                   'two_final_owner_object_views_exit0_no_diagnostics': True,
                   'unchanged_metadata_object_original_receipt_bound': True,
                   'objects_not_recompiled_or_independently_read_here': True},
    'metadata_IO_scope': 'no direct bus/power operation; a last temporary reference concurrent with retirement can run existing pd5v_free/regulator_disable cleanup',
    'limits': ['deterministic fake boundaries do not prove every kernel interleaving',
               'no route/EUD/PHY withdrawal/final transfer permission; no native current or charging permission',
               'future builtin preprocessor object is not a linked or adopted configuration'],
    'device_SDK_build_mount_Git_used': False, 'source_or_Image501_modified': False,
    'candidate_deployed_or_physical_acceptance': False
}
(HERE / 'review.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'review_sha256': sha(HERE / 'review.json'), 'no_new_blocker_found': True}))
