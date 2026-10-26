from pathlib import Path
import os,subprocess,time,hashlib,json
os.umask(0o077);out=Path('/var/lib/samurai/k148-desktop-recovery');out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes();(out/'boot-id-private.txt').write_bytes(boot)
config=Path('/etc/greetd/samurai-phosh.toml');before=config.read_bytes()
assert b'[initial_session]' in before and b'user = "cy122"' in before and b'/usr/local/bin/samurai-phosh-session' in before
assert not subprocess.run(['pgrep','-x','phosh'],stdout=subprocess.DEVNULL).returncode==0
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
marker=Path('/run/greetd.run');assert marker.is_file() and marker.stat().st_size==0
(out/'greetd-marker-backup').write_bytes(marker.read_bytes());(out/'config-private.toml').write_bytes(before)
with (out/'restart-private.log').open('wb') as f:
    subprocess.run(['rc-service','greetd','stop'],stdout=f,stderr=subprocess.STDOUT,check=True)
    for _ in range(20):
        if subprocess.run(['pgrep','-x','phoc'],stdout=subprocess.DEVNULL).returncode!=0:break
        time.sleep(.5)
    else:raise RuntimeError('Compositor did not stop; do not start a second one')
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
    assert marker.read_bytes()==b'';marker.unlink()
    subprocess.run(['rc-service','greetd','start'],stdout=f,stderr=subprocess.STDOUT,check=True)
for _ in range(40):
    if subprocess.run(['pgrep','-x','phosh'],stdout=subprocess.DEVNULL).returncode==0:break
    time.sleep(.5)
else:raise RuntimeError('Original Phosh session did not start')
assert config.read_bytes()==before
report=dict(original_config_preserved=True,original_initial_session_restored=True,boot_preserved=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,
    config_sha256=hashlib.sha256(before).hexdigest(),taint=Path('/proc/sys/kernel/tainted').read_text().strip())
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
