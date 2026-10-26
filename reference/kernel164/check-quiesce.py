from pathlib import Path
import argparse
import json
import os
import subprocess

p=argparse.ArgumentParser();p.add_argument('--record',action='store_true');a=p.parse_args()
before=Path('/var/lib/samurai/k164-preflash')
out=Path('/var/lib/samurai/k164-quiesce')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert os.uname().version.startswith('#163 ')
assert boot==(before / 'boot-id-private.txt').read_text().strip()
assert boot==(out / 'boot-id-private.txt').read_text().strip()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
prior=(before / 'dmesg-private.txt').read_text()
current=subprocess.check_output(['dmesg'],text=True)
assert current.count('gpu fault:')==prior.count('gpu fault:')==0
assert current.count('WARNING:')==prior.count('WARNING:')==0
assert not subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode==0
for n in range(3): assert Path('/sys/class/remoteproc/remoteproc%d/state'%n).read_text().strip()=='offline'
clients=Path('/sys/kernel/debug/dri/1/clients').read_text()
assert len(clients.splitlines())==1
assert 'active=1' not in Path('/sys/kernel/debug/dri/1/state').read_text()
report=dict(stage=164,boot_id=boot,quiesce_audit_pass=True,
    gui_user_and_drm_crtcs_quiesced=True,all_remoteprocs_offline=True,
    no_drm_userspace_clients=True,taint=0,current_kernel=163,target_kernel=163,
    known_baseline_gpu_faults=0,no_new_gpu_faults=True,
    dma_prepare_before=prior.count('unable to prepare channel'),
    dma_prepare_after=current.count('unable to prepare channel'))
if a.record: (out / 'quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K164_CURRENT163_QUIESCE_VALIDATED')
