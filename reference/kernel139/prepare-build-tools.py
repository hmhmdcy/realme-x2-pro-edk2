from pathlib import Path
import ast

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel139'
base = r / 'reference/kernel137'
assert not (ref / 'build-unwind-kernel.sh').exists()
t = (base / 'build-audio-kernel.sh').read_text().replace('kernel137', 'kernel139').replace('137', '139').replace('audio-', 'unwind-').replace('K137_', 'K139_')
t = t.replace("test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel139/unwind-source-validation.json'", "test -f '/mnt/e/RealmeX2Pro edk2/reference/kernel139/host-fault-injection-validation.json'")
t = t.replace('drivers/mfd/wcd934x.o drivers/slimbus/qcom-ngd-ctrl.o drivers/dma/qcom/bam_dma.o', 'drivers/slimbus/qcom-ngd-ctrl.o drivers/slimbus/messaging.o')
(ref / 'build-unwind-kernel.sh').write_text(t)
t = (base / 'record-audio-build.py').read_text().replace('kernel137', 'kernel139').replace('modules-root137', 'modules-root139').replace('audio-', 'unwind-').replace('k137', 'k139').replace('#137', '#139').replace('stage=137, kernel_build=137', 'stage=139, kernel_build=139')
t = t.replace('upstream_mfd_cleanup_applied=True, dma_failure_diagnostics_added=True', 'unsubmitted_unwind_applied=True, baseline132_only_two_slimbus_files_changed=True, host_fault_injection_12_cases_pass=True')
t = t.replace("new_tracepoints=['msm_gpu_vm_update', 'msm_gpu_vm_switch_enqueue']", 'new_tracepoints=[]')
t = t.replace('unwind-cleanup', 'unwind').replace("Image-k139-unwind-private", "Image-k139-unwind-private")
ast.parse(t)
(ref / 'record-unwind-build.py').write_text(t)
print('K139_BUILD_AND_PACKAGE_TOOLS_PREPARED')
