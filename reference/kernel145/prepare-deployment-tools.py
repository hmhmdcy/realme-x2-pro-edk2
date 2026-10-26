"""Create fresh145 deployment tools from reviewed definitions; no device action."""
from pathlib import Path
import ast
import json
import subprocess

root = Path('/mnt/e/RealmeX2Pro edk2')
ref = root / 'reference/kernel145'
base = root / 'reference/kernel143'
bundle = json.loads((ref / 'dsi-observation-build-package-validation.json').read_text())
assert bundle['kernel_build'] == 145 and bundle['all_770_modules_byte_identical132']
assert bundle['fresh145_module_install_verified'] and bundle['host_actual_function_cases'] == 24
assert bundle['eud_handoff_actual_function_cases'] == 26 and not bundle['deployed']


def replace(text, before, after):
    assert before in text, before
    return text.replace(before, after)


def adapted(name):
    text = (base / name).read_text()
    for old, new in [('kernel143', 'kernel145'), ('k143', 'k145'), ('K143', 'K145'),
                     ('stage=143', 'stage=145'), ('kernel_build=143', 'kernel_build=145'),
                     ('current_kernel=143', 'current_kernel=145'), ("'#143 ", "'#145 "),
                     ("b'#143 SMP", "b'#145 SMP"), ("'^#143 ", "'^#145 "),
                     ('first143', 'first145'), ('NEW143', 'NEW145'), ('CURRENT143', 'CURRENT145'),
                     ('new143', 'new145')]:
        text = text.replace(old, new)
    return text.replace('threaded-console-build-package-validation.json', 'dsi-observation-build-package-validation.json')


def write(name, text):
    path = ref / name
    assert not path.exists(), name
    if name.endswith('.py'):
        ast.parse(text)
    path.write_text(text)
    if name.endswith('.sh') or name == 'k145-startup-trace':
        subprocess.run(['sh', '-n', str(path)], check=True)


text = adapted('collect-preflash.sh')
text = replace(text, '/var/lib/samurai/k142-first-runtime/boot-id-private.txt', '/var/lib/samurai/k143-rollback140-runtime/boot-id-private.txt')
text = replace(text, 'dmesg > "$dest/dmesg.txt"', 'sha256sum -c /var/lib/samurai/k135-preflash/gui-config.sha256 > "$dest/gui-config-check.txt"\ndmesg > "$dest/dmesg.txt"')
write('collect-preflash.sh', text)
text = replace(adapted('verify-preflash.py'), 'kernel142/embedded-boot-id-private.txt', 'kernel143/embedded-boot-id-private.txt')
text = replace(text, "assert data['old132-module-check.txt'].count(b': OK') >= 770", "assert data['old132-module-check.txt'].count(b': OK') == 784\nassert data['gui-config-check.txt'].count(b': OK') == 3\nassert b'gpu fault:' not in data['dmesg.txt'] and b'WARNING:' not in data['dmesg.txt']")
write('verify-preflash.py', text)
text = adapted('quiesce-current140.sh')
needle = 'test "$(cat /proc/sys/kernel/tainted)" = 0'
assert text.count(needle) == 2
head, tail = text.rsplit(needle, 1)
write('quiesce-current140.sh', head + 'python3 /tmp/k145-check-quiesce-state.py --record' + tail)
text = replace(adapted('freeze-for-bootloader.sh'), '/tmp/k145-check-known-quiesce-warning.py', '/tmp/k145-check-quiesce-state.py')
write('freeze-for-bootloader.sh', text)
for name in ['enable-transition-eud.ps1', 'enter-bootloader.ps1']:
    write(name, adapted(name).replace('eud-thread-first', 'dsi-raw-first'))

text = adapted('flash-threaded-console-logdump.ps1').replace('eud-thread-first', 'dsi-raw-first')
text = replace(text, '$build.host_actual_function_cases -ne 16', '$build.host_actual_function_cases -ne 24 -or $build.eud_handoff_actual_function_cases -ne 26')
text = replace(text, '$build.eud_nbcon_threaded_normal_output', '$build.dsi_raw_state_trace_only -or !$build.eud_handoff144_preserved')
text = replace(text, "if ($q.taint -ne 512 -or !$q.known_warning_transition_only -or !$q.old_slimbus_warning_not_fixed -or $q.current_kernel -ne 140 -or $q.target_kernel -ne 143) {throw 'Exact old-kernel shutdown warning proof missing'}",
               "if (!$q.shutdown_state_validated -or $q.taint -notin 0,512 -or ($q.taint -eq 512 -and !$q.known_warning_transition_only) -or $q.current_kernel -ne 140 -or $q.target_kernel -ne 145) {throw 'Fresh old-kernel shutdown proof missing'}")
text = replace(text, 'logdump-k145-threaded-console.img', 'logdump-k145-dsi-observation.img')
write('flash-dsi-observation-logdump.ps1', text)
for name in ['check-new-boot.py', 'poll-new-boot.ps1', 'capture-next-startup.py', 'k143-startup-trace',
             'install-early-recorder.sh', 'verify-recorder-install.py', 'peek-recorder.py',
             'remove-completed-recorder.py', 'collect-runtime.sh', 'verify-runtime.py']:
    text = adapted(name)
    if name == 'capture-next-startup.py':
        text = replace(text, "events += [('drm', n)", "events += [('drm_msm_dsi', n) for n in ['msm_dsi_error_irq', 'msm_dsi_error_status', 'msm_dsi_error_work']]\nevents += [('drm', n)")
    if name == 'verify-runtime.py':
        text = text.replace('boot132_and_logdump143_readback_exact', 'boot132_and_logdump145_readback_exact')
        text = replace(text, 'eud_nbcon_threaded_normal_output=True', 'eud_handoff144_preserved=True, dsi_raw_state_trace_only=True')
    write(name.replace('k143', 'k145'), text)
report = dict(stage=145, fresh_current140_identity_from_rollback143=True,
              fresh145_preflash_and_quiesce_paths=True, one_new_boot_only=True,
              startup_recorder_three_new_dsi_events=True,
              existing_dpu_irq_idle_events_preserved=True, python_and_shell_syntax_pass=True,
              only_logdump_flash_planned=True, old143_actions_not_replayed=True,
              recorder_removal_required=True, phone_modified=False, deployed=False,
              goal_complete=False)
(ref / 'deployment-tools-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K145_FRESH_CURRENT140_DEPLOYMENT_TOOLS_PREPARED_NOT_EXECUTED')
