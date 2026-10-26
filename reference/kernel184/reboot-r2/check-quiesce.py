from pathlib import Path
import argparse
import json
import os
import re
import subprocess

p=argparse.ArgumentParser();p.add_argument('--record',action='store_true');a=p.parse_args()
before=Path('/var/lib/samurai/k184r2-preflash')
out=Path('/var/lib/samurai/k184r2-quiesce')
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert os.uname().version.startswith('#183 ')
assert boot==(before / 'boot-id-private.txt').read_text().strip()
assert boot==(out / 'boot-id-private.txt').read_text().strip()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
prior=(before / 'dmesg-private.txt').read_text()
current=subprocess.check_output(['dmesg'],text=True)
assert current.count('gpu fault:')==prior.count('gpu fault:')==0
assert current.count('WARNING:')==prior.count('WARNING:')==0
assert current.count('SLIMBUS_0_RX: ASoC error (-22)')==prior.count('SLIMBUS_0_RX: ASoC error (-22)')==0
assert current.count('Oops:')==prior.count('Oops:')==0
# Preserve old kernel181 audio faults; quiesce proof uses actual offline/resource state.
assert not subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode==0
for n in range(3): assert Path('/sys/class/remoteproc/remoteproc%d/state'%n).read_text().strip()=='offline'
clients=Path('/sys/kernel/debug/dri/1/clients').read_text()
assert len(clients.splitlines())==1
assert 'active=1' not in Path('/sys/kernel/debug/dri/1/state').read_text()
cutoff=float((before/'start-uptime-private.txt').read_text().split()[0])
patterns={'irq_read':'Failed to read IRQ status', 'irq_config':'Failed to write config',
          'irq_mask':'Failed to sync masks', 'pdr_timeout':'register listener txn wait failed', 'asoc':'ASoC error'}
window='\n'.join(line for line in current.splitlines() if (m:=re.match(r'^\[\s*(\d+\.\d+)\]',line)) and float(m[1])>=cutoff)
(out/'quiesce-audio-faults-private.json').write_text(json.dumps({'cutoff':cutoff,'faults':{key:window.count(value) for key,value in patterns.items()}},indent=2)+'\n')
report=dict(stage=184,boot_id=boot,quiesce_audit_pass=True,
    gui_user_and_drm_crtcs_quiesced=True,all_remoteprocs_offline=True,
    no_drm_userspace_clients=True,taint=0,current_kernel=183,target_kernel=183,
    known_baseline_gpu_faults=0,no_new_gpu_faults=True,
    dma_prepare_before=prior.count('unable to prepare channel'),
    dma_prepare_after=current.count('unable to prepare channel'))
if a.record: (out / 'quiesce-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K183_CURRENT181_QUIESCE_VALIDATED')
