"""Compile the exact current board plus lens draft; validate only changed dependencies."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('schema_validate_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
shared = storage.mount.mounted_build()
source = shared.parent / 'kernel453-lens-private/source-view'
output = shared.parent / 'kernel453-lens-private/O/schema'
private = Path('/mnt/e/edk2-samurai-out/kernel453/schema')
output.mkdir(exist_ok=True); private.mkdir(exist_ok=True)
tools = Path('/home/cy122/x2pro-linux/.venv-dtschema/bin')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
inputs = [HERE / 'bu64253.c', HERE / 'rohm,bu64253.yaml', HERE / 'samurai-bu64253-lenses.dtsi',
          shared / '.config', shared / 'Module.symvers', shared / 'include/generated/autoconf.h',
          source / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts']
before = {str(p):sha(p) for p in inputs}

def run(name, command, timeout=90):
    p = subprocess.run(command, capture_output=True, timeout=timeout)
    (private / (name + '-private.log')).write_bytes(p.stdout + p.stderr)
    return dict(exit=p.returncode, diagnostic_bytes=len(p.stdout + p.stderr))

relative = Path('Documentation/devicetree/bindings/media/i2c/rohm,bu64253.yaml')
canonical_original = output / 'canonical-original' / relative
canonical_original.parent.mkdir(parents=True, exist_ok=True)
canonical_original.write_bytes((HERE / 'rohm,bu64253.yaml').read_bytes())
original_doc = run('canonical-original-doc', [str(tools / 'dt-doc-validate'), str(canonical_original)])
candidate = output / 'candidate' / relative
candidate.parent.mkdir(parents=True, exist_ok=True)
text = (HERE / 'rohm,bu64253.yaml').read_text()
assert '\nmaintainers:' not in text
# Deliberate private, non-shipping placeholder. It is not a maintainer identity.
text = text.replace('\ndescription:', '\nmaintainers:\n  - Schema-only placeholder <schema-validation@example.invalid>\n\ndescription:', 1)
candidate.write_text(text)
candidate_doc = run('private-placeholder-doc', [str(tools / 'dt-doc-validate'), str(candidate)])
assert candidate_doc == dict(exit=0, diagnostic_bytes=0), candidate_doc

compiled = {}
for name, extra in [('baseline', ''), ('candidate', '#include "' + str(HERE / 'samurai-bu64253-lenses.dtsi') + '"\n')]:
    wrapper = output / (name + '-private.dts')
    wrapper.write_text('#include "' + str(source / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts') + '"\n' + extra)
    pp = output / (name + '-private.pp.dts')
    cpp = run(name + '-cpp', ['cpp', '-nostdinc', '-undef', '-D__DTS__', '-x', 'assembler-with-cpp',
                             '-I', str(source / 'scripts/dtc/include-prefixes'),
                             '-I', str(source / 'arch/arm64/boot/dts/qcom'), str(wrapper), '-o', str(pp)])
    assert cpp['exit'] == 0, cpp
    dtb = output / (name + '-private.dtb')
    dtc = run(name + '-dtc', ['dtc', '-I', 'dts', '-O', 'dtb', '-o', str(dtb), str(pp)])
    assert dtc['exit'] == 0, dtc
    yaml = output / (name + '-private.yaml')
    yaml_result = run(name + '-dtc-yaml', ['dtc', '-I', 'dts', '-O', 'yaml', '-o', str(yaml), str(pp)])
    assert yaml_result['exit'] == 0, yaml_result
    compiled[name] = dict(cpp=cpp, dtc=dtc, yaml=yaml_result, dtb_sha256=sha(dtb))

spec = importlib.util.spec_from_file_location('schema_fdt211', HERE.parent / 'kernel211/fdt_compare.py')
fdt = importlib.util.module_from_spec(spec); spec.loader.exec_module(fdt)
parse = fdt.parser()
old = parse((output / 'baseline-private.dtb').read_bytes())
new = parse((output / 'candidate-private.dtb').read_bytes())
delta = fdt.compare(old, new, output / 'candidate-private.yaml')
(private / 'board-delta-private.json').write_text(json.dumps(delta, indent=2) + '\n')
lenses = {p:props for p,props in new.items() if props.get('compatible') == b'rohm,bu64253' + bytes([0])}
assert len(lenses) == 2 and not delta['only_old_nodes'] and len(delta['only_new_nodes']) == 4, delta
changed = {(r['path'], r['property']) for r in delta['remaining_changed_properties']}
assert len(changed) == 2 and all(prop == 'lens-focus' for _,prop in changed), changed
handles = {props['phandle']:p for p,props in new.items() if 'phandle' in props}
relations = []
for lens, props in lenses.items():
    sensor = next(p for p,row in new.items() if row.get('lens-focus') == props['phandle'])
    regulator = handles[props['vdd-supply']]
    consumers = [(p,k) for p,row in new.items() for k,v in row.items() if k.endswith('-supply') and v == props['vdd-supply']]
    assert consumers == [(lens, 'vdd-supply')], consumers
    assert int.from_bytes(new[regulator]['regulator-min-microvolt'], 'big') == 2800000
    assert new[regulator]['regulator-max-microvolt'] == new[regulator]['regulator-min-microvolt']
    assert int.from_bytes(props['reg'], 'big') == 0x0c
    assert (sensor, 'lens-focus') in changed
    relations.append(dict(lens=lens, sensor=sensor, regulator=regulator, vdd_sole_consumer=True,
                          firmware_name=props['firmware-name'].rstrip(bytes([0])).decode()))

processed = output / 'schema453-private.json'
mk = run('schema-build', [str(tools / 'dt-mk-schema'), '-j', '-o', str(processed),
                          str(source / 'Documentation/devicetree/bindings'), str(candidate)], timeout=120)
assert mk['exit'] == 0, mk
validations = {}
for select in ['rohm,bu64253', 'qcom,pm8008', 'qcom,i2c-cci', 'sony,imx319', 'samsung,s5k3m5']:
    name = select.replace(',', '-')
    validations[select] = run('schema-' + name, [str(tools / 'dt-validate'), '-s', str(processed), '-l', select, str(output / 'candidate-private.dtb')])
assert {str(p):sha(p) for p in inputs} == before
warning_logs = [(private / (label + '-dtc-private.log')).read_bytes() for label in ['baseline', 'candidate']]
assert warning_logs[0] == warning_logs[1], 'Review changed dtc diagnostics'
report = dict(stage=453, scope='private candidate structural/dependency validation only; public binding metadata incomplete',
              original_public_binding_doc_valid=False, canonical_original_doc=original_doc,
              original_public_binding_submission_ready=False, live_enablement_ready=False,
              private_placeholder_doc=candidate_doc, placeholder_is_not_a_maintainer_or_submission=True,
              private_candidate_structural_validation_passed=True,
              public_binding_or_driver_or_dt_changed=False, dtc_compilations=compiled,
              baseline_and_candidate_dtc_diagnostics_identical=True,
              dtc_diagnostic_sha256=hashlib.sha256(warning_logs[0]).hexdigest(),
              no_removed_nodes=True, new_nodes=delta['only_new_nodes'], changed_existing_properties=sorted([list(x) for x in changed]),
              relations=relations, explicit_phandle_reference_cells_checked=delta['explicit_reference_cells_checked'],
              processed_schema=mk, targeted_dependency_validations=validations, shared_inputs_unchanged=True,
              sdk_or_phone_accessed=False, dts_deployed=False, actual_kernel_pm_or_hardware_verified=False,
              passed=all(v == dict(exit=0, diagnostic_bytes=0) for v in validations.values()))
(HERE / 'schema-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
