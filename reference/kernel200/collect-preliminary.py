from pathlib import Path
import json,os,subprocess

root=Path('/var/lib/samurai');out=root/'k200-preliminary';assert not out.exists();out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();assert boot==(root/'k200-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert not Path('/sys/module/qcom_camss').exists()
assert subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode==1
assert len(Path('/sys/kernel/debug/dri/1/clients').read_text().splitlines())==1
assert all(p.read_text().strip()=='closed' for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'))
assert all('powered=0 muted=1' in Path('/sys/bus/i2c/devices/'+a+'/status').read_text() for a in ['1-0039','1-003a'])
rp={(p/'name').read_text().strip():(p/'state').read_text().strip() for p in Path('/sys/class/remoteproc').glob('remoteproc*')};assert rp==dict(adsp='running',slpi='offline',modem='running')
log=subprocess.check_output(['dmesg']);assert log.count(b'WARNING:')==3 and log.count(b'Oops:')==0 and log.count(b'gpu fault:')==0
r=dict(stage=200,boot_id=boot.decode().strip(),preliminary_quiesce_pass=True,taint=512,current_kernel=183,
    gui_and_camss_stopped=True,sensor_service_stopped=True,pcm_closed_and_amplifiers_muted=True,
    full_remoteproc_shutdown_pending=True,wifi_and_modemmanager_kept_for_management=True,remoteprocs=rp)
(out/'summary-private.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({k:v for k,v in r.items() if k!='boot_id'}))
