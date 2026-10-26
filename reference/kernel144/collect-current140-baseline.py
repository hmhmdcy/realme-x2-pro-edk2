from pathlib import Path
import hashlib
import json
import os
import subprocess
out=Path('/var/lib/samurai/k144-current140')
boot=Path('/var/lib/samurai/k143-rollback140-runtime/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#140 ') and not out.exists()
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
out.mkdir(mode=0o700);out.joinpath('boot-id-private.txt').write_bytes(boot)
def capture(args,name,check=True):
    with out.joinpath(name).open('w') as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=check,timeout=25)
for path,name in [('/sys/kernel/debug/clk/clk_summary','clocks-private.txt'),('/sys/kernel/debug/dri/1/state','drm-state-private.txt'),('/sys/kernel/debug/dri/1/encoder-0/status','encoder-private.txt'),('/proc/interrupts','interrupts-private.txt'),('/proc/uptime','uptime.txt'),('/proc/sys/kernel/tainted','taint.txt')]:capture(['cat',path],name)
capture(['dmesg'],'dmesg-private.txt')
text=out.joinpath('dmesg-private.txt').read_text()
report=dict(stage=144,current_kernel=140,same_boot=True,read_only=True,
    taint=int(out.joinpath('taint.txt').read_text()),
    display_active='active=1' in out.joinpath('drm-state-private.txt').read_text(),
    counts={name:text.count(pattern) for name,pattern in [('gpu','gpu fault:'),('dpu','frame done timeout'),('dsi','dsi_err_worker'),('warn','WARNING:'),('dma','unable to prepare channel')]},
    goal_complete=False)
out.joinpath('baseline-validation.json').write_text(json.dumps(report,indent=2)+'\n')
out.joinpath('SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  ./'+p.name+'\n' for p in sorted(out.iterdir()) if p.is_file()))
subprocess.run(['tar','-C',str(out),'-czf','/tmp/k144-current140-private.tar.gz','.'],check=True,timeout=20)
print(json.dumps(report,indent=2))
