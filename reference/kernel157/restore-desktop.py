"""Restore the configured initial session after the output removal crash."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, time
os.umask(0o077)
out = Path('/var/lib/samurai/k157-desktop-recovery')
assert not out.exists()
assert os.uname().version.startswith('#157 ')
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert boot == Path('/var/lib/samurai/k157-first-startup/boot-id-private.txt').read_bytes()
assert subprocess.run(['pgrep','-x','phosh'],capture_output=True).returncode == 1
config = Path('/etc/greetd/samurai-phosh.toml')
before = config.read_bytes()
assert b'[initial_session]' in before and b'user = "cy122"' in before
marker = Path('/run/greetd.run')
assert marker.is_file() and marker.stat().st_size == 0
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
shutil.copy2(config,out/'config-before-private.toml')
shutil.copy2(marker,out/'marker-before')
shutil.copy2('/home/cy122/.local/state/samurai-phosh-session.log',out/'failed-session-private.log')
for action in ['stop','start']:
    if action == 'start':
        assert not subprocess.run(['pgrep','-x','phoc'],capture_output=True).stdout
        marker.unlink()
    r=subprocess.run(['rc-service','greetd',action],capture_output=True,timeout=25)
    (out/(action+'-private.log')).write_bytes(r.stdout+r.stderr)
    r.check_returncode()
    if action == 'stop': time.sleep(1)
for _ in range(30):
    if subprocess.run(['pgrep','-x','phosh'],capture_output=True).returncode == 0: break
    time.sleep(1)
report=dict(same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,
    configuration_unchanged=config.read_bytes()==before,
    phosh_present=subprocess.run(['pgrep','-x','phosh'],capture_output=True).returncode==0,
    phoc_present=subprocess.run(['pgrep','-x','phoc'],capture_output=True).returncode==0,
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    existing_initial_session_restored=True, kernel_rebooted=False)
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert all(report[x] for x in ['same_boot','configuration_unchanged','phosh_present','phoc_present'])
