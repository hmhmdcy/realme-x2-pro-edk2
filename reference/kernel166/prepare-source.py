from pathlib import Path
import hashlib, json, os, shutil, subprocess, tarfile, re

k = Path('/home/cy122/pmos-samurai-kernel136/kernel')
out = Path('/mnt/e/edk2-samurai-out/kernel166')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel166')
assert os.geteuid() == 0 and not out.exists()
assert not subprocess.check_output(['git','diff','--binary'], cwd=k)
out.mkdir(mode=0o700)
names = ['drivers/slimbus/qcom-ngd-ctrl.c','drivers/slimbus/messaging.c']
for name in names:
    shutil.copyfile(k/name, out/(Path(name).name+'.163-before-private'))
shutil.copyfile(k/'.config', out/'config-before-private')
shutil.copyfile(k/'arch/arm64/boot/Image', out/'Image-before-k163-private')
(out/'baseline-commit.txt').write_bytes(subprocess.check_output(['git','rev-parse','HEAD'],cwd=k))
with tarfile.open(out.parent/'kernel164/first-evidence-private.tar.gz') as archive:
    member=next(x for x in archive.getmembers() if x.name.endswith('dmesg-before-private.txt'))
    log=archive.extractfile(member).read().decode()
diagnostic=re.search(r'TX DMA diagnostic: state=(\d+) qmi=(\d+) channel=(\d+) device=(\d+).*',log)
report=dict(stage=166, historical_failed_boot=164, dma_prepare_failures=log.count('unable to prepare channel'),
            first_failure_state=int(diagnostic[1]), qmi_handle_present=bool(int(diagnostic[2])),
            tx_channel_present=bool(int(diagnostic[3])), wakeup_failed_before_first_dma_failure=True,
            suspend_rejection_logged=False, original_source_archived=True,
            baseline_commit=(out/'baseline-commit.txt').read_text().strip(),
            historical_archive_sha256=hashlib.sha256((out.parent/'kernel164/first-evidence-private.tar.gz').read_bytes()).hexdigest())
assert report['dma_prepare_failures']==917 and report['first_failure_state']==3 and not report['tx_channel_present']
assert 'NGD suspend rejected' not in log
assert log.index('HW wakeup attempt during SSR')<log.index('TX DMA diagnostic')<log.index('WARNING:')
for folder in [ref,out]:
    (folder/'historical-evidence-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
