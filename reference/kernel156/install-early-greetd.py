"""Order the graphical session before the existing radio observation wait."""
from pathlib import Path
import hashlib,json,os,re,subprocess
os.umask(0o077)
assert os.uname().version.startswith('#154 ')
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/tmp/k156-source-boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k156-boot-order')
assert not out.exists();out.mkdir(mode=0o700)
p=Path('/etc/conf.d/greetd');before=p.read_bytes()
assert hashlib.sha256(before).hexdigest()=='386b72683466c261ddd59159ea2ccfa5e6a91a3944b794392fc4b503f0521f2f'
radio=Path('/usr/sbin/samurai-wifi')
radio_sha=hashlib.sha256(radio.read_bytes()).hexdigest()
bluetooth=Path('/usr/share/dbus-1/system-services/org.bluez.service')
assert re.search(r'^Exec=/bin/false$',bluetooth.read_text(),re.M)
assert not any(re.search(r'^Name=org\.freedesktop\.NetworkManager$',f.read_text(),re.M)
    for f in Path('/usr/share/dbus-1/system-services').glob('*.service'))
(out/'greetd-conf-before-private').write_bytes(before)
(out/'boot-id-private.txt').write_bytes(Path('/proc/sys/kernel/random/boot_id').read_bytes())
after=before+b'\n# Start the desktop while the radio readiness observation continues.\nrc_before="samurai-radio"\n'
try:
    p.write_bytes(after)
    r=subprocess.run(['rc-update','-u'],capture_output=True,text=True,timeout=30)
    (out/'dependency-update-private.txt').write_text(r.stdout+r.stderr)
    r.check_returncode()
    tree=Path('/run/openrc/deptree').read_text()
    idx=re.search(r"^depinfo_(\d+)_service='greetd'$",tree,re.M)[1]
    assert re.search(r"^depinfo_"+idx+r"_ibefore_\d+='samurai-radio'$",tree,re.M)
    assert hashlib.sha256(radio.read_bytes()).hexdigest()==radio_sha
except BaseException:
    p.write_bytes(before)
    subprocess.run(['rc-update','-u'],capture_output=True,timeout=30)
    raise
result=dict(stage=156,greetd_conf_before_sha256=hashlib.sha256(before).hexdigest(),
    greetd_conf_after_sha256=hashlib.sha256(after).hexdigest(),
    dependency_edge_confirmed='greetd before samurai-radio',radio_script_unchanged=True,
    bluetooth_dbus_activation_disabled_preserved=True,networkmanager_has_no_early_dbus_activation=True,
    initial_session_and_vt_unchanged=True,current_services_not_restarted=True,next_boot_timing_validation_pending=True)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
