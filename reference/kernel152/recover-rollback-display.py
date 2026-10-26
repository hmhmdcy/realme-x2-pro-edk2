"""One bounded panel reprobe and recovery of the configured desktop session."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,time
os.umask(0o077)
before=Path('/var/lib/samurai/k152-rollback147-failure')
out=Path('/var/lib/samurai/k152-rollback147-display-recovery')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#147 ')
assert boot==(before/'boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert not Path('/dev/dri').exists() and not out.exists()
assert not subprocess.run(['pgrep','-x','phosh'],capture_output=True).stdout
assert not subprocess.run(['pgrep','-x','phoc'],capture_output=True).stdout
panel=Path('/sys/bus/mipi-dsi/devices/ae94000.dsi.0')
assert not (panel/'driver').exists()
assert 'OF_COMPATIBLE_0=samsung,sofef03f-m\n' in (panel/'uevent').read_text()
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
config=Path('/etc/greetd/samurai-phosh.toml')
config_before=config.read_bytes()
assert b'[initial_session]' in config_before and b'user = "cy122"' in config_before
shutil.copy2(config,out/'config-before-private.toml')
def run(args,name,timeout=20):
    r=subprocess.run(args,capture_output=True,timeout=timeout)
    (out/name).write_bytes(r.stdout+r.stderr)
    r.check_returncode()
run(['timeout','20','sh','-c','printf "%s" ae94000.dsi.0 > /sys/bus/mipi-dsi/drivers/panel-samsung-sofef03f/bind'],'panel-bind.txt',25)
assert Path('/dev/dri/renderD128').exists() and (panel/'driver').exists()
run(['rc-service','greetd','stop'],'greetd-stop.txt')
assert not subprocess.run(['pgrep','-x','phoc'],capture_output=True).stdout
marker=Path('/run/greetd.run')
if marker.exists():
    assert marker.is_file() and marker.stat().st_size==0
    shutil.copy2(marker,out/'marker-before')
    marker.unlink()
run(['rc-service','greetd','start'],'greetd-start.txt')
for _ in range(30):
    if subprocess.run(['pgrep','-u','10000','-x','phosh'],capture_output=True).stdout:break
    time.sleep(1)
log=subprocess.check_output(['dmesg'],text=True)
(out/'dmesg-private.txt').write_text(log)
report=dict(kernel_build=147,same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,
    single_panel_reprobe=True,configuration_unchanged=config.read_bytes()==config_before,
    drm_restored=Path('/dev/dri/renderD128').exists(),
    desktop={n:bool(subprocess.run(['pgrep','-u','10000','-x',n],capture_output=True).stdout) for n in ['phoc','phosh']},
    taint=int(Path('/proc/sys/kernel/tainted').read_text()),
    startup_bug_not_fixed=True,mesa149_fix_preserved=hashlib.sha256(Path('/usr/lib/libvulkan_freedreno.so').read_bytes()).hexdigest()=='97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e')
(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
assert report['drm_restored'] and all(report['desktop'].values()) and report['taint']==0
