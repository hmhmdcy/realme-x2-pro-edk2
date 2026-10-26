"""Exercise actual sensor power/stream bodies against API outcomes, not copies."""
from pathlib import Path
import hashlib
import json
import resource
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel235')
out = P / 'imx319-fault-tests-r2'
out.mkdir(mode=0o700)
source = (R / 'imx319.c').read_text()
power = source[source.index('static int imx319_power_off('):source.index('static int imx319_runtime_resume(')]
stream = source[source.index('static int imx319_set_stream('):source.index('static const struct v4l2_subdev_core_ops')]
prefix = (R / 'imx319-fault-prefix.c').read_text()
prefix = prefix.replace('/* IMX319_DEFINES */', '\n'.join(line for line in source.splitlines() if line.startswith('#define IMX319_')))
main = (R / 'imx319-fault-main.c').read_text()
tables = (R / 'imx319-oem-tables.h').read_text() + '''
static const struct imx319_reg_list host_global = { 136, imx319_oem_global_regs };
static const struct imx319_mode host_mode = { { 171, imx319_oem_mode_regs } };
static const struct imx319_profile host_profile = { &host_global };
'''
write_regs = source[source.index('static int imx319_write_regs('):source.index('static int imx319_open(')]
real_start = source[source.index('static int imx319_identify_module('):source.index('static int imx319_set_stream(')]
body = prefix + '\n' + tables + power + write_regs + real_start + stream + main
variants = {'actual': body}
mutations = {
    'no-sticky-gate': ('imx319->power_fault || imx319->vana_enabled', 'imx319->vana_enabled'),
    'no-put-after-stop': ('cleanup_ret = pm_runtime_put_sync_suspend(imx319->dev);\n\t\telse {', 'cleanup_ret = 0;\n\t\telse {'),
    'ignore-reset-release': ('ret = gpiod_set_value_cansleep(imx319->reset_gpio, 0);',
                             'gpiod_set_value_cansleep(imx319->reset_gpio, 0); ret = 0;'),
    'standby-without-identity': ('cleanup_ret = imx319->identified ? imx319_stop_streaming(imx319) : 0;',
                                'cleanup_ret = imx319_stop_streaming(imx319);'),
}
for name, (a, b) in mutations.items():
    assert body.count(a) == 1
    variants[name] = body.replace(a, b)
def no_core():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
results = {}
for name, text in variants.items():
    path = out / (name + '.c')
    path.write_text(text)
    binary = path.with_suffix('')
    build = subprocess.run(['gcc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', '-Wno-misleading-indentation',
                            '-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            str(path), '-o', str(binary)], capture_output=True)
    (out / (name + '-compile-private.log')).write_bytes(build.stdout + build.stderr)
    assert build.returncode == 0, build.stderr.decode()[-2000:]
    run = subprocess.run([str(binary)], capture_output=True, preexec_fn=no_core)
    (out / (name + '-run-private.log')).write_bytes(run.stdout + run.stderr)
    if name == 'actual':
        assert run.returncode == 0 and not run.stderr, run.stderr.decode()[-2000:]
        results[name] = json.loads(run.stdout)
    else:
        assert run.returncode != 0 and b'Assertion' in run.stderr
        results[name] = dict(rejected=True, exit=run.returncode)
report = dict(stage=235, source_sha256=hashlib.sha256(source.encode()).hexdigest(),
              actual_power_stream_identify_table_writer_functions_extracted=True, asan_ubsan_passed=True,
              results=results, pm_reference_and_rail_count_model=True,
              gpio_pinctrl_clock_rail_failure_outcomes=True,
              both_failed_and_mismatching_identity_have_zero_sensor_writes=True,
              all_308_configuration_write_failure_positions_tested=True,
              no_real_kernel_concurrency_or_probe_devres_model=True, no_phone_operation=True)
(R / 'imx319-fault-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
