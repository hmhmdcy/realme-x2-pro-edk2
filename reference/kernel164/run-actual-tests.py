from pathlib import Path
import hashlib, json, subprocess

repo = Path('/home/cy122/edk2-samurai/repo')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel164')
out = Path('/mnt/e/edk2-samurai-out/kernel164')
source = repo / 'Platform/RenegadePkg/Library/PlatformBootManagerLib/PlatformBm.c'
text = source.read_text()
start = text.index('#define SAMURAI_PANEL_RESET_CONFIG')
end = text.index('//\n// SAMURAI: where the mainline Linux kernel lives', start)
helpers = text[start:end]
template = (ref / 'test-firmware-handoff.c').read_text()
test = out / 'actual-firmware-functions-private.c'
test.write_text(template.replace('/* ACTUAL_HELPERS */', helpers))
include = '-I' + str(repo / 'Silicon/Qualcomm/QcomPkg/Include')
results = []
for label, flags in [('normal', ['-O2']), ('asan-ubsan', ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-no-pie'])]:
    exe = out / ('test-' + label)
    build = subprocess.run(['gcc', '-std=gnu17', '-Wall', '-Wextra', '-Werror', '-Wno-unused-variable', include] + flags + [str(test), '-o', str(exe)], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode == 0 and '14 actual firmware-helper scenarios passed' in run.stdout, run.stdout + run.stderr
    results.append(dict(label=label, exit=run.returncode, scenarios=14))
negatives = []
for label, old, new in [('wrong-polarity', 'GPIO_LOW_VALUE', 'GPIO_HIGH_VALUE'),
                        ('wrong-exit-group', '&gEfiEventBeforeExitBootServicesGuid', '&wrong_exit_group')]:
    negative = out / (label + '-private.c')
    negative.write_text(template.replace('/* ACTUAL_HELPERS */', helpers.replace(old, new)))
    exe = out / ('test-' + label)
    subprocess.run(['gcc', '-std=gnu17', '-O2', include, str(negative), '-o', str(exe)], check=True)
    run = subprocess.run([str(exe)], capture_output=True, text=True)
    assert run.returncode != 0
    negatives.append(dict(label=label, rejected=True))
report = dict(stage=164, actual_firmware_helpers_extracted=True, actual_protocol_header_used=True,
              results=results, negative_controls=negatives,
              prepare_and_no_exit_return_do_not_touch_gpio=True,
              callback_config_then_physical_low_once=True,
              protocol_revision_function_event_and_error_paths_checked=True,
              callback_group_before_boot_services_shutdown=True,
              protocol_size48_and_gpioout_offset32_verified=True,
              source_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
(ref / 'actual-function-test-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
