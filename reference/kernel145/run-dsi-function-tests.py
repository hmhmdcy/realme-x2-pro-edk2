from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

root = Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel145')
out = Path('/mnt/e/edk2-samurai-out/kernel145')
assert not (ref / 'actual-function-test-validation.json').exists()
names = ['dsi_err_worker', 'dsi_ack_err_status', 'dsi_timeout_status', 'dsi_dln0_phy_err',
         'dsi_fifo_status', 'dsi_status', 'dsi_clk_status', 'dsi_error', 'dsi_host_irq']
before = (out / 'dsi-host-before-private.c').read_text()
candidate = (out / 'dsi-host-candidate-private.c').read_text()

def function(text, name):
    match = re.search(r'^static[^;{}]*\b' + name + r'\([^;{}]*\)\n\{', text, re.M)
    assert match, name
    depth = 1
    end = match.end()
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[match.start():end]

effects = {}
results = {}
definitions = before + '\n' + (root / 'drivers/gpu/drm/msm/generated/dsi.xml.h').read_text()
for label, text in [('baseline144', before), ('candidate145', candidate)]:
    directory = out / ('host-tests-' + label + '-private')
    directory.mkdir(mode=0o700)
    functions = '\n\n'.join(function(text, name) for name in names)
    tokens = sorted(set(re.findall(r'\b(?:REG_)?DSI_[A-Z0-9_]+\b', functions)))
    constants = []
    for token in tokens:
        match = re.search(r'^#define\s+' + token + r'\s+(0x[0-9a-fA-F]+|[0-9]+)\s*$', definitions, re.M)
        assert match, token
        constants.append('#define ' + token + ' ' + match[1])
    (directory / 'dsi-generated-functions.h').write_text('\n'.join(constants) + '\n\n' + functions + '\n')
    for mode in ['plain', 'asan-ubsan']:
        executable = directory / ('test-' + mode)
        args = ['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter', '-g',
                '-I', str(directory), str(ref / 'test-dsi-observation.c'), '-o', str(executable)]
        if label == 'baseline144':
            args.append('-DBASELINE144')
        if mode == 'asan-ubsan':
            args += ['-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie']
        build = subprocess.run(args, capture_output=True, text=True)
        (directory / (mode + '-compile-private.txt')).write_text(build.stdout + build.stderr)
        assert build.returncode == 0, label + ' ' + mode + ' compile failed'
        env = os.environ.copy()
        env['ASAN_OPTIONS'] = 'detect_leaks=1:abort_on_error=1'
        env['UBSAN_OPTIONS'] = 'halt_on_error=1'
        run = subprocess.run([str(executable)], capture_output=True, text=True, env=env, timeout=20)
        (directory / (mode + '-run-private.txt')).write_text(run.stdout + run.stderr)
        assert run.returncode == 0 and not run.stderr, label + ' ' + mode + ' run failed'
        match = re.fullmatch(r'DSI actual-function cases passed: 24; hardware-effect signature: ([0-9a-f]+)\n', run.stdout)
        assert match
        effects[label + '-' + mode] = match[1]
        results[label + '-' + mode] = dict(cases=24, returncode=0, compiler_diagnostics_empty=not build.stdout and not build.stderr,
                                          sanitizer_diagnostics_empty=True)
assert len(set(effects.values())) == 1
report = dict(stage=145, actual_driver_functions_extracted=names, candidate_cases=24,
              results=results, baseline_candidate_hardware_effect_signatures_identical=True,
              existing_reads_writes_clear_reset_irq_and_completion_order_preserved=True,
              raw_ack_captured_even_with_legacy_zero_aggregate_flag=True,
              raw_status_zero_and_mixed_unknown_bits_checked=True,
              worker_start_and_end_bracket_reset_and_irq_restore=True,
              disabled_tracing_and_no_error_irq_checked=True,
              actual_functions_tested=True, build_tree_modified=False, deployed=False,
              limits='Host MMIO and worker models; unchanged reset/intr-control callees are stubs. Real traces, timing, loss and display acceptance still required.',
              candidate_source_sha256=hashlib.sha256(candidate.encode()).hexdigest(), goal_complete=False)
(ref / 'actual-function-test-validation.json').write_text(json.dumps(report, indent=2) + '\n')
meta = json.loads((ref / 'source-preparation-validation.json').read_text())
meta['actual_functions_tested'] = True
(ref / 'source-preparation-validation.json').write_text(json.dumps(meta, indent=2) + '\n')
print('K145_24_ACTUAL_DSI_CASES_BASELINE_CANDIDATE_MMIO_EFFECTS_IDENTICAL_PLAIN_ASAN_UBSAN')
