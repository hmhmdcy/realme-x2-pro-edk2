from pathlib import Path
import hashlib, json, subprocess

kernel = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel163')
out = Path('/mnt/e/edk2-samurai-out/kernel163')
source = kernel / 'drivers/pinctrl/qcom/pinctrl-sm8150.c'
candidate = source.read_text()
baseline = (out / 'source-before-private.c').read_text()
def extract(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]
functions = extract(candidate, 'static void sm8150_samurai_reset_boot_panel(') + '\n\n'
functions += extract(candidate, 'static int sm8150_pinctrl_probe(')
template = (ref / 'test-early-reset.c').read_text()
test = out / 'actual-functions-private.c'
test.write_text(template.replace('/* ACTUAL_FUNCTIONS */', functions))
results = []
for label, flags in [('normal', ['-O2']), ('asan-ubsan', ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie'])]:
    exe = out / ('test-' + label)
    build = subprocess.run(['gcc', '-std=gnu17', '-Wall', '-Wextra', '-Werror'] + flags + [str(test), '-o', str(exe)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0 and '14 actual-function scenarios passed' in run.stdout, run.stdout + run.stderr
    results.append(dict(label=label, exit=run.returncode, scenarios=14))
negative = out / 'negative-baseline-private.c'
negative.write_text(template.replace('/* ACTUAL_FUNCTIONS */', extract(baseline, 'static int sm8150_pinctrl_probe(')))
exe = out / 'test-negative'
subprocess.run(['gcc', '-std=gnu17', '-O2', str(negative), '-o', str(exe)], check=True)
run = subprocess.run([str(exe)], capture_output=True, text=True)
assert run.returncode != 0
report = dict(stage=163, actual_helper_and_probe_extracted=True, results=results,
              board_panel_controller_pin_and_polarity_guards_verified=True,
              controller_must_be_ready_before_gpio_acquisition=True,
              logical_assertion_drives_active_low_reset=True,
              descriptor_and_of_references_balanced_on_all_paths=True,
              native_panel_can_reacquire_reset_descriptor=True,
              gpio_failure_does_not_fail_controller_probe=True,
              baseline_negative_control_rejected=True,
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(ref / 'actual-function-test-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
