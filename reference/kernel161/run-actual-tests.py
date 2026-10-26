from pathlib import Path
import hashlib, json, subprocess

kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel161')
out = Path('/mnt/e/edk2-samurai-out/kernel161')
source = kernel / 'drivers/iommu/arm/arm-smmu/arm-smmu.c'
baseline = (out / 'source-before-private.c').read_text()
candidate = source.read_text()
def extract(text):
    name = 'static void arm_smmu_rmr_install_bypass_smr('
    start = text.index(name)
    end = text.index('{', start)
    depth = 1
    end += 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]
actual = extract(candidate)
original = extract(baseline)
functions = original.replace('arm_smmu_rmr_install_bypass_smr', 'baseline_function', 1) + '\n\n'
functions += actual.replace('arm_smmu_rmr_install_bypass_smr', 'candidate_function', 1)
template = (ref / 'test-empty-rmr.c').read_text()
assert template.count('/* ACTUAL_FUNCTIONS */') == 1
test = out / 'actual-functions-private.c'
test.write_text(template.replace('/* ACTUAL_FUNCTIONS */', functions))
results = []
for label, flags in [('normal', ['-O2']), ('asan-ubsan', ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie'])]:
    exe = out / ('test-' + label)
    build = subprocess.run(['gcc', '-std=gnu17', '-Wall', '-Wextra', '-Werror'] + flags + [str(test), '-o', str(exe)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0 and '7 actual-function scenarios passed' in run.stdout, run.stdout + run.stderr
    results.append(dict(label=label, exit=run.returncode, scenarios=7))
negative = out / 'negative-baseline-private.c'
negative.write_text(template.replace('/* ACTUAL_FUNCTIONS */', original.replace('arm_smmu_rmr_install_bypass_smr', 'baseline_function', 1) + '\n\n' + original.replace('arm_smmu_rmr_install_bypass_smr', 'candidate_function', 1)))
exe = out / 'test-negative'
subprocess.run(['gcc', '-std=gnu17', '-O2', str(negative), '-o', str(exe)], check=True)
run = subprocess.run([str(exe)], capture_output=True, text=True)
assert run.returncode != 0
report = dict(stage=161, actual_kernel_function_extracted=True, empty_list_no_mmio_verified=True,
              nonempty_rmr_behavior_matches_baseline=True, results=results,
              baseline_negative_control_rejected=True, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(ref / 'actual-function-test-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
