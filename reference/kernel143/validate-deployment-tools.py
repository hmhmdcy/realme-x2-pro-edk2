from pathlib import Path
import ast
import json
import subprocess

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
path=ref/'verify-quiesce.py'
text=path.read_text()
assert text.count('target_kernel=140')==1
path.write_text(text.replace('target_kernel=140','target_kernel=143'))
for file in ref.glob('*.py'):ast.parse(file.read_text())
for file in ref.glob('*.sh'):subprocess.run(['bash','-n',str(file)],check=True)
assert "'^#143 '" in ref.joinpath('collect-runtime.sh').read_text()
assert "version.startswith('#143 ')" in ref.joinpath('capture-next-startup.py').read_text()
assert "version.startswith('#143 ')" in ref.joinpath('check-new-boot.py').read_text()
assert "version.startswith('#143 ')" in ref.joinpath('remove-completed-recorder.py').read_text()
assert 'current_kernel=143' in ref.joinpath('capture-next-startup.py').read_text()
assert "report['current_kernel'] == 143" in ref.joinpath('verify-startup-irq-idle.py').read_text()
assert "b'#143 SMP'" in ref.joinpath('verify-runtime.py').read_text()
assert "= '#140'" in ref.joinpath('install-early-recorder.sh').read_text()
assert 'kernel142/embedded-boot-id-private.txt' in ref.joinpath('verify-preflash.py').read_text()
report=dict(stage=143,current_kernel_before_flash=140,target_kernel=143,
    early_recorder_expected_new143=True,preflash_and_quiesce_guard_old140=True,
    python_parse_and_shell_syntax_pass=True,postboot_runtime_guard_new143=True,
    source_boot_from_actual142=True,goal_complete=False)
ref.joinpath('deployment-tools-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K143_OLD140_NEW143_DEPLOYMENT_TOOL_IDENTITIES_AND_SYNTAX_CHECKED')
