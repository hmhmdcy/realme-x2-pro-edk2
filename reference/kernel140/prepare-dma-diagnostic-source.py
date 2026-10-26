from pathlib import Path
import difflib
import hashlib
import json
import os
import subprocess

r = Path('/mnt/e/RealmeX2Pro edk2')
ref = r / 'reference/kernel140'
out = Path('/mnt/e/edk2-samurai-out/kernel140')
k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
assert os.geteuid() == 0 and not out.exists()
assert hashlib.sha256((k / 'arch/arm64/boot/Image').read_bytes()).hexdigest() == '0b9ff8f7e186dab43497daa5fdd4bf18a77d43cf2ac25774358ee35c32498aa7'
manifest = json.loads((r / 'reference/kernel139/unwind-source-validation.json').read_text())
assert all(hashlib.sha256((k / name).read_bytes()).hexdigest() == digest for name, digest in manifest['files'].items())
out.mkdir(mode=0o700)
(out / 'source139-before-private.patch').write_bytes(subprocess.check_output(['git', '-C', str(k), 'diff', '--binary']))

def replace(t, old, new):
    assert t.count(old) == 1, old
    return t.replace(old, new)

changes = {}
name = 'drivers/slimbus/qcom-ngd-ctrl.c'
old = (k / name).read_text()
new = replace(old, '\tif (!desc->desc) {\n\t\t/* tx_lock serializes reservations; this slot was never queued. */',
              '\tif (!desc->desc) {\n'
              '\t\tstruct dma_chan *chan = ctrl->dma_tx_channel;\n'
              '\t\tstruct dma_device *dma = chan ? chan->device : NULL;\n\n'
              '\t\tdev_err_once(ctrl->dev,\n'
              '\t\t\t     "TX DMA diagnostic: state=%d qmi=%d channel=%d device=%d sg=%d config_sg=%d len=%d\\n",\n'
              '\t\t\t     ctrl->state, !!ctrl->qmi.handle, !!chan, !!dma,\n'
              '\t\t\t     dma && !!dma->device_prep_slave_sg,\n'
              '\t\t\t     dma && !!dma->device_prep_config_sg, len);\n'
              '\t\t/* tx_lock serializes reservations; this slot was never queued. */')
new = replace(new, '\tif (ret && ret != -EBUSY)\n\t\tdev_info(ctrl->dev, "slim resource not idle:%d\\n", ret);',
              '\tif (ret)\n'
              '\t\tdev_info_once(ctrl->dev,\n'
              '\t\t\t      "NGD suspend rejected: ret=%d state=%d tx_channel=%d rx_channel=%d\\n",\n'
              '\t\t\t      ret, ctrl->state, !!ctrl->dma_tx_channel,\n'
              '\t\t\t      !!ctrl->dma_rx_channel);\n'
              '\tif (ret && ret != -EBUSY)\n\t\tdev_info(ctrl->dev, "slim resource not idle:%d\\n", ret);')
changes[name] = (old, new)
name = 'drivers/dma/qcom/bam_dma.c'
old = (k / name).read_text()
new = replace(old, '\tif (!async_desc)\n\t\treturn NULL;',
              '\tif (!async_desc) {\n'
              '\t\tdev_err_once(bdev->dev,\n'
              '\t\t\t     "BAM DMA diagnostic: allocation failed count=%u sg_len=%u len=%u direction=%d\\n",\n'
              '\t\t\t     num_alloc, sg_len, sg_dma_len(sgl), direction);\n'
              '\t\treturn NULL;\n\t}')
changes[name] = (old, new)
patch = []
for name, (old, new) in changes.items():
    (out / (Path(name).name + '.139-before-private')).write_text(old)
    (k / name).write_text(new)
    patch.extend(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/' + name, tofile='b/' + name))
(ref / 'dma-first-failure-diagnostics.patch').write_text(''.join(patch))
check = subprocess.run(['perl', str(k / 'scripts/checkpatch.pl'), '--no-signoff', '--ignore', 'COMMIT_MESSAGE', str(ref / 'dma-first-failure-diagnostics.patch')], capture_output=True)
(out / 'checkpatch-private.txt').write_bytes(check.stdout + check.stderr)
assert check.returncode == 0
report = dict(stage=140, baseline=139, software_generation=132,
              diagnostic_only_addition=True, no_suspend_order_change=True,
              no_dma_allocation_policy_change=True, no_gpu_display_charge_change=True,
              unwind139_preserved=True, source139_archived=True,
              only_new_changed_files=list(changes), checkpatch_code_errors=0, checkpatch_code_warnings=0,
              files={name: hashlib.sha256(new.encode()).hexdigest() for name, (_, new) in changes.items()},
              diagnostic_runtime_not_yet_seen=True, goal_complete=False)
(ref / 'dma-diagnostic-source-validation.json').write_text(json.dumps(report, indent=2) + '\n')
# Preserve runtime-compatible bundle generation, with independent fresh candidate artifacts.
t = (r / 'reference/kernel139/build-unwind-kernel.sh').read_text().replace('kernel139', 'kernel140').replace('modules-root139', 'modules-root140').replace('VERSION=139', 'VERSION=140').replace('unwind-', 'dma-diagnostic-').replace('K139', 'K140')
t = t.replace('host-fault-injection-validation.json', 'dma-diagnostic-source-validation.json').replace('drivers/slimbus/messaging.o', 'drivers/dma/qcom/bam_dma.o')
(ref / 'build-diagnostic-kernel.sh').write_text(t)
t = (r / 'reference/kernel139/record-unwind-build.py').read_text().replace('kernel139', 'kernel140').replace('modules-root139', 'modules-root140').replace('#139', '#140').replace('k139', 'k140').replace('unwind-', 'dma-diagnostic-').replace('stage=139, kernel_build=139', 'stage=140, kernel_build=140')
t = t.replace('baseline132_only_two_slimbus_files_changed=True', 'diagnostic_only_addition_to139=True')
t = t.replace('logdump-k140-unwind.img', 'logdump-k140-dma-diagnostic.img')
(ref / 'record-diagnostic-build.py').write_text(t)
print('K140_FIRST_NULL_AND_SUSPEND_REJECTION_DIAGNOSTICS_SOURCE_READY')
