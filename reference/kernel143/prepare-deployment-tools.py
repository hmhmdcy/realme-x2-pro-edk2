from pathlib import Path
import ast
import json

root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel143'
base=root/'reference/kernel142'
build=json.loads(ref.joinpath('threaded-console-build-package-validation.json').read_text())
assert build['kernel_build']==143 and build['kernel_build_no_warnings'] and build['host_actual_function_cases']==16
assert not ref.joinpath('collect-preflash.sh').exists()
def adapted(name):
    return base.joinpath(name).read_text().replace('kernel142','kernel143').replace('k142','k143').replace('K142','K143').replace('stage=142','stage=143')
def write(name,text):
    assert not ref.joinpath(name).exists()
    if name.endswith('.py'):ast.parse(text)
    ref.joinpath(name).write_text(text)

text=adapted('collect-preflash.sh').replace('/var/lib/samurai/k141-first-runtime/boot-id-private.txt','/var/lib/samurai/k142-first-runtime/boot-id-private.txt')
text=text.replace('FRESH139_PREFLASH','FRESH140_PREFLASH')
write('collect-preflash.sh',text)
text=adapted('verify-preflash.py').replace("kernel141/embedded-boot-id-private.txt","kernel142/embedded-boot-id-private.txt")
write('verify-preflash.py',text)
for name in ['quiesce-current140.sh','verify-quiesce.py','freeze-for-bootloader.sh','enable-transition-eud.ps1','enter-bootloader.ps1']:
    write(name,adapted(name).replace('irq-first','eud-thread-first'))
for name in ['check-new-boot.py','poll-new-boot.ps1','capture-next-startup.py','peek-recorder.py','k142-startup-trace',
    'install-early-recorder.sh','verify-recorder-install.py','remove-completed-recorder.py',
    'collect-runtime.sh','verify-runtime.py','observe-settled-health.py','verify-startup-irq-idle.py']:
    text=adapted(name)
    if name!='install-early-recorder.sh':
        text=text.replace("'#140 '","'#143 '").replace("'#140'","'#143'").replace("b'#140 SMP'","b'#143 SMP'")
        text=text.replace("'^#140 '","'^#143 '").replace('new140_boot_verified','new143_boot_verified')
    text=text.replace('reboot140-startup','first143-startup').replace('NEW140','NEW143').replace('CURRENT140','CURRENT143')
    text=text.replace('current_kernel=140','current_kernel=143').replace('kernel_build=140','kernel_build=143')
    text=text.replace("report['current_kernel'] == 140","report['current_kernel'] == 143")
    text=text.replace('current140-build-package-validation.json','threaded-console-build-package-validation.json')
    if name=='verify-runtime.py':
        text=text.replace('boot132_and_logdump140_readback_exact','boot132_and_logdump143_readback_exact')
        text=text.replace('diagnostic_only_addition_to139=True','eud_nbcon_threaded_normal_output=True')
    if name=='verify-recorder-install.py':
        text=text.replace('kernel_build=143','kernel_build=143,installed_on_current140=True')
    write(name.replace('k142','k143'),text)
text=root.joinpath('reference/kernel140/flash-diagnostic-logdump.ps1').read_text()
text=text.replace('kernel140','kernel143').replace('dma-first','eud-thread-first').replace('dma-diagnostic','threaded-console').replace('k140','k143').replace('K140','K143')
text=text.replace('$build.diagnostic_only_addition_to139','$build.eud_nbcon_threaded_normal_output')
text=text.replace('stage=140','stage=143').replace('kernel_build=140','kernel_build=143')
text=text.replace('DMA_DIAGNOSTIC_LOGDUMP','THREADED_CONSOLE_LOGDUMP')
text=text.replace("if (!$build.eud_nbcon_threaded_normal_output", "if ($build.host_actual_function_cases -ne 16 -or !$build.kernel_build_no_warnings -or !$build.eud_nbcon_threaded_normal_output")
needle="$image=\"$out/logdump-k143-threaded-console.img\""
assert needle in text
text=text.replace(needle,"$recorder=Get-Content -Raw -LiteralPath \"$out/early-recorder-install-validation.json\" | ConvertFrom-Json\nif (!$recorder.installed_recorder_three_files_exact -or !$recorder.one_new_boot_only) {throw 'Early startup recorder install receipt missing'}\n"+needle)
write('flash-threaded-console-logdump.ps1',text)
print('K143_FRESH140_PREFLIGHT_AND_NEW143_BOOT_CAPTURE_TOOLS_PREPARED')
